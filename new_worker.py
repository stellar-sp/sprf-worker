from stellar_base.horizon import Horizon
from db_manager import *
import time
from ipfs_utils import *

HORIZON_ADDRESS = os.environ.get('HORIZON_ADDRESS')
IPFS_ADDRESS = os.environ.get('IPFS_ADDRESS')
START_PAGING_TOKEN_CHECK = int(os.environ.get('START_PAGING_TOKEN_CHECK', 1))

db_manager = DbManager()

operation_paging_token_number = int(db_manager.get_latest_checked_ledger())
if operation_paging_token_number == 0:
    operation_paging_token_number = START_PAGING_TOKEN_CHECK

horizon = Horizon(HORIZON_ADDRESS)

cursor = None
while True:
    operations = horizon.operations(cursor=cursor)['_embedded']['records']
    if len(operations) == 0:
        time.sleep(5)
        continue

    for operation in operations:

        if operation['transaction_successful']:
            if operation['type'] == 'payment':
                transaction = horizon.transaction(operation['transaction_hash'])
                if transaction['memo_type'] == 'hash':
                    smart_account = db_manager.get_smart_account(operation['to'])
                    if smart_account is not None:
                        execution_config_file = load_ipfs_file(transaction['memo'])

            elif operation['type'] == 'set_options':
                print("set_options")

        db_manager.set_latest_checked_paging_token(operation['paging_token'])
