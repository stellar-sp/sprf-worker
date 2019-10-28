import ipfshttpclient
import os


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
