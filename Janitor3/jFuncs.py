from jlib import Balance
from config import shops, sms_token, stores
from woo import Jlib

def printBalanceReport(shops=shops, sms_token=sms_token):
    report = Balance.BalanceReport(shops, sms_token)
    report.print()

def scrapeWooOrders(days):
    scraper = Jlib.WooScraper(stores)
    scraper.scrape(days)
    orders = scraper.ordersScraped
    return orders