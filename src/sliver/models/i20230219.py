import tensorflow
import transformers

from sliver.models.interface import IModel


class i20230219(IModel):
    val_size = 0.09
    test_size = 0.04
    batch_size = 128
    epochs = 33
    learning_rate = 0.000007
    min_delta = 0.005
    patience = 1
    monitor = "loss"

    type = "intensity"
    bert = "vinai/bertweet-base"
    num_labels = 2
    max_length = 180

    def __init__(self):
        super().__init__()
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(self.path)

    def get_bert(self):
        return transformers.TFAutoModel.from_pretrained(
            self.bert, num_labels=self.num_labels, from_pt=True
        )

    def load(self):
        return tensorflow.keras.models.load_model(
            self.path, custom_objects={"TFRobertaModel": self.get_bert()}
        )

    def get(self):
        input_ids = tensorflow.keras.layers.Input(
            shape=(self.max_length,), name="input_ids", dtype="int32"
        )

        mask = tensorflow.keras.layers.Input(
            shape=(self.max_length,), name="attention_mask", dtype="int32"
        )

        embeddings = self.get_bert()(input_ids, attention_mask=mask)[0]
        X = tensorflow.keras.layers.GlobalMaxPool1D()(embeddings)
        X = tensorflow.keras.layers.BatchNormalization()(X)
        X = tensorflow.keras.layers.Dense(1024, activation="relu")(X)
        X = tensorflow.keras.layers.Dropout(0.3)(X)
        y = tensorflow.keras.layers.Dense(1, activation="sigmoid", name="outputs")(X)

        model = tensorflow.keras.Model(inputs=[input_ids, mask], outputs=y)
        model.layers[2].trainable = False

        loss = tensorflow.keras.losses.BinaryCrossentropy()

        optimizer = tensorflow.keras.optimizers.Adam(learning_rate=self.learning_rate)

        model.compile(loss=loss, optimizer=optimizer, metrics=["accuracy"])

        return model
