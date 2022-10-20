#!/usr/bin/env python3

import argparse

import tensorflow
from preprocess import preprocess, tokenize

import hypnox
import hypnox.models

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

    model = hypnox.models.get(args.model_name)
    config = hypnox.models.get_config(args.model_name)
    tokenizer = hypnox.models.get_tokenizer(args.model_name)

    modelpath = hypnox.config["HYPNOX_MODELS_DIR"] + "/" + args.model_name

    train_df, val_df, test_df = preprocess(model, config, args.input_file)
    train_ds, val_ds, test_ds = tokenize(model, config, tokenizer, train_df,
                                         val_df, test_df)

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
        monitor=config["monitor"],
        patience=config["patience"],
        min_delta=config["min_delta"],
        verbose=1,
        mode="min",
        restore_best_weights=True)

    tensorboard = tensorflow.keras.callbacks.TensorBoard(log_dir=modelpath +
                                                         "/logs",
                                                         histogram_freq=1)

    model.fit(train_ds,
              validation_data=val_ds,
              epochs=config["epochs"],
              callbacks=[earlystop, tensorboard],
              batch_size=config["batch_size"])
    result = model.evaluate(test_ds, batch_size=config["batch_size"])
    dict(zip(model.metrics_names, result))

    model.save(modelpath)
