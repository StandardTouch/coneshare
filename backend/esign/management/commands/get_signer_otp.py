"""Print latest OTP code for a signer email (E2E helper)."""
import json
import sys

from django.core.management.base import BaseCommand

from esign.models import SignatureOTP, Signer


class Command(BaseCommand):
    help = "Get latest unverified OTP for esign E2E."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)

    def handle(self, *args, **options):
        email = options["email"]
        signer = Signer.objects.filter(user__email=email).order_by("-created_at").first()
        if not signer:
            self.stderr.write("Signer not found\n")
            sys.exit(1)
        otp = (
            SignatureOTP.objects.filter(signer=signer, verified=False)
            .order_by("-created_at")
            .first()
        )
        payload = {"token": signer.token}
        if otp:
            payload["code"] = otp.code
        self.stdout.write(json.dumps(payload))
