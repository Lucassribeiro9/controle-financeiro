"""Testes do build de estaticos com o storage de manifesto de producao."""

import tempfile

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

PROD_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


class CollectstaticProductionTests(SimpleTestCase):
    """O collectstatic do build Docker nao pode quebrar por referencias soltas."""

    def test_collectstatic_with_manifest_storage_succeeds(self):
        """Todo arquivo de static/ deve resolver as proprias referencias.

        Regressao: o Chart.js vendorizado terminava com um sourceMappingURL
        para um .map ausente e o manifesto abortava o build de producao.
        """

        with tempfile.TemporaryDirectory() as static_root:
            with override_settings(STORAGES=PROD_STORAGES, STATIC_ROOT=static_root):
                call_command("collectstatic", interactive=False, verbosity=0)
