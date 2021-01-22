import requests
import json
from woocommerce import API
from smsapi.client import SmsApiComClient
from datetime import datetime, timedelta
import sqlite3
from tqdm import tqdm
import random
import string as st

token = "HzewQfbqinZr7h0BCHzldZ7kuSS62so9dVUqJtmp"  # SMSAPI
tkey = 'f5f28d9d1f07aba996f7fc6ebb26e9861cdc9'  # CUTTLY API
db = "janitor.db"  # DB PATH
hoConfig = {
    'WP_API_CK': 'ck_22934ad9232bea4e9704a40e4f9db2e5094262c2',
    'WP_API_CS': 'cs_ccc708f1da80617d0f440290638010c20c8bb038',
    'WP_API_URL': 'https://homeone.gr',
    'WP_API': True,
    'VERSION': 'wc/v3'
}

fsConfig = {
    'WP_API_CK': 'ck_471ef9efec5ede4ec40778679fa24da87fe656fd',
    'WP_API_CS': 'cs_4ed7ee9885159bb1b65f6a49d1d57b1b046f9eb9',
    'WP_API_URL': 'https://familystore.gr',
    'WP_API': True,
    'VERSION': 'wc/v3'
}

ktConfig = {
    'WP_API_CK': 'ck_07d5ee96047f66d72f9d2a9b15c2e4fd896fced1',
    'WP_API_CS': 'cs_5db00cad6afb6eb10c45ea4d5bef0873d1fcbc0c',
    'WP_API_URL': 'https://kidstoys.gr',
    'WP_API': True,
    'VERSION': 'wc/v3'
}
wooConfig =hoConfig


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


class CustomSmsApiClient:
    def __init__(self, access_token):
        self.access_token = access_token

    def create_short_url(self, url):
        name = random.choice(st.ascii_lowercase) + ''.join((random.choice(st.ascii_letters + st.digits)
                                                            for i in range(7)))
        response = requests.post('https://api.smsapi.com/short_url/links',
                                 data={
                                     'url': url, 'name': name},
                                 auth=BearerAuth(self.access_token))
        response = json.loads(response.content)
        try:
            return response['short_url']
        except:
            return None


class UrlShortener:
    def __init__(self, longUrl):
        global token
        self.longUrl = longUrl
        self.shortUrl = None
        retries = 0
        while retries < 5 and self.shortUrl == None:
            client = CustomSmsApiClient(
                access_token=token)
            self.shortUrl = client.create_short_url(
                self.longUrl).replace('www.', '')
            if self.shortUrl != None:
                retries += 5
            else:
                retries += 1



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


class TrackingURL:
    global tkey

    def __init__(self, tracking, courier):
        self.courier = str(courier)
        self.tracking = str(tracking)
        if self.courier == 'speedex':
            self.url = 'http://www.speedex.gr/isapohi.asp?voucher_code={}&searcggo=Submit'.format(
                str(tracking))
        elif self.courier == 'acs':
            pass
            # tKey = 'f5f28d9d1f07aba996f7fc6ebb26e9861cdc9'
            # body = {'key': tKey, 'short': self.long, 'name': ''}
            # try:
            #     r = requests.get('https://cutt.ly/api/api.php', body)
            #     self.short = json.loads(r.text)['url']['shortLink']
            # except:
            #     self.short = None


class NotificationSMS:
    def __init__(self, phone, sender='Homeone.gr'):
        global token
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


class WooOrderUpdater:
    def __init__(self, orderId):
        global wooConfig
        self.wooUrl = 'orders/{}'.format(str(orderId))
        self.wcapi = API(
            url=wooConfig['WP_API_URL'],
            consumer_key=wooConfig['WP_API_CK'],
            consumer_secret=wooConfig['WP_API_CS'],
            wp_api=wooConfig['WP_API'],
            version=wooConfig['VERSION']
        )

    def update(self, field, value):
        data = {str(field): str(value)}
        old = self.wcapi.get(self.wooUrl).json()[str(field)]
        if str(old) != str(value):
            self.wcapi.put(self.wooUrl, data)


class WooOrderDelete:
    def __init__(self, orderId):
        global wooConfig
        self.wooUrl = 'orders/{}'.format(str(orderId))
        self.wcapi = API(
            url=wooConfig['WP_API_URL'],
            consumer_key=wooConfig['WP_API_CK'],
            consumer_secret=wooConfig['WP_API_CS'],
            wp_api=wooConfig['WP_API'],
            version=wooConfig['VERSION']
        )

    def delete(self):    
        response = self.wcapi.delete(self.wooUrl, params={"force": True}).json()
        return response

