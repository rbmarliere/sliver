import importlib
from logging import exception, info

import tensorflow

from sliver.exceptions import DisablingError

models = []


def get(model_name):
    try:
        model_module = importlib.import_module(f"sliver.models.{model_name}")
        model_class = getattr(model_module, model_name)
    except (ModuleNotFoundError, AttributeError):
        raise DisablingError(f"model {model_name} does not exist")

    return model_class


def load(model_name):
    for model in models:
        if model.name == model_name:
            return model

    info(f"loading model {model_name}")

    model_class = get(model_name)

    try:
        model = model_class()
    except tensorflow.errors.ResourceExhaustedError:
        del models[0]
        try:
            model = model_class()
        except tensorflow.errors.ResourceExhaustedError:
            raise DisablingError(f"model {model_name} is too large to be loaded")
    except Exception as e:
        exception(e, exc_info=True)
        raise DisablingError(f"could not load model {model_name}")

    models.append(model)

    return model
