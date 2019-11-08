import ipfshttpclient
import os
import base58
from binascii import hexlify, unhexlify
import base64
import random

IPFS_ADDRESS = os.environ.get('IPFS_ADDRESS')
IPFS_DIR = '/tmp/ipfs-files/'
if not os.path.exists(IPFS_DIR):
    os.mkdir(IPFS_DIR)

BASE_PATH = IPFS_DIR + str(random.randint(1, 10000000)) + "/"
if not os.path.exists(BASE_PATH):
    os.mkdir(BASE_PATH)


def load_ipfs_file(ipfs_hash):
    file_path = BASE_PATH + ipfs_hash

    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    with ipfshttpclient.connect(IPFS_ADDRESS) as client:
        with open(file_path, 'wb+') as f:
            f.write(client.cat(ipfs_hash))

    return file_path


def get_sha256_of_file(file):
    with ipfshttpclient.connect(IPFS_ADDRESS) as client:
        hash = client.add(file, only_hash=True)['Hash']
    return hash


def upload_file_to_ipfs(file):
    with ipfshttpclient.connect(IPFS_ADDRESS) as client:
        hash = client.add(file)['Hash']
    return hash


def ipfs_hash_to_base58(hash):
    base58_decoded = base58.b58decode(hash)
    return hexlify(base58_decoded).decode()[4:]


def base58_to_ipfs_hash(base58_code):
    hex = '1220' + base64.b64decode(base58_code).hex()
    return base58.b58encode(unhexlify(hex)).decode()
