"""SSPanel check-in for one or more airports, with optional notifications."""

import json
import json
import os
import time
from urllib.parse import urlsplit

import requests
from geeked import Geeked
from notifier import notify

# 默认验证码 ID 仅针对 ikuuu.org 提取，其他站点通常需要指定自己的 ID。
CAPTCHA_ID = 'cc96d05ba8b60f9112f76e18526fcb73'
MAX_RETRIES = 3
REQUEST_TIMEOUT = 20

# 保持兼容已有的单机场调用方式及测试。
url = os.environ.get('URL')
config = os.environ.get('CONFIG')


def validate_url(value):
    """Validate and normalize an airport root URL without exposing credentials."""
    if not isinstance(value, str):
        return None
    candidate = value.strip().rstrip('/')
    try:
        parsed = urlsplit(candidate)
        if (parsed.scheme not in ('https', 'http') or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path or parsed.query or parsed.fragment):
            return None
    except ValueError:
        return None
    return candidate


def load_airports(environ=None):
    """Load AIRPORTS JSON, or fall back to legacy URL + CONFIG Secrets.

    Returns a list of dicts containing name, url, captcha_id and accounts.
    Invalid individual airports/accounts are skipped; an invalid root format
    or zero usable accounts fails loudly without printing any credentials.
    """
    env = os.environ if environ is None else environ
    multi = (env.get('AIRPORTS') or '').strip()
    if multi:
        try:
            raw = json.loads(multi)
        except json.JSONDecodeError:
            raise ValueError('AIRPORTS 必须是合法的 JSON 数组') from None
        if not isinstance(raw, list) or not raw:
            raise ValueError('AIRPORTS 必须是非空的 JSON 数组')

        airports = []
        for index, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                print(f'机场 {index} 的配置不是对象，已跳过')
                continue
            name = item.get('name')
            if not isinstance(name, str) or not name.strip():
                name = f'机场 {index}'
            else:
                name = name.strip()

            site_url = validate_url(item.get('url'))
            if not site_url:
                print(f'{name}：URL 格式不正确，已跳过')
                continue

            captcha_id = item.get('captcha_id')
            if captcha_id is None or captcha_id == '':
                captcha_id = CAPTCHA_ID
                print(f'{name}：未配置 captcha_id，将使用 ikuuu.org 默认 ID（可能不兼容）')
            elif not isinstance(captcha_id, str) or not captcha_id.strip():
                print(f'{name}：captcha_id 无效，已跳过')
                continue
            else:
                captcha_id = captcha_id.strip()

            raw_accounts = item.get('accounts')
            if not isinstance(raw_accounts, list) or not raw_accounts:
                print(f'{name}：accounts 需要至少一个账号，已跳过')
                continue
            accounts = []
            for position, account in enumerate(raw_accounts, start=1):
                if not isinstance(account, dict):
                    print(f'{name}：第 {position} 个账号格式错误，已跳过')
                    continue
                email, password = account.get('email'), account.get('password')
                if (not isinstance(email, str) or not email.strip()
                        or not isinstance(password, str) or not password):
                    print(f'{name}：第 {position} 个账号缺少邮箱或密码，已跳过')
                    continue
                accounts.append((email.strip(), password))

            if accounts:
                airports.append({
                    'name': name, 'url': site_url,
                    'captcha_id': captcha_id, 'accounts': accounts,
                })
            else:
                print(f'{name}：没有有效账号，已跳过')

        if not airports:
            raise ValueError('AIRPORTS 中没有可运行的机场和账号')
        return airports

    site_url = validate_url(env.get('URL'))
    legacy_config = env.get('CONFIG')
    if not site_url or not legacy_config:
        raise ValueError('请配置 AIRPORTS，或者同时设置 URL 和 CONFIG')
    lines = legacy_config.splitlines()
    if not lines or len(lines) % 2 or any(not value.strip() for value in lines):
        raise ValueError('CONFIG 格式错误：每个账号须占两行（邮箱、密码），不能有空行')
    return [{
        'name': '默认机场', 'url': site_url, 'captcha_id': CAPTCHA_ID,
        'accounts': [(lines[i].strip(), lines[i + 1]) for i in range(0, len(lines), 2)],
    }]


class GeetestResponseError(Exception):
    """Safe, limited diagnostics for unexpected captcha-service responses."""


def parse_geetest_response(raw, callback):
    """Decode JSONP without logging a raw response or any verification tokens."""
    if not isinstance(raw, str):
        raise GeetestResponseError('返回内容不是文本')
    wrapped = raw.strip().rstrip(';').strip()
    prefix = f'{callback}('
    if not wrapped.startswith(prefix) or not wrapped.endswith(')'):
        raise GeetestResponseError('返回内容不是预期 JSONP 格式，可能是网络或服务端拒绝')
    try:
        payload = json.loads(wrapped[len(prefix):-1])
    except ValueError:
        raise GeetestResponseError('返回内容不是有效 JSON') from None
    if not isinstance(payload, dict):
        raise GeetestResponseError('返回内容结构不是对象')

    data = payload.get('data')
    if not isinstance(data, dict):
        # Never print raw response, msg, challenge, payload or tokens. Only safe
        # protocol status and numerical error codes are allowed into logs.
        status = payload.get('status')
        status = status if status in ('success', 'fail', 'error') else 'unknown'
        code = payload.get('code')
        error = payload.get('error')
        if code is None and isinstance(error, dict):
            code = error.get('code')
        code = str(code) if code is not None else ''
        code = code if 1 <= len(code) <= 8 and code.lstrip('-').isdigit() else 'unknown'
        raise GeetestResponseError(f'极验响应缺少 data（status={status}, code={code}）')
    return data


