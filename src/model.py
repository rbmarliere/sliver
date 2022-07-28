import logging
import os
import pandas
import shutil
import src.standardize
import tensorflow
import yaml

from sklearn.model_selection import train_test_split
from transformers import BertTokenizer, TFBertForSequenceClassification, pipeline
from datasets import Dataset

def predict(argp, args):
    if args.model == None:
        logging.error("provide a model name with --model")
        return 1
    modelpath = "models/" + args.model
    if not os.path.exists(modelpath):
        logging.warning(modelpath + " not found")
        return 1
    if args.input == None:
        logging.error("provide an input data .tsv file name with --input")
        return 1
    if not os.path.exists(args.input):
        logging.warning(args.input + " not found")
        return 1
    if args.polarity:
        modelcol = "model_p"
        target = "polarity"
    else:
        modelcol = "model_i"
        target = "intensity"
    model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": src.standardize.standardize})
    df = pandas.read_csv(args.input, lineterminator="\n", encoding="utf-8", sep="\t")
    df[target] = [ x[0] for x in model.predict(df["tweet"], verbose=1) ]
    df["intensity"] = df["intensity"].apply("{:.8f}".format)
    df["polarity"] = df["polarity"].apply("{:.8f}".format)
    output = "data/predict/" + args.model + ".tsv"
    df.to_csv(output, index=False, sep="\t")
    logging.info("saved output data to " + output)

def train(argp, args):
    if args.input == None:
        logging.error("provide a training data .tsv file name with --input")
        return 1
    if not os.path.exists(args.input):
        logging.warning(args.input + " not found")
        return 1
    if args.model == None:
        logging.error("provide a model name with --model")
        return 1
    modelpath = "models/" + args.model
    if os.path.exists(modelpath):
        logging.warning(modelpath + " already exists, overwrite? [y|N]")
        if input() != "y":
            return 1
        shutil.rmtree(modelpath)
    modelcfgpath = "models/" + args.model + ".yaml"
    if not os.path.exists(modelcfgpath):
        logging.warning(modelcfgpath + " not found")
        return 1
    if args.polarity:
        modelcol = "model_p"
        target = "polarity"
    else:
        modelcol = "model_i"
        target = "intensity"

    with open(modelcfgpath, "r") as stream:
        try:
            modelcfg = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            return 1
    batch_size = modelcfg["batch_size"]
    max_features = modelcfg["max_features"]
    sequence_length = modelcfg["sequence_length"]
    embedding_dim = modelcfg["embedding_dim"]
    epochs = modelcfg["epochs"]
    patience = modelcfg["patience"]
    min_delta = modelcfg["min_delta"]
    test_size = modelcfg["test_size"]

    raw_df = pandas.read_csv(args.input, encoding="utf-8", lineterminator="\n", sep="\t")
    df_train, df_test, = train_test_split(raw_df, stratify=raw_df['intensity'], test_size=test_size, random_state=93)
    df_train, df_val = train_test_split(df_train, stratify=df_train['intensity'], test_size=test_size, random_state=93)
    raw_train_ds = tensorflow.data.Dataset.from_tensor_slices( (df_train["tweet"], df_train["intensity"]) ).batch(batch_size)
    raw_test_ds = tensorflow.data.Dataset.from_tensor_slices( (df_test["tweet"], df_test["intensity"]) ).batch(batch_size)
    raw_val_ds = tensorflow.data.Dataset.from_tensor_slices( (df_val["tweet"], df_val["intensity"]) ).batch(batch_size)

    vectorize_layer = tensorflow.keras.layers.TextVectorization(
        standardize=src.standardize.standardize,
        max_tokens=max_features,
        output_mode="int",
        output_sequence_length=sequence_length)
    vectorize_layer.compile()

    train_text = raw_train_ds.map(lambda x, y: x)
    vectorize_layer.adapt(train_text)

    def vectorize_text(text, label):
        text = tensorflow.expand_dims(text, -1)
        return vectorize_layer(text), label
    train_ds = raw_train_ds.map(vectorize_text)
    val_ds = raw_val_ds.map(vectorize_text)

    model = tensorflow.keras.Sequential([
        tensorflow.keras.layers.Embedding(max_features + 1, embedding_dim, mask_zero=True),
        tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(128, return_sequences=True)),
        tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(32)),
        tensorflow.keras.layers.Dense(64, activation="relu"),
        tensorflow.keras.layers.Dropout(0.5),
        tensorflow.keras.layers.Dense(1)
    ])
    model.compile(
        loss=tensorflow.keras.losses.BinaryCrossentropy(from_logits=True),
        optimizer=tensorflow.keras.optimizers.Adam(),
        metrics=tensorflow.metrics.BinaryAccuracy()
    )
    model.summary()

    earlystop = tensorflow.keras.callbacks.EarlyStopping(monitor='loss', patience=patience, min_delta=min_delta)
    tensorboard = tensorflow.keras.callbacks.TensorBoard(log_dir=modelpath+"/logs", histogram_freq=1)
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=[earlystop, tensorboard]
    )

    # test_ds
    #loss, accuracy = model.evaluate(test_ds)
    #print("Loss: ", loss)
    #print("Accuracy: ", accuracy)

    export_model = tensorflow.keras.Sequential([
        vectorize_layer,
        model,
        tensorflow.keras.layers.Activation("sigmoid")
    ])
    export_model.compile(
        loss=tensorflow.keras.losses.BinaryCrossentropy(from_logits=True),
        optimizer=tensorflow.keras.optimizers.Adam(),
        metrics=tensorflow.metrics.BinaryAccuracy()
    )
    export_model.summary()
    export_model.save(modelpath)

