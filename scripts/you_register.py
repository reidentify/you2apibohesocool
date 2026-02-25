#!/usr/bin/env python3
"""You.com 自动注册 + 提取 DS/DSR token，使用 Playwright + DuckMail API"""

import json, re, time, sys, requests
from playwright.sync_api import sync_playwright

DUCKMAIL_API = "https://api.duckmail.sbs"
YOUCOM_SIGNIN = "https://you.com/signin?redirectUrl=%2F"

def create_email():
    ts = int(time.time())
    addr = f"youtest{ts}@baldur.edu.kg"
    pwd = "Yt2026Pass!z"
    r = requests.post(f"{DUCKMAIL_API}/accounts",
                      json={"address": addr, "password": pwd})
    r.raise_for_status()
    print(f"[1] 邮箱创建: {addr}")

    r = requests.post(f"{DUCKMAIL_API}/token",
                      json={"address": addr, "password": pwd})
    token = r.json()["token"]
    return addr, token

def wait_for_code(mail_token, timeout=30):
    print("[3] 等待验证码...", end="", flush=True)
    for _ in range(timeout):
        time.sleep(1)
        print(".", end="", flush=True)
        r = requests.get(f"{DUCKMAIL_API}/messages",
                         headers={"Authorization": f"Bearer {mail_token}"})
        msgs = r.json().get("hydra:member", [])
        for m in msgs:
            if "you.com" in m.get("from", {}).get("address", "").lower():
                mid = m["id"]
                detail = requests.get(f"{DUCKMAIL_API}/messages/{mid}",
                                      headers={"Authorization": f"Bearer {mail_token}"})
                data = detail.json()
                text = data.get("text", "")
                html = "".join(data.get("html", []))
                codes = re.findall(r"\b(\d{6})\b", text or html)
                if codes:
                    print(f" 拿到: {codes[0]}")
                    return codes[0]
    print(" 超时!")
    return None

def register_and_extract():
    addr, mail_token = create_email()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/133.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = ctx.new_page()

        # Step 2: 打开登录页
        print("[2] 打开 You.com 登录页...")
        page.goto(YOUCOM_SIGNIN, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # 输入邮箱
        email_input = page.locator('input[type="email"], input[placeholder*="email"]')
        if email_input.count() == 0:
            email_input = page.locator('input').first
        email_input.click()
        email_input.fill(addr)
        page.wait_for_timeout(500)

        # 点 Continue
        continue_btn = page.get_by_text("Continue", exact=True)
        continue_btn.click()
        page.wait_for_timeout(3000)

        # 检查是否出错
        error_text = page.locator("text=error").first
        if error_text.is_visible():
            print(f"[!] 注册报错: {page.content()[:200]}")
            browser.close()
            return None

        # Step 3: 获取验证码
        code = wait_for_code(mail_token)
        if not code:
            print("[!] 获取验证码失败")
            browser.close()
            return None

        # Step 4: 填验证码 — 逐位输入
        print(f"[4] 输入验证码: {code}")
        code_inputs = page.locator('input[type="text"], input[type="tel"], input[type="number"]')
        count = code_inputs.count()

        if count >= 6:
            for i in range(6):
                code_inputs.nth(i).click()
                code_inputs.nth(i).fill(code[i])
                page.wait_for_timeout(100)
        else:
            # 可能是单个输入框
            page.keyboard.type(code, delay=100)

        print("[5] 等待登录完成...")
        page.wait_for_timeout(8000)

        # 截图确认
        page.screenshot(path="/tmp/you_after_login.png")

        # Step 6: 提取 cookies
        cookies = ctx.cookies()
        ds_val = None
        dsr_val = None
        for c in cookies:
            if c["name"] == "DS" and "you.com" in c["domain"]:
                ds_val = c["value"]
            if c["name"] == "DSR" and "you.com" in c["domain"]:
                dsr_val = c["value"]

        if ds_val:
            print(f"\n{'='*60}")
            print(f"[✓] DS token ({len(ds_val)} chars):")
            print(ds_val)
            print(f"\n[✓] DSR token ({len(dsr_val) if dsr_val else 0} chars):")
            print(dsr_val or "N/A")
            print(f"{'='*60}")

            with open("/tmp/DS_token.txt", "w") as f:
                f.write(ds_val)
            with open("/tmp/DSR_token.txt", "w") as f:
                f.write(dsr_val or "")
            print(f"\n[✓] Token 已保存到 /tmp/DS_token.txt & /tmp/DSR_token.txt")

            # 检查 subscription 状态
            you_sub = next((c["value"] for c in cookies if c["name"] == "you_subscription"), "N/A")
            print(f"[i] 订阅状态: {you_sub}")
        else:
            print("[!] 未找到 DS cookie，可能登录失败")
            print(f"    当前 URL: {page.url}")
            all_cookie_names = [c["name"] for c in cookies if "you.com" in c.get("domain", "")]
            print(f"    You.com cookies: {all_cookie_names}")

        browser.close()
        return ds_val

if __name__ == "__main__":
    ds = register_and_extract()
    sys.exit(0 if ds else 1)
