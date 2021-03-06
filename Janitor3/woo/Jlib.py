import peewee as pw
from datetime import datetime, timedelta
from woocommerce import API
from tqdm import tqdm
import requests
from smsapi.client import SmsApiComClient
import json

db = pw.SqliteDatabase('janitordb.db')

def getOrderScanned(shop, orderid):
    shop = shop.title()
    url= 'https://kirosgranazis.herokuapp.com/janitor/{}/{}'.format(shop, str(orderid))
    dateScanned = requests.get(url).json()
    dateScanned = dateScanned['dateScanned']
    if dateScanned == 'None':
        return ''
    else:
        dateScanned = datetime.strptime(dateScanned, '%Y-%m-%d %H:%M:%S')
        return dateScanned

class Eltrak:
    def __init__(self, tracking, courier='speedex'):
        self.courier = courier
        self.tracking = tracking
        self.delivered = False

    def track(self):
        self.url = None
        if self.courier == 'speedex':
            self.url = 'https://eltrak.herokuapp.com/v1/track/speedex/{}'.format(
                str(self.tracking))
        elif self.courier == 'acs':
            self.url = 'https://eltrak.herokuapp.com/v1/track/acs/{}'.format(
                str(self.tracking))
        if self.url:
            self.results = requests.get(self.url).json()['updates']
        else:
            self.results = 'No data'

    def getLastState(self):
        self.track()
        self.lastState = 'No data'
        if self.results != 'No data':
            self.lastState = self.results[-1]
        return self.lastState

    def getFirstState(self):
        self.track()
        self.firstState = 'No data'
        if self.results != 'No data':
            self.firstState = self.results[0]
        return self.firstState

    def isDelivered(self):
        if self.results!='No data':
            if self.courier=='acs':
                for update in self.results:
                    if update['status']=='ΠΑΡΑΔΟΣΗ':
                        self.delivered = True
                        self.deliveredUpdate = update
                        break
            if self.courier=='speedex':
                for update in self.results:
                    if update['status']=='Η ΑΠΟΣΤΟΛΗ ΠΑΡΑΔΟΘΗΚΕ':
                        self.delivered = True
                        self.deliveredUpdate = update
                        break

class PhoneNumber:
    def __init__(self, number):
        self.rawPhone = number
        phone = ''
        for i in number:
            if i.isnumeric():
                phone+=i
        found = 0
        for i in range(len(phone)-1):
            temp = phone[i]+phone[i+1]
            if temp == '69':
                phone = phone[i:i+10]
                found = 1
                break
        if found and phone.isnumeric() and len(phone) == 10:
            self.validPhone = '0030'+str(phone)
        else:
            self.validPhone = None

class BaseModel(pw.Model):
    class Meta:
        database = db


class NotificationSMS:
    def __init__(self, phone, sender='Homeone.gr', token):
        self.sender = sender
        self.phone = phone
        try:
            self.client = SmsApiComClient(
                access_token=token)
        except:
            self.client = None

    def createSMSBody(self, body, args):
        try:
            self.SMSBody = body.format(*args)
        except:
            self.SMSBody = None

    def sendSms(self):
        if self.client and self.SMSBody:
            try:
                self.results = self.client.sms.send(
                    to=self.phone, message=self.SMSBody, normalize="1", from_=self.sender)
                self.sent = True
            except:
                self.sent = False
        else:
            self.sent = False


class NotificationLog(BaseModel):
    id = pw.AutoField()
    orderid = pw.IntegerField(null=False,)
    shop = pw.TextField(null=False,)
    action = pw.TextField(null=False,)
    timestamp = pw.TextField(null=False,)

class DBOrder(BaseModel):
    orderid = pw.IntegerField()
    shop = pw.TextField(null=False,)
    client = pw.TextField(null=True,)
    phone = pw.TextField(null=True,)
    order_status = pw.TextField(null=True,)
    courier = pw.TextField(null=True,)
    tracking = pw.TextField(null=True,)
    tracking_status = pw.TextField(null=True,)
    active = pw.TextField(null=True,)
    order_created = pw.DateTimeField(null=True,)
    order_last_update = pw.DateTimeField(null=True,)
    order_last_tracked = pw.DateTimeField(null=True,)
    order_scanned = pw.DateTimeField(null=True,)
    order_first_tracked = pw.DateTimeField(null=True,)
    order_delivered = pw.DateTimeField(null=True,)


    class Meta:
        primary_key = pw.CompositeKey('orderid', 'shop')

class WooOrder:
    def __init__(self, orderid, shop, store_data):
        self.orderid = orderid
        self.shop = shop
        self.store_data = store_data

    def update(self, key, value):
        url = 'orders/{}'.format(str(self.orderid))
        wcapi = API(
            url=self.store_data['WP_API_URL'],
            consumer_key=self.store_data['WP_API_CK'],
            consumer_secret=self.store_data['WP_API_CS'],
            wp_api=self.store_data['WP_API'],
            version=self.store_data['VERSION']
        )
        data = {str(key): str(value)}
        old = wcapi.get(url).json()[str(key)]
        if str(old) != str(value):
            wcapi.put(url, data)

