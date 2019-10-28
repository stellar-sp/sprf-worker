import sqlite3
import os

DB_FILE = os.environ.get("DB_FILE")


class DbManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.init_db()

    def init_db(self):
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='configs';")
        item = cur.fetchone()
        if item is None:
            cur.execute("CREATE TABLE configs(key text, value text);")

    def get_latest_checked_paging_token(self):
        cur = self.conn.cursor()
        item = cur.execute("select value from configs where key = 'latest_checked_paging_token'").fetchone()
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
        item = cur.execute("select * from smart_accounts where account_id = '" + account_id + "'").fetchone()
        if item is not None:
            return item[0]
        return None
