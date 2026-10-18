from pathlib import Path

from django.conf import settings
from django.core.checks import Warning, register


@register('evidence', deploy=True)
def evidence_vault_outside_code_directory(app_configs, **kwargs):
    """Evidence must live on persistent storage, not in the code directory a redeploy replaces."""
    vault = Path(getattr(settings, 'EVIDENCE_STORAGE_VAULT', None) or Path(settings.MEDIA_ROOT) / 'evidence_vault')
    vault = vault.resolve()
    base_dir = Path(settings.BASE_DIR).resolve()
    if vault == base_dir or base_dir in vault.parents:
        return [Warning(
            f"The evidence vault ({vault}) is inside the application directory ({base_dir}).",
            hint="Set MEDIA_ROOT or EVIDENCE_STORAGE_VAULT to a persistent volume outside the code directory, "
                 "so a redeploy cannot remove uploaded evidence.",
            id='evidence.W001',
        )]
    return []
