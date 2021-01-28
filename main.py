from datetime import datetime
import Jitor as jt
from time import sleep 
from tqdm import tqdm
from timeit import default_timer as timer
kin = '6956084516'
if True:
    print('scraping orders')
    scraper = jt.WooScraper(88)
    raw = scraper.scrapeRawOrders()
    excluded = scraper.excludeOrdersByStatus(
        ['cancelled', 'failed', 'deliverycompleted', 'completed', 'refunded'])

    orders = scraper.extractWooData(excluded)

    print('saving to local db')
    # # SAVE OR UPDATE LOCAL DB WITH DATA FROM WOOCOMMERCE
    for i in tqdm(range(len(orders))):
        orders[i] = jt.WooOrder(orders[i])
        localOrder, orderOj = orders[i].getLocalOrder()
        if localOrder:
            # compare status and update local db accordingly
            if localOrder['order_status'] == orders[i].order_status:
                pass
            else:
                orders[i].updateLocalOrderStatus()
                orders[i].updateLocalDateModified()
        else:
            # insert new local order
            orders[i].saveToSQL()

if True:
    # ITERATE OVER LOCAL ORDERS AND CHECK FOR TRACKING
    print('check local orders for tracking')
    startT=timer()
    mydb = jt.myDB()
    mydb.setup()
    lOrders = mydb.retrieveAllOrders()
    for each in tqdm(lOrders):
        tDict, order = jt.WooOrder().getLocalOrder(each[0], each[1])
        if order.tracking != 'None':
            trak = jt.Eltrak(order.tracking, order.courier)
            lastStatus = trak.getLastState()
            if lastStatus != 'No data':
                if lastStatus['status'] != order.tracking_status:
                    order.tracking_status = lastStatus['status']
                    order.updateLocalTrackingStatus()
                    order.date_tracked = lastStatus['datetime']
                    order.updateLocalDateTracked()
    mydb.close()
    stopT=timer()
    print(stopT-startT)


if True:
# ITERATE OVER LOCAL DB. IF ORDERS ARE DELIVERED, MARK THEM COMPLETED IN WOO AND DELETE FROM LOCAL DB
# IF TRACKING STATUS [APWN, ...] SEND NOTIFICATION SMS :: TODO
# IF TRACKING STATUS != NONE AND ORDERS_STATUS != exei-apostalei:
# MARK AS EXEI APOSTALEI IN WOOCOMMERCE AND UPDATE LOCAL DB
    print('update woo db accordingly')
    c1 = 0
    c2 = 0
    c3 = 0

    mydb = jt.myDB()
    mydb.setup()
    lOrders = mydb.retrieveAllOrders()
    for each in tqdm(lOrders):
        # sleep(0.1)
        if each[1]=='homeone.gr':
            tDict, order = jt.WooOrder().getLocalOrder(each[0], each[1])
            if order.tracking_status == 'Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΔΟΘΗΚΕ' or order.tracking_status =='ΠΑΡΑΔΟΣΗ':
                try:
                    wu = jt.WooOrderUpdater(str(order.orderid))
                    wu.update('status', 'deliverycompleted')
                    mydb.deleteOrder(order.orderid, order.shop)
                    c1+=1
                except:
                    print(order.orderid)
            elif order.tracking_status != 'None' and order.order_status != 'exei-apostalei':
                wu = jt.WooOrderUpdater(str(order.orderid))
                try:
                    wu.update('status', 'exei-apostalei')
                    order.order_status = 'exei-apostalei'
                    order.updateLocalOrderStatus()
                    c2+=1
                except:
                    print(order.orderid)
            elif order.order_status in ['adynamia-epik','out-of-stock', 'pending', 'on-hold', 'se-anamoni-katath']:
                
                delta = datetime.now() - datetime.strptime(order.date_modified.split('T')[
                                        0],  "%Y-%m-%d")
                wu = jt.WooOrderUpdater(str(order.orderid))
                if delta.days > 35:
                    c3+=1
                    wu.update('status', 'failed')
                    mydb.deleteOrder(order.orderid, order.shop)

    mydb.close()
    print('Exei paradothei: {} orders, exei apostalei: {} orders, apotiximenes: {} orders.'.format(c1,c2,c3))

if False:
    mydb = jt.myDB()
    mydb.setup()
    lOrders = mydb.retrieveAllOrders()
    for each in tqdm(lOrders):
        sleep(0.1)
        if each[1]=='homeone.gr':
            tDict, order = jt.WooOrder().getLocalOrder(each[0], each[1])
            if order.tracking_status == 'ΕΝΗΜΕΡΩΣΗ ΑΠΑΡΑΔΟΤΗΣ ΑΠΟΣΤΟΛΗΣ' or order.tracking_status=='Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΜΕΝΕΙ ΣΤΟ ΣΤΑΘΜΟ':
                try:
                    body = 'ΕΝΗΜΕΡΩΣΗ ΑΠΑΡΑΔΟΤΗΣ ΑΠΟΣΤΟΛΗΣ: Η ΠΑΡΑΓΓΕΛΙΑ #{} ΒΡΙΣΚΕΤΑΙ ΣΤΟ KONTINOTERO ΚΑΤΑΣΤΗΜΑ ΤΗΣ SPEEDEX. ΔΕΙΤΕ ΠΕΡΙΣΣΟΤΕΡΑ: {}'
                    print(vars(order))
                    myUrl = jt.TrackingURL(order.tracking, order.courier).url
                    short = jt.UrlShortener(myUrl).shortUrl
                    myArgs = (order.orderid, short)
                    newSms = jt.NotificationSMS(order.phone)
                    newSms.createSMSBody(body, myArgs)
                    newSms.sendSms()
                except Exception as e:
                    print(e)
                    print(order.orderid)

    mydb.close()
