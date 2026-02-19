# Plan: 英文新闻源接入 + 中文翻译推送

## 状态：血肉层（完善与规范中）

---

## 血肉层任务清单

### 问题 1：部分英文标题未完全翻译

**现象：** Top 10 中有 4 篇文章标题仍保留 "News" 前缀或英文原文片段

**根因分析：**
- AI 返回格式不稳定：有时返回 "标题|摘要"，有时只返回摘要
- 解析逻辑过于简单：按 `|` 或换行分割，容易误判
- 某些页面正文过短（< 100 字），AI 直接跳过，返回 `(original_title, "")`

**修复方案：**
- [ ] 增强 AI prompt，明确要求输出格式
- [ ] 改进解析逻辑，处理边界情况
- [ ] 降低正文长度阈值或移除该限制（英文文章通常较短）
- [ ] 添加日志，记录翻译失败的文章

### 问题 2：代码健壮性

- [ ] 添加单元测试：测试英文源的翻译流程
- [ ] 错误处理：AI 调用失败时的降级策略
- [ ] 性能优化：避免对中文源增加不必要的参数传递

### 问题 3：文档和注释

- [ ] 更新 README.md：说明如何添加英文新闻源
- [ ] 补充代码注释：翻译逻辑的关键步骤

---

## 需求描述

当前所有新闻源均为中文网站。需要：
1. 支持添加英文新闻网站作为新闻源
2. 爬取英文文章后，将标题和摘要翻译为中文再推送

---

## 现有架构分析

| 模块 | 现状 | 对英文源的影响 |
|------|------|--------------|
| `NewsSource` 模型 | 无语言字段 | 无法区分中英文源 |
| `_crawl_one_source()` | 直接使用 HTML 原始标题 | 英文标题会原文展示 |
| `ai_summary.py` | Prompt 未明确指定输出语言 | 英文内容可能输出英文摘要 |
| 标题短过滤（< 4字符）| 按字符数过滤 | 英文标题字符数较多，不受影响 |
| 邮件模板 | 直接展示 `title` 和 `summary` | 英文标题会出现在中文邮件中 |
| 关键词匹配 | 支持中文关键词 | 中文关键词无法匹配英文标题 |

---

## 技术难点分析

### 难点 1：标题翻译
- 标题直接从 HTML 链接文本提取，爬虫不经过 AI 处理
- 需要新增标题翻译步骤，且不能过多增加 API 调用次数

### 难点 2：摘要翻译
- 当前 AI summary prompt 未指定输出语言
- 英文内容输入时，通义千问可能输出英文摘要
- 需修改 prompt，明确要求输出中文

### 难点 3：语言识别与区分
- 系统需知道某个新闻源是英文源，才能启用翻译流程
- 若对所有源都做翻译判断，会增加不必要开销

### 难点 4：翻译合并优化
- 为减少 API 调用，标题翻译应与摘要生成合并为一次调用
- 即：输入英文 HTML，一次性输出「中文标题 + 中文摘要」

---

## 可能的实现路径

### 方案 A：NewsSource 新增 language 字段（推荐）

在 `news_source` 表增加 `language` 字段（默认 `zh`，可选 `en`）：

1. **数据库**：`NewsSource` 增加 `language: str = "zh"` 字段
2. **爬虫**：`_crawl_one_source()` 将 `language` 传入，英文源触发翻译
3. **AI 摘要**：修改 `generate_summary_with_ai()`，增加 `translate_title` 参数，英文源时一次调用同时返回「中文标题 + 中文摘要」
4. **NewsItem**：标题字段存储翻译后的中文标题
5. **Admin 后台**：`NewsSourceView` 增加 language 下拉选项

**改动文件：**
- `backend/models/news_source.py`：增加 `language` 字段
- `backend/services/ai_summary.py`：扩展 prompt，支持翻译+摘要一体化
- `backend/services/news_crawler.py`：传递 language，英文源时调用翻译摘要
- `backend/admin/views.py`：增加 language 字段配置
- `alembic/`：新增数据库迁移脚本

**优点：** 语义清晰，不影响中文源流程，后续可扩展多语言
**缺点：** 需要 schema 变更和迁移

### 方案 B：自动检测语言

爬取后自动检测标题语言（如用 `langdetect` 库），若为英文则触发翻译：

**优点：** 无需修改数据库
**缺点：** langdetect 对短文本准确率低，引入额外依赖，不够可控

---

## 核心假设

