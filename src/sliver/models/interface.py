import pathlib
from abc import ABC, abstractmethod

from sliver.config import Config
from sliver.exceptions import DisablingError


class IModel(ABC):
    name = None
    path = None
    val_size = None
    test_size = None
    batch_size = None
    epochs = None
    learning_rate = None
    min_delta = None
    patience = None
    monitor = None

    def __init__(self, load=True):
        self.name = self.__class__.__name__
        self.path = f"{Config().MODELS_DIR}/{self.name}"

        if load:
            modelpath = pathlib.Path(self.path).resolve()
            if not modelpath.exists():
                raise DisablingError(f"model {self.name} does not exist")
            self.model = self.load()

    def predict(self, *args, **kwargs):
        return self.model.predict(*args, **kwargs)

    @abstractmethod
    def load(self):
        ...

    @abstractmethod
    def get(self):
        ...
