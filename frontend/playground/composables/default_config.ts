import db_creds from "~/assets/defaults/db_creds.json"

export const getDefaultConfig = (db_type: string) => {
    const sql_dbs = ["mysql", "postgresql", "sqlite", "mssql", "sqlserver",
                             "bigquery", "snowflake", "redshift", "oracle"]
    // variant should be set to "sql" or "nosql" based on whether the db_type belongs to sql_dbs
    const variant = sql_dbs.includes(db_type) ? "sql" : "nosql"
    const variant_creds = db_creds[variant]
    const creds = variant_creds[db_type]
    return creds
}