1. **假设 1**：通义千问可在一次 API 调用中完成「翻译标题 + 生成中文摘要」，减少额外 API 开销
2. **假设 2**：主流英文能源新闻网站（如 Reuters Energy、Oil Price、Energy Monitor）结构清晰，CSS 选择器可正常提取文章链接
3. **假设 3**：英文源的文章链接标题字符数 ≥ 4，不会被短标题过滤误杀

---

## 推荐方案

**方案 A**，理由：
- 语言是新闻源的固有属性，加字段语义最准确
- 翻译逻辑只对英文源生效，不影响现有中文源性能
- 标题+摘要合并为一次 AI 调用，成本可控

---

## 待确认事项

1. ~~需要接入哪些英文新闻网站？（请提供候选网站列表）~~ ✅ 已完成调研
2. 是否需要对英文源的关键词规则也改为支持英文输入？

---

## 推荐英文新闻源（能源行业）

基于 2026 年最新调研，推荐以下英文能源新闻网站：

### 优先级 1（综合能源新闻 + 欧盟政策）

| 网站 | URL | 特点 |
|------|-----|------|
| **Clean Energy Wire** | https://www.cleanenergywire.org/ | 欧盟清洁能源和气候政策领先英文媒体 |
| **IEA News** | https://www.iea.org/news | 国际能源署官方，权威政策和数据 |
| **Utility Dive** | https://www.utilitydive.com/ | 电力、电网基础设施、能源政策深度报道 |
| **Canary Media** | https://www.canarymedia.com/ | 清洁能源转型专业报道 |

### 优先级 2（欧盟循环经济与产品合规）

| 网站 | URL | 特点 |
|------|-----|------|
| **EU Circular Economy Platform** | https://circulareconomy.europa.eu/platform/en/news-and-events/all-news | 欧盟官方循环经济新闻平台 |
| **European Commission - Energy** | https://energy.ec.europa.eu/index_en | 欧盟委员会能源政策官方页面 |
| **Circularise Blog** | https://www.circularise.com/blogs | DPP、ESPR、电池护照专业解读 |

### 优先级 3（可再生能源专项）

| 网站 | URL | 特点 |
|------|-----|------|
| **Recharge News** | https://www.rechargenews.com/ | 全球风能和太阳能行业领先媒体 |
| **Renewable Energy World** | https://www.renewableenergyworld.com/ | 清洁能源技术和项目报道 |

**推荐首批接入（5 个网站）：**
1. **Clean Energy Wire**（欧盟能源政策核心）
2. **EU Circular Economy Platform**（ESPR/DPP/电池法官方动态）
3. **IEA News**（国际能源署权威数据）
4. **Utility Dive**（电网和基础设施）
5. **Circularise Blog**（DPP 和电池护照技术解读）

---

## ESPR/DPP/电池法关键时间节点

| 时间 | 事件 |
|------|------|
| 2026 年 7 月 | 欧盟委员会部署中央 DPP 注册中心 |
| 2027 年 2 月 18 日 | 电池护照强制生效（EV 和工业电池 > 2 kWh） |
| 2028-2029 | 电子产品、家具、车辆纳入 DPP 要求 |
| 2030 | 所有产品组必须携带 DPP |

---

## 验收要求（概念层）

请确认以下内容后，输入"确认"进入骨架层：
1. 是否认可方案 A（NewsSource 增加 language 字段）？
2. 是否同意标题+摘要合并为一次 AI 调用？
3. 是否认可首批接入以下 5 个网站：
   - Clean Energy Wire
   - EU Circular Economy Platform
   - IEA News
   - Utility Dive
   - Circularise Blog

---

**调研来源：**
- [Clean Energy Wire - 2026 EU Climate and Energy Architecture](https://www.cleanenergywire.org/news/2026-set-shape-future-eus-climate-and-energy-architecture)
- [European Commission - Circular Economy](https://environment.ec.europa.eu/strategy/circular-economy_en)
- [EU Circular Economy Stakeholder Platform](https://circulareconomy.europa.eu/platform/en/news-and-events/all-news)
- [Circularise - Digital Product Passports](https://www.circularise.com/blogs/dpps-required-by-eu-legislation-across-sectors)
- [Hogan Lovells - Battery Passport Pilot](https://www.hoganlovells.com/en/publications/digital-product-passports-in-the-eu-comprehensive-expansion)
- [IEA News](https://www.iea.org/news)
- [Utility Dive](https://www.utilitydive.com/)
- [Canary Media](https://www.canarymedia.com/)
