from doorbeen.core.connections.credentials.factory import DatabaseCredentialsFactory
from doorbeen.core.types.databases import DatabaseTypes
from doorbeen.core.types.ts_model import TSModel


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