class WooScraper:
    def __init__(self, daysBefore):
        global wooConfig
        after = datetime.now() - timedelta(int(daysBefore))
        self.after = str(after.strftime('%Y-%m-%d'))+'T00%3A00%3A00%2B00%3A00'
        before = datetime.now() - timedelta(1)
        self.before = str(before.strftime('%Y-%m-%d')) + \
            'T24%3A00%3A00%2B00%3A00'
        self.wooUrl = 'orders?per_page=100&after={}&before={}'.format(
            self.after, self.before)
        self.wcapi = API(
            url=wooConfig['WP_API_URL'],
            consumer_key=wooConfig['WP_API_CK'],
            consumer_secret=wooConfig['WP_API_CS'],
            wp_api=wooConfig['WP_API'],
            version=wooConfig['VERSION']
        )
        t = self.wcapi.get(self.wooUrl).headers
        self.pages = t['X-WP-TotalPages']
        self.orders = t['X-WP-Total']

    def scrapeRawOrders(self):
        self.rawOrders = []
        url = self.wooUrl
        for page in tqdm(range(int(self.pages))):
            pg = page+1
            url += '&page='+str(pg)
            orders = self.wcapi.get(url).json()
            for each in orders:
                self.rawOrders.append(each)
        return self.rawOrders

    def excludeOrdersByStatus(self, statusList, orders=''):
        if orders == '':
            orders = self.rawOrders
        self.filteredOrders = []
        for each in orders:
            if each['status'] not in statusList:
                self.filteredOrders.append(each)
        return self.filteredOrders

    def excludeOrdersByShipping(self, orders=''):
        if orders == '':
            orders = self.rawOrders
        self.filteredOrders = []
        for each in orders:
            mdata = each['meta_data']
            for entry in mdata:
                if 'wpslash_voucher_courier' == entry['key']:
                    self.filteredOrders.append(each)
        return self.filteredOrders

    def extractWooData(self, orders=''):
        global wooConfig
        if orders == '':
            orders = self.filteredOrders
        self.extractedOrders = []
        for each in orders:
            t = {'orderid': each['id'], 'order_status': each['status'],
                 'shop':  wooConfig['WP_API_URL'].replace('https://', '')}
            t['client_name'] = each['billing']['first_name'] + \
                ' '+each['billing']['last_name']
            t['phone'] = each['billing']['phone']
            t['date_modified'] = each['date_modified']
            mdata = each['meta_data']
            for entry in mdata:
                if 'wpslash_voucher_courier' == entry['key']:
                    t['courier'] = entry['value']
                elif 'wpslash_voucher_courier_date' == entry['key']:
                    t['date_shipped'] = entry['value']
                elif 'wpslash_voucher_courier_tracking' == entry['key']:
                    t['tracking'] = entry['value']
            self.extractedOrders.append(t)
        return self.extractedOrders


class Eltrak:
    def __init__(self, tracking, courier='speedex'):
        self.courier = courier
        self.tracking = tracking

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


class myDB:
    def __init__(self):
        global db
        self.conn = None
        try:
            self.conn = sqlite3.connect(db)
        except:
            pass

    def setup(self):
        query = """CREATE TABLE IF NOT EXISTS orders (
                                    orderid integer NOT NULL,
                                    shop text NOT NULL,
                                    client_name text,
                                    order_status text,
                                    courier text,
                                    tracking text,
                                    tracking_status text,
                                    phone text,
                                    date_modified text,
                                    date_shipped text,
                                    date_tracked text,
                                    PRIMARY KEY (orderid, shop)
                                );"""
        if self.conn:
            c = self.conn.cursor()
            c.execute(query)
        return self.conn

    def insertOrder(self, p):
        sql = """INSERT OR IGNORE INTO orders(orderid, shop, client_name, order_status, courier, tracking, tracking_status, phone, date_modified, date_shipped, date_tracked)
              VALUES ({}, '{}', '{}', '{}', '{}','{}', '{}','{}', '{}', '{}', '{}')""".format(
            str(p['orderid']).replace("'", ""),
            str(p['shop']).replace("'", ""),
            str(p['client_name']).replace("'", ""),
            str(p['order_status']).replace("'", ""),
            str(p['courier']).replace("'", ""),
            str(p['tracking']).replace("'", ""),
            str(p['tracking_status']).replace("'", ""),
            str(p['phone']).replace("'", ""),
            str(p['date_modified']).replace("'", ""),
            str(p['date_shipped']).replace("'", ""),
            str(p['date_tracked']).replace("'", ""))
        c = self.conn.cursor()
        c.execute(sql)
        self.conn.commit()

    def updateOrder(self, orderid, shop,  field, value):
        sql = """UPDATE orders
                SET {} =  '{}'
                WHERE
                    shop='{}'
                AND
                    orderid={}""".format(str(field), str(value), str(shop), str(orderid))
        c = self.conn.cursor()
        c.execute(sql)
        self.conn.commit()

    def deleteOrder(self, orderid, shop):
        sql = """DELETE FROM orders
                WHERE
                    shop='{}' AND orderid={}""".format(str(shop), str(orderid))
        c = self.conn.cursor()
        c.execute(sql)
        self.conn.commit()

    def retrieveAllOrders(self):
        sql = """SELECT * FROM orders;"""
        c = self.conn.cursor()
        c.execute(sql)
        b = c.fetchall()
        self.conn.commit()
        return b

    def retrieveWhereOrders(self, field, value):
        sql = """SELECT * FROM orders
                WHERE {} = '{}';""".format(str(field), str(value))
        c = self.conn.cursor()
        c.execute(sql)
        b = c.fetchall()
        self.conn.commit()
        return b

    def retrieveOrder(self, shop, orderid):
        sql = """SELECT * FROM orders
                WHERE shop = "{}" AND orderid = {};""".format(str(shop), str(orderid))
        c = self.conn.cursor()
        c.execute(sql)
        b = c.fetchone()
        self.conn.commit()
        return b

    def close(self):
        self.conn.commit()
        self.conn.close()


