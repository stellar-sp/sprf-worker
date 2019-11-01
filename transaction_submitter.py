import os
import time
import redis
from stellar_base.horizon import Horizon
from db_manager import *

HORIZON_ADDRESS = os.environ.get("HORIZON_ADDRESS")
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")

horizon = Horizon(HORIZON_ADDRESS)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
db_manager = DbManager()


def submit_possible_transactions():
    while True:
        for key in r.scan_iter():
            res = horizon.submit(r.get(key))
            if hasattr(res, 'ledger'):
                r.delete(key)
                db_manager.delete_transaction(key)
        time.sleep(2)
