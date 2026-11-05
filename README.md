# 《塞尔达传说：时之笛》主号补货监控

租赁页面：https://manygames.cn/games/library/cmw0iuzvc00gj01novq1f8s0d

使用 GitHub Actions 每5分钟启动一次检测（GitHub 调度可能延迟），通过 Playwright Chrome 读取主号库存。只检测“主号”，副号补货绝不触发；页面异常/数据不完整时不提示。

## 邮件通知方式（无 SMTP、无邮箱密码）

注意：GitHub 已在2026-10-15终止 **Push 事件专用邮件通知**。因此本方案**不使用 Push 邮件**，而是在主号明确补货后，创建一条 **GitHub Issue**，并将仓库拥有者设为受理人、在正文中 @ 提及。GitHub 的 Issue 通知可以按账号的邮件通知设置投递，投递成功与否依赖 GitHub 的邮件设置。

本仓库是公开仓库，所有 Issue 和运行日志都公开；Issue 仅写游戏、库存和时间，**不会放入邮箱地址、密码或账号信息**。无需配置任何 GitHub Secrets 或 Gmail 授权凭据。

## 你的设置（必须完成）

1. 打开 [仓库主页](https://github.com/2003wangziwen-code/zelda-stock-watch)，点击右上方的 **Watch → Custom → Issues** 并保存（或 Watch → All Activity）。这样能订阅仓库创建的新 Issue。
2. 打开 [GitHub 通知设置](https://github.com/settings/notifications)，在 **Subscriptions → Watching** 选择 **Email**，并确保 **Participating and @mentions** 邮件通知也开启；确认账户通知收件邮箱已验证。
3. 配好后，在 [Actions Variables](https://github.com/2003wangziwen-code/zelda-stock-watch/settings/variables/actions) 新建仓库变量 **ZELDA_STOCK_MONITOR_ENABLED**，值设为 **true**。在这之前定时任务已配置但会跳过。
4. 可以在 [Actions](https://github.com/2003wangziwen-code/zelda-stock-watch/actions) 手动运行 `Zelda main-account restock watcher`，保留 `dry_run=true`，只测试库存识别，不创建 Issue。主号可租后会自动创建标题为 `【主号补货】塞尔达传说：时之笛` 的 Issue，并尝试在发出唯一 Issue 后停止任务。

邮件是否成功投递必须经过实际的 **Issue 通知测试** 验证（用户启用上述设置后可通过手工创建明确标为“测试”的 Issue 进行验证）。仅看见 Actions 成功并不等于邮箱已经收到提醒。

## 检测原则

- 通过 Chrome 加载网页的动态库存，最多重试3次；无法明确识别视为 unknown。
- 当主号出现明确可租信息且没有售罄证据时，再发起第二次独立检测；两次均明确可租才触发通知。
- GitHub Issue 使用仓库内置 GITHUB_TOKEN 创建，不需要任何用户外部访问令牌。
- 对已发出的补货 Issue 按标题去重，并写入 `zelda-stock-watch/state.json` 防止重复提醒。脚本尝试停用监控工作流。
- 代码推送默认是测试模式，不会创建补货 Issue。

## 状态

程序曾于2026-11-05在 GitHub 运行器中实际识别到 `主号（已售罄）`。真实“补货”触发与 Issue 邮件投递还未发生、未做端到端验证。保留原 ChatGPT 每小时监控作为备用。

GitHub 官方说明：[配置 GitHub 通知](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications)，[Push 邮件功能已于2026-10-15退役](https://github.blog/changelog/2026-10-15-email-notifications-for-repository-push-events-have-been-retired/)。