def predictb(argp, args):
    if args.model == None:
        logging.error("provide a model name with --model")
        return 1
    modelpath = "models/" + args.model
    if not os.path.exists(modelpath):
        logging.warning(modelpath + " not found")
        return 1
    if args.input == None:
        logging.error("provide an input data .tsv file name with --input")
        return 1
    if not os.path.exists(args.input):
        logging.warning(args.input + " not found")
        return 1

    class ListDataset(Dataset):
        def __init__(self, original_list):
            self.original_list = original_list

        def __len__(self):
            return len(self.original_list)

        def __getitem__(self, i):
            return self.original_list[i]

    model = TFBertForSequenceClassification.from_pretrained(modelpath)
    tokenizer = BertTokenizer.from_pretrained(modelpath + "/tokenizer")
    nlp = pipeline("text-classification", model=model, tokenizer=tokenizer)
    labels = {"Neutral": 0, "Negative": -1, "Positive": 1}
    df = pandas.read_csv(args.input, lineterminator="\n", encoding="utf-8", sep="\t")
    df["clean_tweet"] = df["tweet"].apply(src.standardize.clean)
    df = df.dropna()
    df["polarity"] = [ labels[i["label"]] for i in nlp(df["clean_tweet"].values.tolist()) ]
    df["intensity"] = df["intensity"].apply("{:.8f}".format)
    output = "data/predict/" + args.model + ".tsv"
    df.to_csv(output, index=False, sep="\t")
    logging.info("saved output data to " + output)

def trainb(argp, args):
    if args.input == None:
        logging.error("provide a training data .tsv file name with --input")
        return 1
    if not os.path.exists(args.input):
        logging.warning(args.input + " not found")
        return 1
    if args.model == None:
        logging.error("provide a model name with --model")
        return 1
    modelpath = "models/" + args.model
    if os.path.exists(modelpath):
        logging.warning(modelpath + " already exists, overwrite? [y|N]")
        if input() != "y":
            return 1
        shutil.rmtree(modelpath)
    modelcfgpath = "models/" + args.model + ".yaml"
    if not os.path.exists(modelcfgpath):
        logging.warning(modelcfgpath + " not found")
        return 1

    with open(modelcfgpath, "r") as stream:
        try:
            modelcfg = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            return 1
    batch_size = modelcfg["batch_size"]
    sequence_length = modelcfg["sequence_length"]
    epochs = modelcfg["epochs"]
    learning_rate = modelcfg["learning_rate"]
    patience = modelcfg["patience"]
    min_delta = modelcfg["min_delta"]

    # original labels = {0:'neutral', 1:'positive',2:'negative'}
    model = TFBertForSequenceClassification.from_pretrained('yiyanghkust/finbert-tone', num_labels=3, from_pt=True)
    tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-tone')

    raw_df = pandas.read_csv(args.input, encoding="utf-8", lineterminator="\n", sep="\t")
    raw_df["sentence"] = raw_df["sentence"].apply(src.standardize.clean)
    raw_df = raw_df.dropna()
    df_train, df_test, = train_test_split(raw_df, stratify=raw_df['label'], test_size=0.1, random_state=93)
    df_train, df_val = train_test_split(df_train, stratify=df_train['label'],test_size=0.1, random_state=93)
    dataset_train = Dataset.from_pandas(df_train)
    dataset_val = Dataset.from_pandas(df_val)
    dataset_test = Dataset.from_pandas(df_test)
    dataset_train = dataset_train.map(lambda e: tokenizer(e['sentence'], truncation=True, padding='max_length', max_length=sequence_length), batched=True)
    dataset_val = dataset_val.map(lambda e: tokenizer(e['sentence'], truncation=True, padding='max_length', max_length=sequence_length), batched=True)
    dataset_test = dataset_test.map(lambda e: tokenizer(e['sentence'], truncation=True, padding='max_length', max_length=sequence_length), batched=True)
    train_ds = dataset_train.to_tf_dataset(columns=['input_ids', 'token_type_ids', 'attention_mask'],
    label_cols=["label"], batch_size=batch_size)
    val_ds = dataset_val.to_tf_dataset(columns=['input_ids', 'token_type_ids', 'attention_mask'], label_cols=["label"], batch_size=batch_size)
    test_ds = dataset_test.to_tf_dataset(columns=['input_ids', 'token_type_ids', 'attention_mask'], label_cols=["label"], batch_size=batch_size)

    optimizer = tensorflow.keras.optimizers.Adam(learning_rate=learning_rate)
    loss = tensorflow.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    metric = tensorflow.keras.metrics.SparseCategoricalAccuracy('accuracy')
    model.compile(optimizer=optimizer, loss=loss, metrics=[metric])

    callback = tensorflow.keras.callbacks.EarlyStopping(monitor='accuracy', patience=patience, min_delta=min_delta)
    tensorboard_callback = tensorflow.keras.callbacks.TensorBoard(log_dir=modelpath + "/logs", histogram_freq=1)
    history = model.fit( train_ds, validation_data=val_ds, epochs=epochs, callbacks=[tensorboard_callback],
    batch_size=batch_size)

    model.save_pretrained(modelpath)
    tokenizer.save_pretrained(modelpath + "/tokenizer")

