import tensorflow
import transformers

config = {
    "name": "p20221014",
    "class": "polarity",
    "bert": "finiteautomata/bertweet-base-sentiment-analysis",
    "num_labels": 3,
    "val_size": 0.15,
    "test_size": 0.05,
    "max_length": 180,
    "batch_size": 64,
    "epochs": 30,
    "learning_rate": 0.0004,
    "patience": 5,
    "min_delta": 0.001,
    "monitor": "val_loss"
}


def get_bert():
    return transformers.TFAutoModel.from_pretrained(
        config["bert"], num_labels=config["num_labels"], from_pt=True)


def get_tokenizer():
    return transformers.AutoTokenizer.from_pretrained(config["bert"])


def load_model(modelpath):
    return tensorflow.keras.models.load_model(
        modelpath, custom_objects={"TFRobertaModel": get_bert()})


def get_model():
    # load transformer
    bert = transformers.TFAutoModel.from_pretrained(
        config["bert"], num_labels=config["num_labels"], from_pt=True)

    # build model
    input_ids = tensorflow.keras.layers.Input(shape=(config["max_length"], ),
                                              name="input_ids",
                                              dtype="int32")
    mask = tensorflow.keras.layers.Input(shape=(config["max_length"], ),
                                         name="attention_mask",
                                         dtype="int32")
    embeddings = bert(input_ids, attention_mask=mask)[0]
    X = tensorflow.keras.layers.GlobalMaxPool1D()(embeddings)
    X = tensorflow.keras.layers.BatchNormalization()(X)
    X = tensorflow.keras.layers.Dense(8, activation="relu")(X)
    X = tensorflow.keras.layers.Dropout(0.5)(X)
    y = tensorflow.keras.layers.Dense(config["num_labels"],
                                      activation="softmax",
                                      name="outputs")(X)
    model = tensorflow.keras.Model(inputs=[input_ids, mask], outputs=y)
    model.layers[2].trainable = False

    # set up model parameters
    loss = tensorflow.keras.losses.SparseCategoricalCrossentropy()
    optimizer = tensorflow.keras.optimizers.Adam(
        learning_rate=config["learning_rate"])
    metrics = ["accuracy"]

    # compile model
    model.compile(loss=loss, optimizer=optimizer, metrics=metrics)

    return model
