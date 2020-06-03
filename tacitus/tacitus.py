# https://keras.io/examples/nlp/text_classification_from_scratch/

from tensorflow.keras import layers
from tensorflow.keras.layers.experimental.preprocessing import TextVectorization
import datetime
import re
import tensorflow
import sys
import numpy

# load data
batch_size = 10

raw_train_ds = tensorflow.keras.preprocessing.text_dataset_from_directory(
    "train",
    batch_size=batch_size,
    validation_split=0.2,
    subset="training",
    seed=1337,
)
print(
    "Number of batches in raw_train_ds: %d"
    % tensorflow.data.experimental.cardinality(raw_train_ds)
)

raw_val_ds = tensorflow.keras.preprocessing.text_dataset_from_directory(
    "train",
    batch_size=batch_size,
    validation_split=0.2,
    subset="validation",
    seed=1337,
)
print(
    "Number of batches in raw_val_ds: %d" % tensorflow.data.experimental.cardinality(raw_val_ds)
)

#raw_test_ds = tensorflow.keras.preprocessing.text_dataset_from_directory(
#    "test", batch_size=batch_size
#)
#print(
#    "Number of batches in raw_test_ds: %d"
#    % tensorflow.data.experimental.cardinality(raw_test_ds)
#)

# model constants
max_features = 6666
embedding_dim = 33
sequence_length = 112

# vocab layer
vectorize_layer = TextVectorization(
    max_tokens=max_features,
    output_mode="int",
    output_sequence_length=sequence_length,
)

# create vocab
text_ds = raw_train_ds.map(lambda x, y: x)
vectorize_layer.adapt(text_ds)

# vectorize data
def vectorize_text(text, label):
    text = tensorflow.expand_dims(text, -1)
    return vectorize_layer(text), label
train_ds = raw_train_ds.map(vectorize_text)
val_ds = raw_val_ds.map(vectorize_text)
#test_ds = raw_test_ds.map(vectorize_text)
# Do async prefetching / buffering of the data for best performance on GPU.
train_ds = train_ds.cache().prefetch(buffer_size=10)
val_ds = val_ds.cache().prefetch(buffer_size=10)
#test_ds = test_ds.cache().prefetch(buffer_size=10)

# build model
# A integer input for vocab indices.
inputs = tensorflow.keras.Input(shape=(None,), dtype="int64")
#inputs = tensorflow.keras.Input(shape=(1,), dtype=tensorflow.string, name='text')
# Next, we add a layer to map those vocab indices into a space of dimensionality
# "embedding_dim".
x = layers.Embedding(max_features, embedding_dim)(inputs)
x = layers.Dropout(0.5)(x)
# Conv1D + global max pooling
x = layers.Conv1D(128, 7, padding="valid", activation="relu", strides=3)(x)
x = layers.Conv1D(128, 7, padding="valid", activation="relu", strides=3)(x)
x = layers.GlobalMaxPooling1D()(x)
# We add a vanilla hidden layer:
x = layers.Dense(128, activation="relu")(x)
x = layers.Dropout(0.5)(x)
# We project onto a single unit output layer, and squash it with a sigmoid:
predictions = layers.Dense(1, activation="sigmoid", name="predictions")(x)
model = tensorflow.keras.Model(inputs, predictions)
# Compile the model with binary crossentropy loss and an adam optimizer.
model.compile(loss="binary_crossentropy", optimizer="adam", metrics=["accuracy"])

## train model
epochs = 12
model.fit(train_ds, validation_data=val_ds, epochs=epochs)
#model.evaluate(test_ds)
## save model weights
#now = int(datetime.datetime.now().timestamp())
#model.save_weights("weights_" + str(now) + ".h5")

# A string input
inputs = tensorflow.keras.Input(shape=(1,), dtype="string")
# Turn strings into vocab indices
indices = vectorize_layer(inputs)
# Turn vocab indices into predictions
outputs = model(indices)
# Our end to end model
end_to_end_model = tensorflow.keras.Model(inputs, outputs)
end_to_end_model.compile(
    loss="binary_crossentropy", optimizer="adam", metrics=["accuracy"]
)
# Test it with `raw_test_ds`, which yields raw strings
#end_to_end_model.evaluate(raw_train_ds)

# load data
filename = sys.argv[1]
raw_data = open(filename)
for tweet in raw_data:
    pred = end_to_end_model.predict([tweet])
    if pred > 0.2:
        #print("FOUND POSITIVE TWEET:")
        print(pred)
        print(tweet)
