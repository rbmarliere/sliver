import datetime
import os
import re
import ssl

import pandas
import requests
import tweepy
import urllib3

import core

TRACK_USERS = [
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

cache_file = core.config["HYPNOX_LOGS_DIR"] + "/cache.tsv"


class Stream(tweepy.Stream):

    def on_status(self, status):
        # ignore retweets
        if "retweeted_status" in status._json:
            return
        # ignore replies
        if status._json["in_reply_to_user_id"]:
            return
        # if tweet is truncated, get all text
        if "extended_tweet" in status._json:
            text = status.extended_tweet["full_text"]
        else:
            text = status.text
        # make the tweet single-line
        text = re.sub("\n", " ", text).strip()
        text = re.sub("\r", " ", text).strip()
        # remove any tab character
        text = re.sub("\t", " ", text).strip()
        # format data
        time_with_tz = datetime.datetime.strptime(status._json["created_at"],
                                                  "%a %b %d %H:%M:%S %z %Y")
        time = datetime.datetime.utcfromtimestamp(time_with_tz.timestamp())

        # log to stdin
        core.watchdog.log.info(text)
        try:
            core.db.Tweet(time=time, text=text).save()
        except Exception as e:
            # notify telegram
            core.telegram.notify("stream error!")
            # log to cache csv
            core.watchdog.log.error(
                "error on inserting, caching instead...")
            core.watchdog.log.exception(e, exc_info=True)
            output = pandas.DataFrame({
                "time": [time],
                "text": [text],
                "model_i": [""],
                "intensity": [0],
                "polarity": [0],
                "model_p": [""]
            })
            with open(cache_file, "a") as f:
                output.to_csv(f,
                              header=f.tell() == 0,
                              mode="a",
                              index=False,
                              sep="\t")


def save_uids(users, api):
    # save the ids of the users to track to disk
    core.watchdog.log.info("loading user ids")
    path = core.config["HYPNOX_LOGS_DIR"] + "/user_ids.txt"
    uids_file = open(path, "a")
    uids = []
    for user in users:
        # retrieve user id by name from twitter api
        core.watchdog.log.info("fetching user %s id" % user)
        try:
            uid = str(api.get_user(screen_name=user.strip()).id)
            # save found uids to a file so it does not consume api each run
            print(uid, file=uids_file)
            uids.append(uid)
        except tweepy.errors.TweepyException:
            core.watchdog.log.error("user " + user + " not found")
    return uids


def stream():
    core.watchdog.set_logger("stream")

    core.watchdog.log.info("loading twitter API keys")
    if (core.config["HYPNOX_TWITTER_CONSUMER_KEY"] == ""
            or core.config["HYPNOX_TWITTER_CONSUMER_SECRET"] == ""
            or core.config["HYPNOX_TWITTER_ACCESS_KEY"] == ""
            or core.config["HYPNOX_TWITTER_ACCESS_SECRET"] == ""):
        core.watchdog.log.error("empty keys in config!")
        return 1
    auth = tweepy.OAuthHandler(core.config["HYPNOX_TWITTER_CONSUMER_KEY"],
                               core.config["HYPNOX_TWITTER_CONSUMER_SECRET"])
    auth.set_access_token(core.config["HYPNOX_TWITTER_ACCESS_KEY"],
                          core.config["HYPNOX_TWITTER_ACCESS_SECRET"])
    api = tweepy.API(auth)

    core.telegram.notify("initializing twitter stream...")
    core.watchdog.log.info("initializing")
    stream = Stream(core.config["HYPNOX_TWITTER_CONSUMER_KEY"],
                    core.config["HYPNOX_TWITTER_CONSUMER_SECRET"],
                    core.config["HYPNOX_TWITTER_ACCESS_KEY"],
                    core.config["HYPNOX_TWITTER_ACCESS_SECRET"])

    core.watchdog.log.info("reading users")
    try:
        path = core.config["HYPNOX_LOGS_DIR"] + "/user_ids.txt"
        uids = open(path).read().splitlines()
        if len(uids) != len(TRACK_USERS):
            os.remove(path)
            uids = save_uids(TRACK_USERS, api)
    except FileNotFoundError:
        uids = save_uids(TRACK_USERS, api)

    core.watchdog.log.info("streaming...")
    while not stream.running:
        try:
            stream.filter(languages=["en"], follow=uids)
            # track=["bitcoin", "btc", "crypto", "cryptocurrency"])
        except (requests.exceptions.Timeout, ssl.SSLError,
                urllib3.exceptions.ReadTimeoutError,
                requests.exceptions.ConnectionError) as e:
            core.watchdog.log.error("network error: " + e)
        except Exception as e:
            core.watchdog.log.error("unexpected error: " + e)
        except KeyboardInterrupt:
            core.watchdog.log.info(
                "got keyboard interrupt, shutting down...")
            return 1
