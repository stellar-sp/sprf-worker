import json
from db_manager import *
import requests
import base64
import time
import logging

db_manager = DbManager()


def run_transaction_flooder():
    while True:
        txs = db_manager.get_latest_transactions()
        for tx in txs:
            smart_account = json.loads(db_manager.get_smart_account(tx['smart_account_id'])['data'])
            for i in range(1, 10):
                worker_peer_address_entry_name = 'worker_' + str(i) + '_peer_address'
                if worker_peer_address_entry_name in smart_account['data']:
                    worker_peer_address = base64.b64decode(
                        smart_account['data'][worker_peer_address_entry_name]).decode()
                    try:
                        requests.post(url=worker_peer_address + '/api/smart_transaction',
                                      json={"xdr": tx['xdr']})
                        logging.info("sent a signed transaction to peer")
                    except ConnectionError as e:
                        logging.error("error occurred during send signed transaction to peer", e.strerror)

        logging.info("waiting for new transactions to flooding")
        time.sleep(5)
