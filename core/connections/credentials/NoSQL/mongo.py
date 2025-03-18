from core.connections.credentials.factory import DatabaseCredentialsFactory
from core.types.ts_model import TSModel


class MongoDBCredentials(TSModel):
    host: str
    port: int


class MongoDBCredentialsFactory(DatabaseCredentialsFactory):
    def get_creds(self, **kwargs) -> MongoDBCredentials:
        return MongoDBCredentials(**kwargs)
