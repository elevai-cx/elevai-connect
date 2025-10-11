# Athena Queries

This directory contains SQL query files for Amazon Athena named queries.

## Structure

- **athena-queries/** - Default queries provided with the system
- **custom/athena-queries/** - Custom queries (optional)

## Adding Queries

### Default Queries
1. Create a new `.txt` file in the `athena-queries/` directory
2. Name the file with the desired query name (e.g., `My Custom Report.txt`)
3. Write your SQL query in the file
4. Use `{database_name}` as a placeholder for the database name

### Custom Queries
1. Create the directory `custom/athena-queries/` if it doesn't exist
2. Add your `.txt` query files following the same naming convention
3. Custom queries with the same name as default queries will override them

## Query File Format

Each query file should:
- Be a plain text file with `.txt` extension
- Contain a single SQL query
- Use `{database_name}` placeholder where the database name is needed
- Be named descriptively (the filename becomes the query name in Athena)

### Example Query File: `Daily Contact Summary.txt`

```sql
SELECT 
    date_parse(partition_0, '%Y-%m-%d') as date,
    channel,
    COUNT(*) as total_contacts,
    AVG(CAST(json_extract_scalar(attributes, '$.Duration') AS INTEGER)) as avg_duration
FROM {database_name}.contact_record_link
WHERE DATE(initiation_timestamp) >= DATE '2025-01-01'
GROUP BY partition_0, channel
ORDER BY date DESC
```

## Query Naming

The filename (without `.txt`) becomes the query name in Athena with "Connect - " prefix:
- `List All Tables.txt` → **Connect - List All Tables**
- `Agent Performance.txt` → **Connect - Agent Performance**

## Notes

- All queries are automatically loaded when the infrastructure is deployed
- Query files must be valid SQL for Amazon Athena
- Custom queries are marked with `[Custom]` prefix in their description
