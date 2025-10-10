# Monitoring & Alerting Guide

This guide covers the comprehensive monitoring and alerting capabilities built into elevai-connect, including alarm configuration, customization, and best practices. The example stack YAML file includes recommended settings, however you can tweak as required following the guide below.

---

## 🎯 Overview

The project includes **70+ CloudWatch alarms** covering all critical aspects of your Amazon Connect infrastructure. These alarms are production-ready and follow AWS best practices for contact center monitoring.

**Key Benefits:**
- 🚨 Early detection of issues before they impact customers
- 📊 Proactive capacity monitoring
- 💰 Cost protection through budget alerts
- 🔔 Multi-tier alerting (INFO/WARNING/ERROR)
- ⚙️ Customizable per environment

---

## 🚦 Multi-Tier Alert System

Alarms are organized into three severity levels:

### ERROR Alerts (Critical)
**Use Case:** Issues requiring immediate action
**SNS Topic:** Separate ERROR topic for on-call rotations
**Examples:**
- Connect instance at 85%+ concurrent capacity
- Lambda functions experiencing high error rates
- Critical service failures

**Recommended Response:**
- Page on-call engineer
- Immediate investigation required
- Escalate if not resolved within SLA

### WARNING Alerts (Important)
**Use Case:** Trending toward problems, requires attention
**SNS Topic:** INFO/WARNING topic for operations team
**Examples:**
- Connect instance at 70%+ concurrent capacity
- Elevated Lambda durations
- Increasing error rates
- Budget threshold at 80%

**Recommended Response:**
- Monitor trend
- Schedule investigation
- Consider capacity planning

### INFO Alerts (Informational)
**Use Case:** Awareness and trend monitoring
**SNS Topic:** INFO/WARNING topic
**Examples:**
- Budget threshold at 50%
- Moderate increases in metrics
- Non-critical operational changes

**Recommended Response:**
- Monitor for patterns
- Include in regular reviews
- Document for capacity planning

---

## 📊 Coverage Areas

### Amazon Connect Metrics

#### Concurrent Capacity Monitoring
Tracks usage across all channels to prevent service degradation:

**Voice:**
- **WARNING**: 70% of concurrent call limit
- **ERROR**: 85% of concurrent call limit
- Tracks inbound and outbound calls separately

**Chat:**
- **WARNING**: 70% of concurrent chat limit
- **ERROR**: 85% of concurrent chat limit

**Tasks:**
- **WARNING**: 70% of concurrent task limit
- **ERROR**: 85% of concurrent task limit

**Email:**
- **WARNING**: 70% of concurrent email limit
- **ERROR**: 85% of concurrent email limit

#### Call Quality Monitoring
- **Packet Loss Rate**: Alerts when >20% (poor audio quality)
- **Missed Calls**: Threshold-based alerting for dropped calls
- **Service Throttling**: Immediate alert on any throttling events

#### Operational Monitoring
- **Contact Flow Errors**: Failed executions or logic errors
- **Recording Failures**: Issues with call recording storage
- **Queue Overflow**: When queues exceed configured limits
- **Transfer Failures**: Failed call transfers between agents/queues

---

### Lambda Functions

All Lambda functions deployed by the project are monitored:

#### Error Rate Monitoring
```yaml
# Default thresholds
errors:
  threshold: 5        # Errors in 5-minute period
  period: 300
  evaluationPeriods: 2
```

**Tracks:**
- Function execution errors
- Timeout errors
- Out of memory errors
- Permission errors

#### Throttling Detection
```yaml
throttles:
  threshold: 10       # Dev: 10, Prod: 0 (zero-tolerance)
  period: 300
```

**What it means:**
- Function invocations rejected due to concurrency limits
- Indicates need for reserved concurrency or limit increase

#### Performance Monitoring
- **Duration alerts**: When functions approach timeout limit
- **Cold start tracking**: High initialization times
- **Concurrent executions**: Approaching account/function limits

---

### SQS Dead Letter Queues

**Message Age Monitoring:**
- Alerts when messages sit in DLQ too long
- Indicates processing failures requiring investigation

**Message Count Monitoring:**
- Threshold-based alerts on DLQ depth
- Tracks rate of failed message processing

---

### Cost Management

#### AWS Budget Alerts
Multi-tier budget monitoring with configurable thresholds:

```yaml
billing:
  enabled: true
  monthlyBudgetLimit: "1000"        # USD
  alertThresholds: [50, 80, 100]    # Percentage triggers
  notificationEmail: "billing@example.com"
```

**Alert Levels:**
- **50%**: INFO - Awareness notification
- **80%**: WARNING - Review spending
- **100%**: ERROR - Budget exceeded, investigate immediately

**What's Tracked:**
- All AWS services used by the Connect infrastructure
- Forecasted vs. actual spend
- Month-over-month trends

---

## ⚙️ Alarm Configuration

### Default Configuration

