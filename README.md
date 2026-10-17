# 通用机场签到 😍

使用 GitHub Actions 定时尝试登录机场网站并签到，获取站点提供的签到流量奖励；可选通过 [Server酱](https://sct.ftqq.com/) 推送结果。

> **兼容性说明**：此项目使用 SSPanel 常见的 `/auth/login` 和 `/user/checkin` 接口，但并不保证所有标注「Powered by SSPanel」的网站都可使用。当前 `main.py` 中的 GeeTest V4 验证码 ID 是针对 `ikuuu.org` 写死的，其他站点若使用不同验证码或登录流程，需要先适配代码。不要仅凭网页底部的 SSPanel 标识判断一定兼容。

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
| `URL` | **必填** | 机场站点根地址，例如 `https://example.com`；必须包含 `https://`（或站点实际使用的 `http://`），**末尾不要添加 `/`**。不要填登录页面的 `/auth/login` 地址。 |
| `CONFIG` | **必填** | 机场登录账号和密码，使用下面所示的**多行格式**：第一行邮箱、第二行密码；多账号时继续按「邮箱、密码」成对排列。 |
| `SCKEY` | 可选 | [Server酱](https://sct.ftqq.com/) 的 SendKey，用于推送签到结果；**不需要推送就不创建这个 Secret**。 |

#### `CONFIG` 的正确写法

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
- 工作流里虽然还传入了 `EMAIL`、`PASSWD`，但当前 `main.py` **不读取它们**，不需要配置这两项。
- Secrets 不会显示已保存的明文值；如果填错，可在同一页面更新。**不要把真实账号、密码或 SendKey 提交进 README、代码或 workflow 文件。**

### 3. 手动运行一次

1. 在自己的 Fork 中进入 **Actions**。
2. 左侧选择 **Common airport Checkin**（工作流文件是 `main.yml`）。
3. 点击 **Run workflow**，选择 `main` 分支，再点击绿色的 **Run workflow**。
4. 在生成的运行记录中打开 **build → Run sign**，查看登录和签到结果。

> **注意**：工作流显示绿色（Success）并不一定代表签到成功。请以 `Run sign` 步骤中的实际输出为准；当前脚本在部分异常情况下只打印错误信息，不会让作业失败。

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

**提示“配置文件格式错误”**

检查 `CONFIG` 是否按「邮箱一行、密码一行」成对填写，是否有插入的空白行。不要只填写一行，也不要把 `URL` 放进 `CONFIG`。

**登录请求失败 / 地址错误**

检查 `URL` 是否指向正确的机场站点根地址、不含末尾的 `/`，以及该站点是否真的使用 `/auth/login` 和 `/user/checkin` 接口。

**验证码求解失败 / 登录返回验证码错误**

项目使用 GeeTest V4，且代码中 `CAPTCHA_ID` 当前固定为 `ikuuu.org` 的站点参数。其他机场可能采用不同的验证码 ID 或流程，不能直接复用，需要根据目标站点适配。工作流还会从第三方 [GeekedTest](https://github.com/xKiian/GeekedTest) 仓库获取求解器，第三方依赖变化也可能导致运行异常。

**没有收到 Server酱推送**

确认是否创建了 `SCKEY` 且值正确；不创建 `SCKEY` 时脚本仍会尝试签到，只是不推送。

**需要分享运行日志**

日志可能包含账号邮箱、站点返回的数据或其他敏感信息，公开分享前请先打码；**不要分享 Secret 的真实值**。
