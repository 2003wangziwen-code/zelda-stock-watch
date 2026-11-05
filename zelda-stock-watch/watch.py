#!/usr/bin/env python3
"""Fail-closed rental-stock watcher: alert only for the MAIN account."""
import json
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

URL = "https://manygames.cn/games/library/cmw0iuzvc00gj01novq1f8s0d"
GAME = "塞尔达传说：时之笛"
STATE_FILE = Path(__file__).parent / "state.json"
OUT = re.compile(r"已售罄|暂无库存|无库存|库存不足|暂时缺货|缺货|无货|不可租|售罄")
IN = re.compile(r"可租|有货|现货|可用|库存\s*[1-9]\d*|剩余\s*[1-9]\d*")


def parse_main_label(label, enabled=True):
    """Returns 'available', 'sold_out', or 'unknown'.

    In particular, '副号可租' and joint '主号/副号可租' are NEVER positive.
    """
    s = re.sub(r"\s+", " ", label).replace("（", "(").replace("）", ")")
    hits = list(re.finditer(r"(?<!副)主号", s))
    if not hits:
        return "unknown"
    for hit in hits:
        after = s[hit.end():hit.end() + 35]
        after = after.lstrip(" :：(-")
        deputy = re.search("副号", after)
        out = OUT.search(after)
        available = IN.search(after)
        # If the next stock description is for deputy, do not attribute it to main.
        if deputy and (not out or deputy.start() < out.start()) and (
            not available or deputy.start() < available.start()
        ):
            continue
        if out and (not deputy or out.start() < deputy.start()):
            return "sold_out"
        if available and (not deputy or available.start() < deputy.start()):
            return "available" if enabled else "sold_out"
        if enabled is False:
            return "sold_out"
    return "unknown"


def detect_stock(page):
    body = page.locator("body").inner_text(timeout=15000)
    if GAME not in body:
        print("Unknown: game title absent in rendered page.")
        return "unknown"
    statuses = []
    option_selector = "button, label, [role='option'], [role='radio'], [role='button']"
    for item in page.locator(option_selector).all()[:250]:
        try:
            label = item.inner_text(timeout=1200).strip()
            if not label or len(label) > 140 or "主号" not in label or "副号" in label:
                continue
            enabled = item.is_enabled()
            status = parse_main_label(label, enabled)
            print(f"Option: {label[:70]!r}, enabled={enabled}, status={status}")
            if status != "unknown":
                statuses.append(status)
        except Exception:
            continue
    # The same label may appear as plain page text rather than an option.
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if "主号" not in line or "副号" in line or len(line) > 90:
            continue
        status = parse_main_label(line)
        if status == "unknown" and i + 1 < len(lines) and "副号" not in lines[i + 1]:
            status = parse_main_label(line + " " + lines[i + 1])
        if status != "unknown":
            statuses.append(status)
    if "sold_out" in statuses:
        return "sold_out"
    if "available" in statuses:
        return "available"
    print("Unknown: could not establish an explicit MAIN-account stock label.")
    return "unknown"


def fetch_status():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True, args=["--disable-dev-shm-usage"])
        context = browser.new_context(locale="zh-CN", timezone_id="Asia/Shanghai")
        page = context.new_page()
        try:
            response = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            if not response or response.status >= 400:
                print(f"Unknown: HTTP {response.status if response else 'no response'}")
                return "unknown"
            # Wait for asynchronous stock controls, without treating a timeout as available.
            try:
                page.get_by_text("主号", exact=False).first.wait_for(timeout=12000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
            return detect_stock(page)
        except Exception as exc:
            print(f"Unknown: page load/detection error: {type(exc).__name__}: {exc}")
            return "unknown"
        finally:
            context.close()
            browser.close()


def email_alert():
    username = os.environ.get("ZELDA_SMTP_USER", "")
    password = os.environ.get("ZELDA_SMTP_APP_PASSWORD", "")
    recipient = os.environ.get("ZELDA_EMAIL_TO", "")
    if not username or not password or not recipient:
        raise RuntimeError("Missing ZELDA_SMTP_USER, ZELDA_SMTP_APP_PASSWORD, or ZELDA_EMAIL_TO")
    host = os.environ.get("ZELDA_SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("ZELDA_SMTP_PORT") or "465")
    checked_at = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    mail = EmailMessage()
    mail["Subject"] = "【主号补货提醒】塞尔达传说：时之笛"
    mail["From"] = username
    mail["To"] = recipient
    mail.set_content(
        f"监控页面检测到《塞尔达传说：时之笛》的“主号”出现明确可租标识。\n"
        f"检查时间（北京时间）：{checked_at}\n"
        f"立即查看：{URL}\n\n"
        "库存会随时变化，请以打开页面后的实际可租状态为准。"
    )
    with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
        smtp.login(username, password)
        smtp.send_message(mail)
    return checked_at


def main():
    if STATE_FILE.exists():
        saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if saved.get("notified"):
            print("Previously notified: no further mail.")
            return
    status = fetch_status()
    print(f"Main account status: {status}")
    if status != "available":
        return
    if os.getenv("DRY_RUN", "0") == "1":
        print("DRY_RUN: available, but no email/state change.")
        return
    checked_at = email_alert()  # Failure here MUST NOT mark as notified.
    STATE_FILE.write_text(
        json.dumps({"notified": True, "checked_at": checked_at, "url": URL},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write("notified=true\n")
    print("Alert sent; state updated for one-time notification.")


if __name__ == "__main__":
    main()
