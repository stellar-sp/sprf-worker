import base64
import hashlib
import stellar_base.transaction_envelope as TxEnv
from stellar_base.horizon import Horizon
import os
from stellar_base.keypair import Keypair
import json
from datetime import datetime

EXECUTION_TIMEOUT_IN_SECOND = 60


class ExecutionEnvelop:
    def __init__(self, envelop, horizon_uri=None):
        if horizon_uri is None:
            horizon_uri = os.environ.get('HORIZON_ADDRESS')
        self.horizon = Horizon(horizon_uri)

        self.envelop = envelop
        self.message = json.loads(self.envelop['message'])
        self.message_hash = self.envelop['message_hash']
        self.signature = base64.b64decode(self.envelop['signature'])
        self.gas_pre_payed_tx_hash = self.message['gas_pre_payed_tx_hash']
        self.gas_pre_payed_tx = self.horizon.transaction(self.gas_pre_payed_tx_hash)
        self.smart_account_address = \
            TxEnv.TransactionEnvelope.from_xdr(self.gas_pre_payed_tx.get('envelope_xdr')).tx.operations[
                0].destination
        self.smart_account = self.horizon.account(self.smart_account_address)
        self.sender = self.gas_pre_payed_tx.get('source_account')

    def verify(self):

        if not self.gas_pre_payed_tx.get('successful'):
            raise Exception("this is a failed transaction. sorry!")

        calculated_message_hash = hashlib.sha256(str.encode(self.envelop['message'])).hexdigest()
        if self.message_hash != calculated_message_hash:
            raise Exception("the message hash is not correct")
        Keypair.from_address(self.sender).verify(str.encode(calculated_message_hash), self.signature)

    def is_it_in_right_order(self):
        cursor = self.gas_pre_payed_tx.get('paging_token')
        while True:
            precede_transactions = self.horizon.account_transactions(address=self.smart_account_address,
                                                                     cursor=cursor, order='desc', limit=10)
            if len(precede_transactions['_embedded']['records']) < 1:
                return True

            for tx in precede_transactions['_embedded']['records']:
                if tx.get('memo') == 'exec_smart_program_base_fee':
                    transaction_date = datetime.strptime(tx.get('created_at'), '%Y-%m-%dT%H:%M:%SZ')
                    if (datetime.utcnow() - transaction_date).seconds > EXECUTION_TIMEOUT_IN_SECOND:
                        return True
                    else:
                        if base64.b64decode(
                                self.smart_account.get('data')['last_paging_token_made_change']).decode() == tx.get(
                                'paging_token'):
                            return True
                        else:
                            return False

                cursor = tx.get('paging_token')

    def get_smart_account(self):
        return self.smart_account

    def get_sender(self):
        return self.sender

    def get_input_file(self):
        return self.message['input_file']

    def get_gas_pre_payed_tx_hash(self):
        return self.gas_pre_payed_tx_hash

    def get_paging_token(self):
        self.gas_pre_payed_tx.get('paging_token')

    def get_execution_timeout_date(self):
        return int(datetime.strptime(self.gas_pre_payed_tx.get('created_at'),
                                     '%Y-%m-%dT%H:%M:%SZ').timestamp()) + EXECUTION_TIMEOUT_IN_SECOND
