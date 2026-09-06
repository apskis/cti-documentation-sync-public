# Rebuilding the CTI documentation sync on your own infrastructure

This is a sanitized public copy. The organization is **GeneLabs LLC**, a fictional
company. Every value that pointed at a real environment has been replaced with a
placeholder in angle brackets. Nothing here will run until you set them.

Find everything still outstanding with:

```bash
grep -rn "<your-" . ; grep -rn "<ACCOUNT_ID>" . ; grep -rn "<GAP-NN>" .
```

## 1. Cloud and model provider

| Placeholder | Set to |
| --- | --- |
| `<ACCOUNT_ID>` | Your AWS account id, in the Bedrock IAM policy documents |
| `<your-security-account>` | The account alias you run this from |
| `<your-cybersecurity-role>` | The IAM role your federated login assumes |
| `<you>@genelabs.example` | Your own principal, in the example `sts get-caller-identity` output |

## 2. Secret storage

| Placeholder | Set to |
| --- | --- |
| `<your-keyvault>` | Your Azure Key Vault name, or swap the vault client for your own secret store |
| `<your-splunk-token>` | Held in the vault, never in the repo |

The secret **names** are unchanged and are the setup contract: create a secret per
name, in your own vault, and the launchers resolve them at run time.

## 3. Connected platforms

| Placeholder | Set to |
| --- | --- |
| `<your-stack>.splunkcloud.com` | Your Splunk Cloud stack |
| `<your-tenant>.threatq.online` | Your ThreatQ tenant |
| `<your-instance>.service-now.com` | Your ServiceNow instance |
| `<your-tenant>.sharepoint.com` | Your SharePoint tenant, for deliverable paths |
| `C:/Users/<user>/...` | Your local deliverable folders in `config.yaml` |

## 4. The Splunk data model map — measure it, do not inherit it

`skills/genelabs-splunk-spl/SKILL.md` ships as a **template**. The index to
sourcetype map and the data model reality table contain no measured values, on
purpose: a borrowed coverage map is worse than none, because it reads as
authoritative while describing someone else's environment.

Run the discovery searches against your own Splunk, fill both tables with what you
observe, date every row, and give each finding a `<GAP-NN>` id in your own gap
register. Control test any data model before you build a hunt on it. A model that
is empty or partially accelerated returns **zero with no error**, which is
indistinguishable from a true negative unless you have measured it.

## 5. Example content is fictional

The exposure rows in `tools/build_exposure_briefing.py`, the asset maps in
`config.yaml`, and the advisory ids are illustrative. Hostnames follow a fictional
GeneLabs scheme and every address is in the RFC 5737 documentation range
(`203.0.113.0/24`), which is unroutable by design. Replace them with your own
findings.

## 6. Assets not included

Branded document templates, banner images, wordmarks and example documents were
removed. The builders expect files at those paths, so supply your own before
generating a document. Every skill directory lists what it needs under `assets/`.
