import logging
import numpy
import os
import pandas
import sklearn
import src
import sys
import tensorflow
import transformers

def predict(args):
    # check if input file exists
    if not os.path.exists(args.input):
        logging.error(args.input + " not found")
        sys.exit(1)

    # load model config
    model_config = src.config.ModelConfig(args.model)
    model_config.check_model()

    # load transformer
    bert = transformers.TFAutoModel.from_pretrained(model_config.yaml["bert"], num_labels=model_config.yaml["num_labels"], from_pt=True)
    tokenizer = transformers.AutoTokenizer.from_pretrained(model_config.yaml["bert"])
    labels = {0: 0, 2: -1, 1: 1}

    # load model
    model = tensorflow.keras.models.load_model(model_config.model_path, custom_objects={"TFBertModel": bert})

    # load data
    df = pandas.read_csv(args.input, lineterminator="\n", encoding="utf-8", sep="\t")

    # preprocess model input
    df["clean_tweet"] = df["tweet"].apply(src.text_utils.standardize)
    df = df.dropna()

    # compute predictions
    inputs = tokenizer(df["clean_tweet"].values.tolist(), truncation=True, padding="max_length", max_length=model_config.yaml["max_length"], return_tensors="tf")
    prob = model.predict({ "input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"] }, verbose=1)

    # check model class
    if model_config.yaml["class"] == "polarity":
        df["polarity"] = [ labels[numpy.argmax(x)] * x[numpy.argmax(x)] for x in prob ]
        df["polarity"] = df["polarity"].apply("{:.8f}".format)
    elif model_config.yaml["class"] == "intensity":
        df["intensity"] = [ x[1] for x in prob ]
        df["intensity"] = df["intensity"].apply("{:.8f}".format)
    else:
        logging.error("could not parse model config file (model class is missing)")
        sys.exit(1)

    # drop aux. column
    df = df.drop("clean_tweet", axis=1)

    # output data
    output = "data/predict/" + args.model + ".tsv"
    df.to_csv(output, index=False, sep="\t")
    logging.info("saved output data to " + output)

def train(args):
    # load model config
    model_config = src.config.ModelConfig(args.model)
    model_config.check_overwrite()
    model_config.check_training()

    # load training data
    raw_df = pandas.read_csv(model_config.training_path, encoding="utf-8", lineterminator="\n", sep="\t")

    # check training data
    if "tweet" not in raw_df.columns and "intensity" not in raw_df.columns and "polarity" not in raw_df.columns:
        logging.error("malformed training data")
        sys.exit(1)

    # drop duplicates
    raw_df = raw_df.drop_duplicates(subset="tweet", keep="last")

    # preprocess training data and drop empty rows (based on output of clean)
    raw_df["tweet"] = raw_df["tweet"].apply(src.text_utils.standardize)
    raw_df = raw_df.dropna()

    if model_config.yaml["class"] == "polarity":
        # take only labeled polarity rows (positive 1 or negative 2)
        raw_df = raw_df[raw_df.polarity != 0].reset_index(drop=True)

    # load transformer
    bert = transformers.TFAutoModel.from_pretrained(model_config.yaml["bert"], num_labels=model_config.yaml["num_labels"], from_pt=True)
    tokenizer = transformers.AutoTokenizer.from_pretrained(model_config.yaml["bert"])

    # split training data into training, testing and validating sets
    train_df, test_df, = sklearn.model_selection.train_test_split(raw_df, stratify=raw_df[ model_config.yaml["class"] ], test_size=model_config.yaml["test_size"], random_state=93)
    train_df, val_df = sklearn.model_selection.train_test_split(train_df, stratify=train_df[ model_config.yaml["class"] ],test_size=model_config.yaml["test_size"], random_state=93)

    # tokenize training data
    train_tok = dict( tokenizer(train_df["tweet"].values.tolist(), truncation=True, padding="max_length", max_length=model_config.yaml["max_length"], return_tensors="tf", return_token_type_ids=False) )
    val_tok = dict( tokenizer(val_df["tweet"].values.tolist(), truncation=True, padding="max_length", max_length=model_config.yaml["max_length"], return_tensors="tf", return_token_type_ids=False) )
    test_tok = dict( tokenizer(test_df["tweet"].values.tolist(), truncation=True, padding="max_length", max_length=model_config.yaml["max_length"], return_tensors="tf", return_token_type_ids=False) )

    # build tensorflow datasets
    train_ds = tensorflow.data.Dataset.from_tensor_slices( (train_tok, train_df[ model_config.yaml["class"] ]) ).batch(model_config.yaml["batch_size"])
    val_ds = tensorflow.data.Dataset.from_tensor_slices( (val_tok, val_df[ model_config.yaml["class"] ]) ).batch(model_config.yaml["batch_size"])
    test_ds = tensorflow.data.Dataset.from_tensor_slices( (test_tok, test_df[ model_config.yaml["class"] ]) ).batch(model_config.yaml["batch_size"])

    # build model
    input_ids = tensorflow.keras.layers.Input(shape=(model_config.yaml["max_length"],), name='input_ids', dtype='int32')
    mask = tensorflow.keras.layers.Input(shape=(model_config.yaml["max_length"],), name='attention_mask', dtype='int32')
    embeddings = bert(input_ids, attention_mask=mask)[0]
    X = tensorflow.keras.layers.GlobalMaxPool1D()(embeddings)
    X = tensorflow.keras.layers.BatchNormalization()(X)
    X = tensorflow.keras.layers.Dense(156, activation='relu')(X)
    X = tensorflow.keras.layers.Dropout(0.2)(X)
    #X = tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(32, return_sequences=True))(embeddings)
    #X = tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(16))(X)
    #X = tensorflow.keras.layers.Dense(8, activation="relu")(X)
    #X = tensorflow.keras.layers.Dropout(0.3)(X)
    y = tensorflow.keras.layers.Dense(model_config.yaml["num_labels"], activation='softmax', name='outputs')(X)
    model = tensorflow.keras.Model(inputs=[input_ids, mask], outputs=y)
    model.layers[2].trainable = False

    # set up model parameters
    loss = tensorflow.keras.losses.SparseCategoricalCrossentropy()
    metrics = tensorflow.keras.metrics.SparseCategoricalAccuracy("accuracy")
    optimizer = tensorflow.keras.optimizers.Adam(learning_rate=model_config.yaml["learning_rate"])

    # compile model
    model.compile(loss=loss, optimizer=optimizer, metrics=metrics)
    model.summary()

    # train and evaluate model
    earlystop = tensorflow.keras.callbacks.EarlyStopping(monitor=model_config.yaml["val_loss"], patience=model_config.yaml["patience"], min_delta=model_config.yaml["min_delta"], verbose=1, mode="min", restore_best_weights=True)
    tensorboard = tensorflow.keras.callbacks.TensorBoard(log_dir=model_config.model_path + "/logs", histogram_freq=1)
    model.fit( train_ds, validation_data=val_ds, epochs=model_config.yaml["epochs"], callbacks=[earlystop, tensorboard], batch_size=model_config.yaml["batch_size"])
    model.evaluate( test_ds, callbacks=[tensorboard] )

    # save model
    model.save(model_config.model_path)
    #tokenizer.save_pretrained(model_config.model_path + "/tokenizer")

