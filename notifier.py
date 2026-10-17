"""Optional ServerChan and DingTalk notifications for check-in results."""

import base64
import hashlib
import hmac
import os
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


NOTIFY_TIMEOUT = 10


def signed_dingtalk_webhook(webhook, secret, timestamp=None):
    """Add the DingTalk HMAC-SHA256 signature to a robot webhook URL."""
    if timestamp is None:
        timestamp = str(int(time.time() * 1000))
    else:
        timestamp = str(timestamp)

    string_to_sign = f'{timestamp}\n{secret}'.encode('utf-8')
    digest = hmac.new(secret.encode('utf-8'), string_to_sign, hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode('ascii')

    parts = urlsplit(webhook)
    params = [(name, value) for name, value in parse_qsl(parts.query, keep_blank_values=True)
              if name not in ('timestamp', 'sign')]
    params.extend([('timestamp', timestamp), ('sign', signature)])
    return urlunsplit((parts.scheme, parts.netloc, parts.path,
                       urlencode(params), parts.fragment))


def send_dingtalk(title, message):
    """Notify a DingTalk group when both webhook and signing secret are set."""
    webhook = (os.environ.get('DINGTALK_WEBHOOK') or '').strip()
    secret = (os.environ.get('DINGTALK_SECRET') or '').strip()
    if not webhook and not secret:
        return
    if not webhook or not secret:
        print('钉钉通知未发送：需要同时配置 DINGTALK_WEBHOOK 和 DINGTALK_SECRET')
        return

    parts = urlsplit(webhook)
    if (parts.scheme != 'https' or parts.hostname != 'oapi.dingtalk.com'
            or parts.path != '/robot/send'
            or not any(k == 'access_token' and v for k, v in parse_qsl(parts.query))):
        print('钉钉通知未发送：Webhook 格式无效，应使用钉钉提供的完整 HTTPS Webhook')
        return

    try:
        url = signed_dingtalk_webhook(webhook, secret)
        payload = {'msgtype': 'text', 'text': {'content': f'【{title}】\n{message}'}}
        response = requests.post(url, json=payload, timeout=NOTIFY_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        if result.get('errcode') == 0:
            print('钉钉通知发送成功')
        else:
            print(f'钉钉通知失败（errcode={result.get("errcode")}）：{result.get("errmsg", "未知错误")}')
    except (requests.RequestException, ValueError, TypeError) as exc:
        # Don't log exception URLs: they contain a sensitive access_token/sign.
        print(f'钉钉通知请求失败：{type(exc).__name__}（已隐藏含密钥的请求地址）')


def send_serverchan(title, message):
    """Keep the existing optional ServerChan delivery method."""
    sckey = (os.environ.get('SCKEY') or '').strip()
    if not sckey:
        return
    try:
        response = requests.post(
            f'https://sctapi.ftqq.com/{sckey}.send',
            data={'title': title, 'desp': message},
            timeout=NOTIFY_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        if result.get('code') == 0:
            print('Server酱通知发送成功')
        else:
            print(f'Server酱通知失败（code={result.get("code")}）')
    except (requests.RequestException, ValueError, TypeError) as exc:
        # Avoid printing a URL that contains the private SendKey.
        print(f'Server酱通知请求失败：{type(exc).__name__}（已隐藏密钥）')


def notify(title, message):
    """Attempt each enabled provider independently."""
    send_serverchan(title, message)
    send_dingtalk(title, message)
