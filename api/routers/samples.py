import json
import os

from fastapi import APIRouter
from fastapi_cache.decorator import cache

from api.schemas.requests.assistants import DBConnectionRequestParams
from core.config.execution_env import ExecutionEnv
from core.connections.clients.SQL.bigquery import BigQueryClient
from core.connections.clients.service import DBClientService
from core.types.databases import DatabaseTypes

SamplesRouter = APIRouter()
cache_expiry = 6000 if ExecutionEnv.is_local() else 3600


@SamplesRouter.get("/sandbox/databases", tags=["Samples"])
@cache(namespace="sample_db", expire=cache_expiry)
async def get_sample_data(db_type: DatabaseTypes = DatabaseTypes.BIGQUERY):
    if db_type == DatabaseTypes.BIGQUERY:
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        credentials_file = open(credentials_path, 'r')
        credentials_content = credentials_file.read()
        credentials = json.loads(credentials_content)
        dataset_name = "smol_sandbox"
        conn_params = {
            'db_type': "bigquery",
            'credentials': {
                'project_id': 'prod-datastore-424523',
                'dataset_id': dataset_name,
                'service_account_details': credentials
            }
        }
        credentials_file.close()
        connection = DBConnectionRequestParams(**conn_params)
        client = None
        db_type = DatabaseTypes.BIGQUERY
        client: BigQueryClient = DBClientService.get_client(details=connection.credentials,
                                                            db_type=connection.db_type)
        engine = client.get_engine()
        connection = client.connect()
        table_names = client.get_table_names(dataset_name=dataset_name)
        table_response = {"tables": table_names}
        table_data = []
        row_limit = 5000
        for table_name in table_names:
            print("Table Name: ", table_name)
            sql_query = f"SELECT * FROM `{dataset_name}.{table_name}` LIMIT {row_limit}"
            print("SQL Query: ", sql_query)
            query_result = client.query(sql_query)

            # Assuming query_result is a list of tuples
            if query_result:
                # Extract column names if available
                columns = [column for column in query_result[0]._fields] if query_result and hasattr(query_result[0],
                                                                                                     '_fields') else []

                # Convert rows to a list of dictionaries
                table_rows = [dict(zip(columns, row)) for row in query_result]
                data_table = {table_name: {"columns": columns, "rows": table_rows}}
            else:
                data_table = {table_name: {"columns": [], "rows": []}}
            table_data.append(data_table)
        table_response["data"] = table_data
        return table_response
