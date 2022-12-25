import tensorflow
import transformers

config = {
    "name": "p20221129",
    "class": "polarity",
    "bert": "vinai/bertweet-base",
    "num_labels": 3,
    "val_size": 0.15,
    "test_size": 0.05,
    "max_length": 180,
    "batch_size": 128,
    "epochs": 40,
    "learning_rate": 0.00005,
    "patience": 2,
    "min_delta": 0.001,
    "monitor": "loss"
}


def get_bert():
    return transformers.TFAutoModelForMaskedLM.from_pretrained(
        config["bert"], num_labels=config["num_labels"], from_pt=True)


def load_tokenizer(modelpath: str = config["bert"]):
    return transformers.AutoTokenizer.from_pretrained(modelpath)


def load_model(modelpath):
    return tensorflow.keras.models.load_model(
        modelpath, custom_objects={"TFRobertaForMaskedLM": get_bert()})


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
    X = tensorflow.keras.layers.Dropout(0.5)(X)
    y = tensorflow.keras.layers.Dense(config["num_labels"],
                                      activation="softmax",
                                      name="outputs")(X)

    model = tensorflow.keras.Model(inputs=[input_ids, mask], outputs=y)
    model.layers[2].trainable = False

    loss = tensorflow.keras.losses \
        .SparseCategoricalCrossentropy(from_logits=False)

    optimizer = tensorflow.keras.optimizers \
        .Adam(learning_rate=config["learning_rate"])

    model.compile(loss=loss,
                  optimizer=optimizer,
                  metrics=["accuracy"])

    return model