class Order:
    def __init__(self, orderid, shop, store_data):
        self.orderid = orderid
        self.shop = shop
        # CHECK IF IN LOCAL STORAGE AND LOAD IF FOUND ELSE LOCAL = NONE
        # self.local = DBOrder.get_or_none(
        #     DBOrder.orderid == orderid, DBOrder.shop == shop)
        # RETRIEVE WOOCOMMERCE DATA
        self.woo = WooOrder(self.orderid, self.shop, store_data)
    
    def populateWoo(self, orderData):
        self.woo.order_status= orderData['status']
        if orderData['status'] in ['cancelled', 'failed', 'deliverycompleted', 'completed', 'refunded']:
            self.woo.active = 'No'
        else:
            self.woo.active = 'Yes'
        self.woo.client= orderData['billing']['first_name'].strip() + ' ' + orderData['billing']['last_name'].strip()
        self.woo.phone= PhoneNumber(orderData['billing']['phone']).validPhone
        self.woo.courier= ''
        self.woo.tracking= ''
        mdata = orderData['meta_data']
        for entry in mdata:
            if 'wpslash_voucher_courier' == entry['key']:
                self.woo.courier = entry['value']
            elif 'wpslash_voucher_courier_tracking' == entry['key']:
               self.woo.tracking= entry['value']
        self.woo.tracking_status= ''
        self.woo.order_created = datetime.strptime(orderData['date_created'], '%Y-%m-%dT%H:%M:%S')- timedelta(hours=1)
        self.woo.order_last_update = datetime.strptime(orderData['date_modified'], '%Y-%m-%dT%H:%M:%S')- timedelta(hours=1)
        self.woo.order_scanned = getOrderScanned(self.shop, self.orderid)
        self.woo.order_first_tracked = ''
        self.woo.order_last_tracked = ''
        self.woo.order_delivered =''

    def trackWoo(self):
        if self.woo.courier != '' and self.woo.tracking!='':
            track = Eltrak(self.woo.tracking, self.woo.courier)
            first = track.getFirstState()
            last = track.getLastState()
            if last!='No data':
                 self.woo.tracking_status= last['status']
                 self.woo.order_last_tracked = datetime.strptime(last['datetime'], '%Y-%m-%dT%H:%M:%S')
            if first != 'No data':
                first = first['datetime']
                self.woo.order_first_tracked=datetime.strptime(first, '%Y-%m-%dT%H:%M:%S')
            track.isDelivered()
            if track.delivered:
                delivered = track.deliveredUpdate
                self.woo.tracking_status= 'ΠΑΡΑΔΟΘΗΚΕ'
                self.woo.order_delivered=datetime.strptime(delivered['datetime'], '%Y-%m-%dT%H:%M:%S')

    def checkIfLocal(self):
        self.local = DBOrder.get_or_none(DBOrder.orderid == self.orderid, DBOrder.shop == self.shop)
        return self.local
    
    def insertLocalIfNotExists(self):
        self.local = DBOrder.get_or_none(DBOrder.orderid == self.orderid, DBOrder.shop == self.shop)
        if self.local == None:
            self.local = DBOrder.create(orderid=self.woo.orderid,
                shop = self.woo.shop,
                client = self.woo.client,
                phone = self.woo.phone,
                order_status = self.woo.order_status,
                courier = self.woo.courier,
                tracking = self.woo.tracking,
                active = self.woo.active,
                tracking_status = self.woo.tracking_status,
                order_created = self.woo.order_created,
                order_last_update = self.woo.order_last_update,
                order_last_tracked = self.woo.order_last_tracked,
                order_scanned = self.woo.order_scanned,
                order_first_tracked = self.woo.order_first_tracked,
                order_delivered = self.woo.order_delivered)



class WooScraper:
    def __init__(self, stores):
        self.stores = stores
        self.ordersScraped = []

    def scrape(self, days):
        after = datetime.now() - timedelta(int(days))
        after = str(after.strftime('%Y-%m-%d'))+'T00%3A00%3A00%2B00%3A00'
        before = datetime.now() - timedelta(1)
        before = str(before.strftime('%Y-%m-%d')) + \
            'T24%3A00%3A00%2B00%3A00'
        wooUrl = 'orders?per_page=100&after={}&before={}'.format(
            after, before)
        for store in self.stores:
            wcapi = API(
                url=store['WP_API_URL'],
                consumer_key=store['WP_API_CK'],
                consumer_secret=store['WP_API_CS'],
                wp_api=store['WP_API'],
                version=store['VERSION']
            )
            t = wcapi.get(wooUrl).headers
            pages = t['X-WP-TotalPages']
            url = wooUrl
            for page in tqdm(range(int(pages))):
                pg = page+1
                url += '&page='+str(pg)
                orders = wcapi.get(url).json()
                for each in orders:
                    each['store_data']=store
                    self.ordersScraped.append(each)
        return self.ordersScraped

db.connect()
db.create_tables([DBOrder, NotificationLog])
