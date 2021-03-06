import os
import time
import redis
from stellar_base.horizon import Horizon
from db_manager import *
import stellar_base.transaction_envelope as TxEnv
from stellar_base.keypair import *
from stellar_base.network import Network
from stellar_base.exceptions import *
import logging
import sys

HORIZON_ADDRESS = os.environ.get("HORIZON_ADDRESS")
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
NETWORK_PASSPHRASE = os.environ.get("NETWORK_PASSPHRASE")


class TransactionSubmitter:
    def __init__(self):
        self.horizon = Horizon(HORIZON_ADDRESS)
        self.r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        self.db_manager = DbManager()

    def run_transaction_submitter(self):
        while True:
            logging.debug("tx submitter is searching cache for new tx")
            for key in self.r.scan_iter():
                xdr = self.r.get(key)
                logging.debug("found tx in cache as a candidate for submission: " + xdr.decode())
                validity_for_submission = self.check_max_and_min_required_signs(xdr)
                logging.debug("validation: " + str(validity_for_submission["meet_requirements"]))
                if validity_for_submission["meet_requirements"]:
                    try:
                        logging.debug("trying to submit tx to horizon: " + validity_for_submission["xdr"].decode())
                        self.horizon.submit(validity_for_submission["xdr"].decode())
                        logging.debug("tx submitted successfully to horizon. deleting tx from db")
                        self.db_manager.delete_transaction(key.decode())
                    except HorizonError as e:
                        logging.error("cannot submit transaction to network, due to: " + e.message)
                        pass

                    self.r.delete(key)

            time.sleep(5)

    def check_max_and_min_required_signs(self, tx_xdr):
        tx_envelop = TxEnv.TransactionEnvelope.from_xdr(tx_xdr)
        tx_envelop.network_id = Network(NETWORK_PASSPHRASE).network_id()

        source_accounts = [tx_envelop.tx.source.decode()]

        for op in tx_envelop.tx.operations:
            if op.source is not None:
                source_accounts.append(op.source.decode())

        all_required_signatures = []

        for source_account in source_accounts:
            account = self.horizon.account(source_account)
            med_threshold = account['thresholds']['med_threshold']

            required_signatures = []

            for signature in tx_envelop.signatures:
                for signer in account['signers']:
                    try:
                        if signer['weight'] > 0:
                            Keypair.from_address(signer['key']).verify(tx_envelop.hash_meta(), signature.signature)
                            if len(required_signatures) < med_threshold:
                                required_signatures.append(signature)
                                break
                    except:
                        pass

            if len(required_signatures) < med_threshold:
                return {
                    "meet_requirements": False
                }

            for signature in required_signatures:
                is_already_in_list = False
                for sig in all_required_signatures:
                    if sig == signature:
                        is_already_in_list = True
                        break
                if not is_already_in_list:
                    all_required_signatures.append(signature)

            return {
                "meet_requirements": True,
                "xdr": tx_envelop.xdr()
            }
