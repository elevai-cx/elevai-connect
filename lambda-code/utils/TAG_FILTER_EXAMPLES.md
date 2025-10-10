# Amazon Q in Connect Tag Filtering Examples

This file contains practical examples of tag filtering configurations for different use cases.

## Example 1: Department-Based Filtering

**Scenario**: Route customers to agents with access to department-specific knowledge.

**Contact Flow Setup**:
1. Get customer department from CRM or user input
2. Store in contact attribute: `CustomerDepartment`
3. Invoke Lambda with dynamic tag filter

**Lambda Parameters**:
```json
{
  "requestType": "q_connect_tags",
  "tagFilter": {
    "tagCondition": {
      "tagKey": "department",
      "tagValue": "$.Attributes.CustomerDepartment"
    }
  }
}
```

**Example Tags on Content**:
- Sales articles: `{"department": "sales"}`
- Support articles: `{"department": "support"}`
- Billing articles: `{"department": "billing"}`

---

## Example 2: Product-Based Filtering

**Scenario**: Show knowledge articles relevant to the customer's purchased product.

**Contact Flow Setup**:
1. Lookup customer's product from order system
2. Store in contact attribute: `CustomerProduct`
3. Filter Q in Connect content by product

**Lambda Parameters**:
```json
{
  "requestType": "q_connect_tags",
  "tagFilter": {
    "tagCondition": {
      "tagKey": "product",
      "tagValue": "$.Attributes.CustomerProduct"
    }
  }
}
```

**Example Tags on Content**:
- Widget A docs: `{"product": "widget-a"}`
- Widget B docs: `{"product": "widget-b"}`
- Premium service: `{"product": "premium-service"}`

---

## Example 3: Multi-Product Support (OR Logic)

**Scenario**: Customer owns multiple products, show content for any of them.

**Lambda Parameters**:
```json
{
  "requestType": "q_connect_tags",
  "tagFilter": {
    "orConditions": [
      {
        "tagCondition": {
          "tagKey": "product",
          "tagValue": "widget-a"
        }
      },
      {
        "tagCondition": {
          "tagKey": "product",
          "tagValue": "widget-b"
        }
      },
      {
        "tagCondition": {
          "tagKey": "product",
          "tagValue": "premium-service"
        }
      }
    ]
  }
}
```

---

## Example 4: Region + Department (AND Logic)

**Scenario**: Filter by both geographic region and department for compliance.

**Lambda Parameters**:
```json
{
  "requestType": "q_connect_tags",
  "tagFilter": {
    "andConditions": [
      {
        "tagCondition": {
          "tagKey": "department",
          "tagValue": "$.Attributes.CustomerDepartment"
        }
      },
      {
        "tagCondition": {
          "tagKey": "region",
          "tagValue": "$.Attributes.CustomerRegion"
        }
      }
    ]
  }
}
```

**Example Tags on Content**:
- US Sales docs: `{"department": "sales", "region": "us"}`
- EU Sales docs: `{"department": "sales", "region": "eu"}`
- APAC Support: `{"department": "support", "region": "apac"}`

---

## Example 5: Customer Tier (VIP vs Standard)

**Scenario**: Show enhanced content to VIP customers.

**Contact Flow Setup**:
1. Check customer account level
2. Store in attribute: `CustomerTier` (`vip` or `standard`)
3. Filter content accordingly

**Lambda Parameters**:
```json
{
  "requestType": "q_connect_tags",
  "tagFilter": {
    "tagCondition": {
      "tagKey": "tier",
      "tagValue": "$.Attributes.CustomerTier"
    }
  }
}
```

**Example Tags on Content**:
- Standard support: `{"tier": "standard"}`
- VIP support: `{"tier": "vip"}`
- All customers: `{"tier": "all"}`

---

## Example 6: Language-Based Filtering

**Scenario**: Show content in customer's preferred language.

**Lambda Parameters**:
```json
{
  "requestType": "q_connect_tags",
  "tagFilter": {
    "tagCondition": {
      "tagKey": "language",
      "tagValue": "$.Attributes.CustomerLanguage"
    }
  }
}
```

**Example Tags on Content**:
- English docs: `{"language": "en"}`
- Spanish docs: `{"language": "es"}`
- French docs: `{"language": "fr"}`

---

## Example 7: Complex Filter (Product OR Department) AND Region

**Scenario**: Enterprise customer with complex requirements.

**Lambda Parameters**:
```json
{
  "requestType": "q_connect_tags",
  "tagFilter": {
    "andConditions": [
      {
        "orConditions": [
          {
            "tagCondition": {
              "tagKey": "product",
              "tagValue": "enterprise-suite"
            }
          },
          {
            "tagCondition": {
              "tagKey": "department",
              "tagValue": "enterprise"
            }
          }
        ]
      },
      {
        "tagCondition": {
          "tagKey": "region",
          "tagValue": "$.Attributes.CustomerRegion"
        }
      }
    ]
  }
}
```

---

## Example 8: Account Type + Issue Category

**Scenario**: Filter by account type and the specific issue category.

