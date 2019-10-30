import base64
import tempfile

import docker

from ipfs_utils import *


def exec(smart_account, input_file, sender):
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
            return {
                "success": True,
                "modified": True,
                "new_state_file_hash": new_state_file_hash,
                "log": container_log.decode()
            }

        else:
            return {
                "success": True,
                "modified": False,
                "log": container_log.decode()
            }
    else:
        return {
            "success": False,
            "log": container_log.decode()
        }
