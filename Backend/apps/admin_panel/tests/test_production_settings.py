"""
Production settings must fail fast instead of starting in an unsafe configuration.

FIN-07 regression: before the fix, config.settings.production silently used the repository's SQLite file
(Backend/db.sqlite3) when DATABASE_URL was missing.
"""
import importlib
import os
import sys
from pathlib import Path
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

PROD_ENV = {
    "DJANGO_SECRET_KEY": "k" * 64,
    "ALLOWED_HOSTS": "awards.example.gov.in",
    "DATABASE_URL": "postgres://u:p@db.example.gov.in:5432/nep",
    "REDIS_URL": "redis://127.0.0.1:6379/0",
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


class ProductionDeploymentConfigTests(SimpleTestCase):
    """VM deployment gaps G2-G5 (docs/deployment/VM_SERVER_REQUIREMENTS.md)."""

    def test_missing_redis_url_refuses_to_start(self):
        for env in ({"drop": ("REDIS_URL",)}, {"REDIS_URL": ""}, {"REDIS_URL": "localhost:6379"}):
            drop = env.pop("drop", ())
            with self.assertRaises(ImproperlyConfigured, msg=str(env or drop)):
                load_production_settings(drop=drop, **env)

    def test_redis_url_selects_shared_redis_cache(self):
        for url in ("redis://127.0.0.1:6379/0", "rediss://:pw@cache.example.gov.in:6380/1"):
            cache = load_production_settings(REDIS_URL=url).CACHES["default"]
            self.assertEqual(cache["BACKEND"], "django.core.cache.backends.redis.RedisCache")
            self.assertEqual(cache["LOCATION"], url)

    def test_localhost_cors_origins_dropped(self):
        prod = load_production_settings(
            FRONTEND_URL="https://awards.example.gov.in",
            CORS_ALLOWED_ORIGINS="https://admin.example.gov.in,http://localhost:3000,http://127.0.0.1:8080",
        )
        self.assertEqual(prod.CORS_ALLOWED_ORIGIN_REGEXES, [])
        self.assertEqual(prod.CORS_ALLOWED_ORIGINS, ["https://awards.example.gov.in", "https://admin.example.gov.in"])

    def test_logging_goes_to_stderr(self):
        logging_cfg = load_production_settings(LOG_LEVEL="warning").LOGGING
        self.assertEqual(logging_cfg["handlers"]["console"]["class"], "logging.StreamHandler")
        self.assertEqual(logging_cfg["root"], {"handlers": ["console"], "level": "WARNING"})
        self.assertFalse(logging_cfg["disable_existing_loggers"])

    def test_static_and_evidence_paths(self):
        prod = load_production_settings()
        self.assertEqual(prod.STATIC_ROOT, prod.BASE_DIR / "staticfiles")
        self.assertEqual(prod.EVIDENCE_STORAGE_VAULT, prod.BASE_DIR / "media" / "evidence_vault")

        prod = load_production_settings(MEDIA_ROOT="/srv/nep/media", STATIC_ROOT="/srv/nep/static")
        self.assertEqual(str(prod.STATIC_ROOT), str(Path("/srv/nep/static")))
        self.assertEqual(str(prod.EVIDENCE_STORAGE_VAULT), str(Path("/srv/nep/media/evidence_vault")))

        prod = load_production_settings(MEDIA_ROOT="/srv/nep/media", EVIDENCE_STORAGE_VAULT="/data/evidence")
        self.assertEqual(str(prod.EVIDENCE_STORAGE_VAULT), str(Path("/data/evidence")))


class EvidenceVaultDeployCheckTests(SimpleTestCase):
    def _run(self):
        from apps.evidence.checks import evidence_vault_outside_code_directory
        return [m.id for m in evidence_vault_outside_code_directory(None)]

    def test_warns_when_vault_is_inside_code_directory(self):
        from django.conf import settings
        with self.settings(EVIDENCE_STORAGE_VAULT=Path(settings.BASE_DIR) / "media" / "evidence_vault"):
            self.assertEqual(self._run(), ["evidence.W001"])

    def test_silent_when_vault_is_on_separate_volume(self):
        from django.conf import settings
        outside = Path(settings.BASE_DIR).resolve().parent / "nep-persistent-volume" / "evidence_vault"
        with self.settings(EVIDENCE_STORAGE_VAULT=outside):
            self.assertEqual(self._run(), [])
