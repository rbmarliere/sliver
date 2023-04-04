import importlib
import pathlib

import tensorflow

from sliver.exceptions import DisablingError
from sliver.print import print

models = []


def load(model_name):
    for model in models:
        if model.name == model_name:
            return model

    print(f"loading model {model_name}")

    try:
        model_module = importlib.import_module(f"sliver.models.{model_name}")
        model_class = getattr(model_module, model_name)
        model_obj = model_class()
    except (ModuleNotFoundError, AttributeError):
        raise DisablingError(f"model {model_name} does not exist")

    modelpath = pathlib.Path(model_obj.path).resolve()
    if not modelpath.exists():
        raise DisablingError(f"model {model_name} does not exist")

    try:
        model = model_class().load()
    except tensorflow.errors.ResourceExhaustedError:
        del models[0]
        try:
            model = model_class().load()
        except tensorflow.errors.ResourceExhaustedError:
            raise DisablingError(f"model {model_name} is too large to be loaded")
    except Exception:
        raise DisablingError(f"could not load model {model_name}")

    models.append(model)

    return model
