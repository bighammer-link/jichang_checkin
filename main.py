import requests, json, os, time
from urllib.parse import urlparse
from geeked import Geeked

# 机场的地址
url = os.environ.get('URL')
# 配置用户名（一般是邮箱）

config = os.environ.get('CONFIG')
# server酱
SCKEY = os.environ.get('SCKEY')

# GeeTest V4 验证码 ID（从 ikuuu.org 提取）
CAPTCHA_ID = 'cc96d05ba8b60f9112f76e18526fcb73'

login_url = '{}/auth/login'.format(url)
check_url = '{}/user/checkin'.format(url)

MAX_RETRIES = 3


def build_login_data(user, pwd, captcha, page_loaded_at):
        """构造同时兼容新版分阶段登录和旧版登录接口的表单。"""
        return {
                'host': urlparse(url).netloc,
                'phase': 'password',
                'email': user,
                'passwd': pwd,
                'pageLoadedAt': page_loaded_at,
                'captcha_result[lot_number]': captcha['lot_number'],
                'captcha_result[captcha_output]': captcha['captcha_output'],
                'captcha_result[pass_token]': captcha['pass_token'],
                'captcha_result[gen_time]': captcha['gen_time'],
        }


def login_succeeded(response):
        """兼容新版 phase 响应和旧版 ret 响应。"""
        return (
                response.get('phase') == 'authenticated'
                or str(response.get('ret')) == '1'
        )

def solve_captcha():
        """使用 GeekedTest 求解 GeeTest V4 验证码（纯 Python，无需浏览器），支持重试"""
        for attempt in range(1, MAX_RETRIES + 1):
                try:
                        print(f'验证码求解尝试 {attempt}/{MAX_RETRIES}...')
                        geeked = Geeked(CAPTCHA_ID, 'ai')
                        result = geeked.solve()
                        print('验证码求解成功')
                        return result
                except Exception as ex:
                        print(f'验证码求解失败 (尝试 {attempt}/{MAX_RETRIES}): {ex}')
                        if attempt < MAX_RETRIES:
                                wait = 2
                                print(f'等待 {wait} 秒后重试...')
                                time.sleep(wait)
        print('所有重试均失败')
        return None

def sign(order,user,pwd):
        session = requests.session()
        global url,SCKEY
        header = {
        'origin': url,
        'referer': login_url,
        'x-requested-with': 'XMLHttpRequest',
        'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
        }
        try:
                print(f'===账号{order}进行登录...===')
                print(f'账号：{user}')

                # 先访问登录页，建立与浏览器一致的会话，并记录页面加载时间。
                login_page = session.get(url=login_url, headers=header, timeout=30)
                login_page.raise_for_status()
                page_loaded_at = int(time.time() * 1000)

                # 求解 GeeTest V4 验证码
                captcha = solve_captcha()
                if captcha is None:
                        print('验证码求解失败，跳过此账号')
                        return

                data = build_login_data(user, pwd, captcha, page_loaded_at)

                login_response = session.post(
                        url=login_url, headers=header, data=data, timeout=30
                )
                login_response.raise_for_status()
                print(login_response.text)
                response = login_response.json()
                message = response.get('msg', '登录接口未返回提示信息')
                print(message)

                if not login_succeeded(response):
                        print(f'登录失败: {message}')
                        content = f'登录失败: {message}'
                        if SCKEY != '':
                                push_url = 'https://sctapi.ftqq.com/{}.send?title=机场签到&desp={}'.format(SCKEY, content)
                                requests.post(url=push_url)
                                print('推送成功')
                        return

                # 进行签到
                res2 = session.post(url=check_url,headers=header).text
                print(res2)
                result = json.loads(res2)
                print(result['msg'])
                content = result['msg']
                # 进行推送
                if SCKEY != '':
                        push_url = 'https://sctapi.ftqq.com/{}.send?title=机场签到&desp={}'.format(SCKEY, content)
                        requests.post(url=push_url)
                        print('推送成功')
        except Exception as ex:
                content = '签到失败'
                print(content)
                print("出现如下异常%s"%ex)
                if SCKEY != '':
                        push_url = 'https://sctapi.ftqq.com/{}.send?title=机场签到&desp={}'.format(SCKEY, content)
                        requests.post(url=push_url)
                        print('推送成功')
        print('===账号{order}签到结束===\n'.format(order=order))
if __name__ == '__main__':
        configs = config.splitlines()
        if len(configs) %2 != 0 or len(configs) == 0:
                print('配置文件格式错误')
                exit()
        user_quantity = len(configs)
        user_quantity = user_quantity // 2
        for i in range(user_quantity):
                user = configs[i*2]
                pwd = configs[i*2+1]
                sign(i,user,pwd)
