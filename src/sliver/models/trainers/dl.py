import tensorflow


class DeepLearningTrainer:
    val_size = None
    test_size = None
    batch_size = None
    epochs = None
    min_delta = None
    patience = None
    monitor = None

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def train(self, model, train_ds, val_ds, test_ds):
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
            monitor=self.monitor,
            patience=self.patience,
            min_delta=self.min_delta,
            verbose=1,
            mode="min",
            restore_best_weights=True,
        )

        tensorboard = tensorflow.keras.callbacks.TensorBoard(
            log_dir=f"{model.path}/logs", histogram_freq=1
        )

        model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=self.epochs,
            callbacks=[earlystop, tensorboard],
            batch_size=self.batch_size,
        )

        print("evaluation:")
        model.evaluate(test_ds, batch_size=self.batch_size)

        model.save(model.path)
