# Amazon Q in Connect Setup Guide

Amazon Q in Connect provides real-time AI assistance to contact center agents, helping them resolve customer issues faster with intelligent recommendations and knowledge base integration. 

This integration provides a tagging solution (though rules and meta files) and a Lambda function for usage within the Contact Flows for content filtering


---

## 🎯 Overview

Amazon Q in Connect is an AI-powered assistant that:

- 🔍 **Searches knowledge bases** in real-time during customer interactions
- 💡 **Provides intelligent suggestions** based on conversation context
- 📚 **Organizes content** with automated tagging and metadata
- ⚡ **Reduces handle time** by surfacing relevant information instantly
- 🎯 **Improves accuracy** with AI-powered recommendations

**Benefits:**
- Faster resolution times
- Reduced training requirements for new agents
- Consistent information delivery
- Improved customer satisfaction
- Lower operational costs

---

## ✨ Features

### Knowledge Base Integration

Amazon Q automatically:
- Indexes content from your S3 buckets
- Tags and categorizes documents
- Maintains metadata for efficient searching
- Updates in real-time as content changes

### Real-time Suggestions

During customer interactions, Amazon Q:
- Analyzes conversation context
- Searches relevant knowledge base articles
- Provides ranked recommendations
- Updates suggestions as conversation evolves

### Content Management

Organize your knowledge base with:
- Folder-based structure
- Custom metadata tags
- Department and region categorization
- Content type classification
- Version control integration

### Automated Tagging

The project includes Lambda functions for:
- Automatic document ingestion
- Metadata extraction and tagging
- Content organization
- Session management

---

## ✅ Prerequisites

None

---

## ⚙️ Configuration

### Basic Setup

Edit your `Pulumi.dev.yaml` file to enable Amazon Q:

```yaml
config:
  # Enable Amazon Q in Connect
  qconnect:
    enabled: true
    assistantName: q-assistant
    knowledgeBaseName: my-knowledge-base
```

### Advanced Configuration

For more control over your Q assistant:

```yaml
config:
  qconnect:
    enabled: true
    assistantName: production-q-assistant
    knowledgeBaseName: production-kb
    
    # Configure content tagging
    contentTagging:
      - folderName: sales/emea
        tags:
          Department: Sales
          Region: EMEA
          Language: English
          
      - folderName: sales/americas
        tags:
          Department: Sales
          Region: Americas
          Language: English
          
      - folderName: support/technical
        tags:
          Department: Support
          ContentType: Technical Guide
          Difficulty: Advanced
          
      - folderName: support/billing
        tags:
          Department: Support
          ContentType: Billing Guide
          Difficulty: Basic
```

### Deploy Configuration

After updating your configuration:

```bash
# Preview changes
pulumi preview

# Deploy
pulumi up
```

**Outputs you'll receive:**
- Q Assistant ARN
- Q Assistant ID
- Knowledge Base ARN
- Knowledge Base ID
- S3 bucket for content

---

## 📚 Knowledge Base Management

### Content Structure

Organize your content in S3 following this recommended structure:

```
s3://your-knowledge-base-bucket/
├── sales/
│   ├── emea/
│   │   ├── product-guide.pdf
│   │   ├── product-guide.meta.json       # Optional metadata
│   │   ├── pricing-guide.pdf
│   │   ├── pricing-guide.meta.json       # Optional metadata
│   │   └── competitive-analysis.pdf
│   └── americas/
│       ├── product-guide.pdf
│       └── pricing-guide.pdf
├── support/
│   ├── technical/
│   │   ├── troubleshooting-guide.pdf
│   │   ├── api-documentation.pdf
│   │   ├── api-documentation.meta.json  # Optional metadata
│   │   └── integration-guide.pdf
│   └── billing/
│       ├── payment-methods.pdf
│       ├── refund-policy.pdf
│       └── invoice-guide.pdf
└── hr/
    ├── policies/
    └── procedures/
```

**Note:** `.meta.json` files are optional and provide file-level metadata. Files without metadata will use folder-based tags only.

### Supported Content Types

Amazon Q can index:
- PDF documents
- Microsoft Word documents (.docx)
- Plain text files (.txt)
- Markdown files (.md)
- HTML files (.html)