Alarms are automatically created when you deploy. Default settings are optimized for production use:

```yaml
config:
  # Enable/disable alerting system
  alerting:enabled: true
  
  # Email addresses for different severity levels
  alerting:error_email: "alerts@example.com"
  alerting:info_warning_email: "ops@example.com"
```

### Alarm Settings Structure

Each alarm type follows this pattern:

```yaml
alarms:<service>:
  <metric>:
    threshold: <number>           # Trigger value
    period: <seconds>             # Evaluation period
    evaluationPeriods: <number>   # Consecutive periods
    statistic: "Average"          # Sum, Average, Maximum, etc.
```

---

## 🎛️ Customizing Thresholds

### Environment-Specific Tuning

**Development Environment:**
```yaml
# Pulumi.dev.yaml
config:
  # More lenient thresholds for dev/test
  alarms:lambda:
    errors:
      threshold: 10             # Higher tolerance
      evaluationPeriods: 3
    throttles:
      threshold: 20             # Allow some throttling
  
  alarms:connect:
    concurrentPercentageWarning: 80   # 80% vs. prod 60%
    concurrentPercentageCritical: 90  # 90% vs. prod 75%
  
  billing:monthlyBudgetLimit: "100"   # Lower budget
```

**Production Environment:**
```yaml
# Pulumi.prod.yaml
config:
  # Stricter thresholds for production
  alarms:lambda:
    errors:
      threshold: 3              # Low tolerance
      evaluationPeriods: 2
    throttles:
      threshold: 0              # Zero-tolerance policy
  
  alarms:connect:
    concurrentPercentageWarning: 60   # Earlier warning
    concurrentPercentageCritical: 75  # Lower critical threshold
  
  billing:monthlyBudgetLimit: "5000"  # Production budget
```

### Customizing Specific Alarms

**Lambda Error Thresholds:**
```yaml
alarms:lambda:
  errors:
    threshold: 5
    period: 300         # 5 minutes
    evaluationPeriods: 2
    statistic: "Sum"
  
  duration:
    threshold: 25000    # 25 seconds (if timeout is 30s)
    period: 300
```

**Amazon Connect Capacity:**
```yaml
alarms:connect:
  concurrentPercentageWarning: 70
  concurrentPercentageCritical: 85
  
  missedCalls:
    threshold: 5
    period: 300
    evaluationPeriods: 1
  
  callsPerSecond:
    threshold: 10       # Max calls per second
    period: 60
```

**DynamoDB Throttling:**
```yaml
alarms:dynamodb:
  readThrottles:
    threshold: 0        # Zero tolerance (on-demand tables)
  
  writeThrottles:
    threshold: 0
  
  userErrors:
    threshold: 50       # Application errors
    period: 300
```

---

## 🧪 Testing Alarms

### Pre-Production Testing

Before going live, verify alarms are working correctly:

#### 1. Test SNS Email Subscriptions

```bash
# After deployment, check SNS topics were created
pulumi stack output sns_error_topic_arn
pulumi stack output sns_info_warning_topic_arn

# Verify email subscriptions in AWS Console
aws sns list-subscriptions-by-topic \
  --topic-arn <topic-arn>
```

**Verify:**
- ✅ Confirmation emails received and confirmed
- ✅ Test notification can be sent successfully
- ✅ Emails reach correct distribution lists

---

## 🎯 Best Practices

### Alarm Management

1. **Start Conservative, Then Tune**
   - Deploy with default settings
   - Monitor for false positives
   - Adjust thresholds based on actual patterns
   - Document all changes

2. **Use Composite Alarms for Complex Scenarios**
   ```yaml
   # Example: Alert only if multiple issues occur together
   - High error rate AND high duration AND throttling
   ```

3. **Implement Alarm Actions**
   - ERROR → Page on-call engineer
   - WARNING → Create ticket for investigation
   - INFO → Log for capacity planning

4. **Regular Review Cadence**
   - Weekly: Review triggered alarms
   - Monthly: Analyze patterns and trends
   - Quarterly: Adjust thresholds based on growth

### Alert Fatigue Prevention

**Avoid:**
- ❌ Too many INFO alerts
- ❌ Thresholds that trigger on normal variation
- ❌ Alerts without actionable response
- ❌ Duplicate alerts from correlated metrics

**Do:**
- ✅ Group related metrics into dashboards
- ✅ Use anomaly detection for dynamic thresholds
- ✅ Implement progressive alerting (warn before critical)
- ✅ Document expected response for each alert

### Email Configuration

**Production Setup:**
```yaml
# Use distribution lists, not individual emails
alerting:error_email: "ops-oncall@company.com"
alerting:info_warning_email: "ops-team@company.com"
billing:notificationEmail: "finance-team@company.com"
```

**Benefits of Distribution Lists:**
- Team coverage during vacations/shifts
- Automatic onboarding/offboarding
- Clear audit trail
- Integration with ticketing systems

