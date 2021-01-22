from selenium import webdriver, common
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
from time import sleep
from tqdm import tqdm
from tabulate import tabulate
from smsapi.client import SmsApiComClient


class SMSBalance:
    def __init__(self, sms_token):
        client = SmsApiComClient(
            access_token=sms_token)
        r = client.account.balance()
        self.name = 'SmsApi'
        if r.points > 0.04:
            self.state = 'Ενεργό'
        else:
            self.state = 'Ανενεργό'
        self.balance = str(r.points).replace('.', ',') + ' €'

    def report(self):
        res = []
        res.append(['', '', ''])
        res.append([self.name, self.state, self.balance])
        res.append(['', '', ''])
        return res


class Chrome:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('log-level=3')
        chromedriver_autoinstaller.install()
        self.driver = webdriver.Chrome(options=chrome_options)

    def checkSkroutz(self, shops):
        self.skroutzBalance = []
        print('Scanning Skroutz stores:')
        for each in tqdm(shops):
            self.driver.get('https://merchants.skroutz.gr/merchants')
            # Eisodosz
            self.driver.find_element_by_xpath(
                '/html/body/div[1]/div/a[2]').click()
            sleep(0.2)
            # Username
            self.driver.find_element_by_xpath(
                '/html/body/div[1]/div/form/input[2]').clear()
            self.driver.find_element_by_xpath(
                '/html/body/div[1]/div/form/input[2]').send_keys(each.user)
            sleep(0.1)
            # Password
            self.driver.find_element_by_xpath(
                '/html/body/div[1]/div/form/input[3]').clear()
            self.driver.find_element_by_xpath(
                '/html/body/div[1]/div/form/input[3]').send_keys(each.pwd)
            sleep(0.1)
            # Login Button
            self.driver.find_element_by_xpath(
                '/html/body/div[1]/div/form/input[4]').click()
            sleep(1)
            # Check if multistore
            try:
                self.driver.find_element_by_xpath(
                    '/html/body/header/section/a[1]').click()
                sleep(0.1)
                self.driver.find_element_by_xpath(
                    '/html/body/main/aside/div/section/form/div/div/a/div/b').click()
                sleep(0.1)
                self.driver.find_element_by_xpath(
                    '/html/body/main/aside/div/section/form/div/div/div/ul').click()
                stores = self.driver.find_elements_by_xpath(
                    '/html/body/main/aside/div/section/form/div/div/div/ul/li')
                for i in range(len(stores)):
                    stores[i] = stores[i].get_attribute('innerText')
                for i in range(len(stores)):
                    self.driver.refresh()
                    sleep(0.5)
                    self.driver.find_element_by_xpath(
                        '/html/body/header/section/a[1]').click()
                    sleep(0.1)
                    self.driver.find_element_by_xpath(
                        '/html/body/main/aside/div/section/form/div/div/a/div/b').click()
                    sleep(0.1)
                    temp = self.driver.find_elements_by_xpath(
                        '/html/body/main/aside/div/section/form/div/div/div/ul/li')
                    for each in temp:
                        if each.get_attribute('innerText') == stores[i]:
                            each.click()
                            sleep(1.5)
                            name = self.driver.find_element_by_xpath(
                                '/html/body/header/ul/li[3]/a').text
                            state = self.driver.find_element_by_xpath(
                                '/html/body/header/ul/li[1]').text
                            balance = self.driver.find_element_by_xpath(
                                '/html/body/header/ul/li[2]').text
                            self.skroutzBalance.append(
                                ShopReport(name, state, balance))
                            break

            except:
                name = self.driver.find_element_by_xpath(
                    '/html/body/header/ul/li[3]/a').text
                state = self.driver.find_element_by_xpath(
                    '/html/body/header/ul/li[1]').text
                balance = self.driver.find_element_by_xpath(
                    '/html/body/header/ul/li[2]').text
                self.skroutzBalance.append(ShopReport(name, state, balance))
                sleep(0.3)

            # Get Data

            # Logout
            self.driver.find_element_by_xpath(
                '/html/body/header/ul/li[3]/a').click()
            sleep(0.1)
            self.driver.find_element_by_xpath(
                '/html/body/header/ul/li[3]/ul/li[9]/a').click()
            sleep(0.4)
        self.driver.close()

    def report(self):
        table = []
        for each in self.skroutzBalance:
            table.append(each.toTable())
        return table
        # print(tabulate(table, headers=['Κατάστημα', 'Κατάσταση', 'Υπόλοιπο']))


class SkroutzShop:
    def __init__(self, user, pwd):
        self.user = user
        self.pwd = pwd


class ShopReport:
    def __init__(self, name, state, balance):
        self.name = name
        self.state = state
        self.balance = balance

    def toTable(self):
        self.table = [self.name, self.state.split(
            ': ')[1], self.balance.split(': ')[1]]
        return self.table


class BalanceReport:
    def __init__(self, skroutzShops, sms_token):
        self.skroutz = []
        for each in skroutzShops:
            self.skroutz.append(SkroutzShop(
                user=each['user'], pwd=each['pwd']))
        self.sms = SMSBalance(sms_token=sms_token)
        chrome = Chrome()
        chrome.checkSkroutz(self.skroutz)
        self.report = chrome.report() + self.sms.report()

    def print(self):
        print('')
        print('Αναφορά Υπολοίπου')
        print('')
        print(tabulate(self.report, headers=[
              'Κατάστημα', 'Κατάσταση', 'Υπόλοιπο']))
