from jlib import Balance
from woo import Jlib
from config import shops, sms_token, stores
import jFuncs
import pprint
from timeit import default_timer as timer
# from jFuncs import printBalanceReport

jFuncs.getOrdersDeliveredLastDays(2)
# pp = pprint.PrettyPrinter(indent=4)

# if False:
#     jFuncs.printBalanceReport()

if True:
    orders = jFuncs.scrapeWooOrders(3)
    print('Multithreading')
    start = timer()
    jFuncs.bulkSaveUpdate(orders)
    end = timer()

    print(end-start)


