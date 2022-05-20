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

config = json.load(open(os.path.dirname(os.path.realpath(__file__)) + "/hypnox.conf"))

try:
	nltk.data.find("corpora/stopwords")
except LookupError:
	nltk.download('stopwords')
nltkstops = set(nltk.corpus.stopwords.words("english"))
stops = [w for w in nltkstops if not w in config["TO_KEEP_STOPWORDS"]]

def standardize(tweet):
	# convert to lower case
	tweet = tensorflow.strings.lower(tweet)
	# remove links
	tweet = tensorflow.strings.regex_replace(tweet, "http\S+", "")
	# remove hashtags, usernames and html entities
	tweet = tensorflow.strings.regex_replace(tweet, "(#|@|&|\$)\S+", "")
	# remove punctuation
	tweet = tensorflow.strings.regex_replace(tweet, "[%s]" % re.escape(string.punctuation), " ")
	# remove some stopwords
	tweet = tensorflow.strings.regex_replace(tweet, "\\b(" + "|".join(stops) + ")\\b\s*", "")
	# keep only letters
	tweet = tensorflow.strings.regex_replace(tweet, "[^a-zA-Z]", " ")
	# keep only words with more than 2 characters
	tweet = tensorflow.strings.regex_replace(tweet, "\\b\S\S?\\b", "")
	# remove excess white spaces
	tweet = tensorflow.strings.regex_replace(tweet, " +", " ")
	# remove leading and trailing white spaces
	tweet = tensorflow.strings.strip(tweet)
	return tweet

#def split(tweet):
#	# split tweet into array of words
#	tweet = tensorflow.strings.split(tweet)
#	# apply stemming to each word
#	tweet = tweet.with_flat_values(
#			tensorflow.map_fn(
#				lambda x: tensorflow.constant(st.stem(x.numpy().decode("utf-8"))),
#				tweet.flat_values) )
#	return tweet

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
		# is predictive tweet?
		is_prediction = self.model.predict([text])[0][0]
		# output
		tweet = pandas.DataFrame({ "date": [created_at], "username": [user], "url": [url], "tweet": [text], "is_prediction": [is_prediction], "model": [self.modelname] })
		logging.info(text)
		logging.info("is_prediction: " + str(is_prediction))
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
	if config["TRACK_USERS"] == "":
		logging.error("empty user list in config! (TRACK_USERS) in (" + config_filename + ")")
		return 1
	if args.model == None:
		logging.error("provide a model name with --model")
		return 1
	modelpath = os.path.dirname(os.path.realpath(__file__)) + "/models/" + args.model
	if not os.path.exists(modelpath):
		logging.warning(modelpath + " not found")
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
	stream.model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": standardize})
	stream.modelname = args.model

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
				#track=["bitcoin"], -> need to filter bots by follower count
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
	if args.input == None:
		logging.error("provide a training data .csv file name with --input")
		return 1
	if not os.path.exists(args.input):
		logging.warning(args.input + " not found")
		return 1
	modelpath = os.path.dirname(os.path.realpath(__file__)) + "/models/" + args.model
	if os.path.exists(modelpath):
		logging.warning(modelpath + " already exists, overwrite? [y|N]")
		if input() != "y":
			return 1
		shutil.rmtree(modelpath)
	modelcfgpath = os.path.dirname(os.path.realpath(__file__)) + "/models/" + args.model + ".conf"
	if not os.path.exists(modelcfgpath):
		logging.warning(modelcfg + " not found")
		return 1

	modelcfg = json.load(open(modelcfgpath))
	batch_size = modelcfg["BATCH_SIZE"]
	max_features = modelcfg["MAX_FEATURES"]
	sequence_length = modelcfg["SEQUENCE_LENGTH"]
	embedding_dim = modelcfg["EMBEDDING_DIM"]
	epochs = modelcfg["EPOCHS"]

	raw_df = pandas.read_csv(args.input, encoding="utf-8", lineterminator="\n")

	i = int(len(raw_df)*(70/100)) # 70% of raw_df
	j = int(len(raw_df)*(90/100)) # 90% of raw_df
	train_df = raw_df.head(i)
	val_df = raw_df.iloc[max(train_df.index):j]
	test_df = raw_df.iloc[j:max(raw_df.index)]

	raw_train_ds = tensorflow.data.Dataset.from_tensor_slices( (train_df["tweet"], train_df["is_prediction"]) ).batch(batch_size)
	raw_val_ds = tensorflow.data.Dataset.from_tensor_slices( (val_df["tweet"], val_df["is_prediction"]) ).batch(batch_size)
	raw_test_ds = tensorflow.data.Dataset.from_tensor_slices( (test_df["tweet"], test_df["is_prediction"]) ).batch(batch_size)

	vectorize_layer = tensorflow.keras.layers.TextVectorization(
		standardize=standardize,
		#split=split,
		max_tokens=max_features,
		output_mode='int',
		output_sequence_length=sequence_length)
	train_text = raw_train_ds.map(lambda x, y: x)
	vectorize_layer.compile()
	vectorize_layer.adapt(train_text)

	def vectorize_text(text, label):
		text = tensorflow.expand_dims(text, -1)
		return vectorize_layer(text), label
	train_ds = raw_train_ds.map(vectorize_text)
	val_ds = raw_val_ds.map(vectorize_text)
	test_ds = raw_test_ds.map(vectorize_text)

	model = tensorflow.keras.Sequential([
		tensorflow.keras.layers.Embedding(max_features + 1, embedding_dim),
		tensorflow.keras.layers.GlobalAveragePooling1D(),
		tensorflow.keras.layers.Dropout(0.2),
		tensorflow.keras.layers.Dense(16, activation="relu"),
		tensorflow.keras.layers.Dense(1)])
	model.summary()
	model.compile(
		loss=tensorflow.keras.losses.BinaryCrossentropy(from_logits=True),
		optimizer='adam',
		metrics=tensorflow.metrics.BinaryAccuracy(threshold=0.0))

	tensorboard_callback = tensorflow.keras.callbacks.TensorBoard(log_dir=modelpath+"/logs", histogram_freq=1)
	history = model.fit(train_ds, validation_data=val_ds, epochs=epochs, callbacks=[tensorboard_callback])

	loss, accuracy = model.evaluate(test_ds)
	print("Loss: ", loss)
	print("Accuracy: ", accuracy)

	export_model = tensorflow.keras.Sequential([
		vectorize_layer,
		model,
		tensorflow.keras.layers.Activation('sigmoid') ])
	export_model.summary()
	export_model.compile(
		loss=tensorflow.keras.losses.BinaryCrossentropy(from_logits=False),
		optimizer="adam",
		metrics=['accuracy']
	)
	export_model.save(modelpath)

