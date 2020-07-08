from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from tqdm import tqdm
import datetime
import json
import logging
import math
import nltk
import numpy
import os
import pandas
import re

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" # tensorflow verbosity

# helper to load google encoder
def load_use():
	import tensorflow_hub
	logging.info("loading USE...")
	use = tensorflow_hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
	return use

# helper to clean text
def clean(text):
	# remove links
	text = re.sub("http\S+", "", text)
	# remove html entities
	text = re.sub("&\w+;", "", text)
	# remove usernames
	text = re.sub("(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9-_]+)", "", text)
	# leave only words
	text = re.sub("[^a-zA-Z']", " ", text)
	# convert to lower case, split into individual words
	words = text.lower().split()
	# remove stopwords, but keep some
	keep = [ "this", "that'll", "these", "having", "does", "doing", "until", "while", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "few", "both", "more", "most", "other", "some", "than", "too", "very", "can", "will", "should", "should've", "now", "ain", "aren", "aren't", "could", "couldn", "couldn't", "didn", "didn't", "doesn", "doesn't", "hadn", "hadn't", "hasn", "hasn't", "haven", "haven't", "isn", "isn't", "mighn", "mightn't", "mustn", "mustn't", "needn", "needn't", "shan", "shan't", "shouldn", "shouldn't", "wasn", "wasn't", "weren","weren't", "won'", "won't", "wouldn", "wouldn't" ]
		# load nltk stopwords
	nltkstops = set(nltk.corpus.stopwords.words("english"))
	stops = [w for w in nltkstops if not w in keep]
	meaningful_words = [w for w in words if not w in stops]
	# stem words
	stemmer = nltk.stem.porter.PorterStemmer()
	singles = [stemmer.stem(word) for word in meaningful_words]

	# join the words with more than one char back into one string
	out = " ".join([w for w in singles if len(w) > 1])

	#logging.debug(text)
	#logging.debug(words)
	#logging.debug(stops)
	#logging.debug(meaningful_words)
	#logging.debug(singles)
	#logging.debug(out)

	return out

def filter(argp, args):
	if args.input == None:
		logging.error("provide a data directory with --input")
		return 1
	if not os.path.exists(args.input):
		logging.error("can't find data directory! (" + args.input + ")")
		return 1

	logging.info("loading config...")
	try:
		include_filename = os.path.dirname(os.path.realpath(__file__)) + "/etc/filter/include"
		exclude_filename = os.path.dirname(os.path.realpath(__file__)) + "/etc/filter/exclude"
		include = open( include_filename ).read().splitlines()
		exclude = open( exclude_filename ).read().splitlines()
		logging.info("including tweets from " + include_filename)
		logging.info("excluding tweets from " + exclude_filename)
	except:
		logging.error("can't read filter directory! (" + include_filename + "," + exclude_filename + ")")
		return 1
	outputdir = os.path.dirname(os.path.realpath(__file__)) + "/data/filter"
	if not os.path.exists(outputdir):
		logging.error(outputdir + " doesn't exist!")
		return 1

	logging.info("processing " + args.input)
	for datafile in sorted(os.listdir(args.input)):
		if datafile.startswith("."):
			continue

		outputfile = outputdir + "/" + os.path.splitext(datafile)[0]
		if os.path.exists(outputfile):
			if args.ignore:
				continue
			logging.warning(outputfile + " already exists, overwrite? [y|N]")
			if input() != "y":
				continue

		logging.info("processing " + datafile)
		alltweets = pandas.read_csv(args.input + "/" + datafile, encoding="utf-8", lineterminator="\n")
		alltweets["cleaned_tweet"] = alltweets["tweet"].apply( lambda x: clean(x) )
		alltweets = alltweets.set_index("cleaned_tweet")
		if alltweets.empty:
			logging.info("empty datafile")
			continue

		tweets = None
		for word in include:
			word = clean(word)
			try:
				tweets = pandas.concat([ tweets, alltweets.filter(regex=word, axis=0).reset_index() ])
			except NameError:
				tweets = alltweets.filter(regex=word, axis=0).reset_index()

		tweets = tweets.drop_duplicates()
		tweets = tweets.set_index("cleaned_tweet")

		for word in exclude:
			word = clean(word)
			tweets = tweets.drop( tweets.filter(regex=word, axis=0).index )

		tweets = tweets.reset_index()
		tweets = tweets.drop("cleaned_tweet", axis=1)
		tweets = tweets.drop_duplicates()

		logging.info("writing to " + outputfile)
		if tweets.empty:
			logging.info("empty dataframe")
			continue
		tweets.to_csv(outputfile, index=False)

