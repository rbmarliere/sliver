#!/usr/bin/env python3

import argparse

import tensorflow

import core
import models
from preprocess import preprocess, tokenize


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-i",
                      "--input-file",
                      help="path to training data file",
                      required=True)
    argp.add_argument("-m",
                      "--model-name",
                      help="name of the model to train",
                      required=True)
    args = argp.parse_args()

    model = models.get(args.model_name)

    modelpath = core.config["MODELS_DIR"] + "/" + args.model_name

    train_df, val_df, test_df = preprocess(model, args.input_file)

    print("training data")
    print(train_df)
    print("validation data")
    print(val_df)
    print("test data")
    print(test_df)

    train_ds, val_ds, test_ds = tokenize(model, train_df, val_df, test_df)

    model.summary()

    # https://www.tensorflow.org/guide/keras/train_and_evaluate#checkpointing_models
    checkpoint = tensorflow.keras.callbacks.ModelCheckpoint(
        # Path where to save the model
        # The two parameters below mean that we will overwrite
        # the current checkpoint if and only if
        # the `val_loss` score has improved.
        # The saved model name will include the current epoch.
        filepath="mymodel_{epoch}",
        save_best_only=True,  # Only save a model if `val_loss` has improved.
        monitor="val_loss",
        verbose=1,
    )

    earlystop = tensorflow.keras.callbacks.EarlyStopping(
        monitor=model.config["monitor"],
        patience=model.config["patience"],
        min_delta=model.config["min_delta"],
        verbose=1,
        mode="min",
        restore_best_weights=True)

    tensorboard = tensorflow.keras.callbacks.TensorBoard(log_dir=modelpath +
                                                         "/logs",
                                                         histogram_freq=1)

    model.fit(train_ds,
              validation_data=val_ds,
              epochs=model.config["epochs"],
              callbacks=[earlystop, tensorboard],
              batch_size=model.config["batch_size"])
    result = model.evaluate(test_ds, batch_size=model.config["batch_size"])
    dict(zip(model.metrics_names, result))

    model.save(modelpath)
    model.tokenizer.save_pretrained(modelpath)
