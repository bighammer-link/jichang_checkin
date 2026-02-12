import requests, json, re, os

# 机场的地址
url = os.environ.get('URL')
# 配置用户名（一般是邮箱）
config = os.environ.get('CONFIG')
# Server酱 SCKEY
SCKEY = os.environ.get('SCKEY', '')  # 默认空字符串
# WxPusher 配置
WXPUSHER_APPTOKEN = os.environ.get('WXPUSHER_APPTOKEN', '')
WXPUSHER_UID = os.environ.get('WXPUSHER_UID', '')
# 可选推送方式：'serverchan', 'wxpusher', 'both'，默认 'both' 如果都配置了
PUSH_METHOD = os.environ.get('PUSH_METHOD', 'both').lower()

login_url = '{}/auth/login'.format(url)
check_url = '{}/user/checkin'.format(url)

def sign(order, user, pwd):
    session = requests.session()
    header = {
        'origin': url,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
    }
    data = {
        'email': user,
        'passwd': pwd
    }
    try:
        print(f'===账号{order}进行登录...===')
        print(f'账号：{user}')
        res = session.post(url=login_url, headers=header, data=data).text
        print(res)
        response = json.loads(res)
        print(response['msg'])
        # 进行签到
        res2 = session.post(url=check_url, headers=header).text
        print(res2)
        result = json.loads(res2)
        print(result['msg'])
        content = result['msg']
    except Exception as ex:
        content = '签到失败'
        print(content)
        print("出现如下异常%s" % ex)
    
    # 进行推送
    pushed = False
    
    # Server酱推送
    if (PUSH_METHOD in ['serverchan', 'both']) and SCKEY:
        try:
            push_url = 'https://sctapi.ftqq.com/{}.send?title=机场签到&desp={}'.format(SCKEY, content)
            resp = requests.post(url=push_url)
            print('Server酱推送响应:', resp.text)
            if resp.status_code == 200:
                print('Server酱推送成功')
                pushed = True
            else:
                print('Server酱推送失败:', resp.status_code)
        except Exception as e:
            print('Server酱推送异常:', e)
    
    # WxPusher推送
    if (PUSH_METHOD in ['wxpusher', 'both']) and WXPUSHER_APPTOKEN and WXPUSHER_UID:
        try:
            wxpusher_url = "https://wxpusher.zjiecode.com/api/send/message"
            payload = {
                "appToken": WXPUSHER_APPTOKEN,
                "content": content,
                "summary": "机场签到",  # 可选，微信消息标题
                "contentType": 1,  # 1=纯文本
                "uids": [WXPUSHER_UID]
            }
            resp = requests.post(wxpusher_url, json=payload)
            print('WxPusher响应:', resp.text)
            result = resp.json()
            if result.get("code") == 1000:
                print('WxPusher推送成功')
                pushed = True
            else:
                print('WxPusher推送失败:', result)
        except Exception as e:
            print('WxPusher推送异常:', e)
    
    if not pushed:
        print('未配置有效的推送方式，跳过推送')
    
    print('===账号{order}签到结束===\n'.format(order=order))

if __name__ == '__main__':
    configs = config.splitlines()
    if len(configs) % 2 != 0 or len(configs) == 0:
        print('配置文件格式错误')
        exit()
    user_quantity = len(configs) // 2
    for i in range(user_quantity):
        user = configs[i * 2]
        pwd = configs[i * 2 + 1]
        sign(i, user, pwd)
