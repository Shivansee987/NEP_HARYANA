"""
Management command: create_dev_users
=====================================
Seeds development login accounts for all roles.
Safe to run multiple times (idempotent -- updates passwords on re-run).

Usage:
    python manage.py create_dev_users

DO NOT run in production. Guard is enforced via DEBUG check.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

SEP = "-" * 62

DEV_USERS = [
    # --- DHE Admin ---
    {
        "email": "admin@dev.local",
        "password": "DevAdmin@123",
        "full_name": "Dev Admin",
        "role": "admin",
        "is_staff": True,
        "is_superuser": True,
        "college": None,
        "university": None,
    },
    # --- Screening Committee ---
    {
        "email": "committee@dev.local",
        "password": "DevCommittee@123",
        "full_name": "Dev Committee Member",
        "role": "committee",
        "is_staff": False,
        "is_superuser": False,
        "college": None,
        "university": None,
    },
    # --- Committee Chair ---
    {
        "email": "chair@dev.local",
        "password": "DevChair@123",
        "full_name": "Dev Committee Chair",
        "role": "committee_chair",
        "is_staff": False,
        "is_superuser": False,
        "college": None,
        "university": None,
    },
    # --- College Principal ---
    {
        "email": "principal@dev.local",
        "password": "DevPrincipal@123",
        "full_name": "Dev Principal",
        "role": "principal",
        "is_staff": False,
        "is_superuser": False,
        "college": "__DEV_COLLEGE__",
        "university": None,
    },
    # --- University Nodal Officer ---
    {
        "email": "nodal@dev.local",
        "password": "DevNodal@123",
        "full_name": "Dev Nodal Officer",
        "role": "nodal_officer",
        "is_staff": False,
        "is_superuser": False,
        "college": None,
        "university": "__DEV_UNIVERSITY__",
    },
    # --- University Admin ---
    {
        "email": "univadmin@dev.local",
        "password": "DevUnivAdmin@123",
        "full_name": "Dev University Admin",
        "role": "university_admin",
        "is_staff": False,
        "is_superuser": False,
        "college": None,
        "university": "__DEV_UNIVERSITY__",
    },
]

DEV_COLLEGE = {
    "name": "Dev Test College",
    "aishe_code": "DEV-COLLEGE-001",
}

DEV_UNIVERSITY = {
    "name": "Dev Test University",
}


class Command(BaseCommand):
    help = "Seed development login accounts for all roles (localhost only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running even if DEBUG=False (use with care).",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Refusing to run in production (DEBUG=False). "
                "Pass --force to override."
            )

        from apps.authentication.models import User, College
        from apps.university.models import University

        self.stdout.write(self.style.MIGRATE_HEADING("\n[*] NEP Haryana -- Dev User Seeder"))
        self.stdout.write(SEP)

        with transaction.atomic():
            dev_college = self._get_or_create_college(College)
            dev_university = self._get_or_create_university(University)

            created_count = 0
            updated_count = 0

            for spec in DEV_USERS:
                college_obj = dev_college if spec["college"] == "__DEV_COLLEGE__" else None
                university_obj = dev_university if spec["university"] == "__DEV_UNIVERSITY__" else None

                user, created = User.objects.get_or_create(
                    email=spec["email"],
                    defaults={
                        "full_name": spec["full_name"],
                        "role": spec["role"],
                        "is_staff": spec["is_staff"],
                        "is_superuser": spec["is_superuser"],
                        "college": college_obj,
                        "university": university_obj,
                        "is_active": True,
                    },
                )

                # Always reset password so re-runs are safe
                user.set_password(spec["password"])
                if not created:
                    user.full_name = spec["full_name"]
                    user.role = spec["role"]
                    user.is_staff = spec["is_staff"]
                    user.is_superuser = spec["is_superuser"]
                    user.college = college_obj
                    user.university = university_obj
                    user.is_active = True
                user.save()

                status = self.style.SUCCESS("CREATED") if created else self.style.WARNING("UPDATED")
                self.stdout.write(
                    "  [{}] {:<35} role={}".format(status, spec["email"], spec["role"])
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(SEP)
        self.stdout.write(
            self.style.SUCCESS(
                "\nDone. {} created, {} updated.\n".format(created_count, updated_count)
            )
        )
        self._print_credentials()

    def _get_or_create_college(self, College):
        college, created = College.objects.get_or_create(
            aishe_code=DEV_COLLEGE["aishe_code"],
            defaults={"name": DEV_COLLEGE["name"]},
        )
        action = "CREATED" if created else "exists"
        self.stdout.write("  College ({}): {} [{}]".format(action, college.name, college.aishe_code))
        return college

    def _get_or_create_university(self, University):
        university, created = University.objects.get_or_create(
            name=DEV_UNIVERSITY["name"],
        )
        action = "CREATED" if created else "exists"
        self.stdout.write("  University ({}): {}".format(action, university.name))
        return university

    def _print_credentials(self):
        self.stdout.write(self.style.MIGRATE_HEADING("[KEY] Dev Login Credentials"))
        self.stdout.write(SEP)
        rows = [
            ("Role",             "Email",                     "Password"),
            ("-" * 18,          "-" * 30,                    "-" * 20),
            ("admin",            "admin@dev.local",           "DevAdmin@123"),
            ("committee",        "committee@dev.local",       "DevCommittee@123"),
            ("committee_chair",  "chair@dev.local",           "DevChair@123"),
            ("principal",        "principal@dev.local",       "DevPrincipal@123"),
            ("nodal_officer",    "nodal@dev.local",           "DevNodal@123"),
            ("university_admin", "univadmin@dev.local",       "DevUnivAdmin@123"),
        ]
        for role, email, pw in rows:
            self.stdout.write("  {:<20} {:<32} {}".format(role, email, pw))
        self.stdout.write("")
        self.stdout.write("  Frontend:     http://localhost:5173")
        self.stdout.write("  Backend API:  http://localhost:8000/api")
        self.stdout.write("  Django Admin: http://localhost:8000/admin")
        self.stdout.write(SEP + "\n")
