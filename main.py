import os
import time

import requests
from geeked import Geeked
from notifier import notify

# 机场网站根地址和账号配置（通过 GitHub Actions Secrets 提供）
url = os.environ.get('URL')
config = os.environ.get('CONFIG')

# GeeTest V4 验证码 ID（从 ikuuu.org 提取）
CAPTCHA_ID = 'cc96d05ba8b60f9112f76e18526fcb73'
MAX_RETRIES = 3


def solve_captcha():
    """尝试求解 GeeTest V4 验证码，失败则返回 None。"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f'验证码求解尝试 {attempt}/{MAX_RETRIES}...')
            captcha = Geeked(CAPTCHA_ID, 'ai').solve()
            print('验证码求解成功')
            return captcha
        except Exception as exc:
            print(f'验证码求解失败 (尝试 {attempt}/{MAX_RETRIES}): {exc}')
            if attempt < MAX_RETRIES:
                time.sleep(2)
    print('所有重试均失败')
    return None


def mask_account(email):
    """避免将完整登录邮箱发往外部通知群。"""
    name, sep, domain = email.partition('@')
    return f'{name[:1]}***@{domain}' if sep else '***'


def sign(order, user, pwd):
    session = requests.session()
    account = f'账号 {order + 1}（{mask_account(user)}）'
    headers = {
        'origin': url,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    }
    try:
        print(f'=== {account} 开始登录 ===')
        captcha = solve_captcha()
        if captcha is None:
            print('验证码求解失败，跳过此账号')
            notify('机场签到失败', f'{account}\n验证码求解失败，跳过此账号')
            return

        data = {
            'email': user,
            'passwd': pwd,
            'captcha_result[lot_number]': captcha['lot_number'],
            'captcha_result[captcha_output]': captcha['captcha_output'],
            'captcha_result[pass_token]': captcha['pass_token'],
            'captcha_result[gen_time]': captcha['gen_time'],
        }
        response = session.post(f'{url}/auth/login', headers=headers, data=data).json()
        login_message = response.get('msg', '服务器未返回登录信息')
        print(f'登录结果：{login_message}')
        if response.get('ret') != 1:
            notify('机场签到失败', f'{account}\n登录失败：{login_message}')
            return

        result = session.post(f'{url}/user/checkin', headers=headers).json()
        message = result.get('msg', '服务器未返回签到信息')
        print(f'签到结果：{message}')
        if result.get('ret') == 1:
            notify('机场签到成功', f'{account}\n{message}')
        elif result.get('ret') == 0:
            notify('机场签到失败', f'{account}\n{message}')
        else:
            notify('机场签到结果', f'{account}\n{message}')
    except Exception as exc:
        print(f'签到异常：{type(exc).__name__}: {exc}')
        notify('机场签到失败', f'{account}\n签到异常，请查看 GitHub Actions 日志')
    finally:
        session.close()
        print(f'=== {account} 签到结束 ===\n')


if __name__ == '__main__':
    if not url or not config:
        raise SystemExit('配置错误：请在 GitHub Actions Secrets 中设置 URL 和 CONFIG')
    configs = config.splitlines()
    if not configs or len(configs) % 2:
        raise SystemExit('CONFIG 格式错误：每个账号须占两行（邮箱、密码）')
    for i in range(len(configs) // 2):
        sign(i, configs[2 * i], configs[2 * i + 1])
