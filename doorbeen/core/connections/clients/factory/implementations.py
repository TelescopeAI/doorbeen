from doorbeen.core.connections.clients.NoSQL.mongo import MongoDBClient
from doorbeen.core.connections.clients.SQL.bigquery import BigQueryClient
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.connections.clients.factory.abstracts import DatabaseClientFactory
from doorbeen.core.connections.credentials.NoSQL.mongo import MongoDBCredentials
from doorbeen.core.connections.credentials.SQL.bigquery import BigQueryCredentials
from doorbeen.core.connections.credentials.SQL.common import CommonSQLCredentials


class CommonSQLClientFactory(DatabaseClientFactory):
    def create_client(self, credentials: CommonSQLCredentials) -> CommonSQLClient:
        return CommonSQLClient(credentials=credentials)


class BigQueryClientFactory(DatabaseClientFactory):
    def create_client(self, credentials: BigQueryCredentials) -> BigQueryClient:
        return BigQueryClient(credentials=credentials)


class MongoClientFactory(DatabaseClientFactory):
    def create_client(self, credentials: MongoDBCredentials) -> MongoDBClient:
        return MongoDBClient(credentials=credentials)