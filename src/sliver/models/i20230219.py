import tensorflow
import transformers

from sliver.models.interface import IModel
from sliver.models.preprocessors.tweet import TweetPreprocessor
from sliver.models.trainers.dl import DeepLearningTrainer


class i20230219(IModel):
    val_size = 0.09
    test_size = 0.04
    batch_size = 128

    type = "intensity"
    bert = "vinai/bertweet-base"
    num_labels = 2
    max_length = 180

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        tok = self.bert
        if "load" in kwargs and kwargs["load"]:
            tok = self.path

        self.tokenizer = transformers.AutoTokenizer.from_pretrained(tok)

    @property
    def trainer(self):
        return DeepLearningTrainer(
            epochs=33,
            min_delta=0.005,
            patience=1,
            monitor="loss",
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

        optimizer = tensorflow.keras.optimizers.Adam(learning_rate=0.000007)

        model.compile(loss=loss, optimizer=optimizer, metrics=["accuracy"])

        return model

    def preprocess(self, filepath):
        proc = TweetPreprocessor(self)
        return proc.tokenize(filepath)

    def save(self, *args, **kwargs):
        self.model.save(*args, **kwargs)
        self.tokenizer.save_pretrained(self.path)

    def get_bert(self):
        return transformers.TFAutoModel.from_pretrained(
            self.bert, num_labels=self.num_labels, from_pt=True
        )
