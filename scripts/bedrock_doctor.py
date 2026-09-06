"""Bedrock preflight: does this machine actually reach a Claude model?

Read only. It resolves credentials, checks the region, lists the inference
profiles the account can see, confirms the pinned models are among them, and
optionally makes one real token-billed call to prove the path end to end.

    python scripts/bedrock_doctor.py
    python scripts/bedrock_doctor.py --invoke     # one tiny real call
    python scripts/bedrock_doctor.py --json

Every failure names the fix. Nothing here writes to your AWS account.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

OK, WARN, FAIL = "OK", "WARN", "FAIL"
results: list[dict] = []


def check(name: str, status: str, detail: str = "", fix: str = "") -> None:
    results.append({"check": name, "status": status, "detail": detail, "fix": fix})


def load_env_file() -> None:
    """config/bedrock.env is the repo's own store; the environment wins."""
    env_file = REPO / "config" / "bedrock.env"
    if not env_file.exists():
        check("config/bedrock.env", WARN, "not found",
              "Copy config/bedrock.env.example to config/bedrock.env and fill "
              "it in, or set the variables in your shell.")
        return
    loaded = 0
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if v and k not in os.environ:
            os.environ[k] = v
            loaded += 1
    check("config/bedrock.env", OK, f"{loaded} variable(s) loaded")


def check_routing() -> None:
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") in ("1", "true", "True"):
        check("Bedrock routing", OK, "CLAUDE_CODE_USE_BEDROCK is set")
    else:
        check("Bedrock routing", FAIL, "CLAUDE_CODE_USE_BEDROCK is not set",
              "Without it Claude Code calls the Anthropic API, not Bedrock, "
              "and your Bedrock credentials are ignored. Set it to 1.")


def resolve_region() -> str | None:
    region = (os.environ.get("AWS_REGION")
              or os.environ.get("AWS_DEFAULT_REGION"))
    if region:
        check("Region", OK, f"{region} (from environment)")
        return region
    try:
        import boto3
        s = boto3.session.Session(
            profile_name=os.environ.get("AWS_PROFILE") or None)
        if s.region_name:
            check("Region", OK, f"{s.region_name} (from AWS profile)")
            return s.region_name
    except Exception:  # noqa: BLE001
        pass
    check("Region", WARN, "not set anywhere Claude Code will find it",
          "Claude Code falls back to us-east-1, which may not be where your "
          "model access lives. Set AWS_REGION.")
    return None


def check_credentials() -> str | None:
    """Exactly one credential form should be in play."""
    forms = []
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        forms.append("Bedrock API key")
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        forms.append("access key pair")
    if os.environ.get("AWS_PROFILE"):
        forms.append(f"profile {os.environ['AWS_PROFILE']}")

    if not forms:
        try:
            import boto3
            if boto3.session.Session().get_credentials():
                forms.append("default credential chain")
        except Exception:  # noqa: BLE001
            pass

    if not forms:
        check("Credentials", FAIL, "none found",
              "Set one of AWS_BEARER_TOKEN_BEDROCK, an access key pair, or "
              "AWS_PROFILE. See config/bedrock.env.example.")
        return None

    if len(forms) > 1:
        check("Credentials", WARN, " and ".join(forms),
              "More than one credential form is set. A Bedrock API key wins "
              "over the credential chain, which makes the effective identity "
              "hard to reason about. Leave one set.")
    else:
        check("Credentials", OK, forms[0])
    return forms[0]


def check_identity() -> None:
    """A bearer token has no STS identity, which is expected, not an error."""
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        check("AWS identity", OK,
              "not applicable, a Bedrock API key carries its own scope")
        return
    try:
        import boto3
        sts = boto3.client("sts")
        ident = sts.get_caller_identity()
        arn = ident.get("Arn", "")
        check("AWS identity", OK, f"{arn[:90]}")
    except Exception as exc:  # noqa: BLE001
        check("AWS identity", WARN, f"STS check failed: {type(exc).__name__}",
              "Not fatal on its own, but if the profile check below also "
              "fails, the credentials are the reason. For SSO run "
              "`aws sso login --profile <name>` first.")


def pinned_models() -> dict[str, str]:
    keys = ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL")
    return {k: os.environ[k] for k in keys if os.environ.get(k)}


def check_pinning() -> dict[str, str]:
    pins = pinned_models()
    if not pins:
        check("Model pinning", WARN, "nothing pinned",
              "Unpinned aliases resolve to Claude Code's built-in Bedrock "
              "default, which may not be enabled in your account and is an "
              "Opus-class model you will be billed for. Set ANTHROPIC_MODEL.")
    else:
        check("Model pinning", OK,
              ", ".join(f"{k.split('_')[-2].lower() if 'DEFAULT' in k else 'primary'}={v}"
                        for k, v in pins.items())[:120])
    return pins


