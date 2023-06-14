import argparse
import decimal
import sys

import sliver.database as db
from sliver.asset import Asset
from sliver.exchange import Exchange
from sliver.exchange_asset import ExchangeAsset
from sliver.exchanges.factory import ExchangeFactory
from sliver.market import Market


def save_market(ex_market, exchange):
    with db.connection.atomic():
        if not ex_market["spot"]:
            return

        try:
            amount_prec = ex_market["precision"]["amount"]
            if amount_prec is None or amount_prec == 0:
                print("using default amount_prec = 8")
                amount_prec = 8
            if amount_prec < 1:
                amount_prec = decimal.Decimal(str(amount_prec)).as_tuple().exponent * -1
        except KeyError:
            print("using default amount_prec = 8")
            amount_prec = 8

        try:
            price_prec = ex_market["precision"]["price"]
            if price_prec is None or price_prec == 0:
                print("using default amount_prec = 2")
                price_prec = 2
            if price_prec < 1:
                price_prec = decimal.Decimal(str(price_prec)).as_tuple().exponent * -1
        except KeyError:
            print("using default amount_prec = 2")
            price_prec = 2

        try:
            base_prec = ex_market["precision"]["base"]
            if base_prec is None or base_prec == 0:
                print("using base_prec = amount_prec")
                base_prec = amount_prec
            if base_prec < 1:
                base_prec = decimal.Decimal(str(base_prec)).as_tuple().exponent * -1
        except KeyError:
            print("using base_prec = amount_prec")
            base_prec = amount_prec

        try:
            quote_prec = ex_market["precision"]["quote"]
            if quote_prec is None or quote_prec == 0:
                print("using quote_prec = price_prec")
                quote_prec = price_prec
            if quote_prec < 1:
                quote_prec = decimal.Decimal(str(quote_prec)).as_tuple().exponent * -1
        except KeyError:
            print("using quote_prec = price_prec")
            quote_prec = price_prec

        base, new = Asset.get_or_create(ticker=ex_market["base"])
        quote, new = Asset.get_or_create(ticker=ex_market["quote"])

        ex_b, new = ExchangeAsset.get_or_create(asset=base, exchange=exchange)
        ex_b.precision = base_prec
        ex_b.save()

        ex_q, new = ExchangeAsset.get_or_create(asset=quote, exchange=exchange)
        ex_q.precision = quote_prec
        ex_q.save()

        try:
            m = Market.get(base=ex_b, quote=ex_q)
        except Market.DoesNotExist:
            m = Market(base=ex_b, quote=ex_q)

        m.exchange = exchange
        m.symbol = m.get_symbol()
        m.amount_precision = amount_prec
        m.price_precision = price_prec

        try:
            amount_min = ex_market["limits"]["amount"]["min"]
            if amount_min is None:
                print("using default amount_min = 0.0001")
                amount_min = 0.0001
        except KeyError:
            print("using default amount_min = 0.0001")
            amount_min = 0.0001

        try:
            cost_min = ex_market["limits"]["cost"]["min"]
            if cost_min is None:
                print("using default cost_min = 10")
                cost_min = 10
        except KeyError:
            print("using default cost_min = 10")
            cost_min = 10

        try:
            price_min = ex_market["limits"]["price"]["min"]
            if price_min is None:
                print("using default price_min = 1")
                price_min = 1
        except KeyError:
            print("using default price_min = 1")
            price_min = 1

        m.amount_min = m.base.transform(amount_min)
        m.cost_min = m.quote.transform(cost_min)
        m.price_min = m.quote.transform(price_min)

        m.save()


# def fetch_markets(exchange):
#     print("fetching all markets from exchange api...")
#     ex_markets = exchange.api.fetch_markets()

#     count = 0
#     for ex_market in ex_markets:
#         save_market(ex_market, exchange)
#         count += 1

#     print(f"saved {count} new markets")


if __name__ == "__main__":
    db.init()

    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-e", "--exchange-name", help="exchange name to fetch from", required=True
    )
    argp.add_argument(
        "-s", "--symbol", help="specify a single market to fetch", required=True
    )
    args = argp.parse_args()

    try:
        base = Exchange.get(name=args.exchange_name)
    except Exchange.DoesNotExist:
        print("exchange not found in database")
        sys.exit(1)

    exchange = ExchangeFactory.from_base(base)
    exchange.api = None

    exchange.api.load_markets()  # ccxt only
    save_market(exchange.api.market(args.symbol), exchange)
