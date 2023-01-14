#!/usr/bin/env python3

import core


btc = core.db.Market.get_by_id(1)

print(btc.base.precision)
print("with prec = 8")

print("50 USD / 1200 USD == 0.04166666 BTC")
div = btc.base.div(5000000000, 120000000000)
print(div)
assert div == 4166666

print("1947.51313964 USD / 2 orders == 973.875656982 USD")
div = btc.base.div(194751313964, btc.base.transform(2))
print(div)
assert div == 97375656982

print("203.53282988 USD / 0.96900000 USD == 210.04420008 BTC")
div = btc.base.div(20353282988, 96900000)
print(div)
assert div == 21004420008

print("3078.33252386 USD / 19912.34000000 USD == 0.15459421 BTC")
div = btc.base.div(307833252386, 1991234000000)
print(div)
assert div == 15459421

print("1% of 19912.34555555 USD == 199.12345555 USD")
div = btc.base.div(1991234555555 * 1, btc.base.transform(100))
print(div)
assert div == 19912345555

print("")
print("with prec = 4")

print("50 USD / 1200 USD == 0.04166666 BTC")
div = btc.base.div(5000000000, 120000000000, prec=4)
print(div)
assert div == 4160000

print("1947.51313964 USD / 2 orders == 973.875650000 USD")
div = btc.base.div(194751313964, btc.base.transform(2), prec=4)
print(div)
assert div == 97375650000

print("203.53282988 USD / 0.96900000 USD == 210.04420000 BTC")
div = btc.base.div(20353282988, 96900000, prec=4)
print(div)
assert div == 21004420000

print("3078.33252386 USD / 19912.34000000 USD == 0.15450000 BTC")
div = btc.base.div(307833252386, 1991234000000, prec=4)
print(div)
assert div == 15450000

print("1% of 19912.34555555 USD == 199.12340000 USD")
div = btc.base.div(1991234555555 * 1, btc.base.transform(100), prec=4)
print(div)
assert div == 19912340000
