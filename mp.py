from datetime import datetime
import Jitor as jt
from time import sleep 
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from timeit import default_timer as timer

def main():
    start = timer()
    scrapeFromWoo(80)
    start = timer()
    orders = getAllLocalOrders()
    cpu = cpu_count()*2
    cpu = int(cpu)
    if (len(orders)/cpu)%1==0:
        n = int(len(orders)/cpu)
    else:
        n = int(len(orders)/cpu+1)
        
    splitOrders=[orders[i:i+n] for i in range(0, len(orders), n)]
    mydb = jt.myDB()
    mydb.setup()
    with Pool(cpu) as p:
        p.map(scrapeTracking, splitOrders)
    end = timer()
    print(end-start)
    mydb.close()
    exit(0)
    updateWoo()
    exit()

def scrapeFromWoo(days):
    scraper = jt.WooScraper(days)
    raw = scraper.scrapeRawOrders()
    excluded = scraper.excludeOrdersByStatus(
        ['cancelled', 'failed', 'deliverycompleted', 'completed', 'refunded'])

    orders = scraper.extractWooData(excluded)
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

def getAllLocalOrders():
    mydb = jt.myDB()
    mydb.setup()
    lOrders = mydb.retrieveAllOrders()
    return lOrders

def scrapeTracking(lOrders):
    # lOrders = mydb.retrieveAllOrders()
    for each in lOrders:
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


# ITERATE OVER LOCAL DB. IF ORDERS ARE DELIVERED, MARK THEM COMPLETED IN WOO AND DELETE FROM LOCAL DB
# IF TRACKING STATUS [APWN, ...] SEND NOTIFICATION SMS :: TODO
# IF TRACKING STATUS != NONE AND ORDERS_STATUS != exei-apostalei:
# MARK AS EXEI APOSTALEI IN WOOCOMMERCE AND UPDATE LOCAL DB
def updateWoo():
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
            elif order.order_status in ['adynamia-epik', 'pending', 'on-hold', 'se-anamoni-katath']:
                
                delta = datetime.now() - datetime.strptime(order.date_modified.split('T')[
                                        0],  "%Y-%m-%d")
                wu = jt.WooOrderUpdater(str(order.orderid))
                if delta.days > 30:
                    c3+=1
                    wu.update('status', 'failed')
                    mydb.deleteOrder(order.orderid, order.shop)

    mydb.close()
    print('Exei paradothei: {} orders, exei apostalei: {} orders, apotiximenes: {} orders.'.format(c1,c2,c3))

if __name__ ==  '__main__':
    main()