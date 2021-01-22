from datetime import datetime
import Jitor as jt
from time import sleep
from tqdm import tqdm
import pickle


def doThePickle(source, dest):
    with open(dest, 'wb') as out:
        pickle.dump(source, out)

def readThePickle(source):
    with open(source, 'rb') as out:
        unpickled = pickle.load(out)
    return unpickled


scraper=jt.WooScraper(365*5)
raw = scraper.scrapeRawOrders()


doThePickle(raw, 'allOrders-Kidstoys.pkl')
exit()

# b = readThePickle('allOrders-FS.pkl')

# for each in b:
#     id = each['id']
#     dateModified = each['date_modified'].split('T')[0]
#     dateModified = datetime.strptime(dateModified, "%Y-%m-%d")
#     delta =  datetime.now() - dateModified
#     delta = delta.days
#     if delta > 80:
#         input(id)
#         bye = jt.WooOrderDelete(id)
#         res = bye.delete()
#         print(res)
    