**Best practices for content:**
- Use clear, descriptive filenames
- Include metadata in document properties
- Keep documents focused on single topics
- Update regularly to maintain accuracy
- Remove outdated information

### Uploading Content

Upload content to your S3 knowledge base bucket:

```bash
# Get the bucket name from Pulumi outputs
pulumi stack output qconnect_knowledge_base_bucket

# Upload content with folder-based tagging only
aws s3 cp ./my-document.pdf s3://your-kb-bucket/sales/emea/

# Upload content with file-level metadata
aws s3 cp ./product-guide.pdf s3://your-kb-bucket/sales/emea/
aws s3 cp ./product-guide.meta.json s3://your-kb-bucket/sales/emea/

# Sync entire folder (includes both PDFs and .meta.json files)
aws s3 sync ./content-folder/ s3://your-kb-bucket/support/
```

**Creating metadata files locally:**
```bash
# Create a metadata file for your document
cat > product-guide.meta.json <<EOF
{
  "tags": {
    "department": "sales",
    "Version": "1.0"
  }
}
EOF

# Upload both files
aws s3 cp ./product-guide.pdf s3://your-kb-bucket/sales/
aws s3 cp ./product-guide.meta.json s3://your-kb-bucket/sales/
```

The Lambda function will automatically:
1. Detect new content
2. Check for accompanying `.meta.json` file
3. Extract metadata from JSON (if present)
4. Apply folder-based tags
5. Merge/override with file-level tags
6. Index content in Amazon Q

---

## 🏷️ Content Organization

### Tagging Strategies

The project supports **two complementary approaches** for tagging content:

#### 1. Folder-Based Tagging (Automatic)

The project automatically applies tags based on folder structure:

**Configuration:**
```yaml
qconnect:contentTagging:
  - folderName: sales/emea
    tags:
      Department: Sales
      Region: EMEA
```

**Result:**
All files in `s3://bucket/sales/emea/` automatically get:
- `Department: Sales`
- `Region: EMEA`

#### 2. File-Level Metadata (Manual)

For more granular control, place a `.meta.json` file alongside your content with the same filename:

**File Structure:**
```
s3://bucket/sales/emea/
├── product-guide.pdf
├── product-guide.meta.json
├── pricing-2024.pdf
└── pricing-2024.meta.json
```

**Metadata File Format:**
```json
{
  "tags": {
    "department": "sales",
    "Version": "1.0"
  }
}
```

**How it works:**
- Upload `filename.pdf` and `filename.meta.json` to the same S3 folder
- The Lambda function reads both files during processing
- Tags from `.meta.json` are applied to the document
- File-level tags override or merge with folder-level tags

**Benefits of file-level metadata:**
- ✅ Document-specific versioning
- ✅ Individual author tracking
- ✅ Per-file review dates
- ✅ Override folder defaults
- ✅ More precise categorization


## Filtering

Once the content is within Amazon Q any interaction will use the whole knowledge base. There will be times when you only need certain documents to be included to furnish the response.

To make this happen we need to use an API query to tell Amazon Q which documents to include. As part odf the deployment there is a utils lambda that is available within the Amazon Connect contact flow.

To use this add a "AWS Lambda function" block to the canvas.
- Choose the lambda from the dropdown "utils-xxxxxx"
- Add an input Parameter `requestType` = `q_connect_tags`
- Add another input Parameter `tagFilter` = `{"tagCondition":{"key":"<key>","value":"<value>"}}`
- Set Response validation to `JSON`

This will ensure that for Self Service and Agent Assist these documents will be used in the responses.

---

## 🆘 Support

For issues specific to this implementation:
- 🐛 [Open an Issue](https://github.com/bloy.me.uk/elevai-connect/issues)
- 💬 [Start a Discussion](https://github.com/bloy.me.uk/elevai-connect/discussions)

For Amazon Q support:
- 📖 [AWS Documentation](https://docs.aws.amazon.com/connect/latest/adminguide/amazon-q-connect.html)
- 🎫 [AWS Support Center](https://console.aws.amazon.com/support/)
