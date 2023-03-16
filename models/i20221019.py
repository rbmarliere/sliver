import tensorflow
import transformers


config = {
    "name": "i20221019",
    "class": "intensity",
    "bert": "vinai/bertweet-base",
    "num_labels": 2,
    "val_size": 0.15,
    "test_size": 0.05,
    "max_length": 180,
    "batch_size": 64,
    "epochs": 33,
    "learning_rate": 0.00001,
    "min_delta": 0.005,
    "patience": 1,
    "monitor": "val_loss"
}


def get_bert():
    return transformers.TFAutoModel.from_pretrained(
        config["bert"], num_labels=config["num_labels"], from_pt=True)


def load_tokenizer(modelpath: str = config["bert"]):
    return transformers.AutoTokenizer.from_pretrained(modelpath)


def load_model(modelpath):
    return tensorflow.keras.models.load_model(
        modelpath, custom_objects={"TFRobertaModel": get_bert()})


def get_model():
    input_ids = tensorflow.keras.layers.Input(shape=(config["max_length"], ),
                                              name="input_ids",
                                              dtype="int32")
    mask = tensorflow.keras.layers.Input(shape=(config["max_length"], ),
                                         name="attention_mask",
                                         dtype="int32")

    embeddings = get_bert()(input_ids, attention_mask=mask)[0]
    X = tensorflow.keras.layers.GlobalMaxPool1D()(embeddings)
    X = tensorflow.keras.layers.BatchNormalization()(X)
    X = tensorflow.keras.layers.Dense(256, activation="relu")(X)
    X = tensorflow.keras.layers.Dropout(0.3)(X)
    y = tensorflow.keras.layers.Dense(1, activation="sigmoid",
                                      name="outputs")(X)

    model = tensorflow.keras.Model(inputs=[input_ids, mask], outputs=y)
    model.layers[2].trainable = False

    loss = tensorflow.keras.losses.BinaryCrossentropy()
    optimizer = tensorflow.keras.optimizers.Adam(
        learning_rate=config["learning_rate"])
    metrics = ["accuracy"]

    model.compile(loss=loss, optimizer=optimizer, metrics=metrics)

    return model
