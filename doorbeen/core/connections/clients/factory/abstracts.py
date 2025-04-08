from abc import abstractmethod, ABC

from doorbeen.core.types.ts_model import TSModel


class DatabaseClientFactory(ABC):
    @abstractmethod
    def create_client(self, credentials: TSModel) -> TSModel:
        pass

