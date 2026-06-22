import json, os, sys, time
from datetime import datetime, timezone
import requests

SCKEY = os.environ.get('SCKEY') or ''
cookie_str = (os.environ.get('IKUUU_COOKIE') or '').strip()
base_url = (os.environ.get('AIRPORT_URL') or 'https://ikuuu.org').rstrip('/')
warn_days = int(os.environ.get('COOKIE_WARN_DAYS') or '3')

check_url = f'{base_url}/user/checkin'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
headers = {
    'origin': base_url,
    'referer': f'{base_url}/user',
    'user-agent': UA,
    'x-requested-with': 'XMLHttpRequest',
    'cookie': cookie_str,
}


def push(title):
    if not SCKEY:
        return
    url = f'https://sctapi.ftqq.com/{SCKEY}.send?title=ikuu签到-{title}'
    try:
        requests.post(url=url, timeout=10)
        print('推送成功')
    except Exception as e:
        print(f'推送失败: {e}')


def parse_cookie(raw):
    out = {}
    for part in raw.split(';'):
        part = part.strip()
        if not part or '=' not in part:
            continue
        k, _, v = part.partition('=')
        out[k.strip()] = v.strip()
    return out


def days_left(cookie_map):
    exp = cookie_map.get('expire_in')
    if not exp or not exp.isdigit():
        return None
    expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    delta = expires_at - datetime.now(tz=timezone.utc)
    return delta.total_seconds() / 86400.0, expires_at


def run():
    if not cookie_str:
        raise RuntimeError('IKUUU_COOKIE secret 未设置')

    cmap = parse_cookie(cookie_str)
    print(f'域名: {base_url}')
    print(f'cookie 字段: {sorted(cmap.keys())}')

    dl = days_left(cmap)
    cookie_warning = None
    if dl is not None:
        days, expires_at = dl
        print(f'cookie 过期: {expires_at.isoformat()} (剩 {days:.1f} 天)')
        if days <= 0:
            cookie_warning = f'Cookie 已过期 ({expires_at.isoformat()})，请刷新 IKUUU_COOKIE secret'
        elif days <= warn_days:
            cookie_warning = f'Cookie 还剩 {days:.1f} 天到期 ({expires_at.isoformat()})，请刷新 IKUUU_COOKIE secret'

    print('进行签到...')
    resp = requests.post(check_url, headers=headers, timeout=15)
    print(f'checkin status={resp.status_code} body={resp.text[:300]}')
    try:
        result = json.loads(resp.text)
        content = result.get('msg', f'无 msg 字段, raw={resp.text[:120]}')
    except Exception:
        content = f'签到响应非 JSON: {resp.text[:120]}'

    if cookie_warning:
        content = f'{content} | ⚠️ {cookie_warning}'
    return content


try:
    msg = run()
    print(msg)
    push(msg)
except Exception as e:
    err = f'签到失败: {e}'
    print(err)
    push(err)
    sys.exit(1)
