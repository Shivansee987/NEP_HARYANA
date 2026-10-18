from django.apps import AppConfig


class EvidenceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.evidence'
    verbose_name = 'NEP Evidence Management'

    def ready(self):
        from . import checks  # noqa: F401  (registers the deploy checks)
