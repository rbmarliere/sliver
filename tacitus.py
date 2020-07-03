from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from tqdm import tqdm
import datetime
import json
import logging
import nltk
import numpy
import os
import pandas
import re

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" # tensorflow verbosity

# helper to load google encoder
def load_use():
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

	logging.info("processing " + args.input)
	for datafile in os.listdir(args.input):
		logging.info("processing " + datafile)
		all_tweets = pandas.read_csv(args.input + "/" + datafile)
		all_tweets["cleaned_tweet"] = all_tweets["tweet"].apply( lambda x: clean(x) )
		all_tweets = all_tweets.set_index("cleaned_tweet")

		tweets = None
		for word in include:
			word = clean(word)
			try:
				tweets = pandas.concat([ tweets, all_tweets.filter(regex=word, axis=0).reset_index() ])
			except NameError:
				tweets = all_tweets.filter(regex=word, axis=0).reset_index()

		tweets = tweets.drop_duplicates()
		tweets = tweets.set_index("cleaned_tweet")

		for word in exclude:
			word = clean(word)
			tweets = tweets.drop( tweets.filter(regex=word, axis=0).index )

		tweets = tweets.reset_index()
		tweets = tweets.drop("cleaned_tweet", axis=1)
		tweets = tweets.drop_duplicates()

		outputdir = os.path.dirname(os.path.realpath(__file__)) + "/data/filter"
		outputfile = outputdir + "/" + os.path.splitext(datafile)[0]
		logging.info("writing to " + outputfile)
		if os.path.exists(outputfile):
			logging.warning(outputfile + " already exists, overwrite? [y|N]")
			if input() != 'y':
				continue
		tweets.to_csv(outputfile, index=False)

def parse(argp, args):
	if args.input == None:
		logging.error("provide a data directory with --input")
		return 1
	if not os.path.exists(args.input):
		logging.error("can't find data directory! (" + args.input + ")")
		return 1

	logging.info("loading lexicon...")
	lexicon = os.path.dirname(os.path.realpath(__file__)) + "/etc/lexicon"
	glosema = pandas.read_csv(lexicon)
	glosema["cleaned_word"] = glosema["word"].apply( lambda x: clean(x) )
	glosema = glosema.set_index("cleaned_word")

	logging.info("processing " + args.input)
	for datafile in os.listdir(args.input):
		logging.info("processing " + datafile)
		all_tweets = pandas.read_csv(args.input + "/" + datafile)
		all_tweets["cleaned_tweet"] = all_tweets["tweet"].apply( lambda x: clean(x) )

		# take unique words
		unique = all_tweets["cleaned_tweet"].str.split(" ", expand=True).stack().value_counts()
		# subtract single use words
		unique = pandas.DataFrame({ "cleaned_word": unique[unique > 1] })

		i1 = glosema.index
		i2 = unique.index

		in_glosema = glosema[i1.isin(i2)].reset_index()

		# aggreggate words by emotions based on number of occurrences
		found = in_glosema.sort_values(by=["emotion","word"]).groupby(["emotion","word","intensity"]).size().to_frame("occurrences")
		# filter found words based on a threshold of occurrences
		found = found[found["occurrences"] >= 1]
		found.reset_index(inplace=True)
		# calc intensities
		found["total_intensity"] = found["intensity"] * found["occurrences"]
		intensities = found[["emotion","total_intensity"]].pivot_table(index=["emotion"], aggfunc="sum").reset_index()

		outputdir = os.path.dirname(os.path.realpath(__file__)) + "/data/parse"
		outputfile = outputdir + "/" + os.path.splitext(datafile)[0]
		logging.info("writing to " + outputfile)
		if os.path.exists(outputfile):
			logging.warning(outputfile + " already exists, overwrite? [y|N]")
			if input() != 'y':
				continue
		intensities.to_csv(outputfile, index=False)
		found.to_csv(outputfile, mode="a", index=False)

