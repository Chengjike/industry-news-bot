# Plan: ECS 管理界面 HTTPS 配置

## 状态：骨架层 - 最小可行性验证中

**创建日期：** 2026-02-20
**概念层完成：** 2026-02-20
**骨架层开始：** 2026-02-20

---

## 需求描述

当前 ECS 上的管理界面（Admin UI）访问使用 HTTP 协议（`http://<ECS-IP>/admin`），存在以下安全风险：
1. **明文传输**：管理员登录密码、SMTP 配置等敏感信息在网络中明文传输，可能被中间人截获
2. **身份验证风险**：无法确认服务器真实性，可能遭受中间人攻击
3. **合规性问题**：现代浏览器（Chrome、Firefox）会对 HTTP 表单提交警告"不安全"，影响用户体验

**目标：** 将管理界面访问协议升级为 HTTPS，确保数据传输加密。

**使用场景：** 仅管理员个人使用，无域名，需要安全性。

**已选方案：** 方案 C - 自签名证书

---

## 现有架构分析

### 当前部署架构

```
用户浏览器 --> [HTTP:80] --> Nginx (Docker) --> [HTTP:8000] --> FastAPI App (Docker)
```

**现状：**
- `docker-compose.yml` 中 Nginx 容器仅映射 80 端口
- `nginx/conf.d/app.conf` 中仅监听 `listen 80`，无 SSL/TLS 配置
- 无 SSL 证书文件（`*.crt`, `*.key`）
- 无 HTTPS 强制跳转逻辑

**影响分析：**
- 所有流量明文传输，包括 Admin 登录凭证、SMTP 密码等
- 浏览器地址栏显示"不安全"警告
- 容易遭受网络嗅探和中间人攻击

---

## 技术难点分析

### 难点 1：SSL 证书获取

**问题：** HTTPS 需要有效的 SSL/TLS 证书，有以下选择：

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Let's Encrypt 免费证书** | 免费，自动续期，被浏览器信任 | 需要域名，90 天有效期 | 有域名的生产环境（推荐） |
| **阿里云 SSL 证书** | 免费 DV 证书，1 年有效期 | 需要域名，手动续期 | 有域名，不想自动续期 |
| **自签名证书** | 完全免费，无需域名 | 浏览器不信任，需手动添加例外 | 仅限内网或测试环境 |

**核心问题：** 当前 ECS 是否绑定了域名？如果没有域名，只能用自签名证书。

### 难点 2：证书自动续期

- Let's Encrypt 证书有效期仅 90 天，需要定期续期
- 可用 `certbot` + cron 自动续期，或使用 `acme.sh` 脚本
- 需确保续期后 Nginx 自动重载配置（`nginx -s reload`）

### 难点 3：Nginx 配置调整

需要修改 `nginx/conf.d/app.conf`，包括：
1. 新增 `listen 443 ssl` 监听 HTTPS
2. 配置 SSL 证书路径（`ssl_certificate`, `ssl_certificate_key`）
3. 配置安全的 SSL 参数（TLS 1.2+，推荐密码套件）
4. HTTP 强制跳转到 HTTPS（`return 301 https://$host$request_uri;`）

### 难点 4：Docker 端口映射调整

`docker-compose.yml` 中需要：
1. Nginx 容器新增 `443:443` 端口映射
2. 将 SSL 证书挂载到容器内（如 `./ssl:/etc/nginx/ssl:ro`）

### 难点 5：防火墙与安全组配置

ECS 需要：
1. 安全组开放 443 端口（HTTPS）
2. 保持 80 端口开放（用于 HTTP 到 HTTPS 的跳转）
3. 如果使用 Let's Encrypt，需开放 80 端口用于域名验证

---

## 方案对比（仅供参考）

