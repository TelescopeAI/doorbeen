def get_database_specific_instructions(dialect: str) -> str:
    """Get comprehensive database-specific SQL instructions for generating syntactically correct SELECT queries."""

    if dialect.lower() == "postgresql":
        return """
PostgreSQL-Specific Instructions for SELECT Queries:

DATE/TIME OPERATIONS IN WHERE/SELECT:
- Cast to timestamp: column_name::timestamp or CAST(column_name AS timestamp)
- Extract parts: EXTRACT(HOUR FROM timestamp_column), EXTRACT(EPOCH FROM timestamp_column)
- Time formatting in SELECT: TO_CHAR(timestamp_column, 'YYYY-MM-DD HH24:MI:SS')
- Common formats: 'HH24:MI:SS' (24-hour), 'HH12:MI:SS AM' (12-hour), 'Day, DD Mon YYYY'
- Current time comparisons: WHERE timestamp_column > CURRENT_TIMESTAMP - INTERVAL '1 hour'
- Time arithmetic: WHERE timestamp_column BETWEEN NOW() - INTERVAL '7 days' AND NOW()
- Age calculation: SELECT AGE(timestamp1, timestamp2) returns interval
- Truncate for grouping: GROUP BY DATE_TRUNC('hour', timestamp_column)
- Timezone conversion: SELECT timestamp_column AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York'

STRING OPERATIONS FOR FILTERING/DISPLAY:
- Concatenation in SELECT: first_name || ' ' || last_name AS full_name
- Pattern matching in WHERE: column LIKE '%pattern%', column ILIKE '%pattern%' (case-insensitive)
- Regular expressions: WHERE column ~ '^[A-Z].*' (starts with uppercase)
- String functions: SELECT LOWER(column), UPPER(column), LENGTH(column), TRIM(column)
- Substring: SELECT SUBSTRING(column FROM 1 FOR 10), LEFT(column, 5)
- Position: WHERE POSITION('substring' IN column) > 0

DATA TYPE HANDLING IN QUERIES:
- Boolean in WHERE: WHERE is_active = TRUE (not 'true' or 1)
- Array operations: WHERE tag = ANY(tags_array), WHERE tags_array @> ARRAY['tag1','tag2']
- JSON queries: WHERE data->>'status' = 'active', SELECT data->'user'->>'name'
- JSON path: WHERE data #>> '{address,city}' = 'New York'
- Type casting in WHERE: WHERE column_name::integer > 100
- UUID queries: WHERE id::text LIKE '123e4567%'

NULL HANDLING IN QUERIES:
- WHERE column IS NULL, WHERE column IS NOT NULL (never use = NULL)
- COALESCE in SELECT: SELECT COALESCE(middle_name, '') AS middle_name
- NULL-safe comparison: WHERE column IS DISTINCT FROM 'value'
- NULLIF: SELECT NULLIF(column, '') AS cleaned_column

AGGREGATION AND WINDOW FUNCTIONS:
- Window functions: SELECT ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC)
- Running totals: SELECT SUM(amount) OVER (ORDER BY date ROWS UNBOUNDED PRECEDING)
- Ranking: RANK() OVER (ORDER BY score DESC), DENSE_RANK(), PERCENT_RANK()
- Moving averages: AVG(value) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
- FILTER clause: COUNT(*) FILTER (WHERE status = 'active') AS active_count
- GROUPING SETS: GROUP BY GROUPING SETS ((category), (category, subcategory), ())

JOINS AND SUBQUERIES:
- LATERAL joins: LEFT JOIN LATERAL (SELECT * FROM orders WHERE customer_id = c.id LIMIT 5) o ON true
- CTEs: WITH ranked_sales AS (SELECT *, ROW_NUMBER() OVER (ORDER BY amount DESC) AS rn FROM sales)
- Multiple CTEs: WITH cte1 AS (...), cte2 AS (...) SELECT * FROM cte1 JOIN cte2
- EXISTS for efficiency: WHERE EXISTS (SELECT 1 FROM orders WHERE customer_id = c.id)
- DISTINCT ON: SELECT DISTINCT ON (customer_id) * FROM orders ORDER BY customer_id, order_date DESC

QUERY SYNTAX AND BEST PRACTICES:
- Use single quotes for strings: WHERE name = 'John' (not "John")
- Double quotes for identifiers: SELECT "first-name", "order" FROM "user-table"
- Cast for comparisons: WHERE created_at::date = '2024-01-01'
- Use explicit column names instead of SELECT *
- Table aliases: FROM customers c JOIN orders o ON c.id = o.customer_id
- LIMIT with ORDER BY: ORDER BY created_at DESC LIMIT 10

PERFORMANCE CONSIDERATIONS:
- Use indexes: WHERE indexed_column = value (check with EXPLAIN)
- Avoid functions on indexed columns: Use WHERE date >= '2024-01-01' not WHERE DATE(timestamp) = '2024-01-01'
- Use EXISTS instead of IN for large subqueries
- Consider partial indexes: WHERE status = 'active' if there's a partial index

SPECIAL POSTGRESQL FEATURES:
- Case-insensitive search: WHERE column ILIKE '%search%' or using citext type
- Full-text search: WHERE to_tsvector('english', content) @@ to_tsquery('search & terms')
- Range queries: WHERE daterange(start_date, end_date) && daterange('2024-01-01', '2024-12-31')
- RETURNING in CTEs: WITH deleted AS (DELETE FROM table WHERE condition RETURNING *) SELECT * FROM deleted
"""

    elif dialect.lower() == "mysql":
        return """
MySQL-Specific Instructions for SELECT Queries:

DATE/TIME OPERATIONS IN WHERE/SELECT:
- Extract parts: SELECT HOUR(datetime_column), WHERE MINUTE(datetime_column) = 30
- Time formatting: SELECT DATE_FORMAT(datetime_column, '%Y-%m-%d %H:%i:%s') AS formatted_date
- Format patterns: '%H:%i:%s' (24-hour time), '%h:%i:%s %p' (12-hour), '%W, %d %M %Y'
- String to date in WHERE: WHERE date_column = STR_TO_DATE('2024-01-01', '%Y-%m-%d')
- Current time comparisons: WHERE created_at > NOW() - INTERVAL 1 HOUR
- Date arithmetic: WHERE order_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 7 DAY) AND CURDATE()
- Time differences: SELECT TIMESTAMPDIFF(HOUR, start_time, end_time) AS hours_diff
- Day operations: WHERE DAYOFWEEK(date_column) = 2 (Monday), DAYNAME(date_column)
- Unix timestamps: WHERE UNIX_TIMESTAMP(datetime_column) > 1640995200

STRING OPERATIONS FOR FILTERING/DISPLAY:
- Concatenation: SELECT CONCAT(first_name, ' ', last_name) AS full_name
- With separator: SELECT CONCAT_WS(', ', city, state, country) AS location
- Pattern matching: WHERE column LIKE '%pattern%', WHERE column REGEXP '^[A-Z].*'
- Case conversion: SELECT LOWER(column), UPPER(column), WHERE LOWER(email) = 'user@example.com'
- Substring: SELECT SUBSTRING(column, 1, 10), LEFT(column, 5), RIGHT(column, 3)
- String position: WHERE LOCATE('substring', column) > 0
- Replace in SELECT: SELECT REPLACE(phone, '-', '') AS phone_digits
- Trim: SELECT TRIM(BOTH ' ' FROM column), LTRIM(column), RTRIM(column)

DATA TYPE HANDLING IN QUERIES:
- Boolean (TINYINT): WHERE is_active = 1 (MySQL < 8.0 uses 0/1)
- Type casting: WHERE CAST(column AS SIGNED) > 100, CAST(column AS DECIMAL(10,2))
- CONVERT: SELECT CONVERT(column, UNSIGNED), CONVERT(column USING utf8mb4)
- JSON operations (5.7+): WHERE JSON_EXTRACT(data, '$.status') = 'active'
- JSON shorthand: WHERE data->>'$.user.name' = 'John', data->'$.items[0]'
- JSON contains: WHERE JSON_CONTAINS(tags, '"mysql"', '$')
- Binary comparisons: WHERE BINARY column = 'CaseSensitive'

NULL HANDLING IN QUERIES:
- WHERE column IS NULL, WHERE column IS NOT NULL
- COALESCE: SELECT COALESCE(middle_name, '') AS middle_name
- IFNULL (MySQL specific): SELECT IFNULL(price, 0) AS price
- NULL-safe equality: WHERE column <=> NULL (returns TRUE if both are NULL)
- IF function: SELECT IF(status IS NULL, 'Unknown', status) AS status_display

AGGREGATION AND WINDOW FUNCTIONS:
- GROUP_CONCAT: SELECT GROUP_CONCAT(name ORDER BY name SEPARATOR ', ') AS names_list
- With DISTINCT: GROUP_CONCAT(DISTINCT category ORDER BY category)
- Window functions (8.0+): SELECT ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC)
- Running totals (8.0+): SUM(amount) OVER (ORDER BY date ROWS UNBOUNDED PRECEDING)
- WITH ROLLUP: GROUP BY category, subcategory WITH ROLLUP
- Custom aggregates: SELECT BIT_OR(flags), BIT_AND(permissions)

JOINS AND SUBQUERIES:
- STRAIGHT_JOIN to force join order: SELECT STRAIGHT_JOIN * FROM large_table JOIN small_table
- CTEs (8.0+): WITH ranked AS (SELECT *, ROW_NUMBER() OVER (ORDER BY score) AS rank FROM scores)
- Derived tables: SELECT * FROM (SELECT * FROM orders WHERE status = 'active') AS active_orders
- Correlated subqueries: WHERE price > (SELECT AVG(price) FROM products p2 WHERE p2.category = p1.category)
- EXISTS optimization: WHERE EXISTS (SELECT 1 FROM orders WHERE customer_id = c.id LIMIT 1)

QUERY SYNTAX AND BEST PRACTICES:
- Use backticks for identifiers: SELECT `order`, `group` FROM `user-table`
- Single quotes for strings: WHERE name = 'John'
- Force index hint: FROM orders FORCE INDEX (idx_date) WHERE order_date > '2024-01-01'
- Use index hint: FROM orders USE INDEX (idx_customer, idx_date)
- STRAIGHT_JOIN for join order: SELECT STRAIGHT_JOIN * FROM small_table JOIN large_table
- SQL_CALC_FOUND_ROWS: SELECT SQL_CALC_FOUND_ROWS * FROM table LIMIT 10; SELECT FOUND_ROWS();

PERFORMANCE CONSIDERATIONS:
- Avoid functions on indexed columns: Use WHERE date >= '2024-01-01' not WHERE DATE(datetime) = '2024-01-01'
- Use covering indexes: SELECT indexed_col1, indexed_col2 (if composite index exists)
- LIMIT optimization: Use WHERE id > last_seen_id ORDER BY id LIMIT 100 for pagination
- Avoid SELECT * especially with TEXT/BLOB columns

SPECIAL MYSQL FEATURES:
- Variables in queries: SELECT @row_num := @row_num + 1 AS row_number, name FROM users, (SELECT @row_num := 0) r
- LIMIT with OFFSET: SELECT * FROM table LIMIT 10 OFFSET 20 or LIMIT 20, 10
- Full-text search: WHERE MATCH(title, content) AGAINST('search terms' IN NATURAL LANGUAGE MODE)
- Boolean mode FTS: WHERE MATCH(column) AGAINST('+required -excluded' IN BOOLEAN MODE)
- Group by optimization: SELECT name, ANY_VALUE(address) FROM users GROUP BY name
"""

    elif dialect.lower() == "sqlite":
        return """
SQLite-Specific Instructions for SELECT Queries:

DATE/TIME OPERATIONS IN WHERE/SELECT:
- SQLite stores dates as TEXT ('YYYY-MM-DD HH:MM:SS'), INTEGER (Unix timestamp), or REAL (Julian days)
- Extract parts: SELECT strftime('%H', datetime_column), WHERE strftime('%M', datetime_column) = '30'
- Time formatting: SELECT strftime('%Y-%m-%d %H:%M:%S', datetime_column) AS formatted_date
- Format patterns: '%H:%M:%S' (time), '%Y-%m-%d' (date), '%s' (unix timestamp), '%w' (weekday 0-6)
- Current time: WHERE datetime_column > datetime('now', '-1 hour')
- Date arithmetic: WHERE date_column BETWEEN date('now', '-7 days') AND date('now')
- Time modifiers: datetime('now', 'start of month', '+1 month', '-1 day') for last day of month
- Julian days diff: SELECT julianday('now') - julianday(date_column) AS days_ago
- Weekday: WHERE strftime('%w', date_column) = '1' (Monday)

STRING OPERATIONS FOR FILTERING/DISPLAY:
- Concatenation: SELECT first_name || ' ' || last_name AS full_name
- Pattern matching: WHERE column LIKE '%pattern%' (% and _ wildcards)
- GLOB pattern: WHERE column GLOB '*[0-9]*' (contains digit), GLOB '?ello' (single char wildcard)
- Case operations: SELECT LOWER(column), UPPER(column), WHERE LOWER(email) = 'user@example.com'
- Substring: SELECT SUBSTR(column, 1, 10), SUBSTR(column, -5) for last 5 chars
- String length: WHERE LENGTH(column) > 10
- Replace: SELECT REPLACE(phone, '-', '') AS phone_digits
- Trim: SELECT TRIM(column), LTRIM(column), RTRIM(column), TRIM(column, ',')
- Printf formatting: SELECT PRINTF('%04d', number) AS padded_number

DATA TYPE HANDLING IN QUERIES:
- Type affinity: SQLite uses dynamic typing - columns have affinity, not strict types
- Type checking: WHERE typeof(column) = 'text', typeof(column) IN ('integer', 'real')
- Casting: WHERE CAST(column AS INTEGER) > 100, CAST(price AS REAL)
- Boolean values: WHERE is_active = 1 (use 0 and 1)
- BLOB literals: WHERE data = X'48656C6C6F' (hex string)
- Numeric comparisons work on text if content is numeric

NULL HANDLING IN QUERIES:
- WHERE column IS NULL, WHERE column IS NOT NULL
- COALESCE: SELECT COALESCE(middle_name, '') AS middle_name
- IFNULL: SELECT IFNULL(price, 0) AS price
- NULLIF: SELECT NULLIF(column, '') AS cleaned_value

AGGREGATION AND WINDOW FUNCTIONS:
- Basic aggregates: COUNT(*), SUM(column), AVG(column), MIN(column), MAX(column)
- GROUP_CONCAT: SELECT GROUP_CONCAT(name, ', ') AS names_list
- GROUP_CONCAT with order: GROUP_CONCAT(name, '|') to use custom separator
- Window functions (3.25.0+): SELECT ROW_NUMBER() OVER (ORDER BY score DESC) AS rank
- Window frames (3.25.0+): SUM(amount) OVER (ORDER BY date ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)
- DISTINCT in aggregates: COUNT(DISTINCT category)

JOINS AND SUBQUERIES:
- CTEs: WITH ranked AS (SELECT *, ROW_NUMBER() OVER (ORDER BY score) AS rn FROM scores WHERE rn <= 10)
- Recursive CTEs: WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt WHERE x<10)
- Join types: CROSS JOIN, INNER JOIN, LEFT JOIN (no RIGHT JOIN - rewrite using LEFT)
- Natural join: SELECT * FROM table1 NATURAL JOIN table2
- Compound queries: SELECT * FROM table1 UNION SELECT * FROM table2

QUERY SYNTAX AND BEST PRACTICES:
- Identifiers: Use double quotes "column name" or backticks `column name` or [column name]
- String literals: Always use single quotes 'value'
- Case sensitivity: LIKE is case-insensitive, GLOB is case-sensitive
- Row value comparisons: WHERE (col1, col2) > (val1, val2)
- LIMIT with OFFSET: SELECT * FROM table LIMIT 10 OFFSET 20

PERFORMANCE CONSIDERATIONS:
- Use indexed columns in WHERE when possible
- EXPLAIN QUERY PLAN to analyze query execution
- Avoid functions on indexed columns: Use WHERE date >= '2024-01-01' not WHERE strftime('%Y', date) = '2024'
- CREATE INDEX for frequently queried columns (though this is DDL)
- Use ANALYZE to update internal statistics

SPECIAL SQLITE FEATURES:
- RANDOM(): SELECT * FROM table ORDER BY RANDOM() LIMIT 1
- Multiple databases: SELECT * FROM main.table JOIN attached_db.other_table
- FTS (Full-Text Search): WHERE table MATCH 'search terms' (requires FTS table)
- JSON functions (3.38.0+): SELECT json_extract(data, '$.name'), WHERE json_extract(data, '$.age') > 25
- Table-valued functions: SELECT * FROM json_each(json_column)
- Common Table Expressions are optimization barriers (materialized, not inlined)

LIMITATIONS FOR SELECT QUERIES:
- No native FULL OUTER JOIN (use UNION of LEFT and RIGHT-excluded)
- Window functions require SQLite 3.25.0+
- JSON functions require SQLite 3.38.0+
- Limited date functions compared to other databases
- No stored procedures or user-defined functions
"""

    else:
        return """
Standard SQL Instructions for SELECT Queries:

BASIC SELECT SYNTAX:
- Column selection: SELECT column1, column2 FROM table
- All columns: SELECT * FROM table (avoid in production)
- Aliases: SELECT column AS alias_name, table AS t
- DISTINCT: SELECT DISTINCT column FROM table
- Comments: -- single line comment or /* multi-line comment */

WHERE CLAUSE:
- Comparison: WHERE column = value, column > value, column BETWEEN value1 AND value2
- Pattern matching: WHERE column LIKE '%pattern%' (% = any chars, _ = single char)
- IN operator: WHERE column IN ('value1', 'value2', 'value3')
- NULL checks: WHERE column IS NULL, column IS NOT NULL (never use = NULL)
- Logical operators: AND, OR, NOT
- Parentheses for precedence: WHERE (col1 = val1 OR col1 = val2) AND col2 > val3

STRING OPERATIONS:
- Concatenation: Varies by database (||, +, CONCAT function)
- Case conversion: UPPER(column), LOWER(column)
- Trimming: TRIM(column), LTRIM(column), RTRIM(column)
- Substring: SUBSTRING(column FROM start FOR length)
- Length: CHARACTER_LENGTH(column) or CHAR_LENGTH(column)

DATE/TIME OPERATIONS:
- Extract: EXTRACT(YEAR FROM date_column), EXTRACT(HOUR FROM timestamp_column)
- Current date/time: CURRENT_DATE, CURRENT_TIME, CURRENT_TIMESTAMP
- Date arithmetic: Varies significantly by database
- Casting: CAST(column AS DATE), CAST(column AS TIMESTAMP)

AGGREGATION:
- Functions: COUNT(*), COUNT(column), COUNT(DISTINCT column)
- Numeric: SUM(column), AVG(column), MIN(column), MAX(column)
- GROUP BY: Required for non-aggregated columns when using aggregate functions
- HAVING: Filter grouped results - WHERE filters rows, HAVING filters groups
- Multiple grouping: GROUP BY column1, column2

JOINS:
- INNER JOIN: SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.t1_id
- LEFT JOIN: Returns all from left table, matched from right
- RIGHT JOIN: Returns all from right table, matched from left
- FULL OUTER JOIN: Returns all from both tables
- CROSS JOIN: Cartesian product (every row combination)
- Self-join: FROM table t1 JOIN table t2 ON t1.parent_id = t2.id

SUBQUERIES:
- In SELECT: SELECT column, (SELECT AVG(price) FROM products) AS avg_price
- In FROM: SELECT * FROM (SELECT * FROM table WHERE condition) AS subquery
- In WHERE: WHERE column > (SELECT AVG(column) FROM table)
- EXISTS: WHERE EXISTS (SELECT 1 FROM table2 WHERE table2.id = table1.id)
- NOT EXISTS: WHERE NOT EXISTS (SELECT 1 FROM orders WHERE customer_id = c.id)

ORDER BY:
- Single column: ORDER BY column ASC (or DESC)
- Multiple columns: ORDER BY column1 DESC, column2 ASC
- By position: ORDER BY 1, 2 (not recommended)
- By alias: ORDER BY alias_name
- NULL handling: Varies by database (NULLS FIRST/NULLS LAST)

LIMIT/OFFSET:
- Limit rows: LIMIT 10 (syntax varies: TOP, FETCH FIRST)
- With offset: LIMIT 10 OFFSET 20 (skip first 20)
- Alternative syntax: FETCH FIRST 10 ROWS ONLY

SET OPERATIONS:
- UNION: Combines and removes duplicates
- UNION ALL: Combines keeping duplicates
- INTERSECT: Returns common rows
- EXCEPT/MINUS: Returns rows in first but not second

CASE EXPRESSIONS:
- Simple: CASE column WHEN value1 THEN result1 WHEN value2 THEN result2 ELSE default END
- Searched: CASE WHEN condition1 THEN result1 WHEN condition2 THEN result2 ELSE default END
- In ORDER BY: ORDER BY CASE WHEN condition THEN 1 ELSE 2 END

COMMON TABLE EXPRESSIONS (CTEs):
- Basic: WITH cte_name AS (SELECT ...) SELECT * FROM cte_name
- Multiple: WITH cte1 AS (...), cte2 AS (...) SELECT * FROM cte1 JOIN cte2
- Recursive: WITH RECURSIVE cte AS (initial_query UNION ALL recursive_query)

DATA TYPE CONSIDERATIONS:
- Implicit conversion: Be aware of automatic type conversions
- Explicit casting: CAST(column AS datatype)
- String to number: May work implicitly but better to cast
- Date formats: Vary significantly between databases

BEST PRACTICES:
- Use meaningful aliases for readability
- Qualify columns with table names/aliases in joins
- Use parentheses to make complex logic clear
- Avoid SELECT * except for exploration
- Consider performance impact of functions in WHERE
- Use appropriate data types in comparisons
"""