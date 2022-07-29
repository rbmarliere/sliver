import logging
import numpy
import os
import pandas
import shutil
import sklearn
import src
import sys
import tensorflow
import transformers
import yaml

def predict(args):
    # check if model exists
    path = os.path.dirname(os.path.abspath(__file__))
    modelpath = path + "/../models/" + args.model
    if not os.path.exists(modelpath):
        logging.error(modelpath + " not found")
        sys.exit(1)

    # check if input file exists
    if not os.path.exists(args.input):
        logging.error(args.input + " not found")
        sys.exit(1)

    # load data
    df = pandas.read_csv(args.input, lineterminator="\n", encoding="utf-8", sep="\t")

    # check which column to use
    if args.polarity:
        # load model
        model = transformers.TFBertForSequenceClassification.from_pretrained(modelpath)
        tokenizer = transformers.BertTokenizer.from_pretrained(modelpath + "/tokenizer")
        labels = {0: 0, 2: -1, 1: 1}

        # preprocess model input
        df["clean_tweet"] = df["tweet"].apply(src.standardize.clean)
        df = df.dropna()

        # compute predictions
        inputs = tokenizer(df["clean_tweet"].values.tolist(), truncation=True, padding="max_length", max_length=280, return_tensors="tf")
        outputs = model.predict([inputs["input_ids"], inputs["attention_mask"], inputs["token_type_ids"]], verbose=1)
        prob = tensorflow.nn.softmax( outputs.logits )
        df["model_p"] = args.model
        df["polarity"] = [ labels[numpy.argmax(x)] for x in prob.numpy() ]

    else:
        # load model
        model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": src.standardize.standardize})

        # compute predictions
        df["model_i"] = args.model
        df["intensity"] = [ "{:.8f}".format(x[0]) for x in model.predict(df["tweet"], verbose=1) ]

    # output data
    output = "data/predict/" + args.model + ".tsv"
    df.to_csv(output, index=False, sep="\t")
    logging.info("saved output data to " + output)

def train(args):
    path = os.path.dirname(os.path.abspath(__file__))

    # check if model exists
    modelpath = path + "/../models/" + args.model
    if os.path.exists(modelpath):
        logging.warning(modelpath + " already exists, overwrite? [y|N]")
        if input() != "y":
            sys.exit(1)
        # remove old model upon confirmation
        shutil.rmtree(modelpath)

    # check if model configuration file exists
    modelcfgpath = path + "/../etc/" + args.model + ".yaml"
    if not os.path.exists(modelcfgpath):
        logging.error(modelcfgpath + " not found")
        sys.exit(1)

    # load yaml model configuration
    with open(modelcfgpath, "r") as stream:
        try:
            modelcfg = yaml.safe_load(stream)
            modelcfg["path"] = modelpath
        except yaml.YAMLError as exc:
            logging.error("could not parse model config file")
            sys.exit(1)

    # check if training data file exists
    training_filepath = path + "/../data/training/" + args.model + ".tsv"
    if not os.path.exists(training_filepath):
        logging.error("training data file " + training_filepath + " not found")
        sys.exit(1)

    # check training data
    if "tweet" not in raw_df.columns and "intensity" not in raw_df.columns and "polarity" not in raw_df.columns:
        logging.error("malformed training data")
        sys.exit(1)

    # load training data
    raw_df = pandas.read_csv(training_filepath, encoding="utf-8", lineterminator="\n", sep="\t")

    # check which class of model to train
    if args.polarity:
        train_p(modelcfg, raw_df)
    else:
        train_i(modelcfg, raw_df)

