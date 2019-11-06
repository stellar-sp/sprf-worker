from api_service import run_api_service
from transaction_submitter import run_transaction_submitter
import threading
from ledger_checker import run_ledger_checker
from transaction_flooder import *
import logging
import time

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=LOG_LEVEL)

if __name__ == '__main__':
    threading.Thread(target=run_api_service).start()
    time.sleep(2)
    threading.Thread(target=run_transaction_flooder).start()
    threading.Thread(target=run_transaction_submitter).start()

    t = threading.Thread(target=run_ledger_checker)
    t.start()
    t.join()
