import os
import json
import psycopg2

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "sprf")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "sprf")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "secure_password")


class DbManager:
    __instance = None

    def __new__(cls, *args, **kwargs):
        if DbManager.__instance is None:
            DbManager.__instance = object.__new__(cls)
        return DbManager.__instance

    def __init__(self):
        self.conn = psycopg2.connect(host=POSTGRES_HOST, port=POSTGRES_PORT, database=POSTGRES_DB, user=POSTGRES_USER
                                     , password=POSTGRES_PASSWORD)
        self.init_db()

    def init_db(self):
        cur = self.conn.cursor()
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE  table_schema = 'public' \
                    AND table_name = 'configs');")
        item = cur.fetchone()
        if item[0] is False:
            cur.execute("CREATE TABLE configs(key text primary key, value text);")
            cur.execute("CREATE TABLE smart_accounts(account_id text primary key, data text)")
            cur.execute("CREATE TABLE smart_transactions(transaction_hash text primary key, smart_account_id text"
                        ", paging_token bigint, xdr text)")
            cur.close()
            self.conn.commit()

    def get_latest_checked_paging_token(self):
        cur = self.conn.cursor()
        cur.execute("select value from configs where key = 'latest_checked_paging_token'")
        item = cur.fetchone()
        if item is not None:
            return item[0]
        return 0

    def set_latest_checked_paging_token(self, value):
        cur = self.conn.cursor()
        if self.get_latest_checked_paging_token() == 0:
            cur.execute("insert into configs(key, value) values ('latest_checked_paging_token', '" + str(value) + "')")
        else:
            cur.execute("update configs set key='latest_checked_paging_token', value='" + str(
                value) + "' where key = 'latest_checked_paging_token'")

        self.conn.commit()

    def get_smart_account(self, account_id):
        cur = self.conn.cursor()
        cur.execute("select * from smart_accounts where account_id = '" + account_id + "'")
        row = cur.fetchone()
        if row is not None:
            return {
                "account_id": row[0],
                "data": row[1]
            }
        return None

    def add_or_update_smart_account(self, smart_account):
        cur = self.conn.cursor()
        json_data = json.dumps(smart_account)
        cur.execute("select account_id from smart_accounts where account_id='" + smart_account['id'] + "'")
        previous_record = cur.fetchone()
        if previous_record:
            cur.execute(
                "update smart_accounts set data='" + json_data + "' where account_id='" + smart_account['id'] + "'")
        else:
            cur.execute(
                "insert into smart_accounts(account_id, data) values('" + smart_account[
                    'id'] + "', '" + json_data + "');")
        self.conn.commit()

    def add_smart_transaction(self, smart_account_id, transaction_hash, paging_token, xdr):
        cur = self.conn.cursor()
        cur.execute(
            "insert into smart_transactions(transaction_hash, smart_account_id, paging_token, xdr) values('"
            + transaction_hash + "', '" + smart_account_id + "', " + paging_token + ", '" + xdr + "')")
        self.conn.commit()

    def get_smart_transactions(self, smart_account_id):
        cur = self.conn.cursor()
        cur.execute("select * from smart_transactions where smart_account_id = '" + smart_account_id + "'")
        return cur.fetchall()

    def get_latest_transactions(self):
        cur = self.conn.cursor()
        cur.execute("select * from smart_transactions order by paging_token desc limit 100")
        rows = cur.fetchall()
        transactions = []
        for row in rows:
            transactions.append({
                "transaction_hash": row[0],
                "smart_account_id": row[1],
                "paging_token": row[2],
                "xdr": row[3]
            })
        return transactions

    def delete_transaction(self, transaction_hash):
        cur = self.conn.cursor()
        cur.execute("delete from smart_transactions where transaction_hash='" + transaction_hash + "'")
        self.conn.commit()

# if __name__ == '__main__':
#    db = DbManager()
#    db.get_latest_transactions()
