#!/usr/bin/env python3

import pathlib

import pandas
import sklearn.model_selection
import tensorflow

import core


def preprocess(model, filepath):
    filepath = pathlib.Path().cwd() / filepath
    filepath = filepath.resolve()
    assert filepath.is_file()

    # load training data
    raw_df = pandas.read_csv(filepath, encoding="utf-8", lineterminator="\n", sep="\t")

    # check training data
    assert "tweet" and "intensity" and "polarity" in raw_df.columns

    # drop duplicates
    raw_df = raw_df.drop_duplicates(subset="tweet", keep="last")
    raw_df = raw_df.dropna()

    # preprocess training data
    raw_df["tweet"] = raw_df["tweet"].apply(core.utils.standardize)
    raw_df["tweet"] = raw_df["tweet"].str.slice(0, model.config["max_length"])

    if model.config["class"] == "polarity":
        # take only labeled polarity rows (positive 1 or negative 2)
        raw_df = raw_df.loc[(raw_df["intensity"] > 0) | (raw_df["polarity"] > 0)]

    # split training data into training, validation and test sets
    total_test_size = model.config["val_size"] + model.config["test_size"]
    val_test_ratio = (model.config["test_size"] * 100 / total_test_size) / 100
    train_df, aux_df = sklearn.model_selection.train_test_split(
        raw_df,
        stratify=raw_df[model.config["class"]],
        test_size=total_test_size,
        random_state=93,
    )
    val_df, test_df = sklearn.model_selection.train_test_split(
        aux_df,
        stratify=aux_df[model.config["class"]],
        test_size=val_test_ratio,
        random_state=93,
    )

    return train_df, val_df, test_df


def tokenize(model, train_df, val_df, test_df):
    train_tok = dict(
        model.tokenizer(
            train_df["tweet"].values.tolist(),
            truncation=True,
            padding="max_length",
            max_length=model.config["max_length"],
            return_tensors="tf",
            return_token_type_ids=False,
        )
    )
    val_tok = dict(
        model.tokenizer(
            val_df["tweet"].values.tolist(),
            truncation=True,
            padding="max_length",
            max_length=model.config["max_length"],
            return_tensors="tf",
            return_token_type_ids=False,
        )
    )
    test_tok = dict(
        model.tokenizer(
            test_df["tweet"].values.tolist(),
            truncation=True,
            padding="max_length",
            max_length=model.config["max_length"],
            return_tensors="tf",
            return_token_type_ids=False,
        )
    )

    # build tensorflow datasets
    train_ds = tensorflow.data.Dataset.from_tensor_slices(
        (train_tok, train_df[model.config["class"]])
    ).batch(model.config["batch_size"])
    val_ds = tensorflow.data.Dataset.from_tensor_slices(
        (val_tok, val_df[model.config["class"]])
    ).batch(model.config["batch_size"])
    test_ds = tensorflow.data.Dataset.from_tensor_slices(
        (test_tok, test_df[model.config["class"]])
    ).batch(model.config["batch_size"])

    return train_ds, val_ds, test_ds
