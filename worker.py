import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from stellar_base.horizon import Horizon
import base64
import tempfile
import docker
from stellar_base.transaction import Transaction
from stellar_base.operation import Payment, ManageData
from stellar_base.transaction_envelope import TransactionEnvelope as Te
from stellar_base.keypair import Keypair
from stellar_base.asset import Asset
from execute_envelop import ExecutionEnvelop
from environs import Env
from ipfs_utils import *

if os.path.exists('./.env1'):
    env = Env()
    env.read_env(path="./.env1")

HORIZON_ADDRESS = os.environ.get('HORIZON_ADDRESS')
NETWORK_PASSPHRASE = os.environ.get('NETWORK_PASSPHRASE')
WORKER_SECRET_KEY = os.environ.get('WORKER_SECRET_KEY')

horizon = Horizon(HORIZON_ADDRESS)


class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write(self._html("hi!"))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        envelop = json.loads(post_data)

        execution_envelop = ExecutionEnvelop(envelop)
        execution_envelop.verify()
        if not execution_envelop.is_it_in_right_order():
            raise Exception("retry some second later. there is some transactions submitted before it")

        smart_account = execution_envelop.get_smart_account()
        sender = execution_envelop.get_sender()

        input_file_hash = execution_envelop.get_input_file()
        input_file = load_ipfs_file(input_file_hash)

        if 'current_state' in smart_account['data']:
            current_state_hash = base64.b64decode(smart_account['data']['current_state']).decode()
            current_state_file = load_ipfs_file(current_state_hash)
        else:
            f = tempfile.mkstemp()
            current_state_file = f[1]

        current_state_file_hash = get_sha256_of_file(current_state_file)

        docker_client = docker.from_env()
        smart_program_image_address = base64.b64decode(smart_account['data']['smart_program_image_address']).decode()
        smart_program_image_hash = base64.b64decode(smart_account['data']['smart_program_image_hash']).decode()
        image_complete_name = smart_program_image_address + '@sha256:' + smart_program_image_hash
        container = docker_client.containers.run(image=image_complete_name,
                                                 volumes=
                                                 {
                                                     current_state_file: {'bind': '/state', 'mode': 'rw'},
                                                     input_file: {'bind': '/input', 'mode': 'ro'}
                                                 },
                                                 environment={"SENDER": sender}, detach=True)
        container_result = container.wait(timeout=5)
        container_log = docker_client.containers.get(container.id).logs()
        container.remove()
        if container_result['StatusCode'] == 0:
            print("successfully ran")
            new_state_file_hash = get_sha256_of_file(current_state_file)
            if current_state_file_hash != new_state_file_hash:
                print("the state change by the program")
                print("signing transaction and getting result back to user")
                upload_file_to_ipfs(current_state_file)
                transaction = create_transaction(new_state_file_hash, smart_account, sender, execution_envelop)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({'log': container_log.decode(), 'xdr': transaction.decode('utf-8')}).encode())

            else:
                self.send_response(304)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({'log': container_log.decode()}).encode())
        else:
            print("failed to run smart program")
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({'state': 'not-changed', 'log': container_log.decode()}).encode())


def create_transaction(new_state_hash, smart_account, user_account_public_key, execution_envelop):
    additional_fee = int(base64.b64decode(smart_account['data']['execution_base_fee']).decode()) / 10000000

    operations = [
        Payment(source=user_account_public_key, destination=smart_account['account_id'],
                amount=str(additional_fee), asset=Asset("XLM")),
        ManageData(data_name='current_state', data_value=new_state_hash, source=smart_account['account_id']),
        ManageData(data_name='last_paging_token_made_change', data_value=execution_envelop.get_paging_token(),
                   source=smart_account)
    ]

    tx = Transaction(
        source=user_account_public_key,
        sequence=horizon.account(user_account_public_key).get('sequence'),
        fee=1000 * len(operations),
        operations=operations,
        time_bounds={'minTime': 0, 'maxTime': execution_envelop.get_execution_timeout_date()}
    )

    envelope = Te(tx=tx, network_id=NETWORK_PASSPHRASE)
    envelope.sign(Keypair.from_seed(WORKER_SECRET_KEY))
    return envelope.xdr()


def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simple HTTP server")
    parser.add_argument(
        "-l",
        "--listen",
        default="localhost",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Specify the port on which the server listens",
    )
    args = parser.parse_args()
    run(addr=args.listen, port=args.port)
