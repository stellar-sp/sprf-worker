from transaction_receiver import run_transaction_receiver
from transaction_submitter import run_transaction_submitter
import threading
from ledger_checker import run_ledger_checker
from transaction_flooder import *

if __name__ == '__main__':
    threading.Thread(target=run_transaction_receiver).start()
    threading.Thread(target=run_transaction_flooder).start()
    threading.Thread(target=run_transaction_submitter).start()

    t = threading.Thread(target=run_ledger_checker)
    t.start()
    t.join()
