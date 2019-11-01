import time
import stellar_base.transaction_envelope as TxEnv
from stellar_base.horizon import Horizon
import stellar_base.transaction as Tx
from stellar_base.operation import *
from stellar_base.keypair import Keypair
import codecs
import os
import redis
from db_manager import DbManager
import json
import requests

HORIZON_ADDRESS = os.environ.get("HORIZON_ADDRESS")
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")

transaction_map = {}
transaction_signs = {}
db_manager = DbManager()
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)


def submit_tx(xdr):
    imported_xdr = TxEnv.TransactionEnvelope.from_xdr(xdr)
    transaction_hash = imported_xdr.hash_meta()
    tx_object = Tx.Transaction.from_xdr_object(imported_xdr.to_xdr_object())

    horizon = Horizon(HORIZON_ADDRESS)
    account_info = horizon.account(tx_object.source.decode("utf-8"))

    if transaction_hash not in transaction_signs:
        transaction_signs[transaction_hash] = []

    for sign in imported_xdr.signatures:
        def find_signer():
            for signer in account_info["signers"]:
                keypair = Keypair.from_address(signer['key'])

                decoded_tx_hash = codecs.encode(transaction_hash, 'hex')
                decoded_sign = codecs.encode(sign.signature, 'hex')
                codecs.encode(sign.hint, 'hex')
                if keypair.verify(decoded_sign, decoded_tx_hash):
                    transaction_signs[transaction_hash].append(sign)
                    return

        find_signer()

    if len(transaction_signs[transaction_hash]) == 0:
        return False

    if transaction_hash not in transaction_map:
        transaction_map[transaction_hash] = xdr

    if check_transaction_reach_min_signatures(transaction_hash):
        imported_xdr1 = TxEnv.TransactionEnvelope.from_xdr(transaction_xdr1)
        transaction_hash1 = imported_xdr1.hash_meta()

        imported_xdr2 = TxEnv.TransactionEnvelope.from_xdr(transaction_xdr2)
        transaction_hash2 = imported_xdr2.hash_meta()

        if transaction_hash1 == transaction_hash2:
            for sign in imported_xdr2.signatures:
                imported_xdr1.signatures.append(sign)

            if check_transaction_reach_min_signatures(transaction_xdr1):
                horizon = Horizon(HORIZON_ADDRESS)
                response = horizon.submit(imported_xdr1.xdr())
                print(response)


def check_transaction_reach_min_signatures(transaction_hash):
    imported_xdr = TxEnv.TransactionEnvelope.from_xdr(transaction_map[transaction_hash])
    tx_object = Tx.Transaction.from_xdr_object(imported_xdr.to_xdr_object())

    horizon = Horizon(HORIZON_ADDRESS)
    account_info = horizon.account(tx_object.source.decode("utf-8"))

    required_signer_count = account_info["thresholds"][get_min_required_signer_level(transaction_hash)]
    if len(transaction_signs[transaction_hash]) >= required_signer_count:
        return True

    return False


def get_min_required_signer_level(transaction_hash):
    imported_xdr = TxEnv.TransactionEnvelope.from_xdr(transaction_map[transaction_hash])
    tx_object = Tx.Transaction.from_xdr_object(imported_xdr.to_xdr_object())

    for operation in tx_object.operations:
        if isinstance(operation, (SetOptions, AccountMerge)):
            return "high_threshold"
        elif isinstance(operation, AllowTrust):
            return "low_threshold"
    return "med_threshold"


def submit_possible_transactions():
    while True:
        print("submitting")
