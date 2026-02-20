# 多行业新闻与金融信息推送机器人

## 业务需求核心要点

**多行业支持：** 通过Web界面配置多个行业，每个行业独立管理新闻源、金融数据项、收件人及推送计划。

**早报推送（每天9:00）：** 采集前一天的行业新闻（网页抓取），经过去重、打分排序后，推送Top N条（N可配置）。新闻包含标题、AI生成的摘要（140字）、发布时间、原文链接。

**晚报推送（每天18:00）：** 采集大宗商品价格（如铜、铝）和行业龙头股价，包含最新价、涨跌幅及数据获取时间，数据来源为国产开源库AKShare。

**Web管理界面：** 管理员登录后可配置SMTP、行业、新闻源（含权重、关键词语法）、金融项、收件人邮箱，所有敏感信息加密存储。

**AI摘要生成：** 使用阿里云通义千问API阅读全文后生成高质量摘要，提升阅读体验。

**新闻打分机制：** 综合时效性、关键词匹配度（支持+必须词、!过滤词）、来源权重，参考TrendRadar算法，只推送最重要的新闻。

**去重机制：** 基于标题语义去重（使用semhash），避免重复推送。

**邮件合规：** 邮件底部添加侵权联系邮箱和退订说明，仅推送标题+摘要+链接，符合著作权法规。

**安全与合规：** 个人信息加密存储，SSRF防护，日志脱敏，依赖漏洞扫描。

---

## 晚报金融数据推送

系统支持每天 18:00 推送行业相关的金融数据（股票价格、大宗商品价格），数据来源为 AKShare 开源库。

### 功能特性

- **A 股数据**：支持获取沪深 A 股实时行情（最新价、涨跌幅）
- **期货数据**：支持获取国内期货现货价格（铜、铝等大宗商品）
- **数据时间戳**：每个金融数据都包含获取时间（精确到秒）
- **数据精度**：价格和涨跌幅均保留 2 位小数
- **自动推送**：每天 18:00 自动发送晚报邮件

### 配置金融数据项

#### 通过 Admin 后台配置

1. 登录 Admin 后台（`https://<服务器IP>/admin`）
2. 进入「金融数据项管理」
3. 点击「新增」，填写以下字段：
   - **代码**：股票代码（如 `300274`）或期货合约代码（如 `cu2505`）
   - **名称**：显示名称（如 `阳光电源` 或 `沪铜主力`）
   - **类型**：选择 `stock`（股票）或 `futures`（期货）
   - **所属行业**：选择关联的行业
4. 保存后，下次晚报推送时会自动包含该数据

#### 通过脚本批量配置

```bash
# 在 ECS 上执行
cd /opt/news-bot
docker compose exec app python scripts/setup_finance_items.py
```

### 数据示例

#### 晚报邮件内容

```
【新能源行业】行业晚报 - 今日行情

行业龙头股价
┌────────┬────────┬──────┬──────────┬──────────┐
│ 名称   │ 代码   │ 最新价│ 涨跌幅   │ 数据时间 │
├────────┼────────┼──────┼──────────┼──────────┤
│ 阳光电源│ 300274 │ 149.16│  -4.72%  │ 15:03:50 │
│ 宁德时代│ 300750 │ 365.34│  -2.80%  │ 15:03:48 │
│ 隆基绿能│ 601012 │  18.13│  -1.95%  │ 15:03:54 │
└────────┴────────┴──────┴──────────┴──────────┘

大宗商品行情
┌────────┬────────┬──────┬──────────┬──────────┐
│ 品种   │ 代码   │ 最新价│ 涨跌幅   │ 数据时间 │
├────────┼────────┼──────┼──────────┼──────────┤
│ 沪铜主力│ cu2505 │12863.00│ +0.19%  │ 15:00:50 │
│ 沪铝主力│ al2505 │ 3088.50│ +0.65%  │ 15:00:50 │
└────────┴────────┴──────┴──────────┴──────────┘
```

### 支持的金融数据类型

