from core.connections.credentials.factory import DatabaseCredentialsFactory
from core.types.databases import DatabaseTypes
from core.types.ts_model import TSModel


class CommonSQLCredentials(TSModel):
    host: str
    port: int
    username: str
    password: str
    database: str
    dialect: DatabaseTypes


class CommonSQLCredentialsFactory(DatabaseCredentialsFactory):
    def get_creds(self, **kwargs) -> CommonSQLCredentials:
        return CommonSQLCredentials(**kwargs)
