class DecisionForestTrainer:
    def train(self, model, train_ds, test_ds):
        model.fit(train_ds)
        model.summary()
        model.evaluate(test_ds)
        model.make_inspector().export_to_tensorboard(f"{model.path}/logs")
        model.save(model.path)
