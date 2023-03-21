import importlib
import pathlib
import sys

import tensorflow
import transformers

import core


print = core.watchdog.Watchdog().print

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

    modelpath = pathlib.Path(core.config["MODELS_DIR"] + "/" +
                             model_name).resolve()
    if not modelpath.exists():
        print("model {m} does not exist".format(m=model_name))
        raise core.errors.ModelDoesNotExist

    model_module = importlib.import_module("models." + model_name)

    try:
        model = model_module.load_model(modelpath)
    except tensorflow.errors.ResourceExhaustedError:
        del models[0]
        try:
            model = model_module.load_model(modelpath)
        except tensorflow.errors.ResourceExhaustedError:
            print("model {m} is too large to be loaded"
                  .format(m=model_name))
            raise core.errors.ModelTooLarge
    except Exception as e:
        print("could not load model {m}".format(m=model_name),
              exception=e)
        raise core.errors.ModelDoesNotExist

    model.config = model_module.config
    model.tokenizer = model_module.load_tokenizer(modelpath=modelpath)

    models.append(model)

    return model


def import_model(model_name):
    try:
        return getattr(sys.modules[__name__], model_name)
    except AttributeError:
        pass

    model = load_model(model_name)

    setattr(sys.modules[__name__], model_name, model)

    return model