def train_i(modelcfg, raw_df):
    # split training data into training, testing and validating sets
    train_df, test_df, = sklearn.model_selection.train_test_split(raw_df, stratify=raw_df["intensity"], test_size=modelcfg["test_size"], random_state=93)
    train_df, val_df = sklearn.model_selection.train_test_split(train_df, stratify=train_df["intensity"], test_size=modelcfg["test_size"], random_state=93)

    # build tensorflow datasets
    train_ds = tensorflow.data.Dataset.from_tensor_slices( (train_df["tweet"], train_df["intensity"]) ).batch(modelcfg["batch_size"])
    test_ds = tensorflow.data.Dataset.from_tensor_slices( (test_df["tweet"], test_df["intensity"]) ).batch(modelcfg["batch_size"])
    val_ds = tensorflow.data.Dataset.from_tensor_slices( (val_df["tweet"], val_df["intensity"]) ).batch(modelcfg["batch_size"])

    # build vectorization embedding layer to use in end to end model
    train_text = train_ds.map(lambda x, y: x)
    vectorize_layer = tensorflow.keras.layers.TextVectorization(
        standardize=src.standardize.standardize,
        max_tokens=modelcfg["max_features"],
        output_mode="int",
        output_sequence_length=modelcfg["sequence_length"])
    vectorize_layer.compile()
    vectorize_layer.adapt(train_text)

    # vectorize training data and build vocabulary
    def vectorize_text(text, label):
        text = tensorflow.expand_dims(text, -1)
        return vectorize_layer(text), label
    train_ds = train_ds.map(vectorize_text)
    val_ds = val_ds.map(vectorize_text)
    test_ds = test_ds.map(vectorize_text)

    # define model params
    loss = tensorflow.keras.losses.BinaryCrossentropy(from_logits=True)
    optimizer = tensorflow.keras.optimizers.Adam(learning_rate=modelcfg["learning_rate"])
    metrics = tensorflow.metrics.BinaryAccuracy("accuracy")

    # compile model
    model = tensorflow.keras.Sequential([
        tensorflow.keras.layers.Embedding(modelcfg["max_features"] + 1, modelcfg["embedding_dim"], mask_zero=True),
        tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(128, return_sequences=True)),
        tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(32)),
        tensorflow.keras.layers.Dense(64, activation="relu"),
        tensorflow.keras.layers.Dropout(0.5),
        tensorflow.keras.layers.Dense(1)
    ])
    model.compile(loss=loss, optimizer=optimizer, metrics=metrics)
    model.summary()

    # train and evaluate model
    earlystop = tensorflow.keras.callbacks.EarlyStopping(monitor="loss", patience=modelcfg["patience"], min_delta=modelcfg["min_delta"])
    tensorboard = tensorflow.keras.callbacks.TensorBoard(log_dir=modelcfg["path"]+"/logs", histogram_freq=1)
    model.fit( train_ds, validation_data=val_ds, epochs=modelcfg["epochs"], callbacks=[earlystop, tensorboard] )
    model.evaluate( test_ds, callbacks=[tensorboard] )

    # compile end to end model
    e2e_model = tensorflow.keras.Sequential([ vectorize_layer, model, tensorflow.keras.layers.Activation("sigmoid") ])
    e2e_model.compile(loss=loss, optimizer=optimizer, metrics=metrics)
    e2e_model.summary()

    # save model
    e2e_model.save(modelcfg["path"])

def train_p(modelcfg, raw_df):
    # preprocess training data and drop empty rows (based on output of clean)
    raw_df["tweet"] = raw_df["tweet"].apply(src.standardize.clean)
    raw_df = raw_df.dropna()

    # split training data into training, testing and validating sets
    train_df, test_df, = sklearn.model_selection.train_test_split(raw_df, stratify=raw_df["polarity"], test_size=modelcfg["test_size"], random_state=93)
    train_df, val_df = sklearn.model_selection.train_test_split(train_df, stratify=train_df["polarity"],test_size=modelcfg["test_size"], random_state=93)

    # grab transformer
    model = transformers.TFBertForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone", num_labels=3, from_pt=True)
    tokenizer = transformers.BertTokenizer.from_pretrained("yiyanghkust/finbert-tone")

    # tokenize training data
    train_tok = dict( tokenizer(train_df["tweet"].values.tolist(), truncation=True, padding="max_length", max_length=280, return_tensors="tf") )
    val_tok = dict( tokenizer(val_df["tweet"].values.tolist(), truncation=True, padding="max_length", max_length=280, return_tensors="tf") )
    test_tok = dict( tokenizer(test_df["tweet"].values.tolist(), truncation=True, padding="max_length", max_length=280, return_tensors="tf") )

    # build tensorflow datasets
    train_ds = tensorflow.data.Dataset.from_tensor_slices( (train_tok, train_df["polarity"]) ).batch(modelcfg["batch_size"])
    val_ds = tensorflow.data.Dataset.from_tensor_slices( (val_tok, val_df["polarity"]) ).batch(modelcfg["batch_size"])
    test_ds = tensorflow.data.Dataset.from_tensor_slices( (test_tok, test_df["polarity"]) ).batch(modelcfg["batch_size"])

    # define model params
    loss = tensorflow.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    optimizer = tensorflow.keras.optimizers.Adam(learning_rate=modelcfg["learning_rate"])
    metrics = tensorflow.keras.metrics.SparseCategoricalAccuracy("accuracy")

    # compile model
    model.compile(loss=loss, optimizer=optimizer, metrics=metrics)

    # train and evaluate model
    earlystop = tensorflow.keras.callbacks.EarlyStopping(monitor="accuracy", patience=modelcfg["patience"], min_delta=modelcfg["min_delta"])
    tensorboard = tensorflow.keras.callbacks.TensorBoard(log_dir=modelcfg["path"] + "/logs", histogram_freq=1)
    model.fit( train_ds, validation_data=val_ds, epochs=modelcfg["epochs"], callbacks=[earlystop, tensorboard], batch_size=modelcfg["batch_size"])
    model.evaluate( test_ds, callbacks=[tensorboard] )

    # save model
    model.save_pretrained(modelcfg["path"])
    tokenizer.save_pretrained(modelcfg["path"] + "/tokenizer")