| 方案 | 前提条件 | 优点 | 缺点 | 适用场景 |
|------|----------|------|------|----------|
| **方案 A：Let's Encrypt** | 需要域名 | 浏览器信任，自动续期 | 必须有域名 | 有域名的生产环境 |
| **方案 B：阿里云 SSL 证书** | 需要域名 | 1 年有效期 | 手动续期 | 有域名，不想自动化 |
| **方案 C：自签名证书（已选择）** | 无需域名 | 免费、简单、提供加密 | 浏览器警告 | 无域名的个人使用 |

---

## 用户确认信息（2026-02-20）

1. **ECS 域名绑定情况**：无域名，暂不计划申请
2. **访问场景**：仅管理员个人使用
3. **安全需求**：需要传输加密，保障安全性
4. **ECS 权限**：有权限开放 443 端口

**最终选择：方案 C - 自签名证书**

---

## 采用方案详情：方案 C（自签名证书）

**适用场景：** 无域名，仅供管理员个人访问，需要传输加密

**实现步骤：**

1. **生成自签名证书**
   ```bash
   # 在 ECS 上创建 SSL 证书目录
   mkdir -p /opt/news-bot/ssl

   # 生成自签名证书（有效期 1 年）
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout /opt/news-bot/ssl/selfsigned.key \
     -out /opt/news-bot/ssl/selfsigned.crt \
     -subj "/C=CN/ST=Beijing/L=Beijing/O=NewsBot/CN=<ECS-IP>"
   ```

2. **修改 Nginx 配置**
   - 修改 `nginx/conf.d/app.conf`
   - 增加 HTTPS 监听（443 端口）
   - 配置 SSL 证书路径
   - 配置 HTTP 强制跳转到 HTTPS
   - 配置安全的 SSL 参数（TLS 1.2+）

3. **修改 Docker Compose 配置**
   - `docker-compose.yml` 中 Nginx 容器新增 `443:443` 端口映射
   - 挂载 SSL 证书目录：`./ssl:/etc/nginx/ssl:ro`

4. **开放 ECS 安全组 443 端口**
   - 阿里云控制台 → ECS → 安全组规则 → 入方向规则
   - 添加规则：协议 TCP，端口 443，授权对象 0.0.0.0/0

5. **重启服务并验证**
   ```bash
   docker compose down
   docker compose up -d
   ```

6. **浏览器信任证书（一次性操作）**
   - 首次访问 `https://<ECS-IP>/admin` 会显示安全警告
   - 点击"高级" → "继续访问（不安全）"
   - 可选：将证书导入浏览器受信任根证书列表，后续访问无警告

**优点：**
- 提供 HTTPS 传输加密，防止中间人攻击 ✅
- 无需域名，完全免费 ✅
- 实现简单，10 分钟内完成 ✅
- 仅个人使用，一次性信任证书即可 ✅

**缺点：**
- 浏览器首次访问会显示安全警告（可通过手动信任解决）
- 换浏览器或设备需重新信任（但用户仅一人，影响小）
- 不适合多人协作或公开访问场景

**安全性说明：**
- 自签名证书提供与正规证书**完全相同的加密强度**（TLS 1.2/1.3 + AES-256）
- 唯一区别：浏览器无法验证证书签发者身份（因为是自己签发的）
- 对于个人使用场景，安全性完全足够

---

## 概念层调研总结

### 关键发现

1. **现有架构风险**：
   - Nginx 仅监听 HTTP 80 端口，无 SSL/TLS 配置
   - 管理员密码、SMTP 配置等敏感信息明文传输
   - 存在中间人攻击风险

2. **技术限制**：
   - 无域名情况下，无法申请 Let's Encrypt 等受信任的免费证书
   - 自签名证书可提供传输加密，但浏览器会显示警告

3. **最佳实践**：
   - 自签名证书 + 浏览器手动信任，适合个人使用场景
   - 传输加密强度与正规证书相同（RSA 2048 + TLS 1.2+）
   - 需同时开放 80（HTTP 跳转）和 443（HTTPS）端口