def parse(argp, args):
	if args.input == None:
		logging.error("provide a data directory with --input")
		return 1
	if not os.path.exists(args.input):
		logging.error("can't find data directory! (" + args.input + ")")
		return 1

	logging.info("loading config...")
	config_file = os.path.dirname(os.path.realpath(__file__)) + "/etc/tacitus.conf"
	config = json.load(open(config_file))
	if config["PARSE_OCCURRENCES_THRESHOLD"] == "" or config["PARSE_FREQUENCY_THRESHOLD"] == "" or config["PARSE_DELTA_THRESHOLD"] == "" or config["PARSE_TENSION_BUY_THRESHOLD"] == "" or config["PARSE_TENSION_SELL_THRESHOLD"] == "":
		logging.error("empty parameters in config! (PARSE_OCCURRENCES_THRESHOLD,PARSE_FREQUENCY_THRESHOLD,PARSE_DELTA_THRESHOLD,PARSE_TENSION_BUY_THRESHOLD,PARSE_TENSION_SELL_THRESHOLD)")
		return 1
	outputdir = os.path.dirname(os.path.realpath(__file__)) + "/data/parse"
	if not os.path.exists(outputdir):
		logging.error(outputdir + " doesn't exist!")
		return 1

	logging.info("loading lexicon...")
	lexicon = os.path.dirname(os.path.realpath(__file__)) + "/etc/lexicon"
	glosema = pandas.read_csv(lexicon, encoding="utf-8", lineterminator="\n")
	glosema["cleaned_word"] = glosema["word"].apply( lambda x: clean(x) )
	glosema = glosema.set_index("cleaned_word")

	logging.info("processing " + args.input)
	last_unique = pandas.DataFrame()
	for datafile in sorted(os.listdir(args.input)):
		if datafile.startswith("."):
			continue

		outputfile = outputdir + "/" + os.path.splitext(datafile)[0]
		if os.path.exists(outputfile):
			if args.ignore:
				continue
			logging.warning(outputfile + " already exists, overwrite? [y|N]")
			if input() != "y":
				continue

		logging.info("processing " + datafile)
		tweets = pandas.read_csv(args.input + "/" + datafile, encoding="utf-8", lineterminator="\n")
		tweets["cleaned_tweet"] = tweets["tweet"].apply( lambda x: clean(x) )
		if tweets.empty:
			logging.info("empty datafile")
			continue

		# take unique words used in all tweets
		unique = tweets["cleaned_tweet"].str.split(" ", expand=True).stack().value_counts()
		# filter found unique words based on an occurrence threshold
		unique = pandas.DataFrame({ "occurrences": unique[ unique >= config["PARSE_OCCURRENCES_THRESHOLD"] ] })
		# select only the words that also appear in the last period
		intersect = unique.loc[ unique.index.intersection(last_unique.index) ]
		# check if first datafile
		if last_unique.empty:
			last_unique = unique
			continue
		# grab the occurrences from the last period
		intersect["last_occurrences"] = last_unique.loc[ unique.index.intersection(last_unique.index) ]
		# update loop index
		last_unique = unique
		# make occurrences percentages as frequency
		intersect["frequency"] = intersect["occurrences"] / intersect["occurrences"].sum()
		intersect["last_frequency"] = intersect["last_occurrences"] / intersect["last_occurrences"].sum()
		# filter based on a frequency threshold
		intersect = intersect[ intersect.frequency <= intersect.frequency.quantile( config["PARSE_FREQUENCY_THRESHOLD"] ) ]
		# compute deltas from last period
		intersect["delta"] = intersect["frequency"] - intersect["last_frequency"]
		# filter based on a delta threshold
		intersect = intersect[ intersect.delta > intersect.delta.quantile( config["PARSE_DELTA_THRESHOLD"] ) ]

		# keep only words from glosema
		found = glosema.loc[ intersect.index.intersection(glosema.index) ]
		# concatenate into a single frame
		mirari = pandas.concat([intersect.loc[ found.index ],found], axis=1)
		# aggreggate occurrences by emotions
		emotions = mirari.reset_index()[["emotion","occurrences"]].groupby(["emotion"]).sum()
		# sum opposite emotions and aggregate
		eg = emotions.occurrences.get("ecstasy", 0) + emotions.occurrences.get("grief", 0)
		js = emotions.occurrences.get("joy", 0) + emotions.occurrences.get("sadness", 0)
		sp = emotions.occurrences.get("serenity", 0) + emotions.occurrences.get("pensiveness", 0)
		happy = eg + js + sp
		al = emotions.occurrences.get("admiration", 0) + emotions.occurrences.get("loathing", 0)
		td = emotions.occurrences.get("trust", 0) + emotions.occurrences.get("disgust", 0)
		ab = emotions.occurrences.get("acceptance", 0) + emotions.occurrences.get("boredom", 0)
		like = al + td + ab
		rt = emotions.occurrences.get("rage", 0) + emotions.occurrences.get("terror", 0)
		af = emotions.occurrences.get("anger", 0) + emotions.occurrences.get("fear", 0)
		aa = emotions.occurrences.get("annoyance", 0) + emotions.occurrences.get("apprehension", 0)
		action = rt + af + aa
		vai = emotions.occurrences.get("vigilance", 0) + emotions.occurrences.get("anticipation", 0) + emotions.occurrences.get("interest", 0)
		asd = emotions.occurrences.get("amazement", 0) + emotions.occurrences.get("surprise", 0) + emotions.occurrences.get("distraction", 0)
		asd = 1 if asd == 0 else math.sqrt(asd%1)
		tension = (vai+93) / (asd+93)

		signal = 0
		signal_sum = happy + like + action + tension
		if signal_sum >= config["PARSE_TENSION_BUY_THRESHOLD"] and signal_sum < config["PARSE_TENSION_SELL_THRESHOLD"]:
			signal = 1
		elif signal_sum >= config["PARSE_TENSION_SELL_THRESHOLD"]:
			signal = -1

		logging.info("writing to " + outputfile)
		result = pandas.DataFrame({ "signal": [signal], "happy": [happy], "like": [like], "action": [action], "tension": [tension] })
		if mirari.empty or emotions.empty or result.empty:
			logging.info("empty dataframe")
			continue
		mirari.to_csv(outputfile + ".mirari", index=False)
		emotions.reset_index().to_csv(outputfile + ".deltas", index=False)
		result.to_csv(outputfile, index=False)

