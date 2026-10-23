from django.core.management.base import BaseCommand

from apps.workflows.models import Edge, Node, Trigger, Workflow, WorkflowVersion

EXAMPLES = [
    {
        "name": "Simple Math Transform",
        "slug": "simple-math-transform",
        "description": "Multiply price and quantity, add tax, and return a formatted total.",
        "input_schema": {
            "type": "object",
            "properties": {
                "price": {"type": "number"},
                "quantity": {"type": "integer"},
            },
            "required": ["price", "quantity"],
        },
        "nodes": [
            {
                "key": "multiply",
                "name": "Multiply",
                "node_type": "transform",
                "config": {"code": "result = {'subtotal': data['price'] * data['quantity']}"},
            },
            {
                "key": "add_tax",
                "name": "Add Tax",
                "node_type": "transform",
                "config": {
                    "code": "result = {'total': data['subtotal'] * 1.2, 'tax': data['subtotal'] * 0.2}"
                },
            },
        ],
        "edges": [("multiply", "add_tax")],
    },
    {
        "name": "Data Enrichment",
        "slug": "data-enrichment",
        "description": "Normalize a contact payload and enrich it with a summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "name": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["email", "name"],
        },
        "nodes": [
            {
                "key": "normalize",
                "name": "Normalize",
                "node_type": "transform",
                "config": {
                    "code": "result = {'email': data['email'].strip().lower(), 'name': data['name'].strip().title(), 'tags': data.get('tags', [])}"
                },
            },
            {
                "key": "enrich",
                "name": "Enrich",
                "node_type": "transform",
                "config": {
                    "code": "result = {'summary': {'email': data['email'], 'name': data['name'], 'tag_count': len(data['tags'])}, 'active': True}"
                },
            },
        ],
        "edges": [("normalize", "enrich")],
    },
    {
        "name": "Order Processing Pipeline",
        "slug": "order-processing-pipeline",
        "description": "Multi-step pipeline that validates, enriches, discounts, and formats an order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order": {
                    "type": "object",
                    "properties": {
                        "customer": {"type": "string"},
                        "total": {"type": "number"},
                    },
                    "required": ["customer", "total"],
                }
            },
            "required": ["order"],
        },
        "nodes": [
            {
                "key": "validate",
                "name": "Validate",
                "node_type": "transform",
                "config": {
                    "code": "result = {'order': data['order'], 'valid': data['order'].get('total', 0) > 0}"
                },
            },
            {
                "key": "enrich",
                "name": "Enrich",
                "node_type": "transform",
                "config": {
                    "code": "result = {'customer': helpers.get(data, 'order.customer', 'unknown'), 'total': helpers.get(data, 'order.total', 0)}"
                },
            },
            {
                "key": "discount",
                "name": "Apply Discount",
                "node_type": "transform",
                "config": {
                    "code": "total = data['total']\ndiscount = total * 0.1 if total > 100 else 0\nresult = {'discount': discount, 'final_total': total - discount}"
                },
            },
            {
                "key": "format",
                "name": "Format Receipt",
                "node_type": "transform",
                "config": {
                    "code": "result = {'receipt': {'customer': data['customer'], 'total': data['total'], 'discount': data['discount'], 'final_total': data['final_total']}}"
                },
            },
        ],
        "edges": [("validate", "enrich"), ("enrich", "discount"), ("discount", "format")],
    },
]


class Command(BaseCommand):
    help = "Load (or update) demonstration workflows."

    def handle(self, *args, **options):
        created = []
        updated = []

        for example in EXAMPLES:
            workflow, was_created = Workflow.objects.get_or_create(
                slug=example["slug"],
                defaults={
                    "name": example["name"],
                    "description": example["description"],
                    "is_active": True,
                    "is_public": True,
                },
            )
            if not was_created:
                workflow.name = example["name"]
                workflow.description = example["description"]
                workflow.is_active = True
                workflow.is_public = True
                workflow.save()
                updated.append(workflow)
            else:
                created.append(workflow)

            version, _ = WorkflowVersion.objects.get_or_create(
                workflow=workflow,
                version_number=1,
                defaults={"is_published": True, "definition": {}},
            )
            version.is_published = True
            version.save(update_fields=["is_published"])

            # Reset nodes/edges/triggers for idempotency.
            version.nodes.all().delete()
            workflow.triggers.all().delete()

            node_map = {}
            for node_data in example["nodes"]:
                node = Node.objects.create(
                    workflow_version=version,
                    key=node_data["key"],
                    name=node_data["name"],
                    node_type=node_data["node_type"],
                    config=node_data["config"],
                    input_schema=example["input_schema"]
                    if node_data["key"] == example["nodes"][0]["key"]
                    else {},
                )
                node_map[node.key] = node

            for source_key, target_key in example["edges"]:
                Edge.objects.create(
                    workflow_version=version,
                    source_node=node_map[source_key],
                    target_node=node_map[target_key],
                )

            Trigger.objects.create(
                workflow=workflow,
                trigger_type="webhook",
                is_active=True,
                config={"input_schema": example["input_schema"]},
            )

        self.stdout.write(self.style.SUCCESS("Example workflows loaded."))
        for workflow in created:
            self.stdout.write(f"  Created: {workflow.name} -> /hooks/{workflow.slug}/")
        for workflow in updated:
            self.stdout.write(f"  Updated: {workflow.name} -> /hooks/{workflow.slug}/")
        if not created and not updated:
            self.stdout.write("  No changes.")
