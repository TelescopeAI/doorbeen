from core.connections.clients.NoSQL.mongo import MongoDBClient
from core.connections.clients.SQL.bigquery import BigQueryClient
from core.connections.clients.SQL.common import CommonSQLClient
from core.connections.clients.factory.abstracts import DatabaseClientFactory
from core.connections.credentials.NoSQL.mongo import MongoDBCredentials
from core.connections.credentials.SQL.bigquery import BigQueryCredentials
from core.connections.credentials.SQL.common import CommonSQLCredentials


class CommonSQLClientFactory(DatabaseClientFactory):
    def create_client(self, credentials: CommonSQLCredentials) -> CommonSQLClient:
        return CommonSQLClient(credentials=credentials)


class BigQueryClientFactory(DatabaseClientFactory):
    def create_client(self, credentials: BigQueryCredentials) -> BigQueryClient:
        return BigQueryClient(credentials=credentials)


class MongoClientFactory(DatabaseClientFactory):
    def create_client(self, credentials: MongoDBCredentials) -> MongoDBClient:
        return MongoDBClient(credentials=credentials)