| 类型 | 数据源 | 示例代码 | 说明 |
|------|--------|---------|------|
| A 股 | AKShare `stock_zh_a_spot_em()` | `300274` | 阳光电源 |
| 港股 | AKShare `stock_hk_spot_em()` | `00700` | 腾讯控股 |
| 期货 | AKShare `futures_global_spot_em()` | `cu2505` | 沪铜 2025年5月合约 |

**注意事项：**

- **期货合约代码需定期更新**：期货合约有到期日，如 `cu2505` 表示 2025年5月交割的沪铜合约，到期后需更新为最新主力合约（如 `cu2507`）
- **期货数据获取时间**：建议在期货日盘收盘后（15:00 之后）推送晚报
- **部分商品数据暂不可用**：碳酸锂期货数据由于 AKShare API 限制，暂时无法获取，正在调研替代方案

## 多语言新闻源支持

系统支持中文和英文新闻源。英文新闻源的标题和摘要会自动翻译为中文后推送。

### 添加英文新闻源

1. 登录 Admin 后台（`https://<服务器IP>/admin`）
2. 进入「新闻源管理」
3. 点击「新增」，填写以下字段：
   - **来源名称**：如 `IEA News`
   - **新闻列表页地址**：如 `https://www.iea.org/news`
   - **链接选择器**：CSS 选择器，如 `article a`（用于提取文章链接）
   - **权重**：1-10，影响文章在 Top N 中的排名
   - **关键词**：可选，支持 `+必须词 !排除词 普通词` 语法
   - **语言**：选择 `英文`（重要！）
   - **所属行业 ID**：关联到具体行业
4. 保存后，下次早报推送时会自动爬取并翻译

### 推荐的英文新闻源

| 网站 | URL | 领域 | 链接选择器 |
|------|-----|------|-----------|
| IEA News | https://www.iea.org/news | 国际能源政策 | `article a` |
| Clean Energy Wire | https://www.cleanenergywire.org/ | 欧盟清洁能源 | `a` |
| EU Circular Economy Platform | https://circulareconomy.europa.eu/platform/en/news-and-events/all-news | ESPR/DPP/电池法 | `a` |
| Utility Dive | https://www.utilitydive.com/ | 电网基础设施 | `a` |

### 技术实现

- 英文源爬取后，标题和正文通过阿里云通义千问 API 一次性翻译为中文
- 翻译后的中文标题和摘要与中文源文章一起参与打分排序
- 自动移除常见前缀（如 "News"、"Coal"、"Electricity" 等分类标签）

---

## HTTPS 安全访问

系统默认使用 HTTPS 加密传输，保护管理员登录密码、SMTP 配置等敏感信息。

### 访问地址

- **管理界面**：`https://<ECS-IP>/admin`
- **健康检查**：`https://<ECS-IP>/health`

**注意：** HTTP 访问会自动跳转到 HTTPS（301 重定向）

### 首次访问证书警告

由于使用自签名证书，浏览器首次访问会显示安全警告。这是正常现象，证书提供的加密强度与正规证书完全相同（TLS 1.2/1.3 + RSA 2048）。

**处理方法：**
- **Chrome/Edge**：点击「高级」→「继续访问 <ECS-IP>（不安全）」
- **Firefox**：点击「高级」→「接受风险并继续」

### 消除浏览器警告（可选）

如果希望后续访问不再显示警告，可以手动信任证书：

#### Chrome/Edge

1. 访问 `https://<ECS-IP>/admin`，点击地址栏的"不安全"图标
2. 点击「证书无效」→「详细信息」→「导出」
3. 保存为 `newsbot.crt`
4. 设置 → 隐私和安全 → 安全 → 管理证书 → 受信任的根证书颁发机构 → 导入
5. 选择 `newsbot.crt`，点击确定
6. 重启浏览器，再次访问应该不再警告

#### Firefox

1. 访问 `https://<ECS-IP>/admin`，点击「高级」→「接受风险并继续」
2. 点击地址栏的锁图标 → 「连接不安全」→「更多信息」→「查看证书」→「下载 PEM (证书)」
3. 设置 → 隐私与安全 → 证书 → 查看证书 → 证书颁发机构 → 导入
4. 选择下载的证书，勾选「信任此 CA 标识网站」
5. 重启浏览器

