"""Raise the run summary where April will actually see it.

This replaces the push notification that the Claude scheduled task used to send.
Local runs have no push channel, so notification is: a desktop toast on Windows,
and optionally a message to a Teams or Slack incoming webhook.

    python scripts/notify.py --title "CTI doc sync" --report runs/2026-09-01-doc-sync.md
    python scripts/notify.py --title "CTI doc sync" --message "3 documents updated"

Set CTI_NOTIFY_WEBHOOK to a Teams or Slack incoming webhook URL to also post
there. Nothing is sent anywhere unless that variable is set.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import urllib.request
from pathlib import Path

BANNER_CHARS = 220


def first_paragraph(text: str) -> str:
    for block in text.split("\n\n"):
        line = " ".join(
            l.strip() for l in block.strip().splitlines()
            if l.strip() and not l.strip().startswith("#")
        )
        if line:
            return line
    return text.strip()[:BANNER_CHARS]


def toast(title: str, body: str) -> bool:
    if platform.system() != "Windows":
        return False
    body = body.replace('"', "'")[:BANNER_CHARS]
    ps = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$x = $t.GetElementsByTagName("text")
$x.Item(0).AppendChild($t.CreateTextNode("{title}")) | Out-Null
$x.Item(1).AppendChild($t.CreateTextNode("{body}")) | Out-Null
$n = [Windows.UI.Notifications.ToastNotification]::new($t)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("CTI Documentation Sync").Show($n)
'''
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", ps],
            check=True, capture_output=True, timeout=30,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"toast failed: {exc}", file=sys.stderr)
        return False


def webhook(title: str, body: str) -> bool:
    url = os.environ.get("CTI_NOTIFY_WEBHOOK")
    if not url:
        return False
    payload = {"text": f"**{title}**\n\n{body}"}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"webhook failed: {exc}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--title", default="CTI Documentation Sync")
    ap.add_argument("--message")
    ap.add_argument("--report", help="path to a run report; its first "
                                     "paragraph becomes the notification body")
    a = ap.parse_args()

    if a.report:
        text = Path(a.report).read_text(encoding="utf-8")
        body_full = text
        body_short = first_paragraph(text)
    elif a.message:
        body_full = body_short = a.message
    else:
        print("ERROR pass --message or --report", file=sys.stderr)
        return 1

    print(f"== {a.title} ==")
    print(body_full)

    sent = []
    if toast(a.title, body_short):
        sent.append("desktop toast")
    if webhook(a.title, body_full):
        sent.append("webhook")
    print(f"\nnotified via: {', '.join(sent) if sent else 'console only'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