def predict(argp, args):
	import tensorflow

	if args.input == None:
		logging.error("provide a data directory with --input")
		return 1
	if not os.path.exists(args.input):
		logging.error("can't find data directory! (" + args.input + ")")
		return 1

	use = load_use()

	logging.info("loading config...")
	config_file = os.path.dirname(os.path.realpath(__file__)) + "/etc/tacitus.conf"
	config = json.load(open(config_file))
	if config["PREDICT_LOW_THRESHOLD"] == "" or config["PREDICT_HIGH_THRESHOLD"] == "":
		logging.error("empty parameters in config! (PREDICT_LOW_THRESHOLD, PREDICT_HIGH_THRESHOLD)")
		return 1
	outputdir = os.path.dirname(os.path.realpath(__file__)) + "/data/predict"
	if not os.path.exists(outputdir):
		logging.error(outputdir + " doesn't exist!")
		return 1

	model_file = os.path.dirname(os.path.realpath(__file__)) + "/etc/models/default"
	logging.info("loading model at " + model_file)
	try:
		model = tensorflow.keras.models.load_model(model_file)
	except:
		logging.error("can't load model")
		return 1

	logging.info("processing " + args.input)
	for datafile in sorted(os.listdir(args.input)):
		if datafile.startswith("."):
			continue

		outputfile = outputdir + "/" + os.path.splitext(datafile)[0]
		if os.path.exists(outputfile):
			if args.ignore:
				continue
			logging.warning(outputfile + " already exists, overwrite? [y|N]")
			if input() != "y":
				continue

		logging.info("processing " + datafile)
		tweets = pandas.read_csv(args.input + "/" + datafile, encoding="utf-8", lineterminator="\n")
		if tweets.empty:
			logging.info("empty datafile")
			continue
		tweets["predict"] = model.predict( use(tweets["tweet"]) ).flatten()[1::2]
		def pred(score):
			if score >= config["PREDICT_LOW_THRESHOLD"] and score < config["PREDICT_HIGH_THRESHOLD"]:
				return 0
			elif score >= config["PREDICT_HIGH_THRESHOLD"]:
				return 1
			else:
				return -1
		tweets["predict"] = tweets["predict"].apply( pred )
		tweets = tweets[ tweets["predict"] >= 0 ]

		logging.info("writing to " + outputfile)
		if tweets.empty:
			logging.info("empty dataframe")
			continue
		tweets.to_csv(outputfile, index=False)

