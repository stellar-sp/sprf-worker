from stellar_base.horizon import Horizon
from db_manager import *
from exec_engine import *
from stellar_base.transaction import Transaction
from stellar_base.operation import ManageData
from stellar_base.transaction_envelope import TransactionEnvelope as Te
from stellar_base.keypair import Keypair
import json
import time
import base64
from stellar_base.exceptions import *
import logging

HORIZON_ADDRESS = os.environ.get('HORIZON_ADDRESS')
IPFS_ADDRESS = os.environ.get('IPFS_ADDRESS')
START_PAGING_TOKEN_CHECK = int(os.environ.get('START_PAGING_TOKEN_CHECK', 0))
WORKER_SECRET_KEY = os.environ.get('WORKER_SECRET_KEY')
REDIS_ADDRESS = os.environ.get("REDIS_ADDRESS")
NETWORK_PASSPHRASE = os.environ.get("NETWORK_PASSPHRASE")

db_manager = DbManager()
horizon = Horizon(HORIZON_ADDRESS)

operation_paging_token_number = int(db_manager.get_latest_checked_paging_token())
if operation_paging_token_number == 0:
    operation_paging_token_number = START_PAGING_TOKEN_CHECK
if operation_paging_token_number == 0:
    operation_paging_token_number = int(
        horizon.operations(order="asc", limit=1)["_embedded"]["records"][0]["paging_token"])

latest_ledger = horizon.ledgers(order='desc', limit=1)
TRANSACTION_BASE_FEE = latest_ledger['_embedded']['records'][0]['base_fee_in_stroops']


def add_account_if_smart(account_id):
    try:
        account = horizon.account(account_id)
    except HorizonError as e:
        if e.status_code == 404:
            return
        else:
            logging.error(e.message)

    if 'smart_program_image_address' not in account['data'] or 'execution_fee' not in account['data']:
        return

    # checking worker sign between signers
    found_signer = False
    for sig in account['signers']:
        if sig['key'] == Keypair.from_seed(WORKER_SECRET_KEY).address().decode() and sig['weight'] >= 1:
            found_signer = True
            break
    if not found_signer:
        return

    # checking master weight is zero
    for sig in account['signers']:
        if sig['key'] == account_id and sig['weight'] != 0:
            return

    # checking thresholds
    desired_weight = int((len(account['signers']) - 1) / 2) + 1
    if account['thresholds']['low_threshold'] != desired_weight or account['thresholds']['med_threshold'] != \
            desired_weight or account['thresholds']['high_threshold'] != desired_weight:
        return

    if 'latest_transaction_changed_state' not in account['data'] or 'current_state' not in account['data']:
        return

    db_manager.add_or_update_smart_account(account)


def create_transaction(smart_account, new_state_file_hash, latest_transaction_changed_state):
    operations = [
        ManageData(data_name='current_state', data_value=new_state_file_hash),
        ManageData(data_name='latest_transaction_changed_state', data_value=latest_transaction_changed_state)
    ]

    tx = Transaction(
        source=smart_account['id'],
        sequence=horizon.account(smart_account['id']).get('sequence'),
        fee=int(TRANSACTION_BASE_FEE) * len(operations),
        operations=operations
    )

    envelope = Te(tx=tx, network_id=NETWORK_PASSPHRASE)
    envelope.sign(Keypair.from_seed(WORKER_SECRET_KEY))
    return envelope


def check_transaction_if_smart(op):
    logging.info("checking operation. operation id: " + op['id'])
    transaction = horizon.transaction(op['transaction_hash'])

    smart_account = horizon.account(op['to'])

    execution_fee = float(base64.b64decode(smart_account['data']['execution_fee']).decode())

    if float(op['amount']) * 10000000 < execution_fee:
        logging.debug("transaction is not smart, because it has not sufficient fee. tx id: " + transaction['id'])
        return

    latest_transaction_hash = base64.b64decode(smart_account['data']['latest_transaction_changed_state']).decode()
    latest_transaction = horizon.transaction(latest_transaction_hash)
    if latest_transaction['paging_token'] >= transaction['paging_token']:
        logging.debug("transaction is old. because a newer transaction with paging token: " +
                      latest_transaction['paging_token'] + " changed the smart account state before")
        return

    if transaction['memo_type'] != 'hash':
        logging.debug("transaction is not smart. because it does not have memo. tx id: " + transaction['id'])
        return
    ipfs_utils = IpfsUtils()
    ipfs_hash = ipfs_utils.base58_to_ipfs_hash(transaction['memo'])
    with open(ipfs_utils.load_ipfs_file(ipfs_hash), 'r') as f:
        execution_config = json.load(f)

    # controlling concurrency between transactions
    base_state = execution_config['base_state']
    current_account_state = base64.b64decode(smart_account['data']['current_state']).decode()
    if current_account_state != base_state:
        logging.debug("the base state of smart transaction is not equal to current state of smart account")
        return

    logging.info("accepted smart transaction for execution. tx id: " + transaction['id'])

    input_file = ipfs_utils.load_ipfs_file(execution_config['input_file'])
    sender = op['from']
    result = exec(smart_account, input_file, sender)
    if result['success'] and result['modified']:
        logging.info("smart program execution completed successfully")
        envelope = create_transaction(smart_account, result['new_state_file_hash'], op['transaction_hash'])
        logging.debug("created xdr for saving in db: " + envelope.xdr().decode())
        tx_hash = str(hexlify(envelope.hash_meta()), "ascii")
        db_manager.add_smart_transaction(op['transaction_hash'], smart_account['id'], transaction['paging_token'],
                                         tx_hash, envelope.xdr().decode())
    else:
        logging.error("executing smart program failed with the following error: " + result['log'])


def run_ledger_checker():
    cursor = operation_paging_token_number
    logging.info("starting ledger checker with cursor: " + str(cursor))
    while True:
        operations = horizon.operations(cursor=cursor)['_embedded']['records']
        if len(operations) == 0:
            time.sleep(5)
            continue

        for operation in operations:

            if operation['transaction_successful']:
                if operation['type'] == 'payment':
                    if db_manager.get_smart_account(operation['to']) is not None:
                        check_transaction_if_smart(operation)

                elif operation['type'] == 'set_options' or operation['type'] == 'manage_data':
                    add_account_if_smart(operation['source_account'])

            db_manager.set_latest_checked_paging_token(operation['paging_token'])
            logging.info("operation with paging token: " + operation['paging_token'] + " checked")
            cursor = operation['paging_token']
