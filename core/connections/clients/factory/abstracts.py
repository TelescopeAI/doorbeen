from abc import abstractmethod, ABC

from core.types.ts_model import TSModel


class DatabaseClientFactory(ABC):
    @abstractmethod
    def create_client(self, credentials: TSModel) -> TSModel:
        pass

