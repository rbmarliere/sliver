import argparse
import datetime
import os
import re
import ssl

import pandas
import peewee
import requests
import tweepy
import urllib3

import core
import strategies


TRACKED_USERS = [
    "22loops", "Amdtrades", "Ameba_NM", "Anbessa100", "AnondranCrypto",
    "AstroCryptoGuru", "Astrones2", "BITCOINTRAPPER", "BTC3P0", "BTCVIX",
    "BTC_JackSparrow", "BTC_y_tho", "Benaskren", "BigCheds", "BigChonis",
    "BitBitCrypto", "Bit_Fink", "BitcoinMunger", "BitcoinRiot", "BitcoinTina",
    "BrencJ", "BullChain", "ByzGeneral", "CL207", "CRYPT0HULK",
    "CanteringClark", "CarpeNoctom", "CastilloTrading", "ChartAlertsIO",
    "ChartVampire", "ChartsBtc", "CleverCryptoDog", "CobraBitcoin",
    "ColdBloodShill", "CosmonautC", "CredibleCrypto", "Crypt0Entropy",
    "Crypt0_kenny", "CryptoBoss1984", "CryptoCapo", "CryptoCharles__",
    "CryptoCourage1", "CryptoKaleo", "CryptoKea", "CryptoLeos", "CryptoLimbo_",
    "CryptoMaestro", "CryptoMichNL", "CryptoNewton", "CryptoParadyme",
    "CryptoShadowOff", "CryptoTrooper_", "CryptoUB", "CryptoWizardd",
    "Crypto_Gambit_", "Crypto_Horseman", "Crypto_Jeremiah", "Crypto_Scofield",
    "Cryptorphic1", "DTCcryptotrades", "DaanCrypto", "DanCrypto",
    "DaveCrypto83", "EmperorBTC", "FangTrades", "FeraSY1", "FizeekMoney",
    "Flex__Trades", "FlyBull3", "George1Trader", "Glimmerycoin",
    "HackermanAce", "Hayess5178", "HerroCrypto", "HsakaTrades", "HxroDaily",
    "IamBitmannn", "IamCryptoWolf", "IchimokuScholar", "ImNotTheWolf",
    "IncomeSharks", "IrnCrypt", "J0hnnyw00", "JJcycles", "Jsterz", "KRTrades_",
    "KevinSvenson_", "KoroushAK", "LLLuckyl", "LightCrypto", "Lord_Ashdrake",
    "MMcrypto", "MacnBTC", "MacroCRG", "Mesawine1", "Mojo_Crypto_BTC",
    "MoonOverlord", "Murfski", "MuroCrypto", "NinjaCryptoCoin", "Ninjascalp",
    "OtsukimiCrypto", "Pentosh1", "PhilakoneCrypto", "PositiveCrypto",
    "Psolemn", "QuantRob", "RodMaartin", "RookieXBT", "RyanDraycott",
    "SMtrades_", "SalsaTekila", "Satosheye", "ShardiB2", "SmartContracter",
    "SnatchProfits", "StackinBits", "StockCats", "SwenLink", "THE_FLASH_G",
    "TXWestCapital", "Teaching_Crypto", "TheCryptoDog", "TheCryptomist",
    "TheEuroSniper", "TheMoonCarl", "ThePsychoBot", "TheSeanNance",
    "TheTradingHubb", "ThinkingUSD", "Timeless_Crypto", "Trader2000X",
    "TraderAditya", "TraderKoz", "TraderMagus", "TraderReno", "Trader_xB",
    "Tradermayne", "TradingMotives", "TradySlim", "TrendSpider",
    "TrueCrypto28", "UltraXBT", "VEGETACRYPTO1", "Workedia", "Yodaskk",
    "alanizBTC", "alpha_algo", "anndylian", "ape_rture", "balajis",
    "bearshakalaka", "btcharlatan", "bullshakalaka", "caprioleio", "cburniske",
    "chartstreamer", "coinpocalypse", "coinstechnical", "crypto_Off",
    "crypto_birb", "crypto_iso", "crypto_mak", "cryptodude999", "cryptokita",
    "cryptolimbo_", "cryptomagnified", "cryptomeowmeow", "cryptosham",
    "cryptowhitewalk", "cryptoyoda1338", "cyrii_MM", "davthewave", "devchart",
    "digitalikNet", "easyeight08", "edwardmorra_btc", "ericjuta", "filbfilb",
    "fozcrypto", "galaxyBTC", "glassnode", "greektoshi", "h_bitcoiner",
    "high_fades", "im_goomba", "imkeshav", "j0hnw00", "jackis_trader",
    "jimtalbot", "joshnomics", "loomdart", "lunarCRUSH", "lunatictrader1",
    "mark_cullen", "mason_jang", "moonshilla", "mysteryta47",
    "nebraskangooner", "oilermanhockey", "parabolictrav", "polar_hunt",
    "pushpendrakum", "raticoin1", "realadamli", "redxbt", "rektcapital",
    "santimentfeed", "satsbuyer", "scottmelker", "singhsoro", "squatch_crypto",
    "stonXBT", "teaching_crypto", "thalamu_", "thecryptomars", "theo_crypto99",
    "therealgoldbug1", "thetaseek", "tmttraders", "trader1sz", "vortexics82",
    "walter_wyckoff", "xxstevelee"
]


