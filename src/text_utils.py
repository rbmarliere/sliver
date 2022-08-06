import nltk
import re
import string

try:
    nltk.data.find("corpora/stopwords.zip")
    nltk.data.find("corpora/wordnet.zip")
    nltk.data.find("corpora/omw-1.4.zip")
except LookupError:
    nltk.download("stopwords")
    nltk.download("wordnet")
    nltk.download("omw-1.4")

TO_KEEP_STOPWORDS = ["this", "that'll", "these", "having", "does", "doing", "until", "while", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "few", "both", "more", "most", "other", "some", "than", "too", "very", "can",
                     "will", "should", "should've", "now", "ain", "aren", "aren't", "could", "couldn", "couldn't", "didn", "didn't", "doesn", "doesn't", "hadn", "hadn't", "hasn", "hasn't", "haven", "haven't", "isn", "isn't", "mighn", "mightn't", "mustn", "mustn't", "needn", "needn't", "shan", "shan't", "shouldn", "shouldn't", "wasn", "wasn't", "weren", "weren't", "won'", "won't", "wouldn", "wouldn't", "if"]

nltkstops = set(nltk.corpus.stopwords.words("english"))
stops = [w for w in nltkstops if not w in TO_KEEP_STOPWORDS]

lem = nltk.stem.wordnet.WordNetLemmatizer()


def standardize(text):
    # convert to lower case
    text = text.lower()
    # remove carriages and tabs
    text = re.sub("(\n|\r|\t)", " ", text)
    text = text.strip()
    # remove links
    text = re.sub("http\S+", "", text)
    # remove hashtags, usernames and html entities
    text = re.sub("(#|@|&|\$)\S+", "", text)
    # remove punctuation
    text = re.sub("[%s]" % re.escape(string.punctuation), " ", text)
    # remove some stopwords
    text = re.sub("\\b(" + "|".join(stops) + ")\\b\s*", "", text)
    # keep only letters
    text = re.sub("[^a-zA-Z]", " ", text)
    # keep only words with more than 2 characters
    text = re.sub("\\b\S\S?\\b", "", text)
    # remove excess white spaces
    text = re.sub(" +", " ", text)
    # remove leading and trailing white spaces
    text = text.strip()

    # keep only sentences with four words minimum
    if len(text.split()) > 4:
        # lemmatize each word
        text = "".join([lem.lemmatize(w) for w in text])
        return text
    else:
        return None
