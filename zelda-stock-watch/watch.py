#!/usr/bin/env python3
"""Fail-closed rental-stock watcher: alert only for the MAIN account."""
import json
import os
import re
from datetime import datetime
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
        print(f"Page URL: {page.url!r}; browser title: {page.title()!r}")
        print(f"Visible body preview (public site): {body[:1600]!r}")
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
            # This site intermittently returns an empty/delayed app shell.
            # Retry unknown states only; never interpret an error as restock.
            for attempt in range(1, 4):
                try:
                    response = page.goto(URL, wait_until="domcontentloaded", timeout=30000)
                    if not response or response.status >= 400:
                        print(f"Attempt {attempt}: unknown HTTP {response.status if response else 'no response'}")
                        continue
                    try:
                        page.get_by_text("主号", exact=False).first.wait_for(timeout=9000)
                    except Exception:
                        pass
                    page.wait_for_timeout(1200)
                    status = detect_stock(page)
                    print(f"Attempt {attempt}: {status}")
                    if status != "unknown":
                        return status
                except Exception as exc:
                    print(f"Attempt {attempt}: unknown page error: {type(exc).__name__}: {exc}")
            return "unknown"
        finally:
            context.close()
            browser.close()


def main():
    """The workflow creates the notification Issue; the Python checker never sends mail."""
    if STATE_FILE.exists():
        saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if saved.get("notified"):
            print("Previously notified via GitHub Issue; monitoring complete.")
            return
    status = fetch_status()
    print(f"Main account status: {status}")
    if status != "available":
        return
    if os.getenv("DRY_RUN", "0") == "1":
        print("DRY_RUN: detected available; will not create an alert Issue.")
        return
    # Two positive checks guard against temporary or inconsistent site state.
    verification = fetch_status()
    print(f"Confirmation status: {verification}")
    if verification != "available":
        print("No Issue: positive result was not independently confirmed.")
        return
    checked_at = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    output = os.getenv("GITHUB_OUTPUT")
    if not output:
        raise RuntimeError("GITHUB_OUTPUT unavailable: refusing to trigger alert without Actions context")
    with open(output, "a", encoding="utf-8") as f:
        f.write("restocked=true\n")
        f.write(f"checked_at={checked_at}\n")
    print("Main-account availability confirmed twice; GitHub Issue step may notify.")


if __name__ == "__main__":
    main()
