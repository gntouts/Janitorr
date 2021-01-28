from jlib import Balance
from config import shops, sms_token, stores
from woo import Jlib
import concurrent.futures
from datetime import datetime, timedelta


MAX_THREADS = 30


def printBalanceReport(shops=shops, sms_token=sms_token):
    report = Balance.BalanceReport(shops, sms_token)
    report.print()

def scrapeWooOrders(days):
    scraper = Jlib.WooScraper(stores)
    scraper.scrape(days)
    orders = scraper.ordersScraped
    return orders

def saveOrUpdateOrder(order):
    store =  order['_links']['collection'][0]['href'].split('https://')[1].split('.gr')[0]
    new = Jlib.Order(order['id'],store, order['store_data'])
    new.populateWoo(order)

    if new.woo.active == 'Yes':
        new.trackWoo()
        if new.woo.tracking_status in ['Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΔΟΘΗΚΕ', 'ΠΑΡΑΔΟΘΗΚΕ', 'ΠΑΡΑΔΟΣΗ']:
            new.woo.update('status', 'deliverycompleted')
            new.woo.order_status='deliverycompleted'
        elif new.woo.tracking_status != '' and new.woo.order_status not in ['cancelled', 'failed', 'deliverycompleted', 'completed', 'refunded']:
            new.woo.update('status', 'exei-apostalei')
            new.woo.order_status='exei-apostalei'
        elif new.woo.order_status in ['adynamia-epik','out-of-stock', 'pending', 'on-hold', 'se-anamoni-katath']:
            delta = datetime.now() - datetime.strptime(order.date_modified.split('T')[0],  "%Y-%m-%d")
            if delta.days > 35:
                new.woo.update('status', 'failed')
                new.woo.order_status='failed'
                new.woo.active = 'No'
        elif new.woo.tracking_status in ['ΑΓΝΩΣΤΟΣ', 'ΑΠΩΝ', 'ΑΠΟΣΤΟΛΗ ΣΜΣ', 'ΚΤΛ']:
            # notify client via sms
            pass
        else:
            pass
    else:
        pass
    new.checkIfLocal()
    if new.local != None:
        new.local.save()
    else:
        new.insertLocalIfNotExists()

def bulkSaveUpdate(orders):
    threads = min(MAX_THREADS, len(orders))
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        executor.map(saveOrUpdateOrder, orders)


def getOrdersDeliveredLastDays(days):
    l = datetime.now() - timedelta(days=days)
    orders = Jlib.DBOrder.select().where(Jlib.DBOrder.order_first_tracked>l, Jlib.DBOrder.order_delivered!='')
    print(orders)
    for order in orders:
        print(order)
    