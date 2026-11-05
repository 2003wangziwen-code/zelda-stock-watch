# 《塞尔达传说：时之笛》主号补货提醒

监控页面：https://manygames.cn/games/library/cmw0iuzvc00gj01novq1f8s0d

本仓库使用 GitHub Actions + Playwright 浏览器，每5分钟检查一次页面，只在“主号”出现明确可租信息时发出一次电子邮件。**副号补货不能触发。** GitHub Actions 定时任务可能延迟运行，不代表精确5分钟。

## 当前部署状态
代码提交后会自动执行一次只读试运行。**正式邮件监控默认关闭**，需要先确认网站可以检测、配置发件邮箱，并在 Actions Variables 中启用。站点采用动态数据，无法识别时会记录 unknown 并保持静默，避免误报。

## 邮箱配置
在 [仓库设置](https://github.com/2003wangziwen-code/zelda-stock-watch/settings/secrets/actions) 的 **Secrets → New repository secret** 添加：
- `ZELDA_SMTP_USER`：发件 Gmail 地址
- `ZELDA_SMTP_APP_PASSWORD`：Gmail 应用专用密码（不是登录密码，通常需开启两步验证）
- `ZELDA_EMAIL_TO`：收件邮箱

如果不是 Gmail，可选添加 `ZELDA_SMTP_HOST`、`ZELDA_SMTP_PORT`（默认 smtp.gmail.com:465）。

注意：不要将密码提交到代码、Issue 或聊天。

## 启用流程
1. 进入 [Actions](https://github.com/2003wangziwen-code/zelda-stock-watch/actions) → **Zelda main-account restock watcher**，看试运行日志，确认出现 Main account status: sold_out。若出现 unknown，说明当前页面未能可靠识别，不能直接启用。
2. 完成前述邮箱 Secrets 的配置，然后进入 [Actions](https://github.com/2003wangziwen-code/zelda-stock-watch/actions) → **Zelda email configuration test** → **Run workflow**。收到标题含“测试成功”的邮件后，确认 SMTP 通道可用。这是测试邮件，不代表补货。
3. 在 [Actions Variables](https://github.com/2003wangziwen-code/zelda-stock-watch/settings/variables/actions) 新增名为 `ZELDA_STOCK_MONITOR_ENABLED`、值为 `true` 的仓库变量。这会启动每5分钟的检查。
4. 库存确认后发邮件，并写入 `zelda-stock-watch/state.json` 防止重复发送；流程会尝试自动关闭自己。若没有确认主号明确可租，程序不会发邮件。

GitHub Actions 在公开仓库的标准托管运行器免费，但 GitHub 可能延迟或暂停计划任务。原有 ChatGPT 每小时补货监控可作为备用。

## 工作方式和测试
- 使用 Playwright 控制 GitHub Ubuntu 运行器预装的 Chrome 渲染页面；网页加载不完整时最多尝试3次。
- 只接受对应主号选项的明确正库存文案，且没有任何主号已售罄证据；副号、混合标签和无法判定均不提醒。
- 邮件发送成功后才保存通知记录，避免邮件失败造成漏报。
- 首次代码推送会运行检测测试和实时页面只读检查，**不会发送邮件**。
