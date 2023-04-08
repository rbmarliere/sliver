import argparse

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

    model.train(args.input_file)


if __name__ == "__main__":
    train()
