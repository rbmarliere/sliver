import argparse
import os

import numpy
import pandas
import tensorflow
import tensorflow_hub
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from tqdm import tqdm
import datetime
import re
import nltk

import logging

# define logging level
logging.basicConfig(level=logging.INFO)

# parsing tacitus' arguments
argp = argparse.ArgumentParser(description="Compute all tweets in a directory.")
argp.add_argument("--datadir", help="Path to directory containing text files to process.", default="")
argp.add_argument("--tallydir", help="Path to output directory.", default="tally")
argp.add_argument("--model", help="Path to saved model to use.", type=os.path.abspath, default="model")

# check if required files are there
args = argp.parse_args()
if not os.path.exists(args.model):
	print("Model not found!")
	exit(1)
if not os.path.exists(args.datadir):
	print("Data directory not found!")
	exit(1)
if not os.path.exists(args.tallydir):
	os.mkdir(args.tallydir)

# load USE
logging.error("Loading USE...")
use = tensorflow_hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")

# load nltk stopwords
nltk.download('stopwords')

# helper to compute sentiment over a stream of tweets
def tally(dataframe, outputfile):
	pos = dataframe.loc[dataframe["score"] >= 0.65].size
	neg = dataframe.loc[ (dataframe["score"] > 0.19) & (dataframe["score"] < 0.65)].size
	with open(outputfile, "w") as out:
		print("Positives: " + str( pos ), file=out)
		print("Negatives: " + str( neg ), file=out)
		print("Result: " + str(pos - neg > 0), file=out)
		print("", file=out)

# helper to clean tweet text
def clean(tweet):
	# remove links
	tweet = re.sub("http\S+", "", tweet)
	# remove html entities
	tweet = re.sub("&\w+;", "", tweet)
	# remove usernames
	tweet = re.sub("(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9-_]+)", "", tweet)
	# leave only words
	tweet = re.sub("[^a-zA-Z]", " ", tweet)
	# convert to lower case, split into individual words
	words = tweet.lower().split()
	# remove stopwords, but keep some
	keep = [ "this", "that'll", "these", "having", "does", "doing", "until", "while", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "few", "both", "more", "most", "other", "some", "than", "too", "very", "can", "will", "should", "should’ve", "now", "ain", "aren", "aren’t", "could", "couldn", "couldn't", "didn", "didn’t", "doesn", "doesn’t", "hadn", "hadn’t", "hasn", "hasn’t", "haven", "haven’t", "isn", "isn’t", "mighn", "mightn't", "mustn", "mustn’t", "needn", "needn’t", "shan", "shan’t", "shouldn", "shouldn’t", "wasn", "wasn’t", "weren","weren’t", "won’", "won’t", "wouldn", "wouldn't" ]
	nltkstops = set(nltk.corpus.stopwords.words("english"))
	stops = [w for w in nltkstops if not w in keep]
	meaningful_words = [w for w in words if not w in stops]
	# stem words
	stemmer = nltk.stem.porter.PorterStemmer()
	singles = [stemmer.stem(word) for word in meaningful_words]
	# join the words with more than one char back into one string
	out = " ".join([w for w in singles if len(w) > 1])
	return out

# load glosema with word intensities
glosema = pandas.read_csv("glosema.csv")
glosema["cleaned_word"] = glosema["word"].apply( lambda x: clean(x) )

# iterate through all files in datadir
for datafile in os.listdir(args.datadir):
	# ignore non csv files
	if not datafile.endswith(".csv"):
		continue
	# load csv file
	tweets = pandas.read_csv(args.datadir + "/" + datafile)
	# remove duplicated tweets
	tweets = tweets.drop_duplicates()
	# write simple tally output
	outputfile = args.tallydir + "/" + os.path.splitext(datafile)[0] + ".txt"
	tally(tweets, outputfile)
	# clean tweets into a new column
	tweets["cleaned_tweet"] = tweets["tweet"].apply( lambda x: clean(x) )
	# count unique words occurrences
	unique = tweets["cleaned_tweet"].str.split(" ", expand=True).stack().value_counts()
	with open(outputfile, "a") as out:
		print("Unique words:", file=out)
		with pandas.option_context("display.max_rows", None):
			print(unique, file=out)

	# compare each word in each tweet against glosema values
	#for i, (idx, tweet) in enumerate(tweets.iterrows()):
	#	for i, (idx, word) in enumerate(glosema.iterrows()):
	#		if word.cleaned_word in tweet.cleaned_tweet:
	#			print("Found " + word.word + " in " + tweet.tweet)
	#			input()
