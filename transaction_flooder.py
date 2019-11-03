import json
from db_manager import *
import requests
import base64

db_manager = DbManager()


def run_transaction_flooder():
    while True:
        print("flooding")
        txs = db_manager.get_latest_transactions()
        for tx in txs:
            smart_account = json.loads(db_manager.get_smart_account(tx['smart_account_id'])['data'])
            for i in range(1, 10):
                worker_peer_address_entry_name = 'worker_' + str(i) + '_peer_address'
                if worker_peer_address_entry_name in smart_account['data']:
                    worker_peer_address = base64.b64decode(
                        smart_account['data'][worker_peer_address_entry_name]).decode()
                    requests.post(url=worker_peer_address + '/api/' + smart_account['id'] + '/smart_transaction',
                                  json={"xdr": tx['xdr']})
                    print("sent xdr peer")


if __name__ == '__main__':
    run_transaction_flooder()
