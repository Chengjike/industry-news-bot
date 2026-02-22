# 项目宪法：CLAUDE.md

**版本：** v3.1
**最后更新：** 2026-02-21
**适用项目：** 多行业新闻与金融信息推送机器人

本文档是项目的**长期记忆文件**，记录项目规范、协作流程、技术决策，供所有 Claude Code 实例和团队成员参考。

---

## 目录

- [一、四阶段协作规范](#一四阶段协作规范)
- [二、团队角色与分工](#二团队角色与分工)
- [三、复杂度评估标准](#三复杂度评估标准)
- [四、架构文档维护规范](#四架构文档维护规范)
- [五、文档体系](#五文档体系)
- [六、项目规范](#六项目规范)
- [七、决策记录模板](#七决策记录模板)
- [八、历史决策记录](#八历史决策记录)
- [九、复盘与持续优化](#九复盘与持续优化)

---

## 一、四阶段协作规范

每个阶段完成后必须输出总结，**🟢 等待 PM 明确确认后方可进入下一阶段**。

| 阶段 | 目标 | 主导 | 产出 | PM 验收标准 |
|:---|:---|:---:|:---|:---|
| 1. 概念层 | 可行性调研，**不修改代码** | PM | 调研结论、复杂度评分 | 确认需求方向和复杂度等级 |
| 2. 骨架层 | 最小代码验证核心假设，**允许粗糙** | ARCH | 可运行原型、更新 plan.md | 手动测试，确认核心假设成立 |
| 3. 血肉层 | 按规范完善代码（封装、健壮性、测试） | DEV | 完整代码、单元测试、测试报告 | 审查代码和测试报告 |
| 4. 记忆固化 | 将技术决策写入 CLAUDE.md | QA/PM | 更新后的 CLAUDE.md | 确认记录准确无误 |

---

## 二、团队角色与分工

| 代号 | 角色 | 核心职责 |
|:---:|:---|:---|
| PM | 产品经理 | 需求定义、验收标准、最终决策、提供设计方向 |
| PJM | 项目经理 | 项目计划、进度跟踪（高复杂度时启用） |
| ARCH | 架构师 | 系统设计、技术选型、模块划分 |
| DEV | 开发工程师 | 编码实现、单元测试、UI 实现 |
| QA | 质量保证 | 质量计划、过程审计、预防缺陷 |
| QC | 测试工程师 | 测试用例、功能/回归测试、缺陷报告 |
| OPS | 运维工程师 | 环境搭建、CI/CD、部署监控 |
| SEC | 安全工程师 | 威胁建模、安全测试（高复杂度时启用） |
| TW | 文档工程师 | 用户手册、API 文档（高复杂度时启用） |

**团队配置**：低复杂度（6-12分）→ PM+DEV+QA；中（13-20）→ PM+ARCH+DEV+QC+OPS；高（21-30）→ 全员。

---

## 三、复杂度评估标准

ARCH 牵头打分，PM 最终核定等级（6-12低 / 13-20中 / 21-30高），结果记录到历史决策。

| 维度 | 1分（低） | 3分（中） | 5分（高） |
|:---|:---|:---|:---|
| **功能规模** | 1-3个简单功能 | 4-10个功能，2-3页面 | >10功能，多模块复杂交互 |
| **技术难度** | 成熟技术栈，CRUD | 引入1-2个新库/API | 分布式、高并发、ML等 |
| **数据复杂性** | 1-2个简单实体 | 3-5个实体，简单关联 | >5实体，复杂关联，大数据量 |
| **外部依赖** | 无外部依赖 | 依赖1-2个成熟服务 | 依赖多个不稳定服务 |
| **非功能要求** | 无特殊要求 | 有性能要求，基本安全 | 高并发、金融级安全、合规认证 |
| **风险程度** | 失败无影响 | 影响单个功能，可快速回滚 | 影响核心业务，回滚复杂 |

---

## 四、架构文档维护规范

`ARCHITECTURE.md` 包含应用架构（Mermaid图示）、技术架构、部署架构三部分，必须与代码同步。

- 模块关系、技术选型、部署方式变更时，必须同步更新。
- 应用架构使用 Mermaid `graph TD` 表达模块关系，更新时预览源码等待 PM 确认。
- 各阶段触发：概念层记录预期变动 → 骨架层补充实际职责 → 血肉层记录选型理由 → 记忆固化追加 ADR。

---

## 五、文档体系

| 文档 | 用途 | 维护者 | 长期保留 |
|:---|:---|:---:|:---:|
| `CLAUDE.md` | 项目长期记忆（规范、决策） | 全体 | ✅ |
| `ARCHITECTURE.md` | 系统架构（含 Mermaid 图示） | ARCH | ✅ |
| `plan.md` | 当前迭代任务列表 | 全体 | ❌（迭代后归档） |
| `需求文档.md` | 当前功能需求细节 | PM | ⚠️ 项目结束前 |
| `测试报告.md` | 当前测试结果 | QC | ⚠️ 项目结束前 |
| `缺陷报告.md` | 当前缺陷列表 | QC | ❌（修复后更新） |

---

## 六、项目规范

**编码规范（Python）**：缩进 4 空格；变量/函数 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE_CASE`；每个函数必须有 docstring，复杂逻辑需行内注释；测试文件命名 `test_*.py`，放在 `tests/` 目录。

**测试要求**：每个功能点有对应单元测试（覆盖率 ≥ 80%）；集成测试覆盖核心流程；缺陷修复后必须添加回归测试。

**版本控制**：分支模型 `main` / `feature/*` / `fix/*`；提交信息遵循 Conventional Commits（`feat/fix/docs/refactor/test/chore`）；PR 需至少一人审查。

**任务跟踪**：使用 `plan.md`，任务标注状态（`[ ]`/`[x]`）和负责人（如 `@DEV`）。

---

## 七、决策记录模板

```markdown
### [功能名称] - YYYY-MM-DD

- **功能描述**：简要说明
- **评估参与人**：ARCH, DEV, QA, ...
- **复杂度评分**：规模X / 难度X / 数据X / 依赖X / 非功能X / 风险X → 总分XX（低/中/高）
- **PM 决策**：采用 [低/中/高] 团队配置（具体角色）
- **理由**：结合业务优先级和技术评估的简要说明
- **关键技术决策**：列出本次开发的关键技术点、选型理由
- **易错点与最佳实践**：记录易错点和后续开发应遵循的实践
- **改动文件**：列出主要修改的文件及改动摘要
- **注意事项**：预留扩展性、需重点关注的点
```

---

## 八、历史决策记录
此处按时间倒序记录所有历史决策。每次新功能完成后按第七节模板追加。

### 行业关键词过滤 + 路径前缀重构 - 2026-02-22

- **功能描述**：① 新闻推送前按行业关键词过滤无关内容；② 将管理后台路径从 `/admin` 改为 `/industry-news-bot/admin`，支持未来多服务扩展。
- **评估参与人**：ARCH, DEV, QA
- **复杂度评分**：规模2 / 难度3 / 数据2 / 依赖2 / 非功能3 / 风险3 → 总分15（中）
- **PM 决策**：PM + ARCH + DEV + QC，两个功能均采用方案C
- **关键技术决策**：
  - 行业关键词 OR 语义：`+词` 列表中至少命中一个即通过（区别于来源关键词的 AND 语义）
  - 行业关键词对标题+摘要做硬过滤，来源关键词仅对标题做加分过滤
  - 路径前缀：Nginx `location /industry-news-bot/` + `proxy_pass http://app:8000`（不带末尾 `/`，完整路径透传）
  - starlette-admin `base_url="/industry-news-bot/admin"`（完整路径，不依赖 FastAPI `root_path`）
  - FastAPI 路由同步更新：`/health` → `/industry-news-bot/health`，`/push-log/{id}/preview` → `/industry-news-bot/push-log/{id}/preview`
- **易错点与最佳实践**：
  - `proxy_pass` 末尾带 `/` 会剥离前缀，不带 `/` 才能完整透传路径
  - starlette-admin 子应用有独立中间件链，`root_path` 对其不生效，必须直接设置 `base_url`
  - Nginx volume mount 配置变更后容器不会自动重载，需执行 `nginx -s reload` 或重启容器
  - 未来部署统一使用 `bash /opt/news-bot/scripts/deploy.sh`（含自动 reload）
- **改动文件**：`models/industry.py`（新增 keywords 字段）、`database.py`（迁移）、`services/news_ranking.py`（OR 过滤 + 统计日志）、`tasks/scheduler.py`（传入 industry.keywords）、`admin/views.py`（IndustryView 新增 keywords 字段 + base_url）、`app.py`（路由前缀）、`nginx/conf.d/app.conf`（路径前缀）、`scripts/deploy.sh`（新建）

### 新闻源健康检查机制 - 2026-02-21

- **功能描述**：为每个新闻源增加健康状态监控，支持每日自动检查（06:00）和 Admin 手动触发，连续失败 ≥3 次发送告警邮件。
- **评估参与人**：ARCH, DEV, QA
- **复杂度评分**：规模3 / 难度3 / 数据2 / 依赖2 / 非功能3 / 风险2 → 总分15（中）
- **PM 决策**：PM + ARCH + DEV + QC，采用方案C（自动检查 + 手动按钮）
- **关键技术决策**：
  - 失败只更新状态字段，**不影响推送任务**（与推送失败计数器完全独立）
  - 并发检查（`asyncio.Semaphore(5)`），避免串行检查慢源阻塞整体
  - ORM 实例不跨 session 使用：`_check_and_save` 接收基础属性而非 ORM 对象，每次写入用独立 session
  - Admin 颜色徽章：通过 `serialize_field_value` 覆盖渲染，与 `PushLogView` 保持一致的实现模式
  - 告警邮件复用 `_send_failure_alert` 模式（与推送失败告警相同的 FastMail 实现）
- **易错点与最佳实践**：
  - `check_one_source` 接收的是轻量 proxy 对象，不是 ORM 实例，避免 `DetachedInstanceError`
  - `consecutive_failures` 在 `check_sources_by_ids`（手动）和 `run_health_check_all`（自动）中均维护，成功时重置为 0
  - `health_status` 字段默认值 `unknown`，新建源未检查前显示「未知」徽章
- **改动文件**：`models/news_source.py`、`database.py`、`services/source_health_checker.py`（新建）、`admin/views.py`、`tasks/scheduler.py`

### Admin 登录失败修复（HTTPS 反向代理 session 丢失） - 2026-02-21

- **功能描述**：修复 ECS HTTPS 环境下 Admin 登录后跳回登录页的问题。
- **根本原因**：Nginx→uvicorn 内部是 HTTP，starlette-admin 子应用读取 `scope["scheme"]` 得到 `http`，导致：1) 登录表单 action 为 `http://`（浏览器警告）；2) 登录后 303 重定向到 `http://`，Nginx 再 301 跳转到 `https://` 时不携带 cookie，session 丢失。
- **最终方案**：自定义 `ForwardedProtoMiddleware` ASGI 中间件，读取 `X-Forwarded-Proto` 头直接修改 `scope["scheme"]`，使 starlette-admin 子应用感知真实协议。
- **关键技术决策**：
  - FastAPI 的 `add_middleware` 对 `mount_to()` 挂载的子应用**不生效**，必须修改底层 `scope`。
  - `ProxyHeadersMiddleware`（starlette 内置）在旧版本不存在，需自行实现。
  - `https_only=False`：Nginx→uvicorn 是内部 HTTP，Secure cookie 在此链路无法传递。
  - **docker compose `.env` 中 `$` 必须写成 `$$`**：bcrypt hash 含多个 `$`，不转义会被 compose 展开为空变量，导致 `Invalid salt` 错误。在 ECS 上写入 `.env` 时需用 Python 处理，避免 shell 展开。
- **多轮修复的教训**：
  - **先确认 ECS 环境版本**，再选用依赖库的功能，避免用了不存在的模块。
  - **commit 后立即 push**，部署前确认 `git log` 版本一致，否则 ECS 拉到旧代码浪费调试轮次。
  - **隔离变量诊断**：先用 `docker exec` 直接测 uvicorn（绕过 Nginx），确认问题层级再修复。
  - **starlette-admin 子应用中间件隔离**：挂载的子应用有独立中间件链，外层中间件不透传。
- **改动文件**：`backend/app.py`（`ForwardedProtoMiddleware`、登录速率限制）、`nginx/conf.d/app.conf`（安全响应头、`proxy_redirect`）、`backend/admin/views.py`（登录审计日志）、`backend/utils/log_sanitizer.py`（补充 API Key 脱敏）

### 晚报金融数据推送（时间戳 + 期货数据修复） - 2026-02-20

- **功能描述**：为晚报邮件中的金融数据添加时间戳，并修复失效的期货 API。
- **评估参与人**：ARCH, DEV, QA
- **复杂度评分**：规模3 / 难度4 / 数据3 / 依赖4 / 非功能3 / 风险3 → 总分20（中）
- **PM 决策**：PM + ARCH + DEV + QC + OPS
- **理由**：业务优先级高，需快速修复生产问题；技术实现需替代 API 并保证数据准确。
- **关键技术决策**：
  - 时间戳：`FinanceQuote` 增加 `timestamp` 字段，`datetime.now()` 记录，邮件显示 `HH:MM:SS`。
  - 期货 API：`futures_zh_spot()` 失效，改用 `futures_global_spot_em()`，实现代码/关键词智能匹配。
- **易错点与最佳实践**：
  - 期货合约代码有到期日，需定期更新主力合约。
  - AKShare API 不稳定，需检查价格有效性（过滤 NaN/0）。
  - 数据精度统一：价格和涨跌幅保留 2 位小数。
- **改动文件**：`finance_crawler.py`（时间戳+重写期货函数）、`email_evening.html`（新增时间戳列）、`setup_finance_items.py`（移除碳酸锂）
- **注意事项**：碳酸锂数据需后续调研替代 API（如交易所官方接口）。

### HTTPS 安全传输配置 - 2026-02-20

- **功能描述**：将 ECS 管理界面从 HTTP 升级为 HTTPS，使用自签名证书。
- **评估参与人**：ARCH, DEV, OPS
- **复杂度评分**：规模2 / 难度3 / 数据1 / 依赖3 / 非功能4 / 风险3 → 总分16（中）
- **PM 决策**：PM + ARCH + DEV + OPS
- **理由**：安全要求高，需加密敏感信息传输，实现相对独立。
- **关键技术决策**：自签名证书 + HTTP 301 强制跳转；Nginx TLS 1.2/1.3，443 端口；提供续期脚本和健康检查脚本。
- **易错点与最佳实践**：证书 CN 需匹配 ECS 公网 IP；私钥权限 600，不提交 Git；443 端口需在安全组开放。
- **改动文件**：`nginx/conf.d/app.conf`、`docker-compose.yml`、`ssl/`、`.gitignore`、`scripts/renew-ssl-cert.sh`、`scripts/check-https.sh`
- **注意事项**：证书有效期 365 天，需 cron 定时续期。

### 英文新闻源接入 + 中文翻译推送 - 2026-02-19

- **功能描述**：接入 5 个英文能源新闻网站，将英文标题和摘要翻译为中文后推送。
- **评估参与人**：ARCH, DEV, QA
- **复杂度评分**：规模4 / 难度4 / 数据3 / 依赖4 / 非功能2 / 风险2 → 总分19（中）
- **PM 决策**：PM + ARCH + DEV + QC
- **理由**：内容多样性需求明确，AI 翻译可自动化，技术风险可控。
- **关键技术决策**：`NewsSource` 增加 `language` 字段（`zh`/`en`）；英文源一次 AI 调用完成翻译+摘要，返回 `(标题, 摘要)`。
- **易错点与最佳实践**：AI prompt 需明确输出格式；英文文章正文长度阈值降低（100→50字符）；调用方适应返回值从 `str` 变为 `tuple`。
- **改动文件**：`news_source.py`、`database.py`、`ai_summary.py`、`news_crawler.py`、`scheduler.py`、`admin/views.py`
- **注意事项**：测试需覆盖多语言源，确保翻译质量。

### 新闻来源多样性优化 - 2026-02-19

- **功能描述**：解决早报 Top 10 文章来源单一（全部来自能源界）的问题。
- **评估参与人**：ARCH, DEV, QA
- **复杂度评分**：规模2 / 难度3 / 数据2 / 依赖1 / 非功能2 / 风险3 → 总分13（中）
- **PM 决策**：PM + ARCH + DEV + QA
- **理由**：核心算法逻辑调整，需保证去重机制正确，影响推送质量。
- **关键技术决策**：`SeenArticle` 写入时机从"爬取后"改为"推送后"，避免慢速来源文章被永久锁死。
- **易错点与最佳实践**：语义变更需彻底，测试用例同步更新；旧数据不影响新推送逻辑。
- **改动文件**：`news_crawler.py`（移除爬取时写入）、`scheduler.py`（推送后写入）、`tests/test_crawler.py`
- **注意事项**：监控推送后来源分布，确保优化有效。

---

## 九、复盘与持续优化

**触发条件**：完成重要功能（架构变更/多文件改动）、Token > 100k、耗时 > 2 小时、月度总结。
**输出文档**：`docs/retrospective-YYYY-MM-DD.md`（包含时间分布、Token分析、瓶颈识别、优化方案）。

### 三模式分级开发（基于 2026-02-20 复盘）

| 模式 | 适用场景 | 流程 |
|:---|:---|:---|
| 快速模式 | < 30 分钟（Bug修复、文档更新） | 直接实现 → 本地测试 → 提交 |
| 标准模式 | 30-120 分钟（新功能、功能增强） | 快速调研 → 骨架+血肉合并 → 记忆固化 |
| 完整模式 | > 120 分钟（架构变更、复杂功能） | 完整四阶段 |

**已验证优化项**：`TQDM_DISABLE=1` 禁用进度条；heredoc 批量 SSH；`docker-compose.dev.yml` 热加载；`plan.md` 只记录关键决策和任务清单。

### 安全加固 Phase 1 + 稳定性加固 Phase 2 - 2026-02-21

- **功能描述**：架构审视后执行的两阶段加固：Phase 1 安全加固，Phase 2 稳定性加固。
- **评估参与人**：ARCH, SEC, OPS, DEV
- **复杂度评分**：规模3 / 难度3 / 数据2 / 依赖2 / 非功能4 / 风险3 → 总分17（中）
- **PM 决策**：PM + ARCH + DEV + SEC + OPS

#### Phase 1 安全加固（已完成）

- **关键技术决策**：
  1. `ForwardedProtoMiddleware`：自定义 ASGI 中间件修改 `scope["scheme"]`，解决 starlette-admin 子应用感知不到 HTTPS 的问题（根本原因：子应用有独立中间件链，外层 `add_middleware` 不传播）
  2. bcrypt 密码：`ADMIN_PASSWORD` 改为 bcrypt hash（`$2b$12$...`），启动时校验不允许明文
  3. 登录速率限制：内存 `defaultdict` 实现，10次/分钟/IP
  4. Nginx 安全头：X-Frame-Options、CSP、HSTS、X-Permitted-Cross-Domain-Policies、server_tokens off
  5. 日志脱敏扩展：覆盖 API Key、Token、Secret、Bearer、Fernet 加密串
  6. `/push-log/{id}/preview` 端点加认证检查

- **易错点**：
  - docker compose `.env` 中 bcrypt hash 的 `$` 符号**不需要转义**，直接写原始 hash
  - `https_only=True` 在 SessionMiddleware 中必须开启，但 Nginx→uvicorn 内部是 HTTP，需要 `ForwardedProtoMiddleware` 先修正 scheme
  - starlette-admin 子应用的中间件隔离：必须在 ASGI scope 层面修改，不能依赖 FastAPI 的 `add_middleware`

#### Phase 2 稳定性加固（已完成）

- **关键技术决策**：
  1. 网络重试：`_fetch_page()` 指数退避重试（1s/2s/4s），超时和 5xx 重试，4xx 不重试
  2. 数据库事务隔离：失败日志改用独立 `AsyncSessionLocal` session 写入，避免主 session 脏状态污染
  3. 推送失败告警：连续失败 3 次后发送告警邮件，成功后重置计数器（`_consecutive_failures` 内存字典）
  4. 数据清理优化：快照 3 天清空（保留记录）、日志保留 30 天、清理后执行 VACUUM
  5. 容器资源限制：app 1CPU/1GB，nginx 0.5CPU/256MB
  6. 日志轮转：app 100m×10，nginx 50m×5
  7. 健康检查增强：`/health` 验证 DB 连接和 scheduler 状态，异常返回 503
  8. 启动时密钥校验：`_validate_secrets()` 拒绝默认值和明文密码启动

- **改动文件**：`backend/app.py`、`backend/admin/views.py`、`backend/tasks/scheduler.py`、`backend/services/news_crawler.py`、`nginx/conf.d/app.conf`、`docker-compose.yml`、`backend/utils/log_sanitizer.py`、`scripts/backup_db.sh`（新增）

---

### 阶段性方案回顾评审 - 2026-02-21

**评审结论（ARCH 综合）：**

| 维度 | 评分 |
|------|------|
| 功能完整性 | 8/10 |
| 代码质量 | 7.5/10 |
| 安全性 | 7/10 |
| 可靠性 | 6.5/10 |
| 可维护性 | 7/10 |
| 运维就绪度 | 6/10 |
| **整体** | **7/10 — Beta 阶段** |

**下一阶段 Top 5 优先级：**

1. 🔴 P1：新闻源健康检查机制（每天自动验证 CSS 选择器有效性）
2. 🔴 P1：多 SMTP 配置 + 故障转移（消除 SMTP 单点故障）
3. 🟡 P2：数据库自动备份接入 cron（ECS 上配置 `backup_db.sh`）
4. 🟡 P2：管理后台配置验证按钮（NewsSource/FinanceItem 保存前实时验证）
5. 🟡 P2：操作审计日志（记录所有管理后台增删改操作）

**主要风险：** 外部依赖脆弱性（新闻源选择器、期货 API）、SMTP 单点故障、无外部监控系统、数据库无备份。

---

## 十、变更日志

### 2026-02-21 安全加固 Phase 1 + 稳定性加固 Phase 2

| 文件 | 改动 |
|------|------|
| `backend/app.py` | 新增 `_validate_secrets()` 启动校验；新增 `ForwardedProtoMiddleware`；Session Cookie 加 `https_only=True`、`same_site="strict"`；`/health` 增加 DB 和 scheduler 状态检查；`/push-log/{id}/preview` 加认证 |
| `backend/admin/views.py` | 登录支持 bcrypt hash；接入速率限制；完善登录日志 |
| `backend/tasks/scheduler.py` | 新增 `_consecutive_failures` 计数器和 `_send_failure_alert()`；失败日志改用独立 session；清理策略优化（快照3天、日志30天、VACUUM） |
| `backend/services/news_crawler.py` | `_fetch_page()` 增加指数退避重试（3次，1s/2s/4s） |
| `nginx/conf.d/app.conf` | 新增 HSTS、`server_tokens off`、`X-Permitted-Cross-Domain-Policies` |
| `docker-compose.yml` | 新增容器资源限制（CPU/内存）、日志轮转配置 |
| `backend/utils/log_sanitizer.py` | 扩展脱敏规则：API Key、Token、Secret、Bearer、Fernet |
| `scripts/backup_db.sh` | 新增 SQLite 热备份脚本（保留30天，支持 cron） |

### 2026-02-21 新闻源健康检查机制

| 文件 | 改动 |
|------|------|
| `backend/models/news_source.py` | 新增 4 个健康检查字段：`health_status`（unknown/healthy/warning/error）、`last_check_at`、`last_error`、`consecutive_failures` |
| `backend/database.py` | 新增 4 条 `ALTER TABLE` 迁移语句，应用启动时自动执行 |
| `backend/services/source_health_checker.py` | 新建健康检查服务：`check_one_source()`（10s 超时）、`run_health_check_all()`（并发=5）、`check_sources_by_ids()`（Admin 按钮调用）、`_send_health_alert()`（连续失败≥3次告警） |
| `backend/admin/views.py` | `NewsSourceView` 新增健康状态只读字段 + `serialize_field_value` 渲染颜色徽章 + 「测试健康状态」Action 按钮 |
| `backend/tasks/scheduler.py` | 注册每日 06:00 `run_health_check_all` 定时任务 |

---

> 本文档需要您和所有 AI Agent 共同维护。当您发现任何需要长期记忆的规范或决策时，请及时更新。
