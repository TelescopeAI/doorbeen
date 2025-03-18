from typing import Optional

from langchain_community.llms.ollama import Ollama
from openai import OpenAI

from core.commons.frequency import Frequency
from core.commons.parsers import DateTimeParser
from core.connections.clients.SQL.common import CommonSQLClient
from core.connections.credentials.SQL.common import CommonSQLCredentials
from core.database.database import TSDatabase
from core.entities.entity import Entity
from core.properties.analysis.aggregates import TimePeriodAggregator
from core.properties.history import PropertyHistory
from core.properties.property import Property, PropertySQL, ColumnMap
from core.properties.values import PropertyValue
from core.types.databases import DatabaseTypes

multi_value_sql_text = f"""
        select 
    	to_char(date_trunc('month', event.occurred_at), 'MM/YYYY') as month,
    	count(*) as monthly_account_updated_count,
    	event.customer_id,
    	cust.name
    from 
    	public.events as event
    join
    	customers cust on cust.id = event.customer_id
    where
    	event.name = 'ACCOUNT_UPDATED'
    group by
    	to_char(date_trunc('month', event.occurred_at), 'MM/YYYY'), event.customer_id, cust.name
    order by 
    	month, event.customer_id
        """
single_value_sql_text = f"""
    select 
    	count(*) as account_updated_count,
    	event.customer_id,
    	cust.name
    from 
    	public.events as event
    join
    	customers cust on cust.id = event.customer_id
    where
    	event.name = 'ACCOUNT_UPDATED'
    group by
    	 event.customer_id, cust.name
    order by 
    	event.customer_id"""


def analyse_stats(trait: Property):
    assert trait.history is not None, "Cannot analyse stats for a property without any history"
    aggregates = TimePeriodAggregator.calculate(trait.history)
    trait.aggregates = aggregates
    return trait


def get_property_for_entity(query_result, entity: Entity):
    column_map = ColumnMap(key_column="name", value_column="monthly_account_updated_count", timestamp_column="month")
    property_1 = Property(name="Total Account Updated Events", entity_label=entity.name, column_map=column_map,
                          sql=PropertySQL(statement=single_value_sql_text))
    # sql_connection = SQLConnection(host="localhost", port=5432, username="root", password="password",
    #                                database="core",
    #                                db_type="postgresql").get_connection()
    # result = sql_connection.execute_fetch_sql(property_1.sql.statement)
    result = query_result
    # Convert SQL result into JSON
    result_json = [dict(row._mapping) for row in result]
    property_values = []
    for each in result_json:
        property_value: Optional[PropertyValue] = None
        entity_matched = property_1.entity_label == each[column_map.key_column]
        if each[column_map.key_column] is not None and entity_matched:
            property_value = PropertyValue(value=each[column_map.value_column])
            property_values.append(property_value)
        else:
            assert "This column key does not exist"
        try:
            if each[column_map.timestamp_column] is not None and entity_matched:
                property_value.timestamp = DateTimeParser.parse_str(each[column_map.timestamp_column])
            else:
                assert "Not a Multi Property so timestamp_column isn't required"
        except KeyError as ke:
            pass
        print(each)
    if len(property_values) == 1:
        property_1.value = each[column_map.value_column]
    else:
        assert column_map.timestamp_column is not None, "Cannot have historical values without a timestamp column"
        property_history = PropertyHistory(frequency=Frequency.MONTHLY, values=property_values)
        property_1.history = property_history
        property_1 = analyse_stats(property_1)
        property_1.value = property_1.aggregates.summary.sum
    return property_1


def connect_to_llm(text: str):
    llm = Ollama(model="llama3", temperature=0)
    output = llm.invoke(text)
    print(f"Llama3 Output: \n{output}")


if __name__ == "__main__":
    entity1 = Entity(name="Telescope", type="Accounts")
    entity2 = Entity(name="Thrombox", type="Accounts")
    entities = [entity1, entity2]

    sql_creds = CommonSQLCredentials(host="localhost", port=5432, username="root", password="password",
                                     database="core", dialect=DatabaseTypes.POSTGRESQL)
    sql_client = CommonSQLClient(credentials=sql_creds)
    print("SQL Schema: ", sql_client.get_schema().json())
    sql_result = sql_client.query(multi_value_sql_text)
    for entity in entities:
        db_client = TSDatabase().new_client()
        db = db_client.get_database("core")
        # print("DB Information: ", db)
        collection = db.get_collection("entities")
        # print("Collection Information: ", collection)

        entity_property = get_property_for_entity(sql_result, entity=entity)
        entity.properties = [entity_property]
        # collection.insert_one(entity.dict())
        # print("Collection Post Insert: ", collection.find_one())
        print(entity.json())

    messages = [
        {"role": "system", "content": "You are a helpful assistant who is also a data analyst." +
                                      "Your goal is to help the user understand their data and make better decisions." +
                                      "Here are the details about the important things that are being tracked." +
                                      f"\n {entities}"},
        {"role": "user", "content": "Describe the activity patterns within my data? Which one is growing and which "
                                    "one is likely to churn?"}, ]
    client = OpenAI()
    completion = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)

    print(f"OpenAI GPT4 Response: \n {completion.choices[0].message.content}")
    connect_to_llm(messages)

# Step 1: Create a property/trait
# Step 2: Find the Sum, Avg, Min, Max, and Count of the property.
# Step 3: Create JSON for that metric
# Step 4: Reduce the dimensionality using PCA and generate the vectors
# Step 5: Create a collection in a Vector DB such as ChromaDB or Milvus
# Step 6: Insert the vectors into the collections
