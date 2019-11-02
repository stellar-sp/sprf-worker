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
import base58
from binascii import unhexlify

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


def add_account_if_smart(account_id):
    account = horizon.account(account_id)
    if 'smart_program_image_address' not in account['data']:
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
        ManageData(data_name='current_state', data_value=new_state_file_hash, source=smart_account['account_id']),
        ManageData(data_name='latest_transaction_changed_state', data_value=latest_transaction_changed_state,
                   source=smart_account)
    ]

    tx = Transaction(
        source=smart_account['id'],
        sequence=horizon.account(smart_account['id']).get('sequence'),
        fee=1000 * len(operations),
        operations=operations
    )

    envelope = Te(tx=tx, network_id=NETWORK_PASSPHRASE)
    envelope.sign(Keypair.from_seed(WORKER_SECRET_KEY))
    return envelope.xdr()


def check_transaction_if_smart(op):
    transaction = horizon.transaction(op['transaction_hash'])

    smart_account = horizon.account(op['to'])

    latest_transaction_hash = base64.b64decode(smart_account['data']['latest_transaction_changed_state']).decode()
    latest_transaction = horizon.transaction(latest_transaction_hash)
    if latest_transaction['paging_token'] > transaction['paging_token']:
        return

    if transaction['memo_type'] != 'hash':
        return

    ipfs_hash = base58.b58encode(b'1220'+unhexlify(base64.b64decode(transaction['memo']).hex()))
    execution_config = json.loads(load_ipfs_file(ipfs_hash))

    # controlling concurrency between transactions
    base_state = execution_config['base_state']
    if smart_account['data']['current_state'] != base_state:
        return

    input_file = load_ipfs_file(execution_config['input_file'])
    sender = op['from']
    result = exec(smart_account, input_file, sender)
    if result['success'] and result['modified']:
        envelop_xdr = create_transaction(smart_account, result['new_state_file_hash'], op['transaction_hash'])
        db_manager.add_smart_transaction(smart_account['id'], op['transaction_hash'], transaction['paging_token'],
                                         envelop_xdr)


def run_ledger_checker():
    cursor = operation_paging_token_number
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
            print("operation with paging token: " + operation['paging_token'] + " checked")
            cursor = operation['paging_token']


if __name__ == '__main__':
    run_ledger_checker()
