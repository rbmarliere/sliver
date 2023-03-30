import importlib
import pathlib

import tensorflow
import transformers

from sliver.config import Config
from sliver.exceptions import ModelDoesNotExist, ModelTooLarge
from sliver.print import print

transformers.logging.set_verbosity_error()
tensorflow.get_logger().setLevel("INFO")

models = []


def get_model(model_name):
    model_module = importlib.import_module("models." + model_name)
    model = model_module.get_model()
    model.config = model_module.config
    model.tokenizer = model_module.load_tokenizer()
    return model


def load_model(model_name):
    for model in models:
        if model.config["name"] == model_name:
            return model

    print("loading model {m}".format(m=model_name))

    modelpath = pathlib.Path(Config().MODELS_DIR + "/" + model_name).resolve()
    if not modelpath.exists():
        print("model {m} does not exist".format(m=model_name))
        raise ModelDoesNotExist

    model_module = importlib.import_module("sliver.models." + model_name)

    try:
        model = model_module.load_model(modelpath)
    except tensorflow.errors.ResourceExhaustedError:
        del models[0]
        try:
            model = model_module.load_model(modelpath)
        except tensorflow.errors.ResourceExhaustedError:
            print("model {m} is too large to be loaded".format(m=model_name))
            raise ModelTooLarge
    except Exception as e:
        print("could not load model {m}".format(m=model_name), exception=e)
        raise ModelDoesNotExist

    model.config = model_module.config
    model.tokenizer = model_module.load_tokenizer(modelpath=modelpath)

    models.append(model)

    return model
