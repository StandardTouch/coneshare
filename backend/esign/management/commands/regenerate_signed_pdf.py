"""
Re-run signed PDF generation for a completed signature request (idempotent).

Usage:
  python manage.py regenerate_signed_pdf <request_ulid>
  python manage.py regenerate_signed_pdf <request_ulid> --sync
"""
from django.core.management.base import BaseCommand, CommandError

from esign.models import SignatureRequest
from esign.tasks import generate_signed_pdf_task


class Command(BaseCommand):
    help = "Regenerate the signed PDF (flatten fields + audit certificate) for a completed request."

    def add_arguments(self, parser):
        parser.add_argument("request_id", help="SignatureRequest ULID")
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Run inline in this process instead of Celery (uses task.run).",
        )
        parser.add_argument(
            "--notify",
            action="store_true",
            help="Also re-send completion notification emails (default: skip on regenerate).",
        )

    def handle(self, *args, **options):
        request_id = options["request_id"]
        try:
            signature_request = SignatureRequest.objects.get(pk=request_id)
        except SignatureRequest.DoesNotExist as exc:
            raise CommandError(f"Signature request not found: {request_id}") from exc

        if signature_request.status != "completed":
            raise CommandError(
                f"Request {request_id} is not completed (status={signature_request.status})."
            )

        send_emails = bool(options["notify"])
        if options["sync"]:
            generate_signed_pdf_task.run(request_id, send_completion_emails=send_emails)
            self.stdout.write(
                self.style.SUCCESS(f"Regenerated signed PDF synchronously for {request_id}")
            )
        else:
            generate_signed_pdf_task.delay(request_id, send_completion_emails=send_emails)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Queued regenerate_signed_pdf Celery task for {request_id}"
                )
            )
