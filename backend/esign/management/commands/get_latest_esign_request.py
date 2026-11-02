"""Print latest signature request metadata for E2E verification."""
import json

from django.core.management.base import BaseCommand

from esign.models import SignatureRequest


class Command(BaseCommand):
    help = "Get latest signature request id for E2E."

    def handle(self, *args, **options):
        req = SignatureRequest.objects.order_by("-created_at").first()
        if not req:
            self.stderr.write("No request\n")
            return
        self.stdout.write(
            json.dumps(
                {
                    "id": req.id,
                    "status": req.status,
                    "document_id": req.document_id,
                }
            )
        )
