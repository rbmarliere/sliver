import datetime
import json
import logging
import nltk
import os
import pandas
import re
import requests
import shutil
import ssl
import string
import tensorflow
import tweepy
import urllib3

logging.basicConfig(level=logging.INFO)

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
		text = re.sub("\n", " ", text)
		# parse tweet info
		created_at = datetime.datetime.strptime(status._json["created_at"], "%a %b %d %H:%M:%S %z %Y")
		user = status._json["user"]["screen_name"]
		url = "https://twitter.com/" + user + "/status/" + str(status.id)
		# output
		tweet = pandas.DataFrame({ "date": [created_at], "username": [user], "url": [url], "tweet": [text] })
		logging.info(text)
		with open("data/raw.csv", "a") as f:
			tweet.to_csv(f, header=f.tell()==0, mode="a", index=False)

# save the ids of the users to track to disk
def save_uids(users, api):
	logging.info("loading user ids")
	uids_file = open(".uids", "a")
	uids = []
	for user in users:
		# retrieve user id by name from twitter api
		logging.info("fetching user %s id" % user)
		try:
			uid = str(api.get_user(screen_name=user.strip()).id)
			# save found uids to a file so it doesn't consume api each run
			print(uid, file=uids_file)
			uids.append(uid)
		except tweepy.errors.TweepyException:
			logging.error("user '" + user + "' not found")
	return uids

def stream(argp, args):
	logging.info("loading config")
	config = json.load(open(os.path.dirname(os.path.realpath(__file__)) + "/hypnox.conf"))
	if config["TRACK_USERS"] == "":
		logging.error("empty user list in config! (TRACK_USERS) in (" + config_filename + ")")
		return 1

	logging.info("loading twitter API keys")
	if config["CONSUMER_KEY"] == "" or config["CONSUMER_SECRET"] == "" or config["ACCESS_KEY"] == "" or config["ACCESS_SECRET"] == "":
		logging.error("empty keys in config! (CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET)")
		return 1
	auth = tweepy.OAuthHandler(config["CONSUMER_KEY"], config["CONSUMER_SECRET"])
	auth.set_access_token(config["ACCESS_KEY"], config["ACCESS_SECRET"])
	api = tweepy.API(auth)

	logging.info("initializing")
	stream = Stream(config["CONSUMER_KEY"], config["CONSUMER_SECRET"], config["ACCESS_KEY"], config["ACCESS_SECRET"])

	logging.info("reading users")
	try:
		uids = open(".uids").read().splitlines()
		if len(uids) != len(config["TRACK_USERS"]):
			os.remove(".uids")
			uids = save_uids(config["TRACK_USERS"], api)
	except FileNotFoundError:
		uids = save_uids(config["TRACK_USERS"], api)

	while not stream.running:
		try:
			stream.filter(
				languages=["en"],
				follow=uids,
				#track=["bitcoin"],
			)
		except (requests.exceptions.Timeout, ssl.SSLError, urllib3.exceptions.ReadTimeoutError, requests.exceptions.ConnectionError) as e:
			logging.error("network error")
		except Exception as e:
			logging.error("unexpected error", e)
		except KeyboardInterrupt:
			return 1
		finally:
			logging.error("stream has crashed")

def train(argp, args):
	if args.model == None:
		logging.error("provide a model name with --model")
		return 1

	modelpath = os.path.dirname(os.path.realpath(__file__)) + "/models/" + args.model
	if os.path.exists(modelpath):
		logging.warning(modelpath + " already exists, overwrite? [y|N]")
		if input() != "y":
			return 1
		shutil.rmtree(modelpath)

	try:
		nltk.data.find("corpora/stopwords")
	except LookupError:
		nltk.download('stopwords')
	keep_stopwords = [ "this", "that'll", "these", "having", "does", "doing", "until", "while", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "few", "both", "more", "most", "other", "some", "than", "too", "very", "can", "will", "should", "should've", "now", "ain", "aren", "aren't", "could", "couldn", "couldn't", "didn", "didn't", "doesn", "doesn't", "hadn", "hadn't", "hasn", "hasn't", "haven", "haven't", "isn", "isn't", "mighn", "mightn't", "mustn", "mustn't", "needn", "needn't", "shan", "shan't", "shouldn", "shouldn't", "wasn", "wasn't", "weren","weren't", "won'", "won't", "wouldn", "wouldn't" ]
	nltkstops = set(nltk.corpus.stopwords.words("english"))
	stops = [w for w in nltkstops if not w in keep_stopwords]

	batch_size = 32
	max_features = 10000
	sequence_length = 280
	embedding_dim = 16
	epochs = 10

	raw_df = pandas.read_csv("data/training.csv", encoding="utf-8", lineterminator="\n")

	train_df = raw_df.head(int(len(raw_df)*(80/100))) # 80% of raw_df
	val_df = raw_df.iloc[max(train_df.index):]

	raw_train_ds = tensorflow.data.Dataset.from_tensor_slices( (train_df["tweet"], train_df["is_prediction"]) ).batch(batch_size)
	raw_val_ds = tensorflow.data.Dataset.from_tensor_slices( (val_df["tweet"], val_df["is_prediction"]) ).batch(batch_size)

	def clean(tweet):
		# convert to lower case
		tweet = tensorflow.strings.lower(tweet)
		# remove links
		tweet = tensorflow.strings.regex_replace(tweet, "http\S+", "")
		# remove hashtags, usernames and html entities
		tweet = tensorflow.strings.regex_replace(tweet, "(#|@|&|\$)\S+", "")
		# remove punctuation
		tweet = tensorflow.strings.regex_replace(tweet, "[%s]" % re.escape(string.punctuation), "")
		# remove some stopwords
		tweet = tensorflow.strings.regex_replace(tweet, r'\b(' + r'|'.join(stops) + r')\b\s*',"")
		return tweet

	vectorize_layer = tensorflow.keras.layers.TextVectorization(
		standardize=clean,
		max_tokens=max_features,
		output_mode='int',
		output_sequence_length=sequence_length)
	train_text = raw_train_ds.map(lambda x, y: x)
	vectorize_layer.adapt(train_text)

	def vectorize_text(text, label):
		text = tensorflow.expand_dims(text, -1)
		return vectorize_layer(text), label
	train_ds = raw_train_ds.map(vectorize_text)
	val_ds = raw_val_ds.map(vectorize_text)

	model = tensorflow.keras.Sequential([
		tensorflow.keras.layers.Embedding(max_features + 1, embedding_dim),
		tensorflow.keras.layers.Dropout(0.2),
		tensorflow.keras.layers.GlobalAveragePooling1D(),
		tensorflow.keras.layers.Dropout(0.2),
		tensorflow.keras.layers.Dense(1)])

	model.summary()

	model.compile(
		loss=tensorflow.keras.losses.BinaryCrossentropy(from_logits=True),
		optimizer='adam',
		metrics=tensorflow.metrics.BinaryAccuracy(threshold=0.0))

	log_dir = "models/logs/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
	tensorboard_callback = tensorflow.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)

	model.fit(train_ds, validation_data=val_ds, epochs=epochs, callbacks=[tensorboard_callback])

	export_model = tensorflow.keras.Sequential([
	  vectorize_layer,
	  model,
	  tensorflow.keras.layers.Activation('sigmoid')
	])
	export_model.compile(
	    loss=tensorflow.keras.losses.BinaryCrossentropy(from_logits=False), optimizer="adam", metrics=['accuracy']
	)
	export_model.save(modelpath)
