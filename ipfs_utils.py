import ipfshttpclient
import os
import base58
from binascii import hexlify, unhexlify
import base64
import random
import tempfile
from shutil import copyfile


class IpfsUtils:
    def __init__(self, ipfs_address=os.environ.get('IPFS_ADDRESS')):
        self.ipfs_address = ipfs_address

        IPFS_DIR = '/tmp/ipfs-files/'
        if not os.path.exists(IPFS_DIR):
            os.mkdir(IPFS_DIR)
        self.BASE_PATH = IPFS_DIR + str(random.randint(1, 10000000)) + "/"
        if not os.path.exists(self.BASE_PATH):
            os.mkdir(self.BASE_PATH)
        print("")

    def load_ipfs_file(self, ipfs_hash):
        file_path = self.BASE_PATH + ipfs_hash

        if os.path.exists(file_path):
            return file_path

        # an empty file ipfs hash
        if ipfs_hash == 'QmbFMke1KXqnYyBBWxB74N4c5SBnJMVAiMNRcGu6x1AwQH':
            temp_state_file = tempfile.mkstemp()
            copyfile(temp_state_file[1], self.BASE_PATH + ipfs_hash)
            return file_path

        with ipfshttpclient.connect(self.ipfs_address) as client:
            with open(file_path, 'wb+') as f:
                f.write(client.cat(ipfs_hash))

        return file_path

    def get_sha256_of_file(self, file):
        with ipfshttpclient.connect(self.ipfs_address) as client:
            hash = client.add(file, only_hash=True)['Hash']
        return hash

    def upload_file_to_ipfs(self, file):
        with ipfshttpclient.connect(self.ipfs_address) as client:
            hash = client.add(file)['Hash']
        return hash

    def ipfs_hash_to_base58(self, hash):
        base58_decoded = base58.b58decode(hash)
        return hexlify(base58_decoded).decode()[4:]

    def base58_to_ipfs_hash(self, base58_code):
        hex = '1220' + base64.b64decode(base58_code).hex()
        return base58.b58encode(unhexlify(hex)).decode()
