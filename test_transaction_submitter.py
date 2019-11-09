from transaction_submitter import *

res = TransactionSubmitter().run_transaction_submitter()

print(res["xdr"])
