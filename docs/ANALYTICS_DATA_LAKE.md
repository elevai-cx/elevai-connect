# Analytics Data Lake Guide

## Overview

The Analytics Data Lake provides automated access to your Amazon Connect analytics data through AWS Lake Formation and Amazon Athena. This enables SQL-based analysis of historical contact center data without complex ETL processes or manual configuration.

## What Gets Created Automatically

When you deploy with data lake enabled (default), the infrastructure automatically:

1. **Associates Amazon Connect Analytics Data Lake** - Enables 27 analytics data sets
2. **Accepts RAM Resource Share** - Automatically accepts the shared database from AWS Connect
3. **Discovers Shared Database** - Auto-detects database name and source account from RAM
4. **Creates Lake Formation Database** - Sets up `connect_analytics` (configurable)
5. **Creates 27 Resource Links** - Links to all available Amazon Connect tables
6. **Configures Athena Workgroup** - Pre-configured `connect-analytics` workgroup with query results storage

### Available Data Sets

The following 27 tables are automatically linked and queryable:

**Contact Data:**
- `contact_record` - Complete contact history
- `contact_lens_conversational_analytics` - AI-powered conversation insights
- `contact_statistic_record` - Contact metrics and KPIs
- `contact_evaluation_record` - Quality evaluations
- `contact_flow_events` - Flow execution events

**Agent & Queue Data:**
- `agent_statistic_record` - Agent performance metrics
- `agent_queue_statistic_record` - Agent-queue associations and stats
- `routing_profiles` - Routing configurations
- `users` - Agent and user information
- `agent_hierarchy_groups` - Organizational structure

**Bot & AI Data:**
- `bot_conversations` - Bot interaction history
- `bot_intents` - Intent recognition data
- `bot_slots` - Slot filling information

**Workforce Management:**
- `staff_shifts` - Agent shift schedules
- `shift_activities` - Activity tracking
- `staff_timeoff_intervals` - Time off requests
- `staff_timeoff_balance_changes` - PTO balance changes
- `staffing_group_forecast_groups` - Forecasting groups
- `forecast_groups` - Forecast configurations
- `long_term_forecasts` - Long-term capacity planning
- `short_term_forecasts` - Short-term forecasts
- `staff_shift_activities` - Detailed shift activities
- `shift_profiles` - Shift profile definitions
- `staffing_group_supervisors` - Supervisor assignments
- `staffing_groups` - Workforce groups
- `staff_timeoffs` - Time off records
- `staff_scheduling_profile` - Scheduling preferences

## Configuration

### Minimal Configuration (Uses Defaults)

```yaml
# No configuration needed! 
# Data lake is enabled by default with smart defaults
```

### Custom Configuration

```yaml
s3:connectAthenaQueries.archiveDays: "0"
s3:connectAthenaQueries.deletionDays: "90"
athena:bytesScannedCutoff: "5368709120"  # Custom query size limit. 5GB
```

## Querying Your Data

### Access Athena

1. Open **AWS Console** → **Amazon Athena**
2. Select workgroup: **`connect-analytics`**
3. Database: **`connect_analytics`**

### Example Queries

#### 1. Today's Contact Volume

```sql
SELECT 
    COUNT(*) as total_contacts,
    SUM(CASE WHEN channel = 'VOICE' THEN 1 ELSE 0 END) as voice_calls,
    SUM(CASE WHEN channel = 'CHAT' THEN 1 ELSE 0 END) as chats,
    SUM(CASE WHEN channel = 'TASK' THEN 1 ELSE 0 END) as tasks
FROM contact_record_link
WHERE DATE(initiation_timestamp) = CURRENT_DATE;
```

#### 2. Agent Performance (Last 7 Days)

```sql
SELECT 
    agent_username,
    COUNT(*) as contacts_handled,
    AVG(agent_interaction_duration) as avg_handle_time,
    AVG(after_contact_work_duration) as avg_acw_time
FROM contact_record_link
WHERE initiation_timestamp >= CURRENT_DATE - INTERVAL '7' DAY
    AND agent_username IS NOT NULL
GROUP BY agent_username
ORDER BY contacts_handled DESC;
```

#### 3. Queue Performance

```sql
SELECT 
    queue_name,
    COUNT(*) as total_contacts,
    AVG(queue_duration) as avg_queue_time,
    AVG(agent_interaction_duration) as avg_handle_time,
    SUM(CASE WHEN disconnection_reason = 'CUSTOMER_DISCONNECT' 
        THEN 1 ELSE 0 END) as customer_abandons
FROM contact_record_link
WHERE DATE(initiation_timestamp) = CURRENT_DATE
GROUP BY queue_name
ORDER BY total_contacts DESC;
```

#### 4. Contact Lens Sentiment Analysis

```sql
SELECT 
    contact_id,
    overall_customer_sentiment_score,
    overall_agent_sentiment_score,
    conversation_characteristics
FROM contact_lens_conversational_analytics_link
WHERE DATE(contact_start_time) = CURRENT_DATE
    AND overall_customer_sentiment_score < 0
ORDER BY overall_customer_sentiment_score ASC
LIMIT 10;
```

#### 5. Bot Performance

```sql
SELECT 
    bot_name,
    COUNT(DISTINCT conversation_id) as total_conversations,
    AVG(conversation_duration_seconds) as avg_duration,
    SUM(CASE WHEN successful_completion = true THEN 1 ELSE 0 END) as successful_completions
FROM bot_conversations_link
WHERE DATE(conversation_start_time) = CURRENT_DATE
GROUP BY bot_name;
```

#### 6. Missed Calls by Queue

