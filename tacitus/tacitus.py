import argparse
import datetime
import gensim
import logging
import numpy
import numpy
import os
import pandas
import preprocessor
import re
import sys
import tensorflow

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

argp = argparse.ArgumentParser(description="Gather relevant tweets.")
argp.add_argument("--model", help="Name to use when saving the model.", default="model")

args = argp.parse_args()
if os.path.exists(args.model):
	print("Model already exists in " + args.model + "! Overwrite? [y|N]")
	if input() is not 'y':
		exit(1)

# declare hyperparameters
validation_split = 0.2
embedding_dim = 666
epochs = 11
batch_size = 1

# load relevant tweets
relevant_file = open("train/relevant")
relevant_lines = relevant_file.read().splitlines()
relevant = pandas.DataFrame({ 'tweet': relevant_lines, 'is_relevant': [1] * len(relevant_lines) })
relevant["tweet"] = relevant["tweet"].apply(lambda x: preprocessor.clean(x))

# load irrelevant tweets
irrelevant_file = open("train/irrelevant")
irrelevant_lines = irrelevant_file.read().splitlines()
irrelevant = pandas.DataFrame({ 'tweet': irrelevant_lines, 'is_relevant': [0] * len(irrelevant_lines) })
irrelevant["tweet"] = irrelevant["tweet"].apply(lambda x: preprocessor.clean(x))

# combine all data
raw_data = pandas.concat([relevant, irrelevant])

# shuffle rows
raw_data = raw_data.sample(frac=1).reset_index(drop=True)

# build vocab
corpus = [tweet.split() for tweet in raw_data['tweet'].values.tolist()]
wvmodel = gensim.models.word2vec.Word2Vec(corpus, size=embedding_dim, window=10, min_count=5, workers=16, sg=1) # sg=1 is skipgram, default is 0 = cbow
wvmodel.wv.save_word2vec_format("corpus", binary=False)

# load vocab
embeddings_index = {}
f = open("corpus")
for line in f:
	values = line.split()
	word = values[0]
	coefs = numpy.asarray(values[1:])
	embeddings_index[word] = coefs

# vectorize data
tok = tensorflow.keras.preprocessing.text.Tokenizer()
tok.fit_on_texts(corpus)
seq = tok.texts_to_sequences(corpus)

maxlen = max([len(s) for s in corpus])

tweets_pad = tensorflow.python.keras.preprocessing.sequence.pad_sequences(seq, maxlen=maxlen)
is_relevant = raw_data['is_relevant'].values

num_words = len(tok.word_index) + 1
embedding_matrix = numpy.zeros((num_words, embedding_dim))
for word, i in tok.word_index.items():
	if i > num_words:
		continue
	embedding_vector = embeddings_index.get(word)
	if embedding_vector is not None:
		# words not found will be all-zeros
		embedding_matrix[i] = embedding_vector

# build model
inputs = tensorflow.keras.Input(shape=(None,), dtype="int64")
x = tensorflow.keras.layers.Embedding(
		num_words,
		embedding_dim,
		embeddings_initializer=tensorflow.keras.initializers.Constant( embedding_matrix ),
		input_length=maxlen,
		trainable=False
	)(inputs)
x = tensorflow.keras.layers.Dropout(0.5)(x)
x = tensorflow.keras.layers.Conv1D(128, 7, padding="valid", activation="relu", strides=3)(x)
x = tensorflow.keras.layers.Conv1D(128, 7, padding="valid", activation="relu", strides=3)(x)
x = tensorflow.keras.layers.GlobalMaxPooling1D()(x)
x = tensorflow.keras.layers.Dense(128, activation="relu")(x)
x = tensorflow.keras.layers.Dropout(0.5)(x)
predictions = tensorflow.keras.layers.Dense(1, activation="sigmoid", name="predictions")(x)
model = tensorflow.keras.Model(inputs, predictions)
model.compile(loss="binary_crossentropy", optimizer="adam", metrics=["accuracy"])

print(model.summary())

# train model
nsamples = int(validation_split * raw_data['tweet'].count())
x_train = tweets_pad[:-nsamples]
y_train = is_relevant[:-nsamples]
x_test  = tweets_pad[-nsamples:]
y_test  = is_relevant[-nsamples:]
model.fit(
	x_train,
	y_train,
	validation_data=(x_test, y_test),
	batch_size=batch_size,
	epochs=epochs
)

# create model to be used by acheron that receives raw strings as input
inputs = tensorflow.keras.Input(shape=(1,), dtype="string")
indices = tensorflow.keras.layers.experimental.preprocessing.TextVectorization(
			max_tokens=num_words,
			output_mode='int',
			output_sequence_length=maxlen
		)(inputs)
outputs = model(indices)
end_to_end_model = tensorflow.keras.Model(inputs, outputs)
end_to_end_model.compile(
	loss="binary_crossentropy", optimizer="adam", metrics=["accuracy"]
)

# save e2e model
end_to_end_model.save(args.model)