class WooOrder:
    def __init__(self, data={}):
        if 'orderid' in data:
            self.orderid = data['orderid']
        else:
            self.orderid = None
        if 'order_status' in data:
            self.order_status = data['order_status']
        else:
            self.order_status = None
        if 'shop' in data:
            self.shop = data['shop']
        else:
            self.shop = None
        if 'client_name' in data:
            self.client_name = data['client_name']
        else:
            self.client_name = None
        if 'phone' in data:
            self.phone = PhoneNumber(data['phone']).validPhone
        else:
            self.phone = None
        if 'date_modified' in data:
            self.date_modified = data['date_modified']
        else:
            self.date_modified = None
        if 'courier' in data:
            self.courier = data['courier']
        else:
            self.courier = None
        if 'tracking' in data:
            self.tracking = data['tracking']
        else:
            self.tracking = None
        if 'date_shipped' in data:
            self.date_shipped = data['date_shipped']
        else:
            self.date_shipped = None
        if 'date_tracked' in data:
            self.date_tracked = data['date_tracked']
        else:
            self.date_tracked = None
        if 'tracking_status' in data:
            self.tracking_status = data['tracking_status']
        else:
            self.tracking_status = None

    def saveToSQL(self):
        sql = myDB()
        sql.setup()
        sql.insertOrder(vars(self))

    def existsInSQL(self):
        sql = myDB()
        sql.setup()
        b = sql.retrieveOrder(self.shop, self.orderid)
        if b is None:
            return False
        else:
            return True

    def getLocalOrder(self, orderid='', shop=''):
        t = None
        sql = myDB()
        sql.setup()
        if self.shop != None:
            shop = self.shop
        if self.orderid != None:
            orderid = self.orderid
        b = sql.retrieveOrder(shop, orderid)
        if b is not None:
            t = {}
            t['orderid'] = b[0]
            self.orderid = b[0]
            t['shop'] = b[1]
            self.shop = b[1]
            t['client_name'] = b[2]
            self.client_name = b[2]
            t['order_status'] = b[3]
            self.order_status = b[3]
            t['courier'] = b[4]
            self.courier = b[4]
            t['tracking'] = b[5]
            self.tracking = b[5]
            t['tracking_status'] = b[6]
            self.tracking_status = b[6]
            t['phone'] = b[7]
            self.phone = b[7]
            t['date_modified'] = b[8]
            self.date_modified = b[8]
            t['date_shipped'] = b[9]
            self.date_shipped = b[9]
            t['date_tracked'] = b[10]
            self.date_tracked = b[10]
        return t, self

    def updateLocalOrderStatus(self):
        sql = myDB()
        sql.setup()
        sql.updateOrder(self.orderid, self.shop,
                        'order_status', self.order_status)

    def updateLocalDateModified(self):
        sql = myDB()
        sql.setup()
        sql.updateOrder(self.orderid, self.shop,
                        'date_modified', self.date_modified)

    def updateLocalTrackingStatus(self):
        sql = myDB()
        sql.setup()
        sql.updateOrder(self.orderid, self.shop,
                        'tracking_status', self.tracking_status)

    def updateLocalDateTracked(self):
        sql = myDB()
        sql.setup()
        sql.updateOrder(self.orderid, self.shop,
                        'date_tracked', self.date_tracked)

    def updateWCOrderStatus(self):
        pass
