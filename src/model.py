import logging
import os
import pandas
import shutil
import src.standardize
import tensorflow
import yaml

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
    df[target] = [ x[0] for x in model.predict(df["tweet"], verbose=1, use_multiprocessing=True, workers=os.cpu_count) ]
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

    raw_df = pandas.read_csv(args.input, encoding="utf-8", lineterminator="\n", sep="\t")

    i = int(len(raw_df)*(80/100))
    train_df = raw_df.head(i)
    val_df = raw_df.iloc[i:max(raw_df.index)]

    raw_train_ds = tensorflow.data.Dataset.from_tensor_slices( (train_df["tweet"], train_df[target]) ).batch(batch_size)
    raw_val_ds = tensorflow.data.Dataset.from_tensor_slices( (val_df["tweet"], val_df[target]) ).batch(batch_size)

    vectorize_layer = tensorflow.keras.layers.TextVectorization(
        standardize=src.standardize.standardize,
        max_tokens=max_features,
        output_mode="int",
        output_sequence_length=sequence_length)
    train_text = raw_train_ds.map(lambda x, y: x)
    vectorize_layer.compile()
    vectorize_layer.adapt(train_text)

    def vectorize_text(text, label):
        text = tensorflow.expand_dims(text, -1)
        return vectorize_layer(text), label
    train_ds = raw_train_ds.map(vectorize_text)
    val_ds = raw_val_ds.map(vectorize_text)

    model = tensorflow.keras.Sequential([
        tensorflow.keras.layers.Embedding(max_features + 1, embedding_dim, mask_zero=True),
        tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(256, return_sequences=True)),
        tensorflow.keras.layers.Bidirectional(tensorflow.keras.layers.LSTM(32)),
        tensorflow.keras.layers.Dense(64, activation="relu"),
        tensorflow.keras.layers.Dropout(0.5),
        tensorflow.keras.layers.Dense(1, activation="tanh")
    ])
    model.compile(
        loss=tensorflow.keras.losses.MeanSquaredError(),
        optimizer=tensorflow.keras.optimizers.Adam()
    )

    model.summary()
    callback = tensorflow.keras.callbacks.EarlyStopping(monitor='loss', patience=2, min_delta=0.01)
    tensorboard_callback = tensorflow.keras.callbacks.TensorBoard(log_dir=modelpath+"/logs", histogram_freq=1)
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=[callback, tensorboard_callback]
    )

    # test_ds
    #loss, accuracy = model.evaluate(test_ds)
    #print("Loss: ", loss)
    #print("Accuracy: ", accuracy)

    export_model = tensorflow.keras.Sequential([
        vectorize_layer,
        model,
        tensorflow.keras.layers.Activation("tanh")
    ])
    export_model.compile(
        loss=tensorflow.keras.losses.MeanSquaredError(),
        optimizer=tensorflow.keras.optimizers.Adam(),
    )

    export_model.summary()
    export_model.save(modelpath)

def train_B(argp, args):
    print("BERT")
