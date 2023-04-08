import pathlib
from abc import ABC, abstractmethod

from sliver.config import Config
from sliver.exceptions import DisablingError


class IModel(ABC):
    name = None
    path = None

    def __init__(self, load=True):
        self.name = self.__class__.__name__
        self.path = f"{Config().MODELS_DIR}/{self.name}"

        if load:
            modelpath = pathlib.Path(self.path).resolve()
            if not modelpath.exists():
                raise DisablingError(f"model {self.name} does not exist")
            self.model = self.load()
        else:
            self.model = self.get()

    def __getattr__(self, attr):
        return getattr(self.model, attr)

    @property
    @abstractmethod
    def trainer(self):
        ...

    def train(self, filepath):
        self.trainer.train(self, *self.preprocess(filepath))

    @abstractmethod
    def load(self):
        ...

    @abstractmethod
    def get(self):
        ...

    @abstractmethod
    def preprocess(self, filepath):
        ...
