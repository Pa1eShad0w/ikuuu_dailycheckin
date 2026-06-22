import json, os, sys, time
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

email   = os.environ.get('EMAIL')
passwd  = os.environ.get('PASSWD')
SCKEY   = os.environ.get('SCKEY') or ''
base_url = (os.environ.get('AIRPORT_URL') or 'https://ikuuu.org').rstrip('/')

login_page_url = f'{base_url}/auth/login'
check_url      = f'{base_url}/user/checkin'
user_url       = f'{base_url}/user'
logout_url     = f'{base_url}/user/logout'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def push(title):
    if not SCKEY:
        return
    url = f'https://sctapi.ftqq.com/{SCKEY}.send?title=ikuu签到-{title}'
    try:
        requests.post(url=url, timeout=10)
        print('推送成功')
    except Exception as e:
        print(f'推送失败: {e}')


def run():
    print(f'域名: {base_url}')
    if not email or not passwd:
        raise RuntimeError('EMAIL / PASSWD secret 未设置')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = browser.new_context(user_agent=UA, locale='zh-CN', viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        print('打开登录页...')
        page.goto(login_page_url, wait_until='networkidle', timeout=30000)

        # Wait for form fields rendered by decoded JS
        page.wait_for_selector('input[name="email"], #email', timeout=15000)
        page.fill('input[name="email"], #email', email)
        page.fill('input[name="passwd"], #passwd', passwd)

        print('提交登录...')
        # Capture login XHR response
        with page.expect_response(lambda r: '/auth/login' in r.url and r.request.method == 'POST', timeout=20000) as resp_info:
            page.click('button[type="submit"], #login')
        login_resp = resp_info.value
        login_body = login_resp.text()
        print(f'login status={login_resp.status} body={login_body[:300]}')
        try:
            lj = json.loads(login_body)
        except Exception:
            lj = {}
        if lj.get('ret') != 1:
            raise RuntimeError(f'登录失败: {lj.get("msg") or login_body[:200]}')
        print(lj.get('msg'))

        # Settle any redirect after login
        try:
            page.wait_for_load_state('networkidle', timeout=10000)
        except PWTimeout:
            pass

        print('进行签到...')
        # POST checkin from inside the page so cookies + any anti-bot tokens are present
        chk_body = page.evaluate(
            """async (u) => {
                const r = await fetch(u, {
                    method: 'POST',
                    headers: {'X-Requested-With': 'XMLHttpRequest'},
                    credentials: 'include'
                });
                const t = await r.text();
                return {status: r.status, body: t};
            }""",
            check_url,
        )
        print(f'checkin status={chk_body["status"]} body={chk_body["body"][:300]}')
        try:
            cj = json.loads(chk_body['body'])
            content = cj.get('msg', '签到响应无 msg')
        except Exception:
            content = f'签到响应非 JSON: {chk_body["body"][:120]}'
        print(content)

        try:
            page.goto(logout_url, timeout=10000)
        except Exception:
            pass
        context.close()
        browser.close()
        return content


try:
    msg = run()
    push(msg)
except Exception as e:
    err = f'签到失败: {e}'
    print(err)
    push(err)
    sys.exit(1)