def check_profiles(region: str | None, pins: dict[str, str]) -> None:
    if not region:
        return
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        check("Inference profiles", WARN, "boto3 not installed",
              "pip install boto3 to let this preflight see your account.")
        return

    try:
        client = boto3.client("bedrock", region_name=region)
        paginator = client.get_paginator("list_inference_profiles") \
            if client.can_paginate("list_inference_profiles") else None
        ids: list[str] = []
        if paginator:
            for page in paginator.paginate():
                ids += [p["inferenceProfileId"]
                        for p in page.get("inferenceProfileSummaries", [])]
        else:
            resp = client.list_inference_profiles()
            ids = [p["inferenceProfileId"]
                   for p in resp.get("inferenceProfileSummaries", [])]
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("AccessDeniedException", "UnauthorizedOperation"):
            check("Inference profiles", WARN,
                  "cannot list them: access denied",
                  "Add bedrock:ListInferenceProfiles to the policy (see "
                  "config/iam-policy.json). Claude Code still works without "
                  "it, but cannot verify a model before using it, so a wrong "
                  "model id fails at call time with a 400 instead.")
        else:
            check("Inference profiles", WARN, f"{code or type(exc).__name__}",
                  "Check the region and credentials.")
        return
    except Exception as exc:  # noqa: BLE001
        check("Inference profiles", WARN, f"{type(exc).__name__}: {exc}"[:110],
              "Check the region and credentials.")
        return

    claude = [i for i in ids if "anthropic" in i.lower()]
    if not claude:
        check("Inference profiles", FAIL,
              f"{len(ids)} profiles visible, none for Anthropic models",
              "Your account has Bedrock but no Claude model access in this "
              "region. Enable an Anthropic model in the Bedrock console model "
              "catalog and submit the use case form, or switch AWS_REGION.")
        return

    check("Inference profiles", OK,
          f"{len(claude)} Claude profile(s) visible in {region}")

    for key, model in pins.items():
        if model.startswith("arn:"):
            check(f"Pinned {key}", OK, "application inference profile ARN, "
                                       "not checked against the profile list")
            continue
        exact = model.split("[")[0]
        if any(exact == i or i.startswith(exact) for i in claude):
            check(f"Pinned {key}", OK, exact)
        else:
            near = [i for i in claude if exact.split(".")[-1][:18] in i]
            hint = f" Closest visible: {near[0]}." if near else ""
            check(f"Pinned {key}", FAIL, f"{exact} is not invocable here",
                  f"That profile is not in this account and region.{hint} "
                  f"List them with: aws bedrock list-inference-profiles "
                  f"--region {region}")


def check_websearch() -> None:
    """The one capability Bedrock silently removes."""
    check("WebSearch tool", WARN, "not available on Bedrock",
          "Claude Code's WebSearch tool does not work through Bedrock. The "
          "doc sync does not need it, since it reads local files. Skills that "
          "research the open web, the bulletin and CVE brief among them, lose "
          "that capability. See docs/BEDROCK.md.")


def smoke_test(region: str | None, pins: dict[str, str]) -> None:
    model = pins.get("ANTHROPIC_MODEL")
    if not region or not model:
        check("Live invocation", WARN, "skipped",
              "Needs AWS_REGION and ANTHROPIC_MODEL.")
        return
    try:
        import boto3
        rt = boto3.client("bedrock-runtime", region_name=region)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "Reply with the word: ready"}],
        })
        resp = rt.invoke_model(modelId=model.split("[")[0], body=body)
        payload = json.loads(resp["body"].read())
        text = "".join(b.get("text", "") for b in payload.get("content", []))
        usage = payload.get("usage", {})
        check("Live invocation", OK,
              f"model replied {text.strip()[:30]!r} "
              f"({usage.get('input_tokens', '?')} in, "
              f"{usage.get('output_tokens', '?')} out)")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        fix = ("Read the error above. 'AccessDeniedException' means the IAM "
               "policy or model access; 'ValidationException' naming the model "
               "usually means the id is not an inference profile in this "
               "region; 'on-demand throughput isn't supported' means you must "
               "use the inference profile id rather than the bare model id.")
        check("Live invocation", FAIL, f"{type(exc).__name__}: {msg[:130]}", fix)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--invoke", action="store_true",
                    help="make one real, token-billed call to prove the path")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    load_env_file()
    check_routing()
    region = resolve_region()
    check_credentials()
    check_identity()
    pins = check_pinning()
    check_profiles(region, pins)
    check_websearch()
    if a.invoke:
        smoke_test(region, pins)

    if a.json:
        print(json.dumps(results, indent=2))
    else:
        width = max(len(r["check"]) for r in results)
        print("CTI Documentation Sync — Bedrock preflight")
        print("=" * (width + 62))
        for r in results:
            print(f"  [{r['status']:4}] {r['check']:<{width}}  {r['detail']}")
        problems = [r for r in results if r["status"] in (WARN, FAIL)]
        if problems:
            print("\nFixes")
            print("-" * (width + 62))
            for r in problems:
                print(f"\n  {r['status']}  {r['check']}")
                print(f"       {r['fix']}")

    fails = sum(1 for r in results if r["status"] == FAIL)
    if not a.json:
        warns = sum(1 for r in results if r["status"] == WARN)
        print(f"\n{len(results)} checks, {fails} failing, {warns} warning.")
        if fails == 0 and not a.invoke:
            print("Config looks right. Prove it with: "
                  "python scripts/bedrock_doctor.py --invoke")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
