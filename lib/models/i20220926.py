#!/usr/bin/env python3
import os
import sys

import pandas
import sklearn
import tensorflow
import transformers

sys.path.insert(0, "../..")

import src as hypnox  # noqa: E402

# load model config
model_name = "i20220926"
config = hypnox.utils.load_yaml("/../lib/models/" + model_name + ".yaml")

# check if model exists and asks for confirmation
if os.path.exists(model_name):
    print("directory " + model_name + " is not empty!")
    sys.exit(1)

# load training data
raw_df = pandas.read_csv("training.tsv",
                         encoding="utf-8",
                         lineterminator="\n",
                         sep="\t")

# check training data
if "tweet" and "intensity" and "polarity" not in raw_df.columns:
    print("malformed training data")
    sys.exit(1)

# drop duplicates
raw_df = raw_df.drop_duplicates(subset="tweet", keep="last")

# preprocess training data and drop empty rows (based on output of clean)
raw_df["tweet"] = raw_df["tweet"].apply(hypnox.utils.standardize)
raw_df = raw_df.dropna()

if config.yaml["class"] == "polarity":
    # take only labeled polarity rows (positive 1 or negative 2)
    raw_df = raw_df[raw_df.polarity != 0].reset_index(drop=True)

# load transformer
bert = transformers.TFAutoModel.from_pretrained(
    config.yaml["bert"],
    num_labels=config.yaml["num_labels"],
    from_pt=True)
tokenizer = transformers.AutoTokenizer.from_pretrained(
    config.yaml["bert"])

# split training data into training and validation sets
train_df, val_df, = sklearn.model_selection.train_test_split(
    raw_df,
    stratify=raw_df[config.yaml["class"]],
    test_size=config.yaml["test_size"],
    random_state=93)

# tokenize training data
train_tok = dict(
    tokenizer(train_df["tweet"].values.tolist(),
              truncation=True,
              padding="max_length",
              max_length=config.yaml["max_length"],
              return_tensors="tf",
              return_token_type_ids=False))
val_tok = dict(
    tokenizer(val_df["tweet"].values.tolist(),
              truncation=True,
              padding="max_length",
              max_length=config.yaml["max_length"],
              return_tensors="tf",
              return_token_type_ids=False))

# build tensorflow datasets
train_ds = tensorflow.data.Dataset.from_tensor_slices(
    (train_tok, train_df[config.yaml["class"]])).batch(
        config.yaml["batch_size"])
val_ds = tensorflow.data.Dataset.from_tensor_slices(
    (val_tok, val_df[config.yaml["class"]])).batch(
        config.yaml["batch_size"])

# build model
input_ids = tensorflow.keras.layers.Input(
    shape=(config.yaml["max_length"], ), name="input_ids", dtype="int32")
mask = tensorflow.keras.layers.Input(shape=(config.yaml["max_length"], ),
                                     name="attention_mask",
                                     dtype="int32")
embeddings = bert(input_ids, attention_mask=mask)[0]
X = tensorflow.keras.layers.GlobalMaxPool1D()(embeddings)
X = tensorflow.keras.layers.BatchNormalization()(X)
X = tensorflow.keras.layers.Dense(156, activation="relu")(X)
X = tensorflow.keras.layers.Dropout(0.2)(X)
y = tensorflow.keras.layers.Dense(config.yaml["num_labels"],
                                  activation="softmax",
                                  name="outputs")(X)
model = tensorflow.keras.Model(inputs=[input_ids, mask], outputs=y)
model.layers[2].trainable = False

# set up model parameters
loss = tensorflow.keras.losses.SparseCategoricalCrossentropy()
metrics = tensorflow.keras.metrics.SparseCategoricalAccuracy("accuracy")
optimizer = tensorflow.keras.optimizers.Adam(
    learning_rate=config.yaml["learning_rate"])

# compile model
model.compile(loss=loss, optimizer=optimizer, metrics=[metrics])
model.summary()

# train and evaluate model
earlystop = tensorflow.keras.callbacks.EarlyStopping(
    monitor=config.yaml["monitor"],
    patience=config.yaml["patience"],
    min_delta=config.yaml["min_delta"],
    verbose=1,
    mode="min",
    restore_best_weights=True)
tensorboard = tensorflow.keras.callbacks.TensorBoard(
    log_dir=model_name + "/logs", histogram_freq=1)
model.fit(train_ds,
          validation_data=val_ds,
          epochs=config.yaml["epochs"],
          callbacks=[earlystop, tensorboard],
          batch_size=config.yaml["batch_size"])

# save model
model.save(model_name)