class Stream(tweepy.StreamingClient):

    def on_connection_error(self):
        core.watchdog.warning("connection error")
        super().on_connection_error()

    def on_disconnect(self):
        core.watchdog.warning("disconnected")
        super().on_disconnect()

    def on_exception(self, exception):
        core.watchdog.error("got exception", exception)
        super().on_exception(exception)

    def on_errors(self, errors):
        core.watchdog.error("got errors", errors)
        super().on_errors(errors)

    def on_request_error(self, status_code):
        core.watchdog.error("got request error", status_code)
        super().on_request_error(status_code)

    def on_tweet(self, status):
        # ignore replies
        if status.in_reply_to_user_id:
            return

        time = datetime.datetime.utcnow(),
        text = status.text

        # make the tweet single-line
        text = re.sub("\n", " ", text).strip()
        text = re.sub("\r", " ", text).strip()
        # remove any tab character
        text = re.sub("\t", " ", text).strip()

        # log to stdin
        core.watchdog.info(text)
        tweet = strategies.hypnox.HypnoxTweet(time=time, text=text)
        try:
            tweet.save()
        except Exception as e:
            if (isinstance(e, peewee.InterfaceError)
                    or isinstance(e, peewee.OperationalError)):
                core.db.connection.close()
                try:
                    core.db.connection.connect(reuse_if_open=True)
                    tweet.save()
                except peewee.OperationalError:
                    core.watchdog.warning(
                        "couldn't reestablish connection to database!")

                    # log to cache csv
                    core.watchdog.error(
                        "error on inserting, caching instead...", e)
                    output = pandas.DataFrame({
                        "time": [time],
                        "text": [text]
                    })
                    cache_file = core.config["LOGS_DIR"] + "/cache.tsv"
                    with open(cache_file, "a") as f:
                        output.to_csv(f,
                                      header=f.tell() == 0,
                                      mode="a",
                                      index=False,
                                      sep="\t")


def get_uids():
    uids = []
    client = tweepy.Client(core.config["TWITTER_BEARER_TOKEN"])

    for username in TRACKED_USERS:
        user = client.get_user(username=username)
        if user.errors:
            core.watchdog.info("user {u} not found".format(u=user))
            continue
        uids.append(user.data.id)

    return uids


def get_rules(uids):
    all_rules = []
    curr_rule = []

    for uid in uids:
        new_rule_str = "from:{u}".format(u=uid)
        curr_rule_str = " OR ".join(curr_rule + [new_rule_str])

        if len(curr_rule_str) > 512:
            curr_rule_str = " OR ".join(curr_rule)
            all_rules.append(tweepy.StreamRule(curr_rule_str))
            curr_rule = [new_rule_str]

        curr_rule.append(new_rule_str)

    all_rules.append("lang:en -is:retweet")

    return all_rules


def stream(args):
    core.watchdog.set_logger("stream")

    if (core.config["TWITTER_BEARER_TOKEN"] == ""):
        raise core.errors.BaseError("missing TWITTER_BEARER_TOKEN!")

    stream = Stream(core.config["TWITTER_BEARER_TOKEN"])

    core.watchdog.info("reading users")
    uids_file = core.config["LOGS_DIR"] + "/user_ids.txt"
    if args.users or not os.path.isfile(uids_file):
        core.watchdog.info("storing user ids")
        try:
            os.remove(uids_file)
        except FileNotFoundError:
            pass
        uids = get_uids()
    else:
        uids = open(uids_file, "r").read().splitlines()

    core.watchdog.info("reading rules")
    if args.rules:
        core.watchdog.info("storing rules")

        curr_rules = stream.get_rules()
        if curr_rules.data:
            stream.delete_rules([rule.id for rule in curr_rules.data])

        stream.add_rules(get_rules(uids))

    core.watchdog.info("streaming...")
    while not stream.running:
        try:
            stream.filter()
        except (requests.exceptions.Timeout, ssl.SSLError,
                urllib3.exceptions.ReadTimeoutError,
                requests.exceptions.ConnectionError) as e:
            core.watchdog.error("network error", e)
        except Exception as e:
            core.watchdog.error("unexpected error", e)
        except KeyboardInterrupt:
            core.watchdog.info("got keyboard interrupt")
            break


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--rules", action="store_true")
    argp.add_argument("--users", action="store_true")
    args = argp.parse_args()
    stream(args)
