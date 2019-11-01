import json
import db_manager
import requests


def flood_transactions_to_network():
    while True:
        print("flooding")
        txs = db_manager.get_latest_transactions()
        for tx in txs:
            smart_account = json.loads(db_manager.get_smart_account(tx['smart_account_id'])['data'])
            for i in range(1, 10):
                worker_peer_address = 'worker_' + i + '_peer_address'
                if hasattr(smart_account['data'], worker_peer_address):
                    requests.post(url=worker_peer_address + '/api/' + smart_account['id'] + '/smart_transaction/' + tx[
                        'transaction_hash'], data=tx['xdr'])
                    print("sent xdr peer")
