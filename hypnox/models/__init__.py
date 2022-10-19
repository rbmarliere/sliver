import importlib
import pathlib

import hypnox


def get(model_name):
    model_module = importlib.import_module("hypnox.models." + model_name)
    model = model_module.get_model()
    model.config = model_module.config
    return model


def load(model_name):
    modelpath = pathlib.Path(hypnox.config["HYPNOX_MODELS_DIR"] + "/" +
                             model_name).resolve()
    assert modelpath.exists()

    model_module = importlib.import_module("hypnox.models." + model_name)
    model = model_module.load_model(modelpath)
    model.config = model_module.config
    model.tokenizer = model_module.get_tokenizer()
    return model
