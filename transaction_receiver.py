from flask_api import FlaskAPI
from flask import request, jsonify
from db_manager import *
import os
import redis
from stellar_base.horizon import Horizon
import stellar_base.transaction_envelope as TxEnv
from stellar_base.horizon import Horizon
import stellar_base.transaction as Tx
from stellar_base.operation import *
from stellar_base.keypair import Keypair
from stellar_base.stellarxdr.StellarXDR_pack import *

TRANSACTION_EXPOSER_PORT = os.environ.get('TRANSACTION_EXPOSER_PORT', '5002')
HORIZON_ADDRESS = os.environ.get("HORIZON_ADDRESS")

app = FlaskAPI(__name__)
db_manager = DbManager()
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
horizon = Horizon(HORIZON_ADDRESS)


@app.route('/api/<string:smart_account_id>/smart_transaction/<string:smart_transaction_hash>', methods=['POST'])
def get_smart_accounts(smart_account_id, smart_transaction_hash):
    tx_envelop_xdr = jsonify(request.json).json['xdr']

    imported_xdr = TxEnv.TransactionEnvelope.from_xdr(tx_envelop_xdr)
    tx_hash = imported_xdr.hash_meta()
    tx_object = Tx.Transaction.from_xdr_object(imported_xdr.to_xdr_object())

    import hashlib
    hash = hashlib.sha256(imported_xdr.signature_base())
    hash.update(imported_xdr.signature_base())
    print(hash.digest())

    signed = Keypair.from_seed("SAC4Z4DHUVICKKOUDRUGRGA6ENMZLB4RQO6BMDJNXTLZFBFBY5JV4WVA").sign(tx_hash)
    Keypair.from_address("GCY4Y2SJMSTE3KPVILQPL4276IFG5VTUIZ3GJRTFOVZOTRKUKJMO5QGA").verify(tx_hash, signed)

    horizon = Horizon(HORIZON_ADDRESS)
    account_info = horizon.account(tx_object.source.decode("utf-8"))

    for sig in imported_xdr.signatures:
        for account_signers in account_info['signers']:
            Keypair.from_address(account_signers['key']).verify(tx_hash, sig.signature)
        sig.hint.decode("utf-8")

    smart_transaction = r.get(smart_transaction_hash)
    if smart_transaction is None:
        print("transaction not exists")

    return db_manager.get_smart_transactions(smart_account_id)


def run_rest_service():
    app.run(port=TRANSACTION_EXPOSER_PORT)


if __name__ == '__main__':
    run_rest_service()
