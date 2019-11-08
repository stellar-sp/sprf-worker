import configparser
import json
import tempfile
from stellar_base.horizon import Horizon
from stellar_base.keypair import Keypair
from stellar_base.operation import ManageData, SetOptions
from stellar_base.transaction import Transaction
from stellar_base.transaction_envelope import TransactionEnvelope as Te
from ipfs_utils import *
import requests


def test_create_smart_account():
    config = configparser.ConfigParser()
    config.read('create_smart_account_config.ini')

    horizon_address = config.get('default', 'HORIZON_ADDRESS')
    friendbot_address = config.get('default', 'FRIENDBOT_ADDRESS')
    smart_program_image_address = config.get('default', 'SMART_PROGRAM_IMAGE_ADDRESS')
    smart_program_image_hash = config.get('default', 'SMART_PROGRAM_IMAGE_HASH')
    network_passphrase = config.get('default', 'NETWORK_PASSPHRASE')
    smart_account_secret_key = config.get('default', 'SMART_ACCOUNT_SECRET_KEY')
    workers = json.loads(config.get('default', 'WORKERS'))

    horizon = Horizon(horizon_address)
    smart_account_keypair = Keypair.from_seed(smart_account_secret_key)

    requests.get(friendbot_address + '/?addr=' + smart_account_keypair.address().decode())
    latest_transaction_changed_state = horizon.account_transactions(smart_account_keypair.address().decode()) \
        ['_embedded']['records'][0]['hash']

    temp_state_file = tempfile.mkstemp()
    state_file_hash = upload_file_to_ipfs(temp_state_file[1])

    operations = [
        ManageData(data_name='current_state', data_value=state_file_hash),
        ManageData(data_name='smart_program_image_address', data_value=smart_program_image_address),
        ManageData(data_name='smart_program_image_hash', data_value=smart_program_image_hash),
        ManageData(data_name='execution_fee', data_value='1000'),
        ManageData(data_name='latest_transaction_changed_state', data_value=latest_transaction_changed_state),
    ]

    for i in range(1, len(workers)+1):
        operations.append(ManageData(data_name='worker_' + str(i) + '_peer_address', data_value=workers[i-1]['api_address']))
        operations.append(ManageData(data_name='worker_' + str(i) + '_public_key', data_value=workers[i-1]['public_key']))
        operations.append(SetOptions(signer_address=workers[i-1]['public_key'], signer_weight=1))

    weight = int(len(workers) / 2) + 1
    operations.append(SetOptions(master_weight=0, low_threshold=weight, med_threshold=weight, high_threshold=weight))
    tx_fee = horizon.ledgers(order='desc', limit=1)['_embedded']['records'][0]['base_fee_in_stroops']

    tx = Transaction(
        source=smart_account_keypair.address().decode(),
        sequence=horizon.account(smart_account_keypair.address().decode()).get('sequence'),
        fee=tx_fee * len(operations),
        operations=operations
    )

    envelope = Te(tx=tx, network_id=network_passphrase)
    envelope.sign(Keypair.from_seed(smart_account_keypair.seed()))
    horizon.submit(envelope.xdr())


if __name__ == '__main__':
    test_create_smart_account()
