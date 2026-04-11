# Copyright 2024-2025 ELEVAI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Business User Interface (BUI) for Amazon Connect

Creates Data Tables, Views, a Workspace, and a sample contact flow
that demonstrates multi-table lookup routing with VIP/BLOCKED caller
management, brand routing, message groups, and attribute groups.

Resources created:
  - 4 Data Tables (CallerStatus, Brand, MessageGroup, AttributeGroup)
  - Data Table Attributes for each table
  - Sample records for each table
  - 4 Views (one per table, ReadAndWrite mode)
  - 1 BUI Workspace linking all views
  - 1 Sample contact flow demonstrating data table usage
"""

import json
import os
from typing import Dict, Any

import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native

_CONTACT_FLOWS_DIR = os.path.join(os.path.dirname(__file__), "contact_flows")


# ---------------------------------------------------------------------------
# Helper: create a view template for a DataTable widget
# ---------------------------------------------------------------------------

def _make_view_template(title: str, widget_id: str) -> Dict[str, Any]:
    """Build a View template with a single DataTable widget (ReadAndWrite)."""
    return {
        "Head": {
            "Configuration": {"Layout": {"Columns": [12]}},
            "Integrations": [],
            "Title": title,
        },
        "Body": [
            {
                "_id": widget_id,
                "Type": "DataTable",
                "Props": {
                    "DataTable": "{{DATA_TABLE_ID}}",  # replaced at call site
                    "Mode": "ReadAndWrite",
                    "Display": "TableAndForm",
                    "Attributes": [],
                    "PrimaryValues": [[]],
                },
                "Content": [],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Caller Status Table
# ---------------------------------------------------------------------------

def _create_caller_status_table(
    stage: str,
    connect_instance: aws.connect.Instance,
    tags: Dict[str, str],
) -> Dict[str, Any]:
    """Create the CallerStatus data table with VIP/BLOCKED enum."""
    table = aws_native.connect.DataTable(
        f"{stage}-connect-dt-caller-status",
        instance_arn=connect_instance.arn,
        name="Elevai-CallerStatusTable",
        description="Elevai table to store VIP and BLOCKED caller status",
        time_zone="America/New_York",
        status="PUBLISHED",
        value_lock_level="NONE",
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in tags.items()],
    )

    e164_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-caller-e164",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="e164",
        value_type="TEXT",
        primary=True,
        description="E.164 formatted phone number",
    )

    status_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-caller-status",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="status",
        value_type="TEXT",
        primary=False,
        description="Caller status (VIP or BLOCKED)",
        validation=aws_native.connect.ValidationPropertiesArgs(
            enum=aws_native.connect.ValidationPropertiesEnumPropertiesArgs(
                strict=True,
                values=["VIP", "BLOCKED"],
            ),
        ),
    )

    # Sample VIP record
    vip_record = aws_native.connect.DataTableRecord(
        f"{stage}-connect-dtr-caller-vip",
        instance_arn=connect_instance.arn,
        data_table_arn=table.arn,
        data_table_record=aws_native.connect.DataTableRecordPropertiesArgs(
            primary_values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=e164_attr.attribute_id, attribute_value="+12025551234"),
            ],
            values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=status_attr.attribute_id, attribute_value="VIP"),
            ],
        ),
        opts=pulumi.ResourceOptions(depends_on=[e164_attr, status_attr]),
    )

    return {
        "table": table,
        "attributes": {"e164": e164_attr, "status": status_attr},
        "records": [vip_record],
    }


# ---------------------------------------------------------------------------
# Brand Table
# ---------------------------------------------------------------------------

def _create_brand_table(
    stage: str,
    connect_instance: aws.connect.Instance,
    tags: Dict[str, str],
) -> Dict[str, Any]:
    """Create the Brand data table mapping phone numbers to brand info."""
    table = aws_native.connect.DataTable(
        f"{stage}-connect-dt-brand",
        instance_arn=connect_instance.arn,
        name="Elevai-BrandTable",
        description="Elevai table to store brand information by E.164 number",
        time_zone="America/New_York",
        status="PUBLISHED",
        value_lock_level="NONE",
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in tags.items()],
    )

    e164_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-brand-e164",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="e164",
        value_type="TEXT",
        primary=True,
        description="E.164 formatted phone number",
    )

    attr_group_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-brand-attr-group",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="attribute_group",
        value_type="TEXT",
        primary=False,
        description="Attribute Group identifier",
    )

    language_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-brand-language",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="language",
        value_type="TEXT",
        primary=False,
        description="Language code",
    )

    attrs = [e164_attr, attr_group_attr, language_attr]

    record1 = aws_native.connect.DataTableRecord(
        f"{stage}-connect-dtr-brand-uk",
        instance_arn=connect_instance.arn,
        data_table_arn=table.arn,
        data_table_record=aws_native.connect.DataTableRecordPropertiesArgs(
            primary_values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=e164_attr.attribute_id, attribute_value="+44912345678"),
            ],
            values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=attr_group_attr.attribute_id, attribute_value="TechSupport"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=language_attr.attribute_id, attribute_value="en-GB"),
            ],
        ),
        opts=pulumi.ResourceOptions(depends_on=attrs),
    )

    record2 = aws_native.connect.DataTableRecord(
        f"{stage}-connect-dtr-brand-es",
        instance_arn=connect_instance.arn,
        data_table_arn=table.arn,
        data_table_record=aws_native.connect.DataTableRecordPropertiesArgs(
            primary_values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=e164_attr.attribute_id, attribute_value="+34912345678"),
            ],
            values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=attr_group_attr.attribute_id, attribute_value="TechSupport"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=language_attr.attribute_id, attribute_value="es-ES"),
            ],
        ),
        opts=pulumi.ResourceOptions(depends_on=attrs),
    )

    return {
        "table": table,
        "attributes": {
            "e164": e164_attr,
            "attribute_group": attr_group_attr,
            "language": language_attr,
        },
        "records": [record1, record2],
    }


# ---------------------------------------------------------------------------
# Message Group Table
# ---------------------------------------------------------------------------

def _create_message_group_table(
    stage: str,
    connect_instance: aws.connect.Instance,
    tags: Dict[str, str],
) -> Dict[str, Any]:
    """Create the MessageGroup data table for IVR messages by language."""
    table = aws_native.connect.DataTable(
        f"{stage}-connect-dt-message-group",
        instance_arn=connect_instance.arn,
        name="Elevai-MessageGroupTable",
        description="Elevai table to store message groups by language and message group",
        time_zone="America/New_York",
        status="PUBLISHED",
        value_lock_level="NONE",
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in tags.items()],
    )

    # Primary keys
    language_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-msg-language",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="language",
        value_type="TEXT",
        primary=True,
        description="Language code",
    )

    msg_group_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-msg-group",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="message_group",
        value_type="TEXT",
        primary=True,
        description="Message group identifier",
    )

    # Value attributes
    greeting_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-msg-greeting",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="Greeting",
        value_type="TEXT",
        primary=False,
        description="Greeting message",
    )

    sit_hv_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-msg-sit-hv",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="Sit_HighVolume",
        value_type="TEXT",
        primary=False,
        description="High volume message",
    )

    sit_hv_active_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-msg-sit-hv-active",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="Sit_HighVolume_Active",
        value_type="BOOLEAN",
        primary=False,
        description="High volume active flag",
    )

    menu_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-msg-menu",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="Menu",
        value_type="TEXT",
        primary=False,
        description="Menu message",
    )

    option1_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-msg-option1",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="Option_1",
        value_type="TEXT",
        primary=False,
        description="Menu option 1",
    )

    option2_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-msg-option2",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="Option_2",
        value_type="TEXT",
        primary=False,
        description="Menu option 2",
    )

    goodbye_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-msg-goodbye",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="Goodbye",
        value_type="TEXT",
        primary=False,
        description="Goodbye message",
    )

    all_attrs = [
        language_attr, msg_group_attr, greeting_attr, sit_hv_attr,
        sit_hv_active_attr, menu_attr, option1_attr, option2_attr, goodbye_attr,
    ]

    # English record
    record_en = aws_native.connect.DataTableRecord(
        f"{stage}-connect-dtr-msg-en",
        instance_arn=connect_instance.arn,
        data_table_arn=table.arn,
        data_table_record=aws_native.connect.DataTableRecordPropertiesArgs(
            primary_values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=language_attr.attribute_id, attribute_value="en-GB"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=msg_group_attr.attribute_id, attribute_value="IT Helpdesk"),
            ],
            values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=greeting_attr.attribute_id, attribute_value="Welcome to IT Helpdesk"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=sit_hv_attr.attribute_id, attribute_value="We are experiencing high call volumes"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=sit_hv_active_attr.attribute_id, attribute_value="true"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=menu_attr.attribute_id, attribute_value="Please select from the following options. Press 1 for password resets or option 2 for hardware issues."),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=option1_attr.attribute_id, attribute_value="You selected option 1."),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=option2_attr.attribute_id, attribute_value="You selected option 2."),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=goodbye_attr.attribute_id, attribute_value="Thank you for calling IT Helpdesk"),
            ],
        ),
        opts=pulumi.ResourceOptions(depends_on=all_attrs),
    )

    # Spanish record
    record_es = aws_native.connect.DataTableRecord(
        f"{stage}-connect-dtr-msg-es",
        instance_arn=connect_instance.arn,
        data_table_arn=table.arn,
        data_table_record=aws_native.connect.DataTableRecordPropertiesArgs(
            primary_values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=language_attr.attribute_id, attribute_value="es-ES"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=msg_group_attr.attribute_id, attribute_value="IT Helpdesk"),
            ],
            values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=greeting_attr.attribute_id, attribute_value="Bienvenido al servicio de asistencia de TI"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=sit_hv_attr.attribute_id, attribute_value="Estamos experimentando un alto volumen de llamadas"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=sit_hv_active_attr.attribute_id, attribute_value="true"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=menu_attr.attribute_id, attribute_value="Seleccione una de las siguientes opciones: 1 para restablecer la contraseña o 2 para problemas de hardware."),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=option1_attr.attribute_id, attribute_value="Usted seleccionó la opción 1."),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=option2_attr.attribute_id, attribute_value="Usted seleccionó la opción 2."),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=goodbye_attr.attribute_id, attribute_value="Gracias por llamar al servicio de asistencia de TI"),
            ],
        ),
        opts=pulumi.ResourceOptions(depends_on=all_attrs),
    )

    return {
        "table": table,
        "attributes": {
            "language": language_attr,
            "message_group": msg_group_attr,
            "Greeting": greeting_attr,
            "Sit_HighVolume": sit_hv_attr,
            "Sit_HighVolume_Active": sit_hv_active_attr,
            "Menu": menu_attr,
            "Option_1": option1_attr,
            "Option_2": option2_attr,
            "Goodbye": goodbye_attr,
        },
        "records": [record_en, record_es],
    }


# ---------------------------------------------------------------------------
# Attribute Group Table
# ---------------------------------------------------------------------------

def _create_attribute_group_table(
    stage: str,
    connect_instance: aws.connect.Instance,
    tags: Dict[str, str],
) -> Dict[str, Any]:
    """Create the AttributeGroup data table."""
    table = aws_native.connect.DataTable(
        f"{stage}-connect-dt-attr-group",
        instance_arn=connect_instance.arn,
        name="Elevai-AttributeGroupTable",
        description="Elevai table to store attribute group information",
        time_zone="America/New_York",
        status="PUBLISHED",
        value_lock_level="NONE",
        tags=[aws_native.TagArgs(key=k, value=v) for k, v in tags.items()],
    )

    name_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-ag-name",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="attribute_group",
        value_type="TEXT",
        primary=True,
        description="Attribute Group identifier",
    )

    brand_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-ag-brand",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="brand",
        value_type="TEXT",
        primary=False,
        description="Brand name",
    )

    dept_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-ag-dept",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="department",
        value_type="TEXT",
        primary=False,
        description="Department name",
    )

    survey_attr = aws_native.connect.DataTableAttribute(
        f"{stage}-connect-dta-ag-survey",
        data_table_arn=table.arn,
        instance_arn=connect_instance.arn,
        name="post_contact_survey",
        value_type="BOOLEAN",
        primary=False,
        description="Post contact survey enabled flag",
    )

    all_attrs = [name_attr, brand_attr, dept_attr, survey_attr]

    record_tech = aws_native.connect.DataTableRecord(
        f"{stage}-connect-dtr-ag-techsupport",
        instance_arn=connect_instance.arn,
        data_table_arn=table.arn,
        data_table_record=aws_native.connect.DataTableRecordPropertiesArgs(
            primary_values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=name_attr.attribute_id, attribute_value="TechSupport"),
            ],
            values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=brand_attr.attribute_id, attribute_value="TechCorp"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=dept_attr.attribute_id, attribute_value="IT Department"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=survey_attr.attribute_id, attribute_value="true"),
            ],
        ),
        opts=pulumi.ResourceOptions(depends_on=all_attrs),
    )

    record_cs = aws_native.connect.DataTableRecord(
        f"{stage}-connect-dtr-ag-custservice",
        instance_arn=connect_instance.arn,
        data_table_arn=table.arn,
        data_table_record=aws_native.connect.DataTableRecordPropertiesArgs(
            primary_values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=name_attr.attribute_id, attribute_value="CustomerService"),
            ],
            values=[
                aws_native.connect.DataTableRecordValueArgs(attribute_id=brand_attr.attribute_id, attribute_value="TechCorp"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=dept_attr.attribute_id, attribute_value="Customer Support"),
                aws_native.connect.DataTableRecordValueArgs(attribute_id=survey_attr.attribute_id, attribute_value="false"),
            ],
        ),
        opts=pulumi.ResourceOptions(depends_on=all_attrs),
    )

    return {
        "table": table,
        "attributes": {
            "attribute_group": name_attr,
            "brand": brand_attr,
            "department": dept_attr,
            "post_contact_survey": survey_attr,
        },
        "records": [record_tech, record_cs],
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def _create_view(
    stage: str,
    connect_instance: aws.connect.Instance,
    table: aws_native.connect.DataTable,
    name: str,
    slug: str,
    description: str,
    widget_id: str,
    tags: Dict[str, str],
) -> aws_native.connect.View:
    """Create a View with a DataTable widget pointing at the given table."""
    template = _make_view_template(name, widget_id)

    # Replace the placeholder DataTable ID with the actual table ID (last segment of ARN)
    def resolve_template(table_arn: str) -> Dict[str, Any]:
        table_id = table_arn.split("/")[-1]
        tmpl = json.loads(json.dumps(template))
        tmpl["Body"][0]["Props"]["DataTable"] = table_id
        return tmpl

    resolved = table.arn.apply(resolve_template)

    return aws_native.connect.View(
        f"{stage}-connect-view-{slug}",
        instance_arn=connect_instance.arn,
        name=name,
        description=description,
        template=resolved,
        actions=[],
        tags=[
            aws_native.TagArgs(key=k, value=v)
            for k, v in {**tags, "Purpose": "Workspace"}.items()
        ],
        opts=pulumi.ResourceOptions(depends_on=[table]),
    )


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

def _create_workspace(
    stage: str,
    connect_instance: aws.connect.Instance,
    views: Dict[str, aws_native.connect.View],
    tags: Dict[str, str],
) -> aws_native.connect.Workspace:
    """Create the BUI Workspace linking all views."""
    return aws_native.connect.Workspace(
        f"{stage}-connect-workspace-bui",
        instance_arn=connect_instance.arn,
        name="Elevai BUI",
        description="Elevai Business User Interface workspace",
        pages=[
            aws_native.connect.WorkspacePageArgs(
                page="CallerStatus",
                resource_arn=views["caller_status"].view_arn,
                slug="caller-status",
            ),
            aws_native.connect.WorkspacePageArgs(
                page="Brand",
                resource_arn=views["brand"].view_arn,
                slug="brand",
            ),
            aws_native.connect.WorkspacePageArgs(
                page="MessageGroup",
                resource_arn=views["message_group"].view_arn,
                slug="message-group",
            ),
            aws_native.connect.WorkspacePageArgs(
                page="AttributeGroup",
                resource_arn=views["attribute_group"].view_arn,
                slug="attribute-group",
            ),
        ],
        tags=[
            aws_native.TagArgs(key=k, value=v)
            for k, v in {**tags, "Purpose": "Business Interface"}.items()
        ],
        opts=pulumi.ResourceOptions(
            depends_on=list(views.values()),
        ),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_bui_infrastructure(
    connect_instance: aws.connect.Instance,
    tags: Dict[str, str],
) -> Dict[str, Any]:
    """
    Create all Business User Interface resources.

    Args:
        connect_instance: The Amazon Connect instance.
        tags: Common tags to apply to resources.

    Returns:
        Dictionary containing references to all BUI resources.
    """
    stage = pulumi.get_stack()

    # Create data tables
    caller_status = _create_caller_status_table(stage, connect_instance, tags)
    brand = _create_brand_table(stage, connect_instance, tags)
    message_group = _create_message_group_table(stage, connect_instance, tags)
    attribute_group = _create_attribute_group_table(stage, connect_instance, tags)

    # Create views
    views = {
        "caller_status": _create_view(
            stage, connect_instance,
            caller_status["table"],
            name="Elevai Caller Status",
            slug="caller-status",
            description="Elevai view for managing caller status in data table",
            widget_id="DataTable_1767020897678",
            tags=tags,
        ),
        "brand": _create_view(
            stage, connect_instance,
            brand["table"],
            name="Elevai Brand",
            slug="brand",
            description="Elevai view for managing brand information in data table",
            widget_id="DataTable_Brand",
            tags=tags,
        ),
        "message_group": _create_view(
            stage, connect_instance,
            message_group["table"],
            name="Elevai Message Group",
            slug="message-group",
            description="Elevai view for managing message groups in data table",
            widget_id="DataTable_MessageGroup",
            tags=tags,
        ),
        "attribute_group": _create_view(
            stage, connect_instance,
            attribute_group["table"],
            name="Elevai Attribute Group",
            slug="attribute-group",
            description="Elevai view for managing attribute groups in data table",
            widget_id="DataTable_AttributeGroup",
            tags=tags,
        ),
    }

    # Create workspace
    workspace = _create_workspace(stage, connect_instance, views, tags)

    return {
        "data_tables": {
            "caller_status": caller_status,
            "brand": brand,
            "message_group": message_group,
            "attribute_group": attribute_group,
        },
        "views": views,
        "workspace": workspace,
    }


def create_bui_sample_flow(
    connect_instance: aws.connect.Instance,
    bui_resources: Dict[str, Any],
    tags: Dict[str, str],
) -> aws_native.connect.ContactFlow:
    """
    Create the Elevai Sample BUI contact flow.

    A standalone sample flow that demonstrates multi-table lookup routing
    using the BUI data tables. Can be assigned to a phone number directly.

    Args:
        connect_instance: The Amazon Connect instance.
        bui_resources: The BUI resources dict from create_bui_infrastructure().
        tags: Common tags to apply to resources.

    Returns:
        The created contact flow resource.
    """
    stage = pulumi.get_stack()

    flow_path = os.path.join(_CONTACT_FLOWS_DIR, "elevai-sample-bui.json")
    with open(flow_path, "r") as f:
        flow_template = f.read()

    tables = bui_resources["data_tables"]
    caller_table = tables["caller_status"]["table"]
    brand_table = tables["brand"]["table"]
    msg_table = tables["message_group"]["table"]
    ag_table = tables["attribute_group"]["table"]

    content = pulumi.Output.all(
        caller_table.arn,
        brand_table.arn,
        msg_table.arn,
        ag_table.arn,
    ).apply(lambda args: flow_template
        .replace("{{CALLER_TABLE_ARN}}", args[0])
        .replace("{{BRAND_TABLE_ARN}}", args[1])
        .replace("{{MESSAGE_GROUP_TABLE_ARN}}", args[2])
        .replace("{{ATTRIBUTE_GROUP_TABLE_ARN}}", args[3])
    )

    return aws_native.connect.ContactFlow(
        f"{stage}-cf-elevai-sample-bui",
        instance_arn=connect_instance.arn,
        name="Elevai Sample BUI",
        description="Elevai sample flow demonstrating multi-table lookup with brand, message group, and attribute routing",
        type="CONTACT_FLOW",
        content=content,
        state="ACTIVE",
        tags=[
            aws_native.TagArgs(key=k, value=v)
            for k, v in {**tags, "Name": "Elevai Sample BUI"}.items()
        ],
        opts=pulumi.ResourceOptions(
            depends_on=[caller_table, brand_table, msg_table, ag_table],
        ),
    )
