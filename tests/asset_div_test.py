#!/usr/bin/env python3

import sliver.core

with sliver.core.connection.atomic():
    base_asset = sliver.core.Asset(ticker="BTC_test")
    base_asset.save()

    quote_asset = sliver.core.Asset(ticker="USD_test")
    quote_asset.save()

    exchange = sliver.core.Exchange(name="Tester")
    exchange.save()

    base_ex_asset = sliver.core.ExchangeAsset(
        asset=base_asset, exchange=exchange, precision=8
    )
    base_ex_asset.save()

    quote_ex_asset = sliver.core.ExchangeAsset(
        asset=quote_asset, exchange=exchange, precision=2
    )
    quote_ex_asset.save()

    market = sliver.core.Market(
        base=base_ex_asset,
        quote=quote_ex_asset,
        price_precision=2,
        amount_precision=8,
        symbol="BTC/USDT",
        exchange_id=exchange.id,
    )
    market.save()

    print("with prec = 8")

    print("50 USD / 1200 USD == 0.04166666 BTC")
    div = market.base.div(5000000000, 120000000000)
    print(div)
    assert div == 4166666

    print("1947.51313964 USD / 2 orders == 973.875656982 USD")
    div = market.base.div(194751313964, market.base.transform(2))
    print(div)
    assert div == 97375656982

    print("203.53282988 USD / 0.96900000 USD == 210.04420008 BTC")
    div = market.base.div(20353282988, 96900000)
    print(div)
    assert div == 21004420008

    print("3078.33252386 USD / 19912.34000000 USD == 0.15459421 BTC")
    div = market.base.div(307833252386, 1991234000000)
    print(div)
    assert div == 15459421

    print("1% of 19912.34555555 USD == 199.12345555 USD")
    div = market.base.div(1991234555555 * 1, market.base.transform(100))
    print(div)
    assert div == 19912345555

    print("")
    print("with prec = 4")

    print("50 USD / 1200 USD == 0.04166666 BTC")
    div = market.base.div(5000000000, 120000000000, prec=4)
    print(div)
    assert div == 4160000

    print("1947.51313964 USD / 2 orders == 973.875650000 USD")
    div = market.base.div(194751313964, market.base.transform(2), prec=4)
    print(div)
    assert div == 97375650000

    print("203.53282988 USD / 0.96900000 USD == 210.04420000 BTC")
    div = market.base.div(20353282988, 96900000, prec=4)
    print(div)
    assert div == 21004420000

    print("3078.33252386 USD / 19912.34000000 USD == 0.15450000 BTC")
    div = market.base.div(307833252386, 1991234000000, prec=4)
    print(div)
    assert div == 15450000

    print("1% of 19912.34555555 USD == 199.12340000 USD")
    div = market.base.div(1991234555555 * 1, market.base.transform(100), prec=4)
    print(div)
    assert div == 19912340000

    base_asset = sliver.core.Asset(ticker="DMD_test")
    base_asset.save()

    exchange = sliver.core.Exchange(name="Tester2")
    exchange.save()

    base_ex_asset = sliver.core.ExchangeAsset(
        asset=base_asset, exchange=exchange, precision=6
    )
    base_ex_asset.save()

    quote_ex_asset = sliver.core.ExchangeAsset(
        asset=quote_asset, exchange=exchange, precision=2
    )
    quote_ex_asset.save()

    market = sliver.core.Market(
        base=base_ex_asset,
        quote=quote_ex_asset,
        price_precision=2,
        amount_precision=6,
        symbol="DMD/USDT",
        exchange_id=exchange.id,
    )
    market.save()

    print("")
    print("4097.72 USD / 485.048052 DMD == 8.44 USD")
    div = market.base.div(409772, 485048052)
    print(div)
    assert div == 844

    sliver.core.connection.rollback()
