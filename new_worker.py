from transaction_receiver import run_rest_service
import threading
from ledger_checker import run_ledger_checker

if __name__ == '__main__':
    rest_service_thread = threading.Thread(target=run_rest_service)
    rest_service_thread.start()

    threading.Thread(target=run_ledger_checker).start()

    rest_service_thread.join()