def predict(argp, args):
	import tensorflow
	import tensorflow_hub

	if args.input == None:
		logging.error("provide a data directory with --input")
		return 1
	if not os.path.exists(args.input):
		logging.error("can't find data directory! (" + args.input + ")")
		return 1

	use = load_use()

	logging.info("loading config...")
	model_file = os.path.dirname(os.path.realpath(__file__)) + "/etc/models/default"
	try:
		model = tensorflow.keras.models.load_model(model_file)
	except:
		logging.error("can't load model at " + model_file)
		return 1

	logging.info("processing " + args.input)
	for datafile in os.listdir(args.input):
		logging.info("processing " + datafile)
		tweets = pandas.read_csv(args.input + "/" + datafile)
		predictions = tweets["tweet"].apply( lambda x: format(model.predict( use([x]) )[0][1], "f") )
		predictions.name = "predict"

		outputdir = os.path.dirname(os.path.realpath(__file__)) + "/data/predict"
		outputfile = outputdir + "/" + os.path.splitext(datafile)[0]
		logging.info("writing to " + outputfile)
		if os.path.exists(outputfile):
			logging.warning(outputfile + " already exists, overwrite? [y|N]")
			if input() != 'y':
				continue
		predictions.to_csv(outputfile, index=False)

def tally(argp, args):
	if args.input == None:
		logging.error("provide a data directory with --input")
		return 1
	if not os.path.exists(args.input):
		logging.error("can't find data directory! (" + args.input + ")")
		return 1

	logging.info("loading config...")
	config_file = os.path.dirname(os.path.realpath(__file__)) + "/etc/tacitus.conf"
	config = json.load(open(config_file))
	if config["PREDICT_LOW_THRESHOLD"] == '' or config["PREDICT_HIGH_THRESHOLD"] == '':
		logging.error("empty parameters in config! (PREDICT_LOW_THRESHOLD, PREDICT_HIGH_THRESHOLD)")
		return 1

	logging.info("processing " + args.input)
	outputdir = os.path.dirname(os.path.realpath(__file__)) + "/data/tally"
	for datafile in os.listdir(args.input):
		logging.info("processing " + datafile)
		predictions = pandas.read_csv(args.input + "/" + datafile)
		pos = predictions.loc[ predictions["predict"] >= config["PREDICT_HIGH_THRESHOLD"] ].size
		neg = predictions.loc[ (predictions["predict"] > config["PREDICT_LOW_THRESHOLD"]) & (predictions["predict"] < config["PREDICT_HIGH_THRESHOLD"]) ].size
		trend = str( pos - neg > 0 )

		outputfile = outputdir + "/" + os.path.splitext(datafile)[0]
		logging.info("writing to " + outputfile)
		if os.path.exists(outputfile):
			logging.warning(outputfile + " already exists, overwrite? [y|N]")
			if input() != 'y':
				continue
		tally = pandas.DataFrame({ "pos": [pos], "neg": [neg], "trend": [trend] })
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
		if input() != 'y':
			return 1

	logging.info("loading hyperparameters...")
	if config["SEED"] == '' or config["EPOCHS"] == '' or config["BATCH_SIZE"] == '':
		logging.error("empty parameters in config! (SEED, EPOCHS, BATCH_SIZE)")
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
	train_tweets, test_tweets, y_train, y_test = train_test_split( tweets.tweet, polarity, test_size = .1, random_state = config["SEED"] )
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
	model.add( tensorflow.keras.layers.Dense(units=512, input_shape=(X_train.shape[1], ), activation='relu') )
	model.add( tensorflow.keras.layers.Dropout(rate=0.5) )
	model.add( tensorflow.keras.layers.Dense(units=512, activation='relu') )
	model.add( tensorflow.keras.layers.Dropout(rate=0.5) )
	model.add( tensorflow.keras.layers.Dense(2, activation='softmax') )
	model.compile( loss='categorical_crossentropy', optimizer=tensorflow.keras.optimizers.Adam(0.01), metrics=['accuracy'] )
	logging.info(model.summary())

	logging.info("training model...")
	model.fit(
		X_train, y_train,
		epochs=config["EPOCHS"],
		batch_size=config["BATCH_SIZE"],
		validation_split=0.1,
		verbose=1,
		shuffle=True
	)

	logging.info("evaluating model...")
	model.evaluate(X_test, y_test)

	logging.info("saving model...")
	model.save(modeldir)

