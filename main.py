import requests, json, os

session = requests.session()

email = os.environ.get('EMAIL')
passwd = os.environ.get('PASSWD')
SCKEY = os.environ.get('SCKEY') or ''
# Airport mirror domain (changes periodically). Override via secret AIRPORT_URL if blocked.
base_url = (os.environ.get('AIRPORT_URL') or 'https://ikuuu.org').rstrip('/')

login_page_url = f'{base_url}/auth/login'
login_url      = f'{base_url}/auth/login'
check_url      = f'{base_url}/user/checkin'
logout_url     = f'{base_url}/user/logout'

header = {
    'origin': base_url,
    'referer': login_page_url,
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}
data = {'email': email, 'passwd': passwd}


def push(title):
    if not SCKEY:
        return
    url = f'https://sctapi.ftqq.com/{SCKEY}.send?title=ikuu签到-{title}'
    try:
        requests.post(url=url, timeout=10)
        print('推送成功')
    except Exception as e:
        print(f'推送失败: {e}')


try:
    print(f'域名: {base_url}')
    print('预热登录页...')
    session.get(login_page_url, headers={'user-agent': header['user-agent']}, timeout=15)

    print('进行登录...')
    resp = session.post(url=login_url, headers=header, data=data, timeout=15)
    print(f'login status={resp.status_code} body={resp.text[:300]}')
    login_json = json.loads(resp.text)
    print(login_json.get('msg'))

    print('进行签到...')
    chk = session.post(url=check_url, headers=header, timeout=15)
    print(f'checkin status={chk.status_code} body={chk.text[:300]}')
    result = json.loads(chk.text)
    content = result.get('msg', '签到响应无 msg')
    print(content)

    push(content)
    session.get(logout_url, headers=header, timeout=10)
except Exception as e:
    content = f'签到失败: {e}'
    print(content)
    push(content)
