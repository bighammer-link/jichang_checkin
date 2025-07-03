import requests, json, os
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
                print(f'[info]签到 第{order}个账号')
                # 尝试脱敏输出账号，避免被github actions替换成***
                user_out = ''
                for i in user:
                        user_out += i
                        user_out += " "
                print(f'[info]账号：{user_out}')
                res = session.post(url=login_url,headers=header,data=data).text
                print('[debug]登录接口返回',res)
                response = json.loads(res)
                print(f'[info]第{order}个账号',response['msg'])
                # 进行签到
                res2 = session.post(url=check_url,headers=header).text
                print('[debug]签到接口返回',res2)
                result = json.loads(res2)
                print(f"[info]第{order}个账号",result['msg'])
                return f"[账号{user}]签到成功：{result['msg']}"
        except Exception as ex:
                print('[error]第{order}个账号签到失败')
                print("[error]签到时出现如下异常%s" % ex)
                return f"[账号{user}]签到失败:{ex}"
                
def push(msg):
        if SCKEY != '':
                push_url = 'https://sctapi.ftqq.com/{}.send?title=机场签到&desp={}'.format(SCKEY, msg)
                requests.post(url=push_url)
                print('[info]已推送至 server酱')
        else:
                print('[info]未配置 Server酱，跳过推送流程')

if __name__ == '__main__':
        configs = config.splitlines()
        pushmsg = 'SSPANEL 机场签到结果推送：'
        if len(configs) %2 != 0 or len(configs) == 0:
                print('[warn]机密CONFIG格式错误，参考README.md进行修改\n[exit]退出签到')
                exit()
        user_quantity = len(configs)
        user_quantity = user_quantity // 2
        for i in range(user_quantity):
                user = configs[i*2]
                pwd = configs[i*2+1]
                pushmsg += '\n' + sign(i+1,user,pwd)
        push(pushmsg)
        print('[exit]流程结束')
        exit()