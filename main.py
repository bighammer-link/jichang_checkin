import json
import os
import sys
import time

import requests

# ── Environment variables ─────────────────────────────────────────────────────
url = os.environ.get('URL', '').rstrip('/')
config = os.environ.get('CONFIG', '')
SCKEY = os.environ.get('SCKEY', '')

login_url = '{}/auth/login'.format(url)
check_url = '{}/user/checkin'.format(url)

# ── Retry settings ────────────────────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds; wait = RETRY_BACKOFF * attempt

_HEADERS = {
    'user-agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/109.0.0.0 Safari/537.36'
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def send_notification(title: str, content: str) -> None:
    """Send a Server酱 push notification if SCKEY is configured."""
    if not SCKEY:
        return
    push_url = 'https://sctapi.ftqq.com/{}.send'.format(SCKEY)
    try:
        resp = requests.post(push_url, data={'title': title, 'desp': content}, timeout=15)
        print('[通知] 推送完成，状态码: {}'.format(resp.status_code))
    except Exception as ex:
        print('[通知] 推送失败: {}'.format(ex))


def post_with_retry(session: requests.Session, phase: str, target_url: str,
                    **kwargs) -> requests.Response:
    """POST *target_url* with up to MAX_RETRIES attempts and backoff.

    Logs attempt number, HTTP status, and a truncated response body on each
    failure.  Raises the last exception if all attempts are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print('[{}] 尝试 {}/{} ...'.format(phase, attempt, MAX_RETRIES))
            resp = session.post(target_url, timeout=30, **kwargs)
            print('[{}] HTTP {}'.format(phase, resp.status_code))
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as exc:
            body_preview = ''
            if exc.response is not None:
                body_preview = exc.response.text[:300]
            print('[{}] HTTP错误 (attempt {}): {}'.format(phase, attempt, exc))
            if body_preview:
                print('[{}] 响应体 (截断): {}'.format(phase, body_preview))
            last_exc = exc
        except requests.exceptions.RequestException as exc:
            print('[{}] 网络错误 (attempt {}): {}'.format(phase, attempt, exc))
            last_exc = exc
        if attempt < MAX_RETRIES:
            wait = RETRY_BACKOFF * attempt
            print('[{}] 等待 {}s 后重试...'.format(phase, wait))
            time.sleep(wait)
    raise last_exc  # always set: loop executes at least once (MAX_RETRIES >= 1)


def parse_json(phase: str, text: str) -> dict | None:
    """Parse JSON response body; log and return None on failure."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print('[{}] JSON解析失败: {}  响应体 (截断): {}'.format(phase, exc, text[:300]))
        return None


# ── Core sign-in logic ────────────────────────────────────────────────────────

def sign(order: int, user: str, pwd: str) -> bool:
    """Perform login + check-in for one account.

    Returns True on success, False if either phase ultimately fails.
    """
    session = requests.Session()
    header = dict(_HEADERS)
    header['origin'] = url

    print('=== 账号 {} 开始签到 ==='.format(order + 1))
    print('[账号] {}'.format(user))

    # ── Phase 1: Login ────────────────────────────────────────────────────────
    try:
        resp = post_with_retry(
            session, '登录', login_url,
            headers=header,
            data={'email': user, 'passwd': pwd},
        )
    except Exception as exc:
        print('[登录] 登录阶段最终失败: {}'.format(exc))
        send_notification('机场签到 - 登录失败', '账号 {} 登录网络异常: {}'.format(user, exc))
        return False

    login_data = parse_json('登录', resp.text)
    if login_data is None:
        send_notification('机场签到 - 登录失败', '账号 {} 登录响应解析失败'.format(user))
        return False

    login_msg = login_data.get('msg', '(无消息)')
    print('[登录] msg={}'.format(login_msg))

    # ── Phase 2: Check-in ─────────────────────────────────────────────────────
    try:
        resp2 = post_with_retry(session, '签到', check_url, headers=header)
    except Exception as exc:
        print('[签到] 签到阶段最终失败: {}'.format(exc))
        send_notification('机场签到 - 签到失败', '账号 {} 签到网络异常: {}'.format(user, exc))
        return False

    checkin_data = parse_json('签到', resp2.text)
    if checkin_data is None:
        send_notification('机场签到 - 签到失败', '账号 {} 签到响应解析失败'.format(user))
        return False

    checkin_msg = checkin_data.get('msg', '(无消息)')
    print('[签到] msg={}'.format(checkin_msg))
    send_notification('机场签到', checkin_msg)

    print('=== 账号 {} 签到完成 ===\n'.format(order + 1))
    return True


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if not url:
        print('[错误] 未设置 URL 环境变量')
        sys.exit(1)
    if not config:
        print('[错误] 未设置 CONFIG 环境变量')
        sys.exit(1)

    # Strip blank lines so that a trailing newline in the secret doesn't break
    # the even-line assumption.
    configs = [line for line in config.splitlines() if line.strip()]
    if len(configs) == 0 or len(configs) % 2 != 0:
        print('[错误] 配置文件格式错误，行数应为正偶数 (email 与 passwd 交替排列)')
        sys.exit(1)

    user_quantity = len(configs) // 2
    failed = 0
    for i in range(user_quantity):
        user = configs[i * 2].strip()
        pwd = configs[i * 2 + 1].strip()
        if not sign(i, user, pwd):
            failed += 1

    if failed:
        print('[结果] {}/{} 个账号签到失败'.format(failed, user_quantity))
        sys.exit(1)
    else:
        print('[结果] 全部 {} 个账号签到成功'.format(user_quantity))

