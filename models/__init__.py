import importlib
import pathlib
import sys

import tensorflow
import transformers

import core


transformers.logging.set_verbosity_error()
tensorflow.get_logger().setLevel("INFO")


def get(model_name):
    model_module = importlib.import_module("models." + model_name)
    model = model_module.get_model()
    model.config = model_module.config
    model.tokenizer = model_module.load_tokenizer()
    return model


def load(model_name):
    try:
        return getattr(sys.modules[__name__], model_name)
    except AttributeError:
        pass

    core.watchdog.info("loading model {m}".format(m=model_name))

    modelpath = pathlib.Path(core.config["MODELS_DIR"] + "/" +
                             model_name).resolve()
    if not modelpath.exists():
        core.watchdog.info("model {m} does not exist"
                           .format(m=model_name))
        raise core.errors.ModelDoesNotExist

    model_module = importlib.import_module("models." + model_name)
    try:
        model = model_module.load_model(modelpath)
    except tensorflow.errors.ResourceExhaustedError:
        core.watchdog.info("model {m} is too large to be loaded"
                           .format(m=model_name))
        raise core.errors.ModelTooLarge
    model.config = model_module.config
    model.tokenizer = model_module.load_tokenizer(modelpath=modelpath)

    setattr(sys.modules[__name__], model_name, model)

    return model
