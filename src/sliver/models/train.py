import argparse

import tensorflow

import sliver.models


def train():
    argp = argparse.ArgumentParser()
    argp.add_argument(
        "-i", "--input-file", help="path to training data file", required=True
    )
    argp.add_argument(
        "-m", "--model-name", help="name of the model to train", required=True
    )
    args = argp.parse_args()

    model = sliver.models.get(args.model_name)(load=False)

    train_df, val_df, test_df = model.preprocess(args.input_file)

    model.summary()

    # # https://www.tensorflow.org/guide/keras/train_and_evaluate#checkpointing_models
    # checkpoint = tensorflow.keras.callbacks.ModelCheckpoint(
    #     # Path where to save the model
    #     # The two parameters below mean that we will overwrite
    #     # the current checkpoint if and only if
    #     # the `val_loss` score has improved.
    #     # The saved model name will include the current epoch.
    #     filepath="mymodel_{epoch}",
    #     save_best_only=True,  # Only save a model if `val_loss` has improved.
    #     monitor="val_loss",
    #     verbose=1,
    # )

    earlystop = tensorflow.keras.callbacks.EarlyStopping(
        monitor=model.monitor,
        patience=model.patience,
        min_delta=model.min_delta,
        verbose=1,
        mode="min",
        restore_best_weights=True,
    )

    tensorboard = tensorflow.keras.callbacks.TensorBoard(
        log_dir=f"{model.path}/logs", histogram_freq=1
    )

    model.fit(
        train_df,
        validation_data=val_df,
        epochs=model.epochs,
        callbacks=[earlystop, tensorboard],
        batch_size=model.batch_size,
    )
    result = model.evaluate(test_df, batch_size=model.batch_size)
    dict(zip(model.metrics_names, result))

    model.save(model.path)


if __name__ == "__main__":
    train()
