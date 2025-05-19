import requests, json, re, os
# 机场的地址
url = os.environ.get('URL')
# 配置用户名（一般是邮箱）

config = os.environ.get('CONFIG')
# server酱
SCKEY = os.environ.get('SCKEY')

login_url = '{}/auth/login'.format(url)
check_url = '{}/user/checkin'.format(url)

def sign(order,user,pwd):
        session = requests.session()
        global url,SEKEY
        header = {
        'origin': url,
        'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
        }
        data = {
        'email': user,
        'passwd': pwd
        }
        try:
                print(f'===账号{order}进行登录...===')
                print(f'账号：{user}')
                res = session.post(url=login_url,headers=header,data=data).text
                print(res)
                response = json.loads(res)
                print(response['msg'])
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
        
