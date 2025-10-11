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

Provided in the Athena UI from [here](../core//connect//athena-queries/). Add your custom queries to [custom/athena-queries/](../custom//athena-queries/)

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

### Cost Optimization

- **Athena charges per TB scanned** - Always use date filters
- **Query results are stored in S3** - Set lifecycle policies on query results bucket
- **Use saved queries** - Avoid re-running expensive queries

### Security

- **Grant least-privilege access** - Use Lake Formation to control table/column access
- **Audit query logs** - Enable CloudTrail for Athena queries
- **Encrypt query results** - S3 encryption is enabled by default

## Integration with BI Tools

TODO

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

- [Amazon Connect Analytics Data Lake](https://docs.aws.amazon.com/connect/latest/adminguide/data-lake.html)