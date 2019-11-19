import json
from db_manager import *
import requests
import base64
import time
import logging
import sys
from stellar_base.keypair import Keypair

WORKER_SECRET_KEY = os.environ.get('WORKER_SECRET_KEY')
WORKER_PUBLIC_KEY = Keypair.from_seed(WORKER_SECRET_KEY).address().decode()

db_manager = DbManager()


def run_transaction_flooder():
    while True:
        logging.debug("searching db for new created transactions")
        txs = db_manager.get_latest_transactions()
        for tx in txs:
            logging.debug("found a transaction to flooding")
            smart_account = json.loads(db_manager.get_smart_account(tx['smart_account_id'])['data'])

            for i in range(1, len(smart_account['signers'])):
                worker_peer_address_entry_name = 'worker_' + str(i) + '_peer_address'

                if worker_peer_address_entry_name in smart_account['data']:

                    # worker does not need to flood message to itself. checking is it current worker or not
                    if base64.b64decode(smart_account['data']['worker_' + str(i) + '_public_key']).decode() == \
                            WORKER_PUBLIC_KEY:
                        continue

                    worker_peer_address = base64.b64decode(
                        smart_account['data'][worker_peer_address_entry_name]).decode()
                    try:
                        requests.post(url=worker_peer_address + '/api/smart_transaction',
                                      json={"xdr": tx['xdr']})
                        logging.info("sent a signed transaction to peer")
                    except:
                        logging.error("error occurred during send signed transaction to peer" + str(sys.exc_info()[0]))

        time.sleep(5)
