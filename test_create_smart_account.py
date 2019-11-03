import os
from stellar_base.horizon import Horizon
import requests
from stellar_base.keypair import Keypair
from stellar_base.transaction import Transaction
from stellar_base.transaction_envelope import TransactionEnvelope as Te
from stellar_base.operation import ManageData, SetOptions, Payment
from ipfs_utils import *
import tempfile
from stellar_base.memo import HashMemo
import json
from stellar_base.asset import Asset
import base64

HORIZON_ADDRESS = os.environ.get('HORIZON_ADDRESS')
horizon = Horizon(HORIZON_ADDRESS)
FRIENDBOT_ADDRESS = os.environ.get('FRIENDBOT_ADDRESS')
SMART_PROGRAM_IMAGE_ADDRESS = os.environ.get('SMART_PROGRAM_IMAGE_ADDRESS')
SMART_PROGRAM_IMAGE_HASH = os.environ.get('SMART_PROGRAM_IMAGE_HASH')
NETWORK_PASSPHRASE = os.environ.get("NETWORK_PASSPHRASE")

smart_account_keypair = Keypair.random()
worker1_keypair = Keypair.random()
user1_keypair = Keypair.random()

if os.path.exists("test_accounts.json"):
    with open("test_accounts.json", "r") as f:
        test_accounts = json.load(f)
    smart_account_keypair = Keypair.from_seed(test_accounts["smart_account"]["private_key"])
    worker1_keypair = Keypair.from_seed(test_accounts["worker1_account"]["private_key"])
    user1_keypair = Keypair.from_seed(test_accounts["user1_account"]["private_key"])
else:
    with open("test_accounts.json", 'w') as f:
        json.dump({
            "smart_account": {
                "public_key": smart_account_keypair.address().decode(),
                "private_key": smart_account_keypair.seed().decode()
            },
            "worker1_account": {
                "public_key": worker1_keypair.address().decode(),
                "private_key": worker1_keypair.seed().decode()
            },
            "user1_account": {
                "public_key": user1_keypair.address().decode(),
                "private_key": user1_keypair.seed().decode()
            }
        }, f)


def test():
    test_create_smart_account()
    test_create_smart_transaction()


def test_create_smart_account():
    requests.get(FRIENDBOT_ADDRESS + '/?addr=' + smart_account_keypair.address().decode())
    latest_transaction_changed_state = horizon.account_transactions(smart_account_keypair.address().decode()) \
        ['_embedded']['records'][0]['hash']

    temp_state_file = tempfile.mkstemp()
    state_file_hash = upload_file_to_ipfs(temp_state_file[1])

    operations = [
        ManageData(data_name='current_state', data_value=state_file_hash),
        ManageData(data_name='smart_program_image_address', data_value=SMART_PROGRAM_IMAGE_ADDRESS),
        ManageData(data_name='smart_program_image_hash', data_value=SMART_PROGRAM_IMAGE_HASH),
        ManageData(data_name='execution_fee', data_value='1000'),
        ManageData(data_name='worker_1_peer_address', data_value='http://worker1:5002'),
        ManageData(data_name='worker_1_public_key', data_value=worker1_keypair.address().decode()),
        ManageData(data_name='latest_transaction_changed_state', data_value=latest_transaction_changed_state),
        SetOptions(master_weight=0, low_threshold=1, med_threshold=1, high_threshold=1,
                   signer_address=worker1_keypair.address().decode(), signer_weight=1)
    ]

    tx = Transaction(
        source=smart_account_keypair.address().decode(),
        sequence=horizon.account(smart_account_keypair.address().decode()).get('sequence'),
        fee=50000 * len(operations),
        operations=operations
    )

    envelope = Te(tx=tx, network_id=NETWORK_PASSPHRASE)
    envelope.sign(Keypair.from_seed(smart_account_keypair.seed()))
    horizon.submit(envelope.xdr())


def test_create_smart_transaction():
    # requests.get(FRIENDBOT_ADDRESS + '/?addr=' + user1_keypair.address().decode())
    operations = [
        Payment(destination=smart_account_keypair.address().decode(), amount='1', asset=Asset("XLM"))
    ]

    temp_input_file = tempfile.mkstemp()
    input_config = {
        "function": "vote",
        "candidate_name": "test_candid"
    }
    with open(temp_input_file[1], 'w') as f:
        json.dump(input_config, f)
    input_file_hash = upload_file_to_ipfs(temp_input_file[1])

    execution_config = {
        "input_file": input_file_hash,
        "base_state": base64.b64decode(horizon.account(smart_account_keypair.address().decode())['data']
                                       ['current_state']).decode()
    }
    temp_execution_config_file = tempfile.mkstemp()
    with open(temp_execution_config_file[1], 'w') as f:
        json.dump(execution_config, f)
    execution_config_file_hash = upload_file_to_ipfs(temp_execution_config_file[1])
    execution_config_file_hex = ipfs_hash_to_base58(execution_config_file_hash)

    tx = Transaction(
        source=user1_keypair.address().decode(),
        sequence=horizon.account(user1_keypair.address().decode()).get('sequence'),
        fee=50000 * len(operations),
        operations=operations,
        memo=HashMemo(execution_config_file_hex)
    )

    envelope = Te(tx=tx, network_id=NETWORK_PASSPHRASE)
    envelope.sign(Keypair.from_seed(user1_keypair.seed()))
    horizon.submit(envelope.xdr())


if __name__ == '__main__':
    test()
