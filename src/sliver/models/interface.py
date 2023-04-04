from abc import ABC, abstractmethod

from sliver.config import Config


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

    def __init__(self):
        self.name = self.__class__.__name__
        self.path = f"{Config().MODELS_DIR}/{self.name}"

    @property
    @abstractmethod
    def load(self):
        ...

    @abstractmethod
    def get(self):
        ...
