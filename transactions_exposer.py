from flask_api import FlaskAPI
from db_manager import *
import os

TRANSACTION_EXPOSER_PORT = os.environ.get('TRANSACTION_EXPOSER_PORT', '5002')

app = FlaskAPI(__name__)
db_manager = DbManager()


@app.route('/smart_accounts/<string:account_id>/smart_transactions')
def get_smart_accounts(account_id):
    return db_manager.get_smart_transactions(account_id)


def run_rest_service():
    app.run(port=TRANSACTION_EXPOSER_PORT)
