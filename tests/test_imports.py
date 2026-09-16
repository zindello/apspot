"""Runtime-compatibility smoke test.

Importing every *deployed* lambda module exercises module-level code
(env reads, client construction, syntax, stdlib usage). Running this under a
new interpreter (python3.12/3.13) is the fastest proof that a runtime bump
won't break the deploy: a removed stdlib module (e.g. distutils in 3.12) or a
syntax incompatibility surfaces here as an ImportError.
"""
import importlib

import pytest

# The modules wired up as functions in serverless.yml (empty stub files like
# search_sota.py / email_handler.py are intentionally excluded — not deployed).
DEPLOYED_MODULES = [
    "processmessage",
    "spot_pota",
    "spot_pnp",
    "spots_pota",
    "spots_sota",
    "spots_siota",
    "spots_wwff",
    "search_pota",
    "sns_sms",
    "sns_email",
]


@pytest.mark.parametrize("module_name", DEPLOYED_MODULES)
def test_module_imports(module_name):
    module = importlib.import_module(module_name)
    assert hasattr(module, "lambda_handler"), (
        f"{module_name} is missing a lambda_handler entry point"
    )
