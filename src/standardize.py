import nltk
import re
import string
import tensorflow

TO_KEEP_STOPWORDS = [ "this", "that'll", "these", "having", "does", "doing", "until", "while", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "few", "both", "more", "most", "other", "some", "than", "too", "very", "can", "will", "should", "should've", "now", "ain", "aren", "aren't", "could", "couldn", "couldn't", "didn", "didn't", "doesn", "doesn't", "hadn", "hadn't", "hasn", "hasn't", "haven", "haven't", "isn", "isn't", "mighn", "mightn't", "mustn", "mustn't", "needn", "needn't", "shan", "shan't", "shouldn", "shouldn't", "wasn", "wasn't", "weren","weren't", "won'", "won't", "wouldn", "wouldn't", "if" ]

try:
	nltk.data.find("corpora/stopwords")
except LookupError:
	nltk.download("stopwords")
nltkstops = set(nltk.corpus.stopwords.words("english"))
stops = [w for w in nltkstops if not w in TO_KEEP_STOPWORDS]

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