```sql
SELECT 
    queue_name,
    COUNT(*) as missed_calls,
    ROUND(AVG(queue_duration), 2) as avg_wait_time_before_abandon
FROM contact_record_link
WHERE DATE(initiation_timestamp) = CURRENT_DATE
    AND disconnection_reason IN ('CONTACT_FLOW_DISCONNECT', 'CUSTOMER_DISCONNECT')
    AND queue_duration > 0
    AND agent_connection_attempts = 0
GROUP BY queue_name
ORDER BY missed_calls DESC;
```

## Verification

Check that everything was set up correctly:

```bash
# View deployment outputs
pulumi stack output

# Check resource link creation
pulumi stack output resource_links_result
# Expected: {"created":27,"skipped":0,"total":27}

# View discovered database info
pulumi stack output --show-secrets shared_database_info
# Expected: {"database_name":"connect_datalake","account_id":"123456789012"}
```

## Troubleshooting

### Resource Links Not Created

**Symptom:** No tables visible in Athena

**Check:**
```bash
pulumi stack output resource_links_result
```

**Solution:** Ensure data is flowing to Connect (make test calls first)

### Query Returns No Data

**Cause:** Amazon Connect needs time to populate the data lake

**Timeline:**
- Contact records: Available within 15 minutes
- Agent statistics: Updated every 15 minutes
- Workforce data: Daily updates

**Verify:**
```sql
SELECT MAX(initiation_timestamp) as latest_contact
FROM contact_record_link;
```

### Permission Denied

**Cause:** IAM permissions for Lake Formation

**Solution:** Ensure your IAM user/role has:
- `lakeformation:GetDataAccess`
- `glue:GetTable`
- `glue:GetDatabase`
- `s3:GetObject` on the Connect data bucket

### "Table Not Found" Error

**Check database name:**
```bash
pulumi stack output lake_formation_database
```

**Verify resource links exist:**
```sql
SHOW TABLES IN connect_analytics;
```

Should list all 27 tables with `_link` suffix.

## Data Retention

Amazon Connect retains analytics data for **2 years** by default. After 2 years, data is automatically purged from the data lake tables.


## Best Practices

### Query Performance

1. **Always filter by date** - Use partition columns for better performance:
   ```sql
   WHERE DATE(initiation_timestamp) >= DATE '2025-01-01'
   ```

2. **Limit result sets** - Use `LIMIT` for exploratory queries:
   ```sql
   SELECT * FROM contact_record_link LIMIT 100;
   ```

3. **Use columnar formats** - When exporting, use PARQUET for better compression:
   ```sql
   CREATE TABLE exports.contacts_summary
   WITH (format = 'PARQUET')
   AS SELECT ...
   ```

### Cost Optimization

- **Athena charges per TB scanned** - Always use date filters
- **Query results are stored in S3** - Set lifecycle policies on query results bucket
- **Use saved queries** - Avoid re-running expensive queries

### Security

- **Grant least-privilege access** - Use Lake Formation to control table/column access
- **Audit query logs** - Enable CloudTrail for Athena queries
- **Encrypt query results** - S3 encryption is enabled by default

## Integration with BI Tools

### Amazon QuickSight

1. Create new data set → Athena
2. Select workgroup: `connect-analytics`
3. Select database: `connect_analytics`
4. Choose tables and create visualizations

### Tableau / Power BI

Use Athena JDBC/ODBC drivers:
- **Endpoint:** `https://athena.{region}.amazonaws.com`
- **Workgroup:** `connect-analytics`
- **Database:** `connect_analytics`

### Python / Jupyter Notebooks

```python
import boto3
import pandas as pd

athena = boto3.client('athena', region_name='us-east-1')

query = """
SELECT * FROM connect_analytics.contact_record_link 
WHERE DATE(initiation_timestamp) = CURRENT_DATE
"""

response = athena.start_query_execution(
    QueryString=query,
    WorkGroup='connect-analytics'
)

# Poll for results and load into pandas DataFrame
```

## Architecture

```
┌─────────────────────┐
│  Amazon Connect     │
│  (Producer)         │
│  - Generates data   │
└──────────┬──────────┘
           │
           │ AWS RAM Share
           ▼
┌─────────────────────┐
│  AWS RAM            │
│  (Shared Database)  │
│  connect_datalake   │
└──────────┬──────────┘
           │
           │ Auto-discovered
           ▼
┌─────────────────────┐
│  Lake Formation     │
│  (Consumer)         │
│  connect_analytics  │
│  - 27 Resource Links│
└──────────┬──────────┘
           │
           │ Query via
           ▼
┌─────────────────────┐
│  Amazon Athena      │
│  connect-analytics  │
│  workgroup          │
└─────────────────────┘
```

## Additional Resources

- [Amazon Connect Analytics Data Lake](https://docs.aws.amazon.com/connect/latest/adminguide/analytics-datalake.html)
- [AWS Lake Formation](https://docs.aws.amazon.com/lake-formation/)
- [Amazon Athena SQL Reference](https://docs.aws.amazon.com/athena/latest/ug/ddl-sql-reference.html)
- [Contact Record Data Model](https://docs.aws.amazon.com/connect/latest/adminguide/contact-record-data-model.html)

## Support

For issues or questions:
- **GitHub Issues:** [Report a bug](https://github.com/bloy.me.uk/elevai-connect/issues)
- **Discussions:** [Ask a question](https://github.com/bloy.me.uk/elevai-connect/discussions)

---

**Next Steps:**
- [Query historical contact data](#example-queries)
- [Connect to QuickSight](#integration-with-bi-tools)
- [Export data for compliance](#data-retention)