### 改动范围

| 文件 | 改动内容 |
|------|----------|
| `nginx/conf.d/app.conf` | 增加 HTTPS 监听、SSL 配置、HTTP 跳转 |
| `docker-compose.yml` | Nginx 容器增加 443 端口映射、挂载 SSL 证书目录 |
| `/opt/news-bot/ssl/` | 新增自签名证书文件（`.crt` 和 `.key`） |
| ECS 安全组规则 | 开放 TCP 443 端口 |

### 验证计划（骨架层）

1. 在 ECS 上生成自签名证书
2. 修改 Nginx 配置，启用 HTTPS
3. 修改 Docker Compose，映射 443 端口
4. 重启服务，验证 HTTPS 访问
5. 确认 HTTP 自动跳转到 HTTPS
6. 确认管理员登录正常（会显示证书警告，但可继续访问）

---

## 骨架层验证步骤

### 步骤 1：本地配置文件修改 ✅

已完成以下文件修改：

1. **nginx/conf.d/app.conf**
   - 增加 HTTPS 监听（443 端口）
   - 配置 SSL 证书路径
   - HTTP 强制跳转到 HTTPS
   - 配置 TLS 1.2/1.3 安全参数

2. **docker-compose.yml**
   - Nginx 容器增加 `443:443` 端口映射
   - 挂载 SSL 证书目录：`./ssl:/etc/nginx/ssl:ro`

3. **ssl/ 目录**
   - 创建 SSL 证书目录
   - 添加 README.md 说明文件

4. **.gitignore**
   - 排除证书文件（`*.crt`, `*.key`, `*.pem`），防止误提交敏感文件

### 步骤 2：ECS 操作指令（待执行）

请在 ECS 服务器上按顺序执行以下命令：

#### 2.1 拉取最新代码

```bash
# SSH 到 ECS
ssh root@<ECS-IP>

# 进入项目目录
cd /opt/news-bot

# 拉取最新配置
git pull
```

#### 2.2 生成自签名 SSL 证书

```bash
# 创建 SSL 证书目录（如果不存在）
mkdir -p ssl

# 生成自签名证书（有效期 1 年，RSA 2048 位）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/selfsigned.key \
  -out ssl/selfsigned.crt \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=NewsBot/CN=$(curl -s ifconfig.me)"

# 验证证书生成成功
ls -lh ssl/
# 应该看到两个文件：
# selfsigned.crt (约 1.3K)
# selfsigned.key (约 1.7K)

# 查看证书信息（可选）
openssl x509 -in ssl/selfsigned.crt -text -noout | head -n 20
```

#### 2.3 开放 ECS 安全组 443 端口

⚠️ **重要：在阿里云控制台操作**

1. 登录阿里云控制台
2. 进入 **ECS 控制台** → **实例**
3. 找到你的 ECS 实例，点击右侧的 **安全组配置**
4. 点击 **配置规则** → **入方向规则** → **添加规则**
5. 填写以下信息：
   - **协议类型**：TCP
   - **端口范围**：443/443
   - **授权对象**：0.0.0.0/0
   - **描述**：HTTPS 访问
6. 点击 **确定**

#### 2.4 重启 Docker 服务

```bash
# 停止现有服务
docker compose down

# 重新构建并启动（会自动加载新配置）
docker compose up -d

# 查看容器状态
docker compose ps
# 应该看到 news_bot_nginx 和 news_bot_app 都是 Up 状态

# 查看 Nginx 日志，确认无错误
docker compose logs nginx
```

#### 2.5 验证 HTTPS 访问

```bash
# 在 ECS 上测试本地 HTTPS 访问
curl -k https://localhost/health
# 应该返回：{"status":"ok"}

# 测试 HTTP 跳转到 HTTPS
curl -I http://localhost/admin
# 应该看到 301 重定向到 https://...
```

#### 2.6 浏览器访问测试

