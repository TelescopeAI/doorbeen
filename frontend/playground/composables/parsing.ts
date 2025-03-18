export const parseDBConfig = (connection: Object) =>{
    let dialect = ""
    const db_type = connection.db_type
    const parsedConnection: any= {db_type: db_type}
    const parsedCredentials: any = {}
    const commonsql_dbs = ["mysql", "postgresql", "sqlite", "mssql", "oracle"]
    // Check if the dialect belongs to commonsql_dbs
    const is_commonsql_db = commonsql_dbs.includes(connection.db_type)
    if(is_commonsql_db){
        if(db_type === "mysql"){
            dialect = "mysql"
        } else if(db_type === "postgresql"){
            dialect = "postgres"
        } else if(db_type === "sqlite"){
            dialect = "sqlite"
        } else if(db_type === "mssql"){
            dialect = "mssql"
        }
        parsedCredentials.host = connection.host
        parsedCredentials["port"] = connection.port
        parsedCredentials["username"] = connection.username
        parsedCredentials["password"] = connection.password
        parsedCredentials["database"] = connection.database
        parsedCredentials["dialect"] = db_type
    }
    parsedConnection["credentials"] = parsedCredentials
    return parsedConnection
}