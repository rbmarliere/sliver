import pathlib

import pandas
import sklearn.model_selection
import tensorflow
import tensorflow_decision_forests as tfdf
import tensorflow_addons as tfa

from sliver.models.trainers.df import DecisionForestTrainer
from sliver.models.interface import IModel


class w20230404(IModel):
    test_size = 0.20
    batch_size = 32

    @property
    def trainer(self):
        return DecisionForestTrainer()

    def load(self):
        return tensorflow.keras.models.load_model(self.path)

    def get(self):
        model = tfdf.keras.RandomForestModel(
            # model = tfdf.keras.GradientBoostedTreesModel(
            # verbose=2,
            task=tfdf.keras.core.Task.REGRESSION,
            # tuner=self.get_tuner(),
            # num_trees=1200,
            # split_axis="SPARSE_OBLIQUE",
        )

        metrics = tfa.metrics.r_square.RSquare()
        model.compile(metrics=[metrics])

        return model

    def preprocess(self, filepath):
        filepath = pathlib.Path().cwd() / filepath
        filepath = filepath.resolve()
        assert filepath.is_file()

        df = pandas.read_csv(filepath)

        if "time" in df.columns:
            df = df.drop("time", axis=1)

        # train_df, test_df = sklearn.model_selection.train_test_split(
        #     df,
        #     test_size=self.test_size,
        #     random_state=93,
        # )

        train_size = int(len(df) * (1 - self.test_size))
        train_df = df[:train_size]
        test_df = df[train_size:]

        print(train_df)
        print(test_df)

        train_ds = tfdf.keras.pd_dataframe_to_tf_dataset(
            train_df, label="operation", task=tfdf.keras.core.Task.REGRESSION
        )
        test_ds = tfdf.keras.pd_dataframe_to_tf_dataset(
            test_df, label="operation", task=tfdf.keras.core.Task.REGRESSION
        )

        # train_target = train_df.pop("operation")
        # train_ds = tensorflow.data.Dataset.from_tensor_slices(
        #     (train_df.values.tolist(), train_target)
        # ).batch(self.batch_size)

        # test_target = test_df.pop("operation")
        # test_ds = tensorflow.data.Dataset.from_tensor_slices(
        #     (test_df.values.tolist(), test_target)
        # ).batch(self.batch_size)

        return train_ds, test_ds

    def get_tuner(self):
        # Configure the tuner.
        # Create a Random Search tuner with 50 trials.
        # tuner = tfdf.tuner.RandomSearch(num_trials=50)
        # Define the search space.
        # Adding more parameters generaly improve the quality of the model, but make
        # the tuning last longer.
        # tuner.choice("min_examples", [2, 5, 7])
        # tuner.choice("categorical_algorithm", ["CART", "RANDOM"])
        # Some hyper-parameters are only valid for specific values of other
        # hyper-parameters. For example, the "max_depth" parameter is mostly useful when
        # "growing_strategy=LOCAL" while "max_num_nodes" is better suited when
        # "growing_strategy=BEST_FIRST_GLOBAL".
        # local_search_space = tuner.choice("growing_strategy", ["LOCAL"])
        # local_search_space.choice("max_depth", [3, 4, 5])
        # merge=True indicates that the parameter (here "growing_strategy") is already
        # defined, and that new values are added to it.
        # global_search_space = tuner.choice(
        #     "growing_strategy", ["BEST_FIRST_GLOBAL"], merge=True
        # )
        # global_search_space.choice("max_num_nodes", [16, 32, 64, 128, 256])
        # tuner.choice("use_hessian_gain", [True, False])
        # tuner.choice("shrinkage", [0.02, 0.05, 0.10, 0.15])
        # tuner.choice("num_candidate_attributes_ratio", [0.2, 0.5, 0.9, 1.0])
        # Uncomment some (or all) of the following hyper-parameters to increase the
        # quality of the search. The number of trial should be increased accordingly.
        # tuner.choice("split_axis", ["AXIS_ALIGNED"])
        # oblique_space = tuner.choice("split_axis", ["SPARSE_OBLIQUE"], merge=True)
        # oblique_space.choice("sparse_oblique_normalization",
        #                      ["NONE", "STANDARD_DEVIATION", "MIN_MAX"])
        # oblique_space.choice("sparse_oblique_weights", ["BINARY", "CONTINUOUS"])
        # oblique_space.choice("sparse_oblique_num_projections_exponent", [1.0, 1.5])
        tuner = tfdf.tuner.RandomSearch(num_trials=50, use_predefined_hps=True)
        return tuner