def tally(argp, args):
	if args.input == None:
		logging.error("provide a data directory with --input")
		return 1
	if not os.path.exists(args.input):
		logging.error("can't find data directory! (" + args.input + ")")
		return 1

	logging.info("loading config...")
	outputdir = os.path.dirname(os.path.realpath(__file__)) + "/data/tally"
	if not os.path.exists(outputdir):
		logging.error(outputdir + " doesn't exist!")
		return 1

	logging.info("processing " + args.input)
	for datafile in sorted(os.listdir(args.input)):
		if datafile.startswith("."):
			continue

		outputfile = outputdir + "/" + os.path.splitext(datafile)[0]
		if os.path.exists(outputfile):
			if args.ignore:
				continue
			logging.warning(outputfile + " already exists, overwrite? [y|N]")
			if input() != "y":
				continue

		logging.info("processing " + datafile)
		predictions = pandas.read_csv(args.input + "/" + datafile, encoding="utf-8", lineterminator="\n")
		if predictions.empty:
			logging.info("empty datafile")
			continue
		pos = predictions.loc[ predictions["predict"] == 1 ].size
		neg = predictions.loc[ predictions["predict"] == 0 ].size
		trend = pos - neg > 0

		logging.info("writing to " + outputfile)
		tally = pandas.DataFrame({ "pos": [pos], "neg": [neg], "trend": [trend] })
		if tally.empty:
			logging.info("empty dataframe")
			continue
		tally.to_csv(outputfile, index=False)

def train(argp, args):
	import tensorflow
	import tensorflow_hub

	use = load_use()

	logging.info("loading config...")
	config_file = os.path.dirname(os.path.realpath(__file__)) + "/etc/tacitus.conf"
	config = json.load(open(config_file))
	modeldir = os.path.dirname(os.path.realpath(__file__)) + "/etc/models/" + datetime.datetime.now().strftime("%Y%m%d")
	if os.path.exists(modeldir):
		logging.warning(modeldir + " already exists, overwrite? [y|N]")
		if input() != "y":
			return 1

	logging.info("loading hyperparameters...")
	if config["TRAIN_SEED"] == "" or config["TRAIN_EPOCHS"] == "" or config["TRAIN_BATCH_SIZE"] == "":
		logging.error("empty parameters in config! (TRAIN_SEED, TRAIN_EPOCHS, TRAIN_BATCH_SIZE)")
		return 1

	logging.info("loading training data...")
	try:
		train_datadir = os.path.dirname(os.path.realpath(__file__)) + "/etc/train"
		pos_file = open(train_datadir + "/pos")
		neg_file = open(train_datadir + "/neg")
	except FileNotFoundError:
		print("training data not found")
	# load positive tweets
	pos_lines = pos_file.read().splitlines()
	pos = pandas.DataFrame({ "tweet": pos_lines, "polarity": [1] * len(pos_lines) })
	# load negative tweets
	neg_lines = neg_file.read().splitlines()
	neg = pandas.DataFrame({ "tweet": neg_lines, "polarity": [0] * len(neg_lines) })
	# combine all data
	tweets = pandas.concat([pos, neg])
	# shuffle rows
	tweets = tweets.sample(frac=1).reset_index(drop=True)
	# remove None rows
	tweets = tweets.dropna()

	logging.info("building training data...")
	polarity = OneHotEncoder(sparse=False).fit_transform( tweets.polarity.to_numpy().reshape(-1, 1) )
	train_tweets, test_tweets, y_train, y_test = train_test_split( tweets.tweet, polarity, test_size = .1, random_state = config["TRAIN_SEED"] )
	X_train = []
	for r in tqdm(train_tweets):
		emb = use([r])
		tweet_emb = tensorflow.reshape(emb, [-1]).numpy()
		X_train.append(tweet_emb)
	X_train = numpy.array(X_train)
	X_test = []
	for r in tqdm(test_tweets):
		emb = use([r])
		tweet_emb = tensorflow.reshape(emb, [-1]).numpy()
		X_test.append(tweet_emb)
	X_test = numpy.array(X_test)

	logging.info("building model...")
	model = tensorflow.keras.Sequential()
	model.add( tensorflow.keras.layers.Dense(units=512, input_shape=(X_train.shape[1], ), activation="relu") )
	model.add( tensorflow.keras.layers.Dropout(rate=0.5) )
	model.add( tensorflow.keras.layers.Dense(units=512, activation="relu") )
	model.add( tensorflow.keras.layers.Dropout(rate=0.5) )
	model.add( tensorflow.keras.layers.Dense(2, activation="softmax") )
	model.compile( loss="categorical_crossentropy", optimizer=tensorflow.keras.optimizers.Adam(0.01), metrics=["accuracy"] )
	logging.info(model.summary())

	logging.info("training model...")
	model.fit(
		X_train, y_train,
		epochs=config["TRAIN_EPOCHS"],
		batch_size=config["TRAIN_BATCH_SIZE"],
		validation_split=0.1,
		verbose=1,
		shuffle=True
	)

	logging.info("evaluating model...")
	model.evaluate(X_test, y_test)

	logging.info("saving model...")
	model.save(modeldir)