---

## 部署指南

### 生产环境部署（ECS）

#### 1. 拉取代码

```bash
ssh root@<ECS-IP>
cd /opt/news-bot
git pull
```

#### 2. 生成 SSL 证书（首次部署）

```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/selfsigned.key \
  -out ssl/selfsigned.crt \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=NewsBot/CN=$(curl -s ifconfig.me)"
```

**说明：**
- 证书有效期：365 天
- 加密算法：RSA 2048 位
- 过期前需重新生成（见下方"证书续期"章节）

#### 3. 开放 443 端口（首次部署）

在阿里云控制台操作：
1. ECS 控制台 → 实例 → 安全组配置
2. 配置规则 → 入方向规则 → 添加规则
3. 协议：TCP，端口：443/443，授权对象：0.0.0.0/0

#### 4. 启动服务

```bash
docker compose down
docker compose up -d
```

#### 5. 验证部署

```bash
# 测试 HTTPS 访问
curl -k https://localhost/health
# 应返回：{"status":"ok"}

# 测试 HTTP 跳转
curl -I http://localhost/admin
# 应返回：301 Moved Permanently
```

### 证书续期

自签名证书有效期 365 天，到期前需重新生成。

#### 手动续期

```bash
cd /opt/news-bot
# 备份旧证书
mv ssl/selfsigned.crt ssl/selfsigned.crt.bak
mv ssl/selfsigned.key ssl/selfsigned.key.bak

# 生成新证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/selfsigned.key \
  -out ssl/selfsigned.crt \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=NewsBot/CN=$(curl -s ifconfig.me)"

# 重启 Nginx
docker exec news_bot_nginx nginx -s reload
```

#### 自动续期（推荐）

创建续期脚本 `/opt/news-bot/scripts/renew-ssl-cert.sh`：

```bash
#!/bin/bash
cd /opt/news-bot
mv ssl/selfsigned.crt ssl/selfsigned.crt.bak
mv ssl/selfsigned.key ssl/selfsigned.key.bak

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/selfsigned.key \
  -out ssl/selfsigned.crt \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=NewsBot/CN=$(curl -s ifconfig.me)"

docker exec news_bot_nginx nginx -s reload
```

添加 cron 定时任务（每年执行一次）：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每年 1 月 1 日凌晨 2 点执行）
0 2 1 1 * /bin/bash /opt/news-bot/scripts/renew-ssl-cert.sh >> /opt/news-bot/logs/ssl-renew.log 2>&1
```

---

## 常见问题

### 1. 无法访问 HTTPS（ERR_CONNECTION_REFUSED）

**排查步骤：**

```bash
# 检查容器状态
docker compose ps

# 检查端口监听
netstat -tuln | grep 443

# 查看 Nginx 日志
docker compose logs nginx

# 验证证书文件
ls -lh /opt/news-bot/ssl/
```

**常见原因：**
- 证书文件不存在 → 运行证书生成命令
- 443 端口未开放 → 检查 ECS 安全组规则
- Nginx 容器未启动 → 运行 `docker compose up -d`

### 2. 浏览器显示 "ERR_CERT_AUTHORITY_INVALID"

这是正常现象，因为使用的是自签名证书。点击"高级" → "继续访问"即可。如需消除警告，请按照上方"消除浏览器警告"章节操作。

### 3. HTTP 不跳转到 HTTPS

```bash
# 检查 Nginx 配置
docker exec news_bot_nginx cat /etc/nginx/conf.d/app.conf | grep "return 301"

# 应该看到：return 301 https://$host$request_uri;
```

如果没有，拉取最新代码并重启：
```bash
git pull
docker compose down
docker compose up -d
```

---

## 技术支持

如遇问题，请查看：
- 架构文档：`ARCHITECTURE.md`
- 开发规范：`CLAUDE.md`
- 项目 Issues：https://github.com/Chengjike/industry-news-bot/issues
