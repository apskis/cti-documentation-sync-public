"""Verify that all mapped credentials resolve from Azure Key Vault.

Usage:
    python scripts/fetch_secrets.py --list    # show all vault secrets and mapping status
    python scripts/fetch_secrets.py --check   # verify all mapped secrets resolve
"""

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAP_PATH = REPO / "config" / "secrets-map.json"
ENV_PATH = REPO / ".env"

OPTIONAL_KEYS = frozenset({
    "AWS_BEARER_TOKEN_BEDROCK",
    "CLAROTY_API_HOST",
    "RAPID7_REGION",
})


def _load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _get_client():
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    vault_url = os.environ.get("KEY_VAULT_URL", "").strip()
    if not vault_url:
        print("ERROR: KEY_VAULT_URL not set. Check .env", file=sys.stderr)
        sys.exit(1)

    return SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())


def _load_map():
    if not MAP_PATH.exists():
        print(f"ERROR: {MAP_PATH} not found", file=sys.stderr)
        sys.exit(1)
    data = json.loads(MAP_PATH.read_text())
    return {k: v for k, v in data.items() if not k.startswith("_")}


def cmd_list():
    _load_env()
    client = _get_client()
    secret_map = _load_map()

    vault_names = set()
    print("\n--- Secrets in vault ---")
    for prop in client.list_properties_of_secrets():
        vault_names.add(prop.name)
        print(f"  {prop.name}")

    mapped_vault_names = set(secret_map.values())
    unmapped = vault_names - mapped_vault_names
    missing = mapped_vault_names - vault_names

    print(f"\n--- Mapped ({len(secret_map)}) ---")
    for env_var, vault_name in sorted(secret_map.items()):
        status = "OK" if vault_name in vault_names else "NOT IN VAULT"
        print(f"  {env_var:30s} -> {vault_name:30s}  [{status}]")

    if unmapped:
        print(f"\n--- In vault but not mapped ({len(unmapped)}) ---")
        for name in sorted(unmapped):
            print(f"  {name}")

    if missing:
        print(f"\n--- Mapped but not in vault ({len(missing)}) ---")
        for name in sorted(missing):
            print(f"  {name}")

    print()


def cmd_check():
    _load_env()
    client = _get_client()
    secret_map = _load_map()
    from azure.core.exceptions import ResourceNotFoundError

    ok = 0
    skipped = 0
    failed = 0

    for env_var, vault_name in sorted(secret_map.items()):
        try:
            secret = client.get_secret(vault_name)
            if secret.value:
                ok += 1
            else:
                if env_var in OPTIONAL_KEYS:
                    print(f"  SKIP  {env_var} ({vault_name}) — empty, optional")
                    skipped += 1
                else:
                    print(f"  FAIL  {env_var} ({vault_name}) — exists but empty")
                    failed += 1
        except ResourceNotFoundError:
            if env_var in OPTIONAL_KEYS:
                print(f"  SKIP  {env_var} ({vault_name}) — not found, optional")
                skipped += 1
            else:
                print(f"  FAIL  {env_var} ({vault_name}) — not found in vault")
                failed += 1
        except Exception as e:
            print(f"  FAIL  {env_var} ({vault_name}) — {type(e).__name__}: {e}")
            failed += 1

    print()
    if failed == 0:
        print(f"All mapped credentials resolved. {ok} OK, {skipped} optional skipped.")
        print("No values were printed.")
    else:
        print(f"{ok} OK, {skipped} optional skipped, {failed} FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("--list", "--check"):
        print("Usage: python scripts/fetch_secrets.py --list | --check")
        sys.exit(1)

    if sys.argv[1] == "--list":
        cmd_list()
    else:
        cmd_check()
