import os
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
import ipfshttpclient
from execute_envelop import ExecutionEnvelop
from environs import Env

if os.path.exists('./.env1'):
    env = Env()
    env.read_env(path="./.env1")

HORIZON_ADDRESS = os.environ.get('HORIZON_ADDRESS')
IPFS_ADDRESS = os.environ.get('IPFS_ADDRESS')
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
        container = docker_client.containers.run(image=smart_program_image_address,
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
                transaction = create_transaction(new_state_file_hash, smart_account, sender)

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


def get_sha256_of_file(file):
    with ipfshttpclient.connect(IPFS_ADDRESS) as client:
        hash = client.add(file, only_hash=True)['Hash']
    return hash


def load_ipfs_file(ipfs_hash):
    file_path = '/tmp/' + ipfs_hash
    with ipfshttpclient.connect(IPFS_ADDRESS) as client:
        with open(file_path, 'wb') as f:
            f.write(client.cat(ipfs_hash))

    return file_path


def upload_file_to_ipfs(file):
    with ipfshttpclient.connect(IPFS_ADDRESS) as client:
        hash = client.add(file)['Hash']
    return hash


def create_transaction(new_state_hash, smart_account, user_account_public_key):
    sequence = horizon.account(smart_account['address']).get('sequence')

    operations = [
        Payment(source=user_account_public_key, destination=smart_account['address'],
                amount=smart_account['data']['execution_base_fee'], asset=Asset("XLM")),
        ManageData(data_name='current_state', data_value=new_state_hash, source=smart_account['address'])
    ]

    tx = Transaction(
        source=smart_account['address'],
        sequence=int(sequence),
        fee=1000 * len(operations),
        operations=operations
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