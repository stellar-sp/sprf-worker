import ipfshttpclient
import os
import base58
from binascii import hexlify, unhexlify
import base64

IPFS_ADDRESS = os.environ.get('IPFS_ADDRESS')


def load_ipfs_file(ipfs_hash):
    file_path = '/tmp/' + ipfs_hash
    with ipfshttpclient.connect(IPFS_ADDRESS) as client:
        with open(file_path, 'wb') as f:
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
