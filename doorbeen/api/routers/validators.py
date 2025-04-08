from fastapi import APIRouter, Body

from doorbeen.api.schemas.requests.assistants import DBConnectionRequestParams
from doorbeen.api.schemas.response.validators import DBValidationResult
from doorbeen.core.connections.clients.SQL.common import CommonSQLClient
from doorbeen.core.connections.clients.service import DBClientService

ValidationRouter = APIRouter()


@ValidationRouter.post("/validators/db", tags=["Validators"])
async def validate_credentials(details: DBConnectionRequestParams = Body()):
    details = DBConnectionRequestParams(**details.model_dump())
    result = DBValidationResult()
    try:
        client: CommonSQLClient = DBClientService.get_client(details=details.credentials,
                                                             db_type=details.db_type)
        connection = client.connect()
        result.can_connect = True
        tables = client.get_table_names(details.credentials['database'])
        result.non_null_tables = True if len(tables) > 0 else False
    except Exception as e:
        result.error = str(e)
    return result