def solve_captcha(captcha_id=None):
    """尝试求解 GeeTest V4 验证码，失败则返回 None。"""
    site_captcha_id = captcha_id or CAPTCHA_ID
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f'验证码求解尝试 {attempt}/{MAX_RETRIES}...')
            solver = Geeked(site_captcha_id, 'ai')
            # GeekedTest's upstream format_response currently assumes every
            # response has a data key. Decode errors without leaking raw values.
            solver.format_response = lambda response: parse_geetest_response(
                response, solver.callback
            )
            captcha = solver.solve()
            print('验证码求解成功')
            return captcha
        except GeetestResponseError as exc:
            print(f'验证码求解失败 (尝试 {attempt}/{MAX_RETRIES}): {exc}')
            if attempt < MAX_RETRIES:
                time.sleep(2)
        except KeyError as exc:
            # Only report expected protocol field names; never log raw responses or tokens.
            safe_fields = {'data', 'lot_number', 'payload', 'process_token', 'pow_detail',
                           'pt', 'hashfunc', 'version', 'bits', 'datetime', 'seccode'}
            field = exc.args[0] if exc.args and exc.args[0] in safe_fields else '未知字段'
            print(f'验证码求解失败 (尝试 {attempt}/{MAX_RETRIES}): 返回数据缺少字段 {field}')
            if attempt < MAX_RETRIES:
                time.sleep(2)
        except Exception as exc:
            print(f'验证码求解失败 (尝试 {attempt}/{MAX_RETRIES}): {type(exc).__name__}')
            if attempt < MAX_RETRIES:
                time.sleep(2)
    print('所有重试均失败')
    return None


def mask_account(email):
    """避免向通知群和日志发送完整登录邮箱。"""
    name, sep, domain = email.partition('@')
    return f'{name[:1]}***@{domain}' if sep else '***'


def sign(order, user, pwd, airport_url=None, captcha_id=None, airport_name='默认机场'):
    """对指定机场的单个账号签到，所有结果独立通知。"""
    site_url = airport_url or url
    site_captcha_id = captcha_id or CAPTCHA_ID
    account = f'账号 {order + 1}（{mask_account(user)}）'
    prefix = f'机场：{airport_name}\n{account}'
    session = requests.session()
    headers = {
        'origin': site_url,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    }
    try:
        print(f'=== {airport_name} / {account} 开始登录 ===')
        captcha = solve_captcha(site_captcha_id)
        if captcha is None:
            print('验证码求解失败，跳过此账号')
            notify('机场签到失败', f'{prefix}\n验证码求解失败，跳过此账号')
            return False

        data = {
            'email': user,
            'passwd': pwd,
            'captcha_result[lot_number]': captcha['lot_number'],
            'captcha_result[captcha_output]': captcha['captcha_output'],
            'captcha_result[pass_token]': captcha['pass_token'],
            'captcha_result[gen_time]': captcha['gen_time'],
        }
        response = session.post(
            f'{site_url}/auth/login', headers=headers, data=data, timeout=REQUEST_TIMEOUT
        ).json()
        login_message = response.get('msg', '服务器未返回登录信息')
        print(f'登录结果：{login_message}')
        if response.get('ret') != 1:
            notify('机场签到失败', f'{prefix}\n登录失败：{login_message}')
            return False

        result = session.post(
            f'{site_url}/user/checkin', headers=headers, timeout=REQUEST_TIMEOUT
        ).json()
        message = result.get('msg', '服务器未返回签到信息')
        print(f'签到结果：{message}')
        if result.get('ret') == 1:
            notify('机场签到成功', f'{prefix}\n{message}')
            return True
        elif result.get('ret') == 0:
            notify('机场签到失败', f'{prefix}\n{message}')
            return False
        else:
            notify('机场签到结果', f'{prefix}\n{message}')
            return False
    except Exception as exc:
        print(f'签到异常：{type(exc).__name__}，请检查网络或 GitHub Actions 日志')
        notify('机场签到失败', f'{prefix}\n签到异常，请查看 GitHub Actions 日志')
        return False
    finally:
        session.close()
        print(f'=== {airport_name} / {account} 签到结束 ===\n')


def run_all(environ=None):
    """按机场顺序运行所有账号，不因个别账号异常而停止。"""
    airports = load_airports(environ)
    total = sum(len(airport['accounts']) for airport in airports)
    print(f'已载入 {len(airports)} 个机场、{total} 个账号')
    failed = 0
    for airport in airports:
        for index, (email, password) in enumerate(airport['accounts']):
            try:
                result = sign(
                    index, email, password,
                    airport_url=airport['url'],
                    captcha_id=airport['captcha_id'],
                    airport_name=airport['name'],
                )
                if result is False:
                    failed += 1
            except Exception as exc:
                failed += 1
                print(f'{airport["name"]}：第 {index + 1} 个账号出现未处理的异常 {type(exc).__name__}')
                notify('机场签到失败', f'机场：{airport["name"]}\n账号 {index + 1}\n签到异常，请查看 GitHub Actions 日志')
    print(f'签到任务结束：总计 {total} 个账号，失败 {failed} 个')
    return failed


if __name__ == '__main__':
    try:
        failed_count = run_all()
        if failed_count:
            raise SystemExit(1)
    except ValueError as exc:
        raise SystemExit(f'配置错误：{exc}') from None