1. 打开浏览器，访问 `https://<ECS-IP>/admin`
2. 会看到安全警告（这是正常的，因为是自签名证书）
3. 点击 **高级** → **继续访问（不安全）** 或 **接受风险并继续**
4. 应该能看到管理界面登录页面
5. 测试登录功能是否正常

#### 2.7 （可选）浏览器信任证书

为了后续访问不再显示警告，可以将证书导入浏览器：

**Chrome/Edge：**
1. 访问 `https://<ECS-IP>/admin`，点击地址栏的 "不安全" 图标
2. 点击 **证书无效** → **详细信息** → **导出**
3. 保存为 `newsbot.crt`
4. 设置 → 隐私和安全 → 安全 → 管理证书 → 受信任的根证书颁发机构 → 导入
5. 选择刚导出的 `newsbot.crt`，点击确定
6. 重启浏览器，再次访问应该不再警告

**Firefox：**
1. 访问 `https://<ECS-IP>/admin`，点击 **高级** → **接受风险并继续**
2. 点击地址栏的锁图标 → **连接不安全** → **更多信息** → **查看证书** → **下载 PEM (证书)**
3. 设置 → 隐私与安全 → 证书 → 查看证书 → 证书颁发机构 → 导入
4. 选择下载的证书，勾选 **信任此 CA 标识网站**
5. 重启浏览器

### 步骤 3：验证清单

完成以上步骤后，请验证以下内容：

- [ ] `https://<ECS-IP>/admin` 可以访问（虽然有安全警告）
- [ ] `http://<ECS-IP>/admin` 自动跳转到 HTTPS
- [ ] 管理界面登录功能正常
- [ ] 可以查看和编辑行业、新闻源等配置
- [ ] （可选）浏览器已信任证书，不再显示警告

### 遇到问题时的排查步骤

如果遇到无法访问的情况，请按以下顺序排查：

1. **检查证书文件是否生成**
   ```bash
   ls -lh /opt/news-bot/ssl/
   ```

2. **检查 Nginx 容器是否正常启动**
   ```bash
   docker compose ps nginx
   docker compose logs nginx
   ```

3. **检查 443 端口是否监听**
   ```bash
   netstat -tuln | grep 443
   ```

4. **检查 ECS 安全组是否开放 443 端口**
   - 阿里云控制台 → ECS → 安全组 → 入方向规则 → 查看 443/TCP

5. **测试本地连接**
   ```bash
   curl -k https://localhost/health
   ```

6. **查看完整日志**
   ```bash
   docker compose logs -f
   ```

---

## 骨架层验证结果（待填写）

### 验证日期：____

### 验证结果：
- HTTPS 访问：[ ] 成功 / [ ] 失败
- HTTP 跳转：[ ] 成功 / [ ] 失败
- 管理界面功能：[ ] 正常 / [ ] 异常
- 浏览器警告：[ ] 符合预期 / [ ] 异常

### 遇到的问题：
（如有问题，请在此记录）

### 解决方案：
（如有问题，请记录如何解决）

### 是否通过骨架层验证：[ ] 是 / [ ] 否

---

## 验收要求（骨架层）

骨架层验证成功标准：
1. ✅ HTTPS 访问正常（`https://<ECS-IP>/admin` 可访问）
2. ✅ HTTP 自动跳转到 HTTPS
3. ✅ 管理界面功能正常（登录、配置管理）
4. ✅ 证书生成和挂载成功

**完成验证后，请回复验证结果，我将进入血肉层进行代码完善和文档补充。**

---

## 参考资料

- [Let's Encrypt 官方文档](https://letsencrypt.org/getting-started/)
- [Certbot 使用指南](https://certbot.eff.org/)
- [Nginx SSL 配置最佳实践](https://ssl-config.mozilla.org/)
- [阿里云 SSL 证书](https://www.aliyun.com/product/cas)
