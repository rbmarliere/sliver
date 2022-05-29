import datetime
import json
import logging
import nltk
import numpy
import os
import pandas
import psycopg2
import re
import requests
import shutil
import ssl
import string
import tensorflow
import tweepy
import urllib3
import yaml

logging.basicConfig(level=logging.INFO)

CONFIG = json.load(open(os.path.dirname(os.path.realpath(__file__)) + "/config.json"))

try:
	nltk.data.find("corpora/stopwords")
except LookupError:
	nltk.download("stopwords")
nltkstops = set(nltk.corpus.stopwords.words("english"))
stops = [w for w in nltkstops if not w in CONFIG["TO_KEEP_STOPWORDS"]]

def standardize(text):
	# convert to lower case
	text = tensorflow.strings.lower(text)
	# remove links
	text = tensorflow.strings.regex_replace(text, "http\S+", "")
	# remove hashtags, usernames and html entities
	text = tensorflow.strings.regex_replace(text, "(#|@|&|\$)\S+", "")
	# remove punctuation
	text = tensorflow.strings.regex_replace(text, "[%s]" % re.escape(string.punctuation), " ")
	# remove some stopwords
	text = tensorflow.strings.regex_replace(text, "\\b(" + "|".join(stops) + ")\\b\s*", "")
	# keep only letters
	text = tensorflow.strings.regex_replace(text, "[^a-zA-Z]", " ")
	# keep only words with more than 2 characters
	text = tensorflow.strings.regex_replace(text, "\\b\S\S?\\b", "")
	# remove excess white spaces
	text = tensorflow.strings.regex_replace(text, " +", " ")
	# remove leading and trailing white spaces
	text = tensorflow.strings.strip(text)
	return text

def replay(argp, args):
	if args.model == None:
		logging.error("provide a model name with --model")
		return 1
	modelpath = os.path.dirname(os.path.realpath(__file__)) + "/models/" + args.model
	if not os.path.exists(modelpath):
		logging.warning(modelpath + " not found")
		return 1

	model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": standardize})
	db = psycopg2.connect(host=CONFIG["DB_HOST"], database=CONFIG["DB_DATABASE"], user=CONFIG["DB_USER"], password=CONFIG["DB_PASSWORD"])
	cursor = db.cursor()

	cursor.execute("SELECT * FROM stream_user")
	while True:
		rows = cursor.fetchmany(1024)
		for row in rows:
			intensity = "{:.8f}".format(model.predict([row[2]])[0][0])
			db.cursor().execute("UPDATE stream_user SET intensity = %s, model = %s WHERE id = %s", (intensity, args.model, row[0]))
		if not rows:
			break

	db.commit()
	cursor.close()
	db.close()

def predict(argp, args):
	if args.model == None:
		logging.error("provide a model name with --model")
		return 1
	modelpath = os.path.dirname(os.path.realpath(__file__)) + "/models/" + args.model
	if not os.path.exists(modelpath):
		logging.warning(modelpath + " not found")
		return 1
	if args.input == None:
		logging.error("provide an input data .tsv file name with --input")
		return 1
	if not os.path.exists(args.input):
		logging.warning(args.input + " not found")
		return 1

	model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": standardize})

	df = pandas.read_csv(args.input, lineterminator="\n", encoding="utf-8", sep="\t")
	df["model"] = args.model
	df["intensity"] = df.apply(lambda x: "{:.8f}".format(model.predict([x.text])[0][0]), axis=1)
	df.to_csv("data/replay/" + args.model + ".tsv", index=False, sep="\t")

def store(argp, args):
	if args.input == None:
		logging.error("provide a data .tsv file name with --input")
		return 1
	if not os.path.exists(args.input):
		logging.warning(args.input + " not found")
		return 1

	db = psycopg2.connect(host=CONFIG["DB_HOST"], database=CONFIG["DB_DATABASE"], user=CONFIG["DB_USER"], password=CONFIG["DB_PASSWORD"])
	cursor = db.cursor()

	query = "COPY stream_user(created_at,text,model,intensity,polarity) FROM STDOUT WITH CSV HEADER ENCODING 'UTF8' DELIMITER AS '\t'"
	with open(args.input, "r", encoding="utf-8") as f:
		cursor.copy_expert(query, f)

	db.commit()
	cursor.close()
	db.close()

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
		# remove any tab character
		text = re.sub("\t", " ", text).strip()
		# format data
		created_at = datetime.datetime.strptime(status._json["created_at"], "%a %b %d %H:%M:%S %z %Y")
		output = pandas.DataFrame({ "created_at": [created_at], "text": text, "model": "", "intensity": 0, "polarity": 0 })
		# log to stdin
		logging.info("---")
		logging.info(text)
		# log to cache csv
		with open("data/cache/" + created_at.strftime("%Y%m%d") + ".tsv", "a") as f:
			output.to_csv(f, header=f.tell()==0, mode="a", index=False, sep="\t")

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
	if CONFIG["TRACK_USERS"] == "":
		logging.error("empty user list in config! (TRACK_USERS)")
		return 1

	logging.info("loading twitter API keys")
	if CONFIG["CONSUMER_KEY"] == "" or CONFIG["CONSUMER_SECRET"] == "" or CONFIG["ACCESS_KEY"] == "" or CONFIG["ACCESS_SECRET"] == "":
		logging.error("empty keys in config! (CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET)")
		return 1
	auth = tweepy.OAuthHandler(CONFIG["CONSUMER_KEY"], CONFIG["CONSUMER_SECRET"])
	auth.set_access_token(CONFIG["ACCESS_KEY"], CONFIG["ACCESS_SECRET"])
	api = tweepy.API(auth)

	logging.info("initializing")
	stream = Stream(CONFIG["CONSUMER_KEY"], CONFIG["CONSUMER_SECRET"], CONFIG["ACCESS_KEY"], CONFIG["ACCESS_SECRET"])

	logging.info("reading users")
	try:
		uids = open(".uids").read().splitlines()
		if len(uids) != len(CONFIG["TRACK_USERS"]):
			os.remove(".uids")
			uids = save_uids(CONFIG["TRACK_USERS"], api)
	except FileNotFoundError:
		uids = save_uids(CONFIG["TRACK_USERS"], api)

	while not stream.running:
		try:
			stream.filter(
				languages=["en"],
				follow=uids,
				#track=["bitcoin", "btc", "crypto", "cryptocurrency"]
			)
		except (requests.exceptions.Timeout, ssl.SSLError, urllib3.exceptions.ReadTimeoutError, requests.exceptions.ConnectionError) as e:
			logging.error("network error")
		except Exception as e:
			logging.error("unexpected error", e)
		except KeyboardInterrupt:
			return 1

