from doorbeen.core.connections.clients.base import DatabaseClient
from doorbeen.core.connections.credentials.NoSQL.mongo import MongoDBCredentials
from doorbeen.core.connections.credentials.factory import DatabaseCredentialsFactory


class MongoDBClient(DatabaseClient):
    credentials: MongoDBCredentials

    def connect(self):
        pass

    def get_uri(self):
        pass

    def query(self):
        pass

    def get_schema(self):
        pass


class MongoDBCredentialsFactory(DatabaseCredentialsFactory):
    def get_creds(self, **kwargs) -> MongoDBCredentials:
        return MongoDBCredentials(**kwargs)
