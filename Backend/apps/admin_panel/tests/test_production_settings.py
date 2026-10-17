"""
Production settings must fail fast instead of starting in an unsafe configuration.

FIN-07 regression: before the fix, config.settings.production silently used the repository's SQLite file
(Backend/db.sqlite3) when DATABASE_URL was missing.
"""
import importlib
import os
import sys
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

PROD_ENV = {
    "DJANGO_SECRET_KEY": "k" * 64,
    "ALLOWED_HOSTS": "awards.example.gov.in",
    "DATABASE_URL": "postgres://u:p@db.example.gov.in:5432/nep",
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
}
_MODULES = ("config.settings.production", "config.settings.base")


def load_production_settings(drop=(), **extra_env):
    """Imports config.settings.production in isolation with a synthetic production environment."""
    env = {k: v for k, v in {**PROD_ENV, **extra_env}.items() if k not in drop}
    saved = {m: sys.modules.pop(m) for m in _MODULES if m in sys.modules}
    try:
        with mock.patch.dict(os.environ, env, clear=True), mock.patch("sys.argv", ["gunicorn", "config.wsgi"]):
            return importlib.import_module("config.settings.production")
    finally:
        for m in _MODULES:
            sys.modules.pop(m, None)
        sys.modules.update(saved)


class ProductionDatabaseConfigTests(SimpleTestCase):
    def test_missing_database_url_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(drop=("DATABASE_URL",))

    def test_sqlite_database_url_refused(self):
        for url in ("sqlite:///db.sqlite3", "sqlite:////tmp/x.sqlite3", "mysql://u:p@h/db"):
            with self.assertRaises(ImproperlyConfigured, msg=url):
                load_production_settings(DATABASE_URL=url)
        # An unparseable URL is rejected while parsing (dj_database_url raises a ValueError subclass).
        with self.assertRaises((ImproperlyConfigured, ValueError)):
            load_production_settings(DATABASE_URL="not-a-url")

    def test_postgres_database_url_used(self):
        prod = load_production_settings()
        db = prod.DATABASES["default"]
        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual((db["HOST"], db["NAME"]), ("db.example.gov.in", "nep"))
        self.assertNotIn("sqlite", str(db).lower())

    def test_test_runner_argv_cannot_downgrade_production_db(self):
        """base.py switches to SQLite (and the locmem SMS backend) when 'test' is in argv; production must either
        refuse to start or keep PostgreSQL, never run on SQLite."""
        env = {**PROD_ENV}
        saved = {m: sys.modules.pop(m) for m in _MODULES if m in sys.modules}
        try:
            with mock.patch.dict(os.environ, env, clear=True), mock.patch("sys.argv", ["manage.py", "test"]):
                try:
                    prod = importlib.import_module("config.settings.production")
                except ImproperlyConfigured:
                    return
            self.assertEqual(prod.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql")
        finally:
            for m in _MODULES:
                sys.modules.pop(m, None)
            sys.modules.update(saved)

    def test_existing_guards_still_hold(self):
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(drop=("DJANGO_SECRET_KEY",))
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(DJANGO_SECRET_KEY="django-insecure-" + "x" * 60)
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(drop=("ALLOWED_HOSTS",))
        with self.assertRaises(ImproperlyConfigured):
            load_production_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
        prod = load_production_settings()
        self.assertFalse(prod.DEBUG)
        self.assertFalse(prod.ENABLE_DJANGO_ADMIN)
