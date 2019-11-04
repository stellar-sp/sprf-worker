import os

import redis
import requests
import stellar_base.transaction as Tx
import stellar_base.transaction_envelope as TxEnv
from flask import request, jsonify
from flask_api import FlaskAPI
from stellar_base.horizon import Horizon
from stellar_base.transaction_envelope import TransactionEnvelope as Te
from db_manager import *
import json
from stellar_base.network import Network
from binascii import hexlify
from stellar_base.keypair import *

TRANSACTION_RECEIVER_PORT = os.environ.get('TRANSACTION_RECEIVER_PORT', '5002')
HORIZON_ADDRESS = os.environ.get("HORIZON_ADDRESS")
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
NETWORK_PASSPHRASE = os.environ.get("NETWORK_PASSPHRASE")

app = FlaskAPI(__name__)
db_manager = DbManager()
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
horizon = Horizon(HORIZON_ADDRESS)


@app.route('/api/smart_transaction', methods=['POST'])
def receive_transaction():
    tx_envelop_xdr = jsonify(request.json).json['xdr']

    tx_envelop = TxEnv.TransactionEnvelope.from_xdr(tx_envelop_xdr)
    tx_envelop.network_id = Network(NETWORK_PASSPHRASE).network_id()

    validate_envelop(tx_envelop, remove_bad_signatures=True, remove_duplicate_signatures=True)

    tx_hash = str(hexlify(tx_envelop.hash_meta()), "ascii")
    previous_registered_xdr = r.get(tx_hash)
    if previous_registered_xdr is not None:
        tx_envelop_xdr = merge_envelops(tx_envelop_xdr, previous_registered_xdr)

    r.set(tx_hash, tx_envelop_xdr)

    return {
        "result": "ok"
    }


def merge_envelops(xdr1, xdr2):
    imported_xdr1 = TxEnv.TransactionEnvelope.from_xdr(xdr1)
    imported_xdr2 = TxEnv.TransactionEnvelope.from_xdr(xdr2)

    if imported_xdr1.hash_meta() != imported_xdr2.hash_meta() or imported_xdr1.network_id != imported_xdr2.network_id:
        raise Exception("cannot merge envelops, because envelops is not equals with each other")

    for sign in imported_xdr2.signatures:
        imported_xdr1.signatures.append(sign)

    envelop1 = Te(tx=Tx.Transaction.from_xdr_object(imported_xdr1.to_xdr_object()),
                  signatures=imported_xdr1.signatures)
    envelop1.network_id = imported_xdr1.network_id

    return envelop1.xdr().decode()


def validate_envelop(tx_envelop, remove_bad_signatures=False, remove_duplicate_signatures=False):
    source_accounts = [tx_envelop.tx.source.decode()]
    for op in tx_envelop.tx.operations:
        if op.source is not None:
            source_accounts.append(op.source.decode())

    signers = []
    for address in source_accounts:
        for signer in horizon.account(address)['signers']:
            if signer['weight'] > 0:
                signers.append(signer['key'])

    for i in range(len(tx_envelop.signatures)-1, -1, -1):
        validated = False
        for signer in signers:
            try:
                Keypair.from_address(signer).verify(tx_envelop.hash_meta(), tx_envelop.signatures[i].signature)
                validated = True
                break
            except:
                pass
        if not validated and remove_bad_signatures:
            tx_envelop.signatures.remove(tx_envelop.signatures[i])

    if remove_duplicate_signatures:
        for i in range(len(tx_envelop.signatures)-1, -1, -1):
            for j in range(i-1, -1, -1):
                if tx_envelop.signatures[i].signature == tx_envelop.signatures[j].signature:
                    tx_envelop.signatures.remove(tx_envelop.signatures[i])


def run_transaction_receiver():
    app.run(port=TRANSACTION_RECEIVER_PORT)


if __name__ == '__main__':
    run_transaction_receiver()
