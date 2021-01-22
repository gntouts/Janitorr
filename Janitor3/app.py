from jlib import Balance
from woo import Jlib
from config import shops, sms_token, stores
# from jFuncs import printBalanceReport
import jFuncs
import pprint
pp = pprint.PrettyPrinter(indent=4)


if False:
    jFuncs.printBalanceReport()

if True:
    orders = jFuncs.scrapeWooOrders(5)

    for order in orders:
        # print(order)
        store =  order['_links']['collection'][0]['href'].split('https://')[1].split('.gr')[0]
        new = Jlib.Order(order['id'],store)
        new.populateWoo(order)
        new.trackWoo()
        pp.pprint(vars(new.woo))

