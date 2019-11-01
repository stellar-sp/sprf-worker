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

TRANSACTION_EXPOSER_PORT = os.environ.get('TRANSACTION_EXPOSER_PORT', '5002')
HORIZON_ADDRESS = os.environ.get("HORIZON_ADDRESS")
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
TRANSACTION_VALIDATOR_ADDRESS = os.environ.get("TRANSACTION_VALIDATOR_ADDRESS")

app = FlaskAPI(__name__)
db_manager = DbManager()
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
horizon = Horizon(HORIZON_ADDRESS)


@app.route('/api/<string:smart_account_id>/smart_transaction/<string:smart_transaction_hash>', methods=['POST'])
def receive_transaction(smart_account_id):
    tx_envelop_xdr = jsonify(request.json).json['xdr']

    validation_result = requests.post(url=TRANSACTION_VALIDATOR_ADDRESS + "/validate?remove_bad_signatures=true",
                                      json={'xdr': tx_envelop_xdr})
    if validation_result.headers.status_code != 200:
        return validation_result

    imported_xdr = TxEnv.TransactionEnvelope.from_xdr(tx_envelop_xdr)
    tx_hash = imported_xdr.hash_meta()

    privious_registered_xdr = r.get(tx_hash)
    if privious_registered_xdr is not None:
        tx_envelop_xdr = merge_envelops(tx_envelop_xdr, privious_registered_xdr)

    r.set(tx_hash, tx_envelop_xdr)

    return db_manager.get_smart_transactions(smart_account_id)


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


def run_rest_service():
    app.run(port=TRANSACTION_EXPOSER_PORT)


if __name__ == '__main__':
    run_rest_service()