**Contact Flow Setup**:
1. Get account type: `business` or `personal`
2. Determine issue from IVR: `technical`, `billing`, `sales`
3. Filter content by both

**Lambda Parameters**:
```json
{
  "requestType": "q_connect_tags",
  "tagFilter": {
    "andConditions": [
      {
        "tagCondition": {
          "tagKey": "account-type",
          "tagValue": "$.Attributes.AccountType"
        }
      },
      {
        "tagCondition": {
          "tagKey": "category",
          "tagValue": "$.Attributes.IssueCategory"
        }
      }
    ]
  }
}
```

**Example Tags on Content**:
- Business technical: `{"account-type": "business", "category": "technical"}`
- Personal billing: `{"account-type": "personal", "category": "billing"}`
- Business sales: `{"account-type": "business", "category": "sales"}`

---

## Dynamic Tag Filter Construction

### Using AWS Lambda to Build Complex Filters

If you need to build very complex filters based on multiple business rules:

**Option 1**: Create a second Lambda that constructs the tag filter

```python
def build_tag_filter(event, context):
    customer_data = get_customer_data(event['customerId'])
    
    # Build filter based on complex logic
    conditions = []
    
    if customer_data['is_vip']:
        conditions.append({
            "tagCondition": {"tagKey": "tier", "tagValue": "vip"}
        })
    
    if customer_data['products']:
        for product in customer_data['products']:
            conditions.append({
                "tagCondition": {"tagKey": "product", "tagValue": product}
            })
    
    return {
        "tagFilter": {
            "orConditions": conditions
        }
    }
```

**Option 2**: Store pre-built filters in DynamoDB by customer segment

```python
# In contact flow: Lookup customer segment
# Then: Get pre-built tag filter from DynamoDB
# Finally: Pass to utils Lambda
```

---

## Best Practices for Tagging Content

### 1. **Use Consistent Tag Keys**
```
✅ Good: department, product, region, tier
❌ Bad: dept, deptartment, DEPARTMENT (inconsistent)
```

### 2. **Use Lowercase Values**
```
✅ Good: {"department": "sales"}
❌ Bad: {"department": "Sales"} (case sensitive!)
```

### 3. **Plan Your Tag Hierarchy**
```
Strategy:
- Primary filter: department (broad)
- Secondary filter: product (specific)
- Tertiary filter: language (localization)
```

### 4. **Tag for Fallback**
```
Always tag some content as "general" or "all" for fallback:
{"department": "all", "product": "all"}
```

### 5. **Document Your Tags**
Create a tag registry:
```
department: [sales, support, billing, technical]
product: [widget-a, widget-b, premium-service]
region: [us, eu, apac, latam]
tier: [standard, premium, enterprise]
language: [en, es, fr, de]
```

---

## Troubleshooting Tag Filters

### No Results Returned

**Cause**: Tags don't match or content isn't tagged

**Solution**:
1. Check content tags in Q in Connect console
2. Verify tag key/value match exactly (case sensitive)
3. Add "all" tagged content as fallback
4. Check CloudWatch logs for tag filter being sent

### Wrong Content Shown

**Cause**: Tag filter not applied or too broad

**Solution**:
1. Check Lambda response in CloudWatch logs
2. Verify `status-code` is 200
3. Make tag conditions more specific (use AND logic)
4. Ensure Q in Connect block is BEFORE Lambda invoke

### Filter Not Updating

**Cause**: Lambda called before Q in Connect block

**Solution**:
Contact flow order must be:
1. Set recording behaviour (enable Contact Lens)
2. Amazon Q in Connect block
3. Invoke utils Lambda with tag filter
4. Transfer to queue

---

## Testing Your Tag Filters

### In CloudWatch Logs

Look for these log entries:
```
"Request details": {
  "contact_id": "...",
  "has_tag_filter": true
}

"Parsed tag filter": {
  "tag_filter": { ... }
}

"Successfully updated Q in Connect session with tag filter"
```

### Validate Response

Success response should include:
```json
{
  "status-code": 200,
  "body": "Success - Updated Q in Connect session with tag filter",
  "session-arn": "arn:aws:wisdom:...",
  "tag-filter": { ... }
}
```

---

## Advanced: Tag Filter Templates

Save these as Lex bot intents or contact attributes:

**Template: Single Department**
```json
{"tagCondition": {"tagKey": "department", "tagValue": "{DEPARTMENT}"}}
```

**Template: Product Family**
```json
{
  "orConditions": [
    {"tagCondition": {"tagKey": "product-family", "tagValue": "{FAMILY}"}},
    {"tagCondition": {"tagKey": "product", "tagValue": "all"}}
  ]
}
```

**Template: Geo + Language**
```json
{
  "andConditions": [
    {"tagCondition": {"tagKey": "region", "tagValue": "{REGION}"}},
    {"tagCondition": {"tagKey": "language", "tagValue": "{LANGUAGE}"}}
  ]
}
```

Replace `{PLACEHOLDERS}` with contact attributes in your flow!

---

Remember: Tag filtering is powerful but requires good content management. Start simple, test thoroughly, and expand as needed! 🎯
