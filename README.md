# 通用机场签到😍<br/>
>只要机场网站''' Powered by SSPANEL ''',就可以进行签到。要确认是否是''' Powered by SSPANEL '''，在机场首页滑倒最底端就可以看到。例如：
![Y0}SY$J`8837H8T5GXM1DZY](https://user-images.githubusercontent.com/21276183/214764546-4f66333a-cb9b-420e-8260-697d26fb4547.png)
## 作用
>每天进行签到，获取额外的流量奖励

## 推送方式
  🚀🚀该脚本采用的是<a href = 'https://sct.ftqq.com/r/5126'>Server酱</a>的推送方式，如果不需要推送，就下面的SCKEY参数的值设置为<b>空</b>就行

# 部署过程
 
1. 右上角Fork此仓库
2. 然后到`Settings`→`Secrets and variables`→`Actions` 新建以下机密：

| 参数   | 是否必须  | 内容  | 
| ------------ | ------------ | ------------ |
| CONFIG| 是  | 账号密码  |
| SCKEY  | 否  | Sever酱秘钥  |
<br/>
<b>其中URL的值必须是机场网站的地址，例如：https://example.com</b>,尾部不要加''' / '''号 config写法：一行账号一行密码

3. 到`Actions`中创建一个workflow，运行一次，以后每天项目都会自动运行。<br/>
4. 最后，可以到Run sign查看签到情况，同时也会也会将签到详情推送到Sever酱。