def train(argp, args):
	if args.input == None:
		logging.error("provide a training data .tsv file name with --input")
		return 1
	if not os.path.exists(args.input):
		logging.warning(args.input + " not found")
		return 1
	if args.model == None:
		logging.error("provide a model name with --model")
		return 1
	modelpath = os.path.dirname(os.path.realpath(__file__)) + "/models/" + args.model
	if os.path.exists(modelpath):
		logging.warning(modelpath + " already exists, overwrite? [y|N]")
		if input() != "y":
			return 1
		shutil.rmtree(modelpath)
	modelcfgpath = os.path.dirname(os.path.realpath(__file__)) + "/models/" + args.model + ".yaml"
	if not os.path.exists(modelcfgpath):
		logging.warning(modelcfgpath + " not found")
		return 1

	with open(modelcfgpath, "r") as stream:
		try:
			modelcfg = yaml.safe_load(stream)
		except yaml.YAMLError as exc:
			print(exc)
			return 1
	batch_size = modelcfg["batch_size"]
	max_features = modelcfg["max_features"]
	sequence_length = modelcfg["sequence_length"]
	embedding_dim = modelcfg["embedding_dim"]
	epochs = modelcfg["epochs"]

	raw_df = pandas.read_csv(args.input, encoding="utf-8", lineterminator="\n", sep="\t")

	i = int(len(raw_df)*(70/100)) # 70% of raw_df
	train_df = raw_df.head(i)
	val_df = raw_df.iloc[i:max(raw_df.index)]

	raw_train_ds = tensorflow.data.Dataset.from_tensor_slices( (train_df["text"], train_df["intensity"]) ).batch(batch_size)
	raw_val_ds = tensorflow.data.Dataset.from_tensor_slices( (val_df["text"], val_df["intensity"]) ).batch(batch_size)

	vectorize_layer = tensorflow.keras.layers.TextVectorization(
		standardize=standardize,
		#split=split,
		max_tokens=max_features,
		output_mode="int",
		output_sequence_length=sequence_length)
	train_text = raw_train_ds.map(lambda x, y: x)
	vectorize_layer.compile()
	vectorize_layer.adapt(train_text)

	def vectorize_text(text, label):
		text = tensorflow.expand_dims(text, -1)
		return vectorize_layer(text), label
	train_ds = raw_train_ds.map(vectorize_text)
	val_ds = raw_val_ds.map(vectorize_text)

	model = tensorflow.keras.Sequential([
		tensorflow.keras.layers.Embedding(max_features + 1, embedding_dim, mask_zero=True),
		tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(64, return_sequences=True)),
		tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(32)),
		tensorflow.keras.layers.Dense(64, activation="relu"),
		tensorflow.keras.layers.Dropout(0.5),
		tensorflow.keras.layers.Dense(1)
	])
	model.summary()
	model.compile(
		loss=tensorflow.keras.losses.BinaryCrossentropy(from_logits=True),
		optimizer="adam",
		metrics="binary_accuracy"
	)

	tensorboard_callback = tensorflow.keras.callbacks.TensorBoard(log_dir=modelpath+"/logs", histogram_freq=1)
	history = model.fit(train_ds, validation_data=val_ds, epochs=epochs, callbacks=[tensorboard_callback])

	loss, accuracy = model.evaluate(val_ds)
	print("Loss: ", loss)
	print("Accuracy: ", accuracy)

	export_model = tensorflow.keras.Sequential([
		vectorize_layer,
		model,
		tensorflow.keras.layers.Activation("sigmoid")
	])
	export_model.summary()
	export_model.compile(
		loss=tensorflow.keras.losses.BinaryCrossentropy(from_logits=False),
		optimizer="adam",
		metrics="binary_accuracy"
	)
	export_model.save(modelpath)

