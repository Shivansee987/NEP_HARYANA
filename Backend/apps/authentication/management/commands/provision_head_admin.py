"""
Backend-controlled management command for provisioning and protecting the Head Administrator.
Usage:
    python manage.py provision_head_admin --email admin@dhe.haryana.gov.in --name "Head Admin" --password "SecureSecretPass123!"
Or in non-interactive/automated pipelines:
    HEAD_ADMIN_PASSWORD="MySecurePassword!" python manage.py provision_head_admin --email admin@dhe.haryana.gov.in
"""
import getpass
import os
import secrets
import string

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from apps.authentication.models import User, UserAuditLog


class Command(BaseCommand):
    help = "Securely provision the Head Administrator account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email address of the Head Administrator.",
        )
        parser.add_argument(
            "--name",
            type=str,
            default="Head Administrator",
            help="Full name of the Head Administrator.",
        )
        parser.add_argument(
            "--password",
            type=str,
            default=None,
            help="Password for the account. If omitted, checks HEAD_ADMIN_PASSWORD or prompts.",
        )
        parser.add_argument(
            "--phone",
            type=str,
            default="",
            help="Optional contact mobile number.",
        )
        parser.add_argument(
            "--non-interactive",
            action="store_true",
            help="Generate a secure temporary password if none provided.",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        full_name = options["name"].strip()
        phone = options["phone"].strip()
        password = options.get("password")
        non_interactive = options.get("non_interactive", False)

        try:
            validate_email(email)
        except ValidationError:
            raise CommandError(f"Invalid email address format: '{email}'")

        if not password:
            password = os.environ.get("HEAD_ADMIN_PASSWORD")

        generated = False
        if not password:
            if non_interactive or not os.isatty(0):
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                password = "".join(secrets.choice(alphabet) for _ in range(16))
                generated = True
            else:
                password = getpass.getpass("Enter password for Head Administrator: ")
                confirm = getpass.getpass("Confirm password: ")
                if password != confirm:
                    raise CommandError("Passwords do not match.")

        if len(password) < 8:
            raise CommandError("Password must be at least 8 characters long.")

        user = User.objects.filter(email__iexact=email).first()
        is_created = False

        if user:
            user.full_name = full_name
            user.role = "head_admin"
            user.is_staff = True
            # Head Admin authority is the application role. It is never a Django superuser, so it carries no
            # implicit model-level powers outside the governed API (FIN-01).
            user.is_superuser = False
            user.is_active = True
            if phone:
                user.phone_number = phone
            user.set_password(password)
            user.save()
            action_desc = "Updated existing user and promoted to Head Administrator"
        else:
            user = User.objects.create_user(
                email=email,
                full_name=full_name,
                role="head_admin",
                password=password,
                phone_number=phone,
                is_staff=True,
                is_superuser=False,
                is_active=True,
            )
            is_created = True
            action_desc = "Created new Head Administrator user"

        # Record audit log
        UserAuditLog.objects.create(
            actor=None,
            target_user=user,
            action="HEAD_ADMIN_PROVISIONED",
            details={
                "provision_method": "CLI_COMMAND",
                "email": email,
                "is_created": is_created,
                "role": "head_admin",
            },
        )

        self.stdout.write(self.style.SUCCESS(f"Successfully provisioned Head Admin '{email}'. ({action_desc})"))
        if generated:
            self.stdout.write(self.style.WARNING(f"Generated Temporary Password: {password}"))
            self.stdout.write(self.style.WARNING("Please store this securely and update on first login."))
