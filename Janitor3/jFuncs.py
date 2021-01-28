from jlib import Balance
from config import shops, sms_token, stores
from woo import Jlib
import concurrent.futures
from datetime import datetime, timedelta
import csv


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
            new.woo.active = 'No'
        elif new.woo.tracking_status != '' and new.woo.order_status not in ['cancelled', 'failed', 'deliverycompleted', 'completed', 'refunded']:
            new.woo.update('status', 'exei-apostalei')
            new.woo.order_status='exei-apostalei'
        elif new.woo.order_status in ['adynamia-epik','out-of-stock', 'pending', 'on-hold', 'se-anamoni-katath'] and new.woo.tracking_status == '':
            delta = datetime.now() - datetime.strptime(order.date_modified.split('T')[0],  "%Y-%m-%d")
            if delta.days > 35:
                new.woo.update('status', 'failed')
                new.woo.order_status='failed'
                new.woo.active = 'No'
    new.checkIfLocal()
    if new.local != None:
        new.local.save()
    else:
        new.insertLocalIfNotExists()

    
    

def bulkSaveUpdate(orders):
    threads = min(MAX_THREADS, len(orders))
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        executor.map(saveOrUpdateOrder, orders)


def scrapeLocalOrders():
    orders = Jlib.DBOrder.select().where(Jlib.DBOrder.active == 'Yes')
    l = [ order for order in orders]
    return l

def createLists():
    orders = scrapeLocalOrders()
    notificationTriggers = ['ΑΠΟΣΤΟΛΗ ΕΝΗΜΕΡΩΣΗΣ (SMS)', 'ΕΝΗΜΕΡΩΣΗ ΑΠΑΡΑΔΟΤΗΣ ΑΠΟΣΤΟΛΗΣ', 'ΠΑΡΑΛΑΒΗ ΑΠΟ ΣΤΑΘΜΟ - ΕΝΤΟΛΗ ΠΕΛΑΤΗ', 'Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΜΕΝΕΙ ΣΤΟ ΣΤΑΘΜΟ', 'ΑΠΩΝ', 'ΑΓΝΩΣΤΟΣ ΠΑΡΑΛΗΠΤΗΣ']
    sevenNonTriggers =  ['ΠΑΡΑΔΟΘΗΚΕ', 'ΕΠΙΣΤΡΟΦΗ ΑΠΑΡΑΔΟΤΟΥ','ΑΡΝΗΣΗ ΠΑΡΑΛΑΒΗΣ', 'ΕΝΗΜΕΡΩΣΗ ΑΠΑΡΑΔΟΤΗΣ ΑΠΟΣΤΟΛΗΣ', 'ΑΠΟΣΤΟΛΗ ΕΝΗΜΕΡΩΣΗΣ (SMS)', 'ΠΑΡΑΛΑΒΗ ΑΠΟ ΣΤΑΘΜΟ - ΕΝΤΟΛΗ ΠΕΛΑΤΗ', 'Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΜΕΝΕΙ ΣΤΟ ΣΤΑΘΜΟ', '']
    sevenDayList = []
    fourteenDayList = []
    ourList = []
    notificationList = []
    for order in orders:
        if order.tracking_status in notificationTriggers and order.tracking_status != '' and order.courier == 'speedex':
            # check if sms was sent. if not send sms and log
            message = Jlib.NotificationLog.select().where(Jlib.NotificationLog.orderid == order.orderid & Jlib.NotificationLog.shop ==  order.shop)
            message = [m for m in message]
            if len(message)==0:
                notificationList.append(order)

        if order.order_last_tracked != '':
            pastDays = datetime.now() - order.order_last_tracked
            pastDays = int(pastDays.days)
            

            if order.tracking_status not in sevenNonTriggers and pastDays>=7:
                sevenDayList.append(order)
            
            if order.tracking_status not in ['ΠΑΡΑΔΟΘΗΚΕ', 'ΕΠΙΣΤΡΟΦΗ ΑΠΑΡΑΔΟΤΟΥ'] and pastDays>=14:
                fourteenDayList.append(order)
            
            if order.tracking_status not in ['ΠΑΡΑΔΟΘΗΚΕ', 'ΕΠΙΣΤΡΟΦΗ ΑΠΑΡΑΔΟΤΟΥ'] and pastDays>=7:
                ourList.append(order)
    
    speedexList = sevenDayList + fourteenDayList
    speedexList = list(set(speedexList))

    return {'speedexList':speedexList, 'our':ourList, 'notification':notificationList}         

def createCsvFiles(lists):
    for each in lists:
        this = lists[each]
        thisTemp = []
        for i in this:    
            date = i.order_last_tracked.strftime("%d/%m/%Y, %H:%M:%S")
            today = datetime.now().strftime("%d-%m-%Y")
            temp = {'shop':i.shop, 'courier':i.courier, 'orderid':"'"+str(i.orderid), 'tracking':"'"+str(i.tracking) , 'status': i.tracking_status, 'last_update':date}
            thisTemp.append(temp)
        keys = thisTemp[0].keys()
        with open(each+'-List-'+today+'.csv', 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys, delimiter = '\t')
            dict_writer.writeheader()
            dict_writer.writerows(thisTemp)

def sendSms(order):
    # print(order.tracking, order.courier)
    msg = 'ΤΟ ΔΕΜΑ ΣΟΥ ΜΕ ΑΡ. ΑΠΟΣΤΟΛΗΣ {} ΕΙΝΑΙ ΣΤΟ ΚΟΝΤΙΝΟΤΕΡΟ ΚΑΤ/ΜΑ ΤΗΣ {} ΣΕ ΚΑΤΑΣΤΑΣΗ "{}". ΠΡΟΛΑΒΕ ΤΟ ΠΡΙΝ ΕΠΙΣΤΡΑΦΕΙ!'
    senders = {'homeone':'Homeone.gr', 'kidstoys':'Kidstoys.gr', 'familystore':'Familystore'}
    notification = Jlib.NotificationSMS(order.phone, senders[order.shop], sms_token)
    notification.createSMSBody(msg,(str(order.tracking), str(order.courier).upper(), order.tracking_status))
    notification.sendSms()
    return notification.sent

def logSms(order):
    pass

def sendSmsAndCreateCsv():
    lists = createLists()
    createCsvFiles(lists)
    notificationList = lists['notification']
    for each in notificationList:
        succ = sendSms(each)
        if succ:
            logSms(each)


    print(notificationList)

def getOrdersDeliveredLastDays(days):
    l = datetime.now() - timedelta(days=days)
    orders = Jlib.DBOrder.select().where(Jlib.DBOrder.order_first_tracked>l, Jlib.DBOrder.order_delivered!='')
    print(orders)
    for order in orders:
        print(order)
    
