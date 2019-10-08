## SPRF (Smart Program Runner Framework)

SPRF is a collection of tools that help you to run a program and track its state on a blockchain network. SPRF using normal stellar account to track changes and history of a program. Each program should have an account on stellar and some manage data field that show its current state.
There are some workers in the sidechain that can calculate the next state of a program and change manage data fields. These workers get fee from users who want change state of program by their input.

The SPRF is a framework for managing programs and their state using blockchain networks. 

### Is it possible to attach and detach an application from its state?
Yes. by using containerization technology (like docker) we can detach and attach state of an application whenever. For each deterministic application, if a state file attached to it and some input go to it, the same result will return by every execution.

### How we can track program changes and state of program changes?
SPRF using ipfs for storing program states. Isolated programs can be saved on docker registries (like DockerHub).

### Why SPRF using blockchain for tracking state?
Using a blockchain network make it easy for changing state of program by consensus. 

### Who it works?
The execution of program and changing state is very easy! The following steps creates a dapps application and change its state by consensus:
Smart Account specification:
The first step is creating an account for holding smart program information on its managed data fields. 
The fields of this account is as follows:

```markdown
  - smart_program_image_address: "DOKCER_IMAGE_ADDRESS:VERSION"
  - current_state: "HASH_OF_IPFS_FILE"
  - execution_base_fee: 100
  - worker_1_address: "API_ADDRESS_OF_WORKER1"
  - worker_2_address: "API_ADDRESS_OF_WORKER2"
  - worker_3_address: "API_ADDRESS_OF_WORKER3"
  - …
  - worker_1_public_key: "WORKER1_PUBLIC_KEY"
  - worker_2_public_key: "WORKER2_PUBLIC_KEY"
  - worker_3_public_key: "WORKER3_PUBLIC_KEY"
  - ... 
```
The signer weighs of this account should be as follow:
```markdown
  - master weight = 0
  - worker_1_pub_key = 1
  - worker_2_pub_key = 1
  - worker_3_pub_key = 1
  - ...
```
Others options:
```markdown
  - low_threshold = int(workers count / 2) + 1
  - medium_threshold = int(workers count / 2) + 1
  - high_threshold = int(workers count / 2) + 1
```
Each account can have as many workers as want. 

### Workers specification:
Each worker should have an api for accepting new incoming requests from users for running smart programs and get new state. The scenario between user and worker is as follows:

- User creates and submit a payment transaction with amount of “execution_base_fee” (specified in managed data fields in smart account) to smart account (this payment is used to avoid spam requests to workers)

- User sends program input and execution_base_fee to all workers. The user also sign this request by its private key to claim that he owns the “execution_base_fee”

- Workers start to loading program from docker registry and loading current state of program from ipfs and attaching them together and start program. After a few seconds the workers watch the docker exit status. If it exited, the worker will check the state file changes by calculating a hash of it. If the state file changed, it means that program moved to new state

- Worker create and sign an xdr and send it back to user. This xdr is a transaction with two operations. The transaction is as follows:

```markdown
Source account: SMART_ACCOUNT_PUBLIC_KEY
Operations:
    - operation type: payment
      destination account: SMART_ACCOUNT_PUBLIC_KEY
      source account: USER_ACCOUNT_PUBLIC_KEY
      amount: additional gas usage 
    - operation type: manage data
      entry name: current_state
      entry value: HASH_OF_NEW_STATE
      source account: SMART_ACCOUNT_PUBLIC_KEY
```

 The user should collect at least “int(workers count / 2) + 1” sign to be able to submit transaction to network and change the current state of program. The user should also sign the transaction because one of operations is a payment operation from user account to smart account
