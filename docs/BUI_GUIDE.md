# Business User Interface (BUI) Guide

The Business User Interface (BUI) enables operations teams to manage contact center configurations directly through Amazon Connect's Admin UI, without requiring code changes or IT intervention. It leverages Data Tables and Admin Workspaces to provide operational control within defined guardrails.

---

## Overview

The BUI gives operations teams the ability to make real-time changes to the contact center within defined guardrails. Instead of raising IT tickets or waiting for code deployments, business users can manage routing, messages, caller status, and channel settings through user-friendly administrative forms.

**Key capabilities:**

- Manage VIP and blocked caller lists in real-time
- Configure per-channel routing and attributes
- Update customer-facing messages across languages
- Control brand-specific phone channel metadata
- All changes take effect immediately without deployments

**Benefits:**

- Reduced dependency on IT for day-to-day operational changes
- Faster response to business needs with intra-day adjustments
- Built-in guardrails prevent misconfiguration
- Full audit trail through Amazon Connect's native logging
- No need for separate third-party administrative interfaces

---

## What Gets Deployed

The BUI module deploys the following resources:

### Data Tables

| Table               | Purpose                                                                                      |
| ------------------- | -------------------------------------------------------------------------------------------- |
| CallerStatusTable   | Manage VIP and blocked phone numbers. Lookup callers on inbound to apply routing rules       |
| BrandTable          | Store phone channel metadata per brand. Map inbound numbers to brand-specific configurations |
| AttributeGroupTable | Channel-specific routing settings. Configure attributes that drive contact flow decisions    |
| MessageGroupTable   | Multi-language message storage. Manage IVR prompts and messages across locales               |

### Admin UI Workspaces

Four custom workspaces are deployed into Amazon Connect's Admin UI, providing form-based interfaces for managing each data table. Operations staff access these through the standard Amazon Connect admin console.

### Views

Four views are deployed that enable customer-facing and agent-facing interfaces to read from the data tables, providing real-time configuration lookup during contact flows.

### Sample Contact Flow

A sample contact flow is included demonstrating how to:

- Query the CallerStatusTable to identify VIP or blocked callers
- Retrieve brand configuration from the BrandTable
- Load channel-specific attributes from the AttributeGroupTable
- Fetch language-appropriate messages from the MessageGroupTable

---

## Architecture

The BUI integrates with the following AWS services:

- **Amazon Connect Data Tables** - Structured data storage for operational configurations
- **Amazon Connect Admin Workspaces** - Custom admin pages for business user management
- **Amazon Connect Views** - Interface components for data table interaction
- **Amazon Connect Contact Flows** - Real-time configuration lookup during calls

---

## Configuration

### Enabling the BUI

The BUI is enabled by default


### Post-Deployment

After deployment:

1. **Access the Admin UI** - Log into your Amazon Connect instance admin console
2. **Navigate to Workspaces** - Find the four BUI workspaces in the admin navigation
3. **Populate Data Tables** - Add initial data for caller status, brands, attributes, and messages
4. **Test the Sample Flow** - Use the included contact flow to verify data table lookups

---

## Data Table Patterns

### Caller Status Lookup

The CallerStatusTable enables inbound caller identification. When a call arrives, the contact flow queries this table to determine if the caller is a VIP (route to priority queue) or blocked (terminate call).

### Brand Configuration

The BrandTable maps inbound phone numbers to brand-specific settings. This allows a single Amazon Connect instance to serve multiple brands, each with distinct routing, messaging, and agent configurations.

### Attribute Groups

The AttributeGroupTable stores channel-specific routing attributes. Different channels (voice, chat, email) can have independent configuration sets that drive contact flow logic.

### Message Management

The MessageGroupTable stores customer-facing messages in multiple languages. IVR prompts, hold messages, and queue announcements can be updated by operations staff without deploying code.

---

## Best Practices

1. **Start with the sample flow** - Use the included contact flow as a template for your own implementations
2. **Define guardrails** - Use Amazon Connect's permissions to control which operations staff can modify which tables
3. **Test in non-production first** - Validate data table changes in a staging environment before applying to production
4. **Use consistent naming** - Establish naming conventions for table entries to maintain clarity as the configuration grows
5. **Document your schemas** - Keep records of what each table field means and valid values

---

## Multi-Region Support

The BUI supports deployment across 11 AWS regions where Amazon Connect is available, including AWS GovCloud. Region selection follows your main elevai-connect instance configuration.

---

## Further Reading

- [Amazon Connect Admin Guide - Data Tables](https://docs.aws.amazon.com/connect/latest/adminguide/data-tables.html)
- [Custom Extensions Guide](CUSTOM_EXTENSIONS_GUIDE.md) - Extending BUI with additional tables and workspaces
- [Parameter Store Guide](PARAMETER_STORE_GUIDE.md) - Exporting BUI resource ARNs for external integrations
