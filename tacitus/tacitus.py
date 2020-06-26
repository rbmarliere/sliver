# HYPERPARAMS
RANDOM_SEED = 666
EPOCHS=11
BATCH_SIZE=32

import argparse
import os

import numpy
import pandas
import tensorflow
import tensorflow_hub
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from tqdm import tqdm

use = tensorflow_hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")

argp = argparse.ArgumentParser(description="Gather relevant tweets.")
argp.add_argument("--model", help="Name to use when saving the model.", default="model")

args = argp.parse_args()
if os.path.exists(args.model):
	print("Model already exists ('" + args.model + "')! Overwrite? [ y | N ]")
	if input() != "y":
		exit(1)

if not os.path.exists("train/pos"):
	print("train/pos file not found")
	exit(1)
if not os.path.exists("train/neg"):
	print("train/neg file not found")
	exit(1)

# load positive tweets
pos_file = open("train/pos")
pos_lines = pos_file.read().splitlines()
pos = pandas.DataFrame({ "tweet": pos_lines, "polarity": [1] * len(pos_lines) })

# load negative tweets
neg_file = open("train/neg")
neg_lines = neg_file.read().splitlines()
neg = pandas.DataFrame({ "tweet": neg_lines, "polarity": [0] * len(neg_lines) })

# combine all data
tweets = pandas.concat([pos, neg])

# shuffle rows
tweets = tweets.sample(frac=1).reset_index(drop=True)

# remove None rows
tweets = tweets.dropna()

polarity = OneHotEncoder(sparse=False).fit_transform( tweets.polarity.to_numpy().reshape(-1, 1) )

train_tweets, test_tweets, y_train, y_test = train_test_split( tweets.tweet, polarity, test_size = .1, random_state = RANDOM_SEED )

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

# build model
model = tensorflow.keras.Sequential()
model.add( tensorflow.keras.layers.Dense(units=512, input_shape=(X_train.shape[1], ), activation='relu') )
model.add( tensorflow.keras.layers.Dropout(rate=0.5) )
model.add( tensorflow.keras.layers.Dense(units=512, activation='relu') )
model.add( tensorflow.keras.layers.Dropout(rate=0.5) )
model.add( tensorflow.keras.layers.Dense(2, activation='softmax') )
model.compile( loss='categorical_crossentropy', optimizer=tensorflow.keras.optimizers.Adam(0.01), metrics=['accuracy'] )

print(model.summary())

# train model
model.fit(
	X_train, y_train,
	epochs=EPOCHS,
	batch_size=BATCH_SIZE,
	validation_split=0.1,
	verbose=1,
	shuffle=True
)

model.evaluate(X_test, y_test)

model.save(args.model)

