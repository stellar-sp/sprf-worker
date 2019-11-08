from binascii import hexlify
from flask_api import status
import redis
import stellar_base.transaction_envelope as TxEnv
from flask import request, jsonify
from flask_api import FlaskAPI
from stellar_base.horizon import Horizon
from stellar_base.keypair import *
from stellar_base.network import Network
from ipfs_utils import *
from db_manager import *

TRANSACTION_RECEIVER_PORT = os.environ.get('TRANSACTION_RECEIVER_PORT', '5002')
HORIZON_ADDRESS = os.environ.get("HORIZON_ADDRESS")
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
NETWORK_PASSPHRASE = os.environ.get("NETWORK_PASSPHRASE")

app = FlaskAPI(__name__)
db_manager = DbManager()
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
horizon = Horizon(HORIZON_ADDRESS)
from exec_engine import *


@app.route('/api/smart_program/<string:smart_account_id>', methods=['GET'])
def exec_getter_method_of_smart_contract(smart_account_id):
    if db_manager.get_smart_account(smart_account_id) is None:
        return {'success': False,
                'message': 'this smart account not supported by this worker'}, status.HTTP_400_BAD_REQUEST

    input_file_hash = request.args.get('input_file_hash')
    input_file = load_ipfs_file(input_file_hash)

    sender = request.args.get('sender')
    smart_account = horizon.account(smart_account_id)
    result = exec(smart_account, input_file, sender)
    if result['success'] and result['modified']:
        return {'success': False,
                'message': 'a setter method called! only getter methods can be called through this api'}
    return result


@app.route('/api/smart_transaction', methods=['POST'])
def receive_transaction():
    tx_envelop_xdr = jsonify(request.json).json['xdr']

    tx_envelop = TxEnv.TransactionEnvelope.from_xdr(tx_envelop_xdr)
    tx_envelop.network_id = Network(NETWORK_PASSPHRASE).network_id()

    validate_envelop(tx_envelop, remove_bad_signatures=True, remove_duplicate_signatures=True)

    tx_hash = str(hexlify(tx_envelop.hash_meta()), "ascii")
    previous_registered_xdr = r.get(tx_hash)
    if previous_registered_xdr is not None:
        tx_envelop_xdr = merge_envelops(tx_envelop_xdr, previous_registered_xdr.decode())

    r.set(tx_hash, tx_envelop_xdr)

    return {
        "result": "ok"
    }


def merge_envelops(xdr1, xdr2):
    imported_xdr1 = TxEnv.TransactionEnvelope.from_xdr(xdr1)
    imported_xdr2 = TxEnv.TransactionEnvelope.from_xdr(xdr2)

    if imported_xdr1.hash_meta() != imported_xdr2.hash_meta() or imported_xdr1.network_id != imported_xdr2.network_id:
        raise Exception("cannot merge envelops, because envelops is not equals with each other")

    for sign2 in imported_xdr2.signatures:
        found = False
        for sign1 in imported_xdr1.signatures:
            if sign1.signature == sign2.signature:
                found = True
                break
        if not found:
            imported_xdr1.signatures.append(sign2)

    return imported_xdr1.xdr().decode()


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

    for i in range(len(tx_envelop.signatures) - 1, -1, -1):
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
        for i in range(len(tx_envelop.signatures) - 1, -1, -1):
            for j in range(i - 1, -1, -1):
                if tx_envelop.signatures[i].signature == tx_envelop.signatures[j].signature:
                    tx_envelop.signatures.remove(tx_envelop.signatures[i])


def run_api_service():
    app.run(host="0.0.0.0", port=TRANSACTION_RECEIVER_PORT)
