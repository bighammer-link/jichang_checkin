# 通用机场签到 😍

使用 GitHub Actions 定时尝试登录机场网站并签到，获取站点提供的流量奖励。支持**单机场多账号**及**多机场多账号**，可选通过 [Server酱](https://sct.ftqq.com/) 和钉钉自定义机器人（加签鉴权）分别推送账号签到结果；两者可以同时使用。

> **兼容性说明**：此项目使用 SSPanel 常见的 `/auth/login` 和 `/user/checkin` 接口，但并不保证所有标注「Powered by SSPanel」的网站都可使用。多机场模式可以为每个机场配置不同的 GeeTest V4 `captcha_id`；未指定时使用针对 `ikuuu.org` 提取的默认 ID。其他站点如果采用不同验证码或登录流程，仍需要适配代码。

## 部署到自己的 Fork

### 1. Fork 仓库并启用 Actions

1. 点击页面右上角 **Fork**，将仓库复制到自己的 GitHub 账号下。
2. 打开**自己的 Fork 仓库**，进入 **Actions**。如果 GitHub 提示 Fork 中的工作流已禁用，按页面提示启用。
3. 仓库已包含 [`.github/workflows/main.yml`](.github/workflows/main.yml)，**无需新建 workflow 文件**。

### 2. 配置 GitHub Actions Secrets

在**自己的 Fork 仓库**依次打开：

**Settings → Secrets and variables → Actions → Secrets → New repository secret**

每个 Secret 单独创建一项，**Name** 填入下表中完全相同的大写名称，**Secret** 填入对应的值，然后点击 **Add secret**。

| Secret 名称 | 是否必填 | 填写说明 |
| --- | --- | --- |
| `URL` | 单机场模式必填 | 机场站点根地址，例如 `https://example.com`；不要填 `/auth/login` 登录接口。程序会自动去除末尾的 `/`。使用 `AIRPORTS` 时不需要。 |
| `CONFIG` | 单机场模式必填 | 机场登录账号和密码，按下方**多行格式**配置。使用 `AIRPORTS` 时不需要。 |
| `AIRPORTS` | 多机场模式必填 | **一个 JSON 数组**，保存每个机场的名称、根地址、独立验证码 ID 和账号列表。设置后优先使用 `AIRPORTS`，旧的 `URL` + `CONFIG` 不会重复执行。见下方示例。 |
| `SCKEY` | 可选 | [Server酱](https://sct.ftqq.com/) 的 SendKey，用于推送签到结果；**不需要推送就不创建这个 Secret**。 |
| `DINGTALK_WEBHOOK` | 可选 | 钉钉群自定义机器人的完整 Webhook，例如 `https://oapi.dingtalk.com/robot/send?access_token=你的令牌`。与下方 `DINGTALK_SECRET` **成对配置**。 |
| `DINGTALK_SECRET` | 可选 | 钉钉机器人的“加签”密钥，通常以 `SEC` 开头。与上方 `DINGTALK_WEBHOOK` **成对配置**。 |

#### 方式一：单机场（`URL` + `CONFIG`）

适用于一个机场、一个或多个账号。创建两个 Secrets：`URL`（例如 `https://example.com`）以及 `CONFIG`。

##### `CONFIG` 的正确写法

**单账号示例**（整个文本填入一个名称为 `CONFIG` 的 Secret）：

```text
alice@example.com
your-password-here
```

**多账号示例**：

```text
alice@example.com
alice-password-here
bob@example.com
bob-password-here
```

请注意：

- `CONFIG` 是**一个多行 Secret**，不是每个账号创建一个 Secret；每两行代表一个账号。
- 不要加 `CONFIG=`、引号、逗号、JSON 格式或空白分隔行；行数必须为偶数。
- `URL` 和 `CONFIG` 是两个**独立的 Secret**。不要把 `URL` 写进 `CONFIG`。
- 如果同时设置了 `AIRPORTS` 和 `URL` / `CONFIG`，**只按 `AIRPORTS` 执行**；想恢复旧模式，删除或清空 `AIRPORTS`。
- 工作流里虽然还传入了 `EMAIL`、`PASSWD`，但当前 `main.py` **不读取它们**，不需要配置这两项。
- Secrets 不会显示已保存的明文值；如果填错，可在同一页面更新。**不要把真实账号、密码或 SendKey 提交进 README、代码或 workflow 文件。**

#### 方式二：多机场多账号（`AIRPORTS`）

只需额外创建**一个**名称为 `AIRPORTS` 的 GitHub Actions Secret，把下面整个 **JSON 数组**作为 Secret 值填入（用自己的机场地址、账号密码和验证码 ID 替换示例值）。

```json
[
  {
    "name": "机场A",
    "url": "https://airport-a.example.com",
    "captcha_id": "此处填写机场A的GeeTestV4验证码ID",
    "accounts": [
      {"email": "alice@example.com", "password": "alice-password"},
      {"email": "bob@example.com", "password": "bob-password"}
    ]
  },
  {
    "name": "机场B",
    "url": "https://airport-b.example.com",
    "captcha_id": "此处填写机场B的GeeTestV4验证码ID",
    "accounts": [
      {"email": "charlie@example.com", "password": "charlie-password"}
    ]
  }
]
```

上面的示例表示：**机场 A 有 2 个账号，机场 B 有 1 个账号**。实际机场数和账号数不限（受 GitHub Actions 运行时间和 Secret 大小限制）。

- `name`：机场显示名称，用于日志和钉钉、Server酱通知，可省略。
- `url`：**必填**。机场网站根地址，使用真实的 `https://...` 地址。
- `accounts`：**必填**。账号对象数组，每项必须包含 `email` 与 `password`。
- `captcha_id`：可选的 GeeTest V4 验证码 ID。**建议每个机场按自身情况填写**；省略时会使用代码中针对 `ikuuu.org` 的默认 ID，其他站点可能因 ID 不匹配而失败。并非所有机场都使用 GeeTest V4。
- 如果某机场的地址无效、没有有效账号，程序会记录提示并跳过该机场；单个账号签到失败不会阻断后续账号或其他机场。
- 如 `AIRPORTS` 整体不是合法 JSON，或没有任何有效账号，任务会因配置错误退出。请确认使用**双引号**、逗号和正确的括号，不要加入 JSON 注释。
- `AIRPORTS` 中包含**真实账号密码**，务必保存为 GitHub **Secret**，不要放在仓库文件、提交记录或公开聊天中。钉钉推送会显示机场名称和脱敏账号，机器人仍使用同一对 `DINGTALK_WEBHOOK` / `DINGTALK_SECRET`。

#### 配置钉钉机器人通知（加签鉴权）

1. 在需要接收签到通知的钉钉群中，进入 **群设置 → 机器人 / 智能群助手 → 添加自定义机器人**。
2. 填写机器人名称（例如“机场签到”），选择 **安全设置 → 加签**，复制 `SEC` 开头的密钥。无需额外设置关键词或固定 IP 白名单。
3. 勾选服务条款，点击 **完成**，再复制创建完成后钉钉提供的**完整 Webhook** 地址。
4. 在自己 Fork 的 GitHub **Settings → Secrets and variables → Actions → New repository secret** 中，分别添加 `DINGTALK_WEBHOOK` 和 `DINGTALK_SECRET`，务必与钉钉页面的值一致。
5. 按下面的步骤手动运行一次工作流，在 **Run sign** 日志中查看 `钉钉通知发送成功`，并检查钉钉群是否收到通知。

加签方式由程序自动生成毫秒级 `timestamp`、使用 `HMAC-SHA256` 和 Base64 计算签名，再将 `sign` URL 编码后附加到 Webhook。**GitHub Secret 中填写原始 Webhook 即可，无需手动拼接 `timestamp` 或 `sign`**。详细机制见 [钉钉自定义机器人文档](https://open.dingtalk.com/document/group/custom-robot-access)。

- `DINGTALK_WEBHOOK` 和 `DINGTALK_SECRET` **必须同时配置**才能启用钉钉通知；未配置时不影响签到。单独配置其中一个，日志会提示缺少另一项。
- 支持与 `SCKEY` 同时使用；通知包含成功、登录失败、验证码失败、签到失败或异常等结果。为保护隐私，通知中的账号邮箱会做简单脱敏。
- Webhook 中的 `access_token` 和 `SEC` 加签密钥都属于敏感信息，**不要放进公开仓库、Issues、PR、截图或聊天**。如不慎暴露，请在钉钉重置密钥并更新 GitHub Secrets。
- 代码只接受钉钉官方 `https://oapi.dingtalk.com/robot/send` 格式的 Webhook，不会向任意第三方 URL 发送密钥。
### 3. 手动运行一次

1. 在自己的 Fork 中进入 **Actions**。
2. 左侧选择 **Common airport Checkin**（工作流文件是 `main.yml`）。
3. 点击 **Run workflow**，选择 `main` 分支，再点击绿色的 **Run workflow**。
4. 在生成的运行记录中打开 **build → Run sign**，查看登录和签到结果。

> **注意**：工作流退出状态会反映账号失败数量：有任何账号签到失败就会返回非零退出码，显示为失败（红色）。请仍以 `Run sign` 的详细日志确认原因；钉钉通知发送成功只表示通知送达，不表示机场签到成功。

### 4. 每日自动签到

现有工作流同时支持手动触发 `workflow_dispatch` 和定时触发 `schedule`：

```yaml
schedule:
  - cron: "10 16 * * *"
```

它表示**每天 UTC 16:10**，即**北京时间次日 00:10（UTC+8）**。GitHub Actions 的定时任务可能延迟，不能保证精确到分钟。请确保 Fork 的 Actions 和定时工作流已启用；如长期没有运行，请到 Actions 页面检查是否被禁用。

## 常见问题

**工作流没有出现 / 找不到“Run workflow”**

确认进入的是自己的 Fork、Actions 已启用、查看的是 `main` 分支，并选择已有的 **Common airport Checkin** 工作流，而不是创建新工作流。

**提示“配置文件格式错误”或“AIRPORTS 必须是合法的 JSON 数组”**

旧模式请检查 `CONFIG` 是否按「邮箱一行、密码一行」成对填写，不要只填写一行或留空行。多机场模式请用 JSON 校验工具检查 `AIRPORTS` 格式，并确保数组包含有效的 `url` 和 `accounts`。

**登录请求失败 / 地址错误**

检查旧模式的 `URL` 或多机场模式各项 `url` 是否指向正确的机场站点根地址，以及该站点是否真的使用 `/auth/login` 和 `/user/checkin` 接口。

**验证码求解失败 / 登录返回验证码错误**

项目使用 GeeTest V4，默认 `CAPTCHA_ID` 针对 `ikuuu.org`。多机场模式可为每个机场单独设置 `captcha_id`，但其他站点若使用不同验证码方案或登录流程，则还需要适配代码。工作流会从第三方 [GeekedTest](https://github.com/xKiian/GeekedTest) 仓库获取求解器，第三方依赖变化也可能导致运行异常。

**验证码求解报 `KeyError` / `返回数据缺少字段`**

这是 GeekedTest 求解器处理极验返回数据时出现的字段缺失，**不代表你的 AIRPORTS 或钉钉 Secrets 配置错误**。新版本针对“极验响应缺少 `data`”会输出经过限制的 `status` 和数字 `code`，例如 `status=fail, code=60100`（仅为示例），同时不会打印完整验证码响应、令牌或敏感字段。如果响应不是有效 JSONP，则提示格式异常。极验官方的 [错误码文档](https://docs.geetest.com/gt4/apirefer/errorcode/web) 解释了 ID、网络及服务拒绝等不同错误原因；可以结合错误码排查。请勿公开实际账号密码或响应令牌。验证码失败时程序不会直接跳过验证去登录。

**没有收到钉钉机器人通知**

检查两个 Secrets 是否均已配置，机器人是否已经完成创建，Webhook 是否包含 `access_token`。检查 `Run sign` 的钉钉通知错误码；如果提示 `invalid signature`，重新复制加签密钥；如果提示 `invalid timestamp`，确认运行环境时间正确。没有真正进入登录或签到流程时不会发通知。多机场运行时，钉钉每个账号单独推送，消息中会附带机场名称。

**没有收到 Server酱推送**

确认是否创建了 `SCKEY` 且值正确；不创建 `SCKEY` 时脚本仍会尝试签到，只是不推送。

**需要分享运行日志**

日志可能包含账号邮箱、站点返回的数据或其他敏感信息，公开分享前请先打码；**不要分享 Secret 的真实值，包括 `AIRPORTS` 内的账号密码、钉钉 Webhook 和加签密钥**。
