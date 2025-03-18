from core.connections.clients.SQL.bigquery import BigQueryClient
from core.connections.clients.factory.implementations import CommonSQLClientFactory, BigQueryClientFactory
from core.connections.clients.generator import DatabaseClientGenerator
from core.connections.credentials.SQL.bigquery import BigQueryCredentialsFactory
from core.connections.credentials.SQL.common import CommonSQLCredentialsFactory
from core.connections.credentials.generator import DatabaseCredentialsGenerator
from core.types.databases import DatabaseTypes
from core.types.ts_model import TSModel


class DBClientService(TSModel):

    @staticmethod
    def get_client(details: dict, db_type: DatabaseTypes):
        factory = None
        client = None
        creds = None
        is_common_sql = db_type in [DatabaseTypes.POSTGRESQL, DatabaseTypes.MYSQL, DatabaseTypes.ORACLE,
                                    DatabaseTypes.SQLITE]
        if is_common_sql:
            creds_factory = CommonSQLCredentialsFactory()
            creds = DatabaseCredentialsGenerator().parse(factory=creds_factory, **details)
            client_factory = CommonSQLClientFactory()
            details['dialect'] = details['dialect'].lower()
        if db_type == DatabaseTypes.BIGQUERY:
            creds_factory = BigQueryCredentialsFactory()
            creds = DatabaseCredentialsGenerator().parse(factory=creds_factory, **details)
            client_factory = BigQueryClientFactory()
        client = DatabaseClientGenerator().parse(factory=client_factory, credentials=creds)
        return client


if __name__ == '__main__':
    conn_details = {"host": 'localhost', "port": 5432, "username": 'root', "password": 'password',
                    "database": 'core', "dialect": 'postgresql'}
    bq_details = {"project_id": "telescope-web-dev", "service_account_details": {
}
}
    # connection: CommonSQLClient = DBClientService.get_client(details=conn_details, db_type=DatabaseTypes.POSTGRESQL)
    connection: BigQueryClient = DBClientService.get_client(details=bq_details, db_type=DatabaseTypes.BIGQUERY)
    print("Client: ", connection)
    print(connection.connect())

