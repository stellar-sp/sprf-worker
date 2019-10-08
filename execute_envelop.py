import base64
import hashlib
import stellar_base.transaction_envelope as TxEnv
from stellar_base.horizon import Horizon
import os
from stellar_base.keypair import Keypair
import json


class ExecutionEnvelop:
    def __init__(self, envelop, horizon_uri=None):
        if horizon_uri is None:
            horizon_uri = os.environ.get('HORIZON_ADDRESS')
        horizon = Horizon(horizon_uri)

        self.envelop = envelop
        self.message = json.loads(self.envelop['message'])
        self.message_hash = self.envelop['message_hash']
        self.signature = base64.b64decode(self.envelop['signature'])
        self.gas_pre_payed_tx = horizon.transaction(self.message['gas_pre_payed_tx_hash'])
        self.smart_account_address = \
            TxEnv.TransactionEnvelope.from_xdr(self.gas_pre_payed_tx.get('envelope_xdr')).tx.operations[
                0].destination
        self.smart_account = horizon.account(self.smart_account_address)
        self.sender = self.gas_pre_payed_tx.get('source_account')

    def verify(self):

        if not self.gas_pre_payed_tx.get('successful'):
            raise Exception("this is a failed transaction. sorry!")

        calculated_message_hash = hashlib.sha256(str.encode(self.envelop['message'])).hexdigest()
        if self.message_hash != calculated_message_hash:
            raise Exception("the message hash is not correct")
        Keypair.from_address(self.sender).verify(str.encode(calculated_message_hash), self.signature)

    def get_smart_account(self):
        return self.smart_account

    def get_sender(self):
        return self.sender

    def get_input_file(self):
        return self.message['input_file']
