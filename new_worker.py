from api_service import run_api_service
from transaction_submitter import *
import threading
from ledger_checker import run_ledger_checker
from transaction_flooder import *
import logging

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

logging.basicConfig(format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S', level=LOG_LEVEL)

if __name__ == '__main__':
    t = threading.Thread(target=run_ledger_checker)
    t.start()

    threading.Thread(target=run_transaction_flooder).start()

    threading.Thread(target=run_api_service).start()

    threading.Thread(target=TransactionSubmitter().run_transaction_submitter).start()

    t.join()
