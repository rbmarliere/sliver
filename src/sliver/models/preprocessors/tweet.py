import pathlib

import pandas
import sklearn.model_selection
import tensorflow

from sliver.utils import standardize


class TweetPreprocessor:
    def __init__(self, model):
        self.model = model

    def preprocess(self, filepath):
        filepath = pathlib.Path().cwd() / filepath
        filepath = filepath.resolve()
        assert filepath.is_file()

        # load training data
        raw_df = pandas.read_csv(
            filepath, encoding="utf-8", lineterminator="\n", sep="\t"
        )

        # check training data
        assert "tweet" and "intensity" and "polarity" in raw_df.columns

        # drop duplicates
        raw_df = raw_df.drop_duplicates(subset="tweet", keep="last")
        raw_df = raw_df.dropna()

        # preprocess training data
        raw_df["tweet"] = raw_df["tweet"].apply(standardize)
        raw_df["tweet"] = raw_df["tweet"].str.slice(0, self.model.max_length)

        if self.model.type == "polarity":
            # take only labeled polarity rows (positive 1 or negative 2)
            raw_df = raw_df.loc[(raw_df["intensity"] > 0) | (raw_df["polarity"] > 0)]

        # split training data into training, validation and test sets
        total_test_size = self.model.val_size + self.model.test_size
        val_test_ratio = (self.model.test_size * 100 / total_test_size) / 100
        train_df, aux_df = sklearn.model_selection.train_test_split(
            raw_df,
            stratify=raw_df[self.model.type],
            test_size=total_test_size,
            random_state=93,
        )
        val_df, test_df = sklearn.model_selection.train_test_split(
            aux_df,
            stratify=aux_df[self.model.type],
            test_size=val_test_ratio,
            random_state=93,
        )

        return train_df, val_df, test_df

    def tokenize(self, filepath):
        train_df, val_df, test_df = self.preprocess(filepath)

        train_tok = dict(
            self.model.tokenizer(
                train_df["tweet"].values.tolist(),
                truncation=True,
                padding="max_length",
                max_length=self.model.max_length,
                return_tensors="tf",
                return_token_type_ids=False,
            )
        )
        val_tok = dict(
            self.model.tokenizer(
                val_df["tweet"].values.tolist(),
                truncation=True,
                padding="max_length",
                max_length=self.model.max_length,
                return_tensors="tf",
                return_token_type_ids=False,
            )
        )
        test_tok = dict(
            self.model.tokenizer(
                test_df["tweet"].values.tolist(),
                truncation=True,
                padding="max_length",
                max_length=self.model.max_length,
                return_tensors="tf",
                return_token_type_ids=False,
            )
        )

        # build tensorflow datasets
        train_ds = tensorflow.data.Dataset.from_tensor_slices(
            (train_tok, train_df[self.model.type])
        ).batch(self.model.batch_size)
        val_ds = tensorflow.data.Dataset.from_tensor_slices(
            (val_tok, val_df[self.model.type])
        ).batch(self.model.batch_size)
        test_ds = tensorflow.data.Dataset.from_tensor_slices(
            (test_tok, test_df[self.model.type])
        ).batch(self.model.batch_size)

        return train_ds, val_ds, test_ds
