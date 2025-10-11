# Custom Athena Queries

Place your custom Athena query files here. Each `.txt` file will be loaded as a named query.

## Example

Create a file named `My Custom Query.txt` with your SQL:

```sql
SELECT 
    contactid,
    channel,
    initiationtimestamp
FROM {database_name}.contact_record_link
WHERE partition_0 = date_format(current_date, '%Y-%m-%d')
LIMIT 50
```

This will create a named query called **"Connect - My Custom Query"** in Athena.

## Notes

- Custom queries with the same name as default queries will override them
- Use `{database_name}` placeholder for the database name
- Query files must have `.txt` extension
