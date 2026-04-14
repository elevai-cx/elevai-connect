# Amazon Connect Q Knowledgebase Workshop

As part of the elevai-connect deployment includes a pre-packaged Amazon Q content ingestion tagging and session context solution. This is the recommended best practice way of ingesting documents from multiple sources. elevai-connect deploys the Amazon Q domain within Amazon S3 as the knowledgebase. This allows you to load [supported documents](https://docs.aws.amazon.com/connect/latest/adminguide/enable-q.html#q-content-types) into the S3 bucket provided.

## Prerequisites

- Amazon Connect instance deployed with elevai-connect
- Access to AWS Console


## Step 1: Upload Documents to S3

1. Get your Q Knowledge Base bucket name:
   ```bash
   pulumi stack output qconnect_kb_bucket
   ```
   Example output: `q-knowledge-bucket-xxxxxx`

2. Navigate to the S3 bucket in AWS Console

3. Upload the following files from the `examples/q-knowledgebase/` folder:
   - `FAQ for Current Account.pdf`
   - `FAQ for Current Account.meta.json`
   - `FAQ for Mortgage Account.pdf`
   - `FAQ for Mortgage Account.meta.json`

   **Note:** The `.meta.json` files contain document tags that Amazon Q uses for filtering and context.

4. Wait for Amazon Q to sync the documents (this may take a few minutes)

## Step 2: Create the Lex Bot

1. Login to Amazon Connect

2. Navigate to **Contact flows** > **Bots**

3. Click **Create bot**

4. Create a new bot with these settings:
   - **Bot name:** FAQBot
   - **Language:** English (GB)
   - **Amazon Q in Connect Intent** Enable the toggle and select the domain
   
5. Build and publish the bot:
   - Click **Build**
   - Once built, click **Version** and create a version
   - Then, create an **Alias** called **live**, associate to the version and check the box **Enable for use in flow and flow modules**

## Step 3: Import the Contact Flow

1. In Amazon Connect, navigate to **Routing** > **Contact flows**

2. Click **Create contact flow**

3. In the contact flow editor, click the dropdown arrow next to **Save** and select **Import flow (beta)**

4. Select the file `Amazon Q Sample.json` from the `examples/q-knowledgebase/` folder

5. Review the imported flow and update the 4 blocks as called out in the template.

6. Click **Publish**

## Step 4: Use the chat test facility to test

1. Navigate to **https://yourInstanceName.my.connect.aws/test-chat**

2. Select **Test Settings** in the top left

3. Choose your newly published flow and press **Apply**

4. Testing. The flow will route you 50% of the time to mortgages and 50% to current account FAQs. Ask questions to verify the content segmentation is working as expected.
   - How do I update my contact information
   - What is a current account


## Troubleshooting

- **Q not responding:** Verify documents are synced in the S3 bucket
  ```bash
  # Get your knowledge base ID
  pulumi stack output qconnect_knowledge_base_id
  
  # List all synced contents
  aws qconnect list-contents --knowledge-base-id <Id>
  ```
  You should see your uploaded PDFs listed and the tags assigned.

- **Bot not found:** Ensure FAQBot is published with alias 'live' and associated with Connect
- **Flow errors:** Check that all Lex bot blocks reference the correct bot name and alias



# Further reading

[AWS Documentation](https://docs.aws.amazon.com/connect/latest/adminguide/amazon-q-connect.html)

[AWS Workshop](https://catalog.workshops.aws/amazon-q-in-connect/en-US)

## Advanced: Multiple Tag Filtering

When using the Q Connect tag filtering lambda, you can filter content using multiple tags with different logical conditions.

### Single Tag Condition
```json
{"tagCondition":{"key":"account_type","value":"mortgage"}}
```

### AND Conditions (all tags must match)
```json
{
  "andConditions": [
    {"tagCondition": {"key": "account_type", "value": "mortgage"}},
    {"tagCondition": {"key": "customer_tier", "value": "premium"}},
    {"tagCondition": {"key": "region", "value": "northeast"}}
  ]
}
```

### OR Conditions (at least one tag must match)
```json
{
  "orConditions": [
    {"tagCondition": {"key": "account_type", "value": "mortgage"}},
    {"tagCondition": {"key": "account_type", "value": "current"}}
  ]
}
```

### Complex Nested Logic (combining AND/OR)
```json
{
  "andConditions": [
    {"tagCondition": {"key": "account_type", "value": "mortgage"}},
    {
      "orConditions": [
        {"tagCondition": {"key": "customer_tier", "value": "premium"}},
        {"tagCondition": {"key": "customer_tier", "value": "gold"}}
      ]
    }
  ]
}
```

**Note:** The tagFilter structure follows AWS Q Connect's TagFilter schema and can be nested for complex filtering logic.