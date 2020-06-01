import json
import nltk
import re
import tweepy
import pprint

# download stopwords from nltk
nltk.download('stopwords')

# load config parameters to memory
with open('config.json') as f:
	config = json.load(f)

def clean_text(tweet):
	# remove links
	tweet = re.sub("http\S+", "", tweet)
	# leave only letters and numbers
	tweet = re.sub("[^a-zA-Z0-9]", " ", tweet)
	# convert to lower case, split into individual words
	words = tweet.lower().split()
	# remove stopwords
	stops = set(nltk.corpus.stopwords.words("english"))
	meaningful_words = [w for w in words if not w in stops]
	# stem words
	stemmer = nltk.stem.porter.PorterStemmer()
	singles = [stemmer.stem(word) for word in meaningful_words]
	# join the words back into one string
	return(" ".join(singles))
	# todo: spellcheck?

class AcheronListener(tweepy.StreamListener):
	def on_status(self, status):
		# ignore retweets
		if 'retweeted_status' in status._json:
			return
		# ignore replies
		if status._json['in_reply_to_user_id']:
			return
		# if tweet is truncated, get all text
		if 'extended_tweet' in status._json:
			tweet = status.extended_tweet['full_text']
		else:
			tweet = status.text
		# transform tweet into a single line
		tweet = tweet.replace('\n', ' ').replace('\r', '') + '\n'
		print(tweet)
		# clean the tweet text
		tweet = clean_text(tweet)
		print(tweet)
		print()
		print()
		with open('data', 'a') as output:
			#todo: check if file exists, rename, etc
			print(tweet, file=output)

# initialize tweepy api object
auth = tweepy.OAuthHandler(config['CONSUMER_KEY'], config['CONSUMER_SECRET'])
auth.set_access_token(config['ACCESS_KEY'], config['ACCESS_SECRET'])
api = tweepy.API(auth)

# load the ids of the users to track into memory
try:
	with open('uids') as uids:
		users = uids.read().splitlines()
except FileNotFoundError:
	users = []
	with open('uids', 'a') as uids:
		for user in config['TRACK_USERS']:
			# retrieve user id by name from twitter api
			uid = str(api.get_user(user.strip()).id)
			print(uid, file=uids)
			users.append(uid)

acheron = AcheronListener()
stream = tweepy.Stream(auth = api.auth, listener=acheron)
#stream.filter(languages=["en"], follow=users)
stream.filter(languages=["en"], track=['bitcoin'])

