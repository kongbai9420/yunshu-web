# 云枢 Web 控制中心 (YunShu Web Edition)

<p align="center">
  <img src="src/ui/app_icon.png" alt="云枢 YunShu Logo" width="112" height="112" style="border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
</p>

<p align="center">
  <b>多品牌服务器智能温控与混合集群监控运维平台 · 纯 Web / Docker 版</b><br>
  苹果 Liquid Glass 设计美学 · 跨端自适应响应式 · 带外 IPMI 2.0 硬件控温 · SSH 系统内核探针 · 工业级安全网关
</p>

<p align="center">
  <a href="https://hub.docker.com/r/kongbai9420/yunshu-web"><img src="https://img.shields.io/docker/pulls/kongbai9420/yunshu-web?style=flat-square&logo=docker" alt="Docker Pulls"></a>
  <a href="https://hub.docker.com/r/kongbai9420/yunshu-web"><img src="https://img.shields.io/docker/v/kongbai9420/yunshu-web?style=flat-square&logo=docker" alt="Docker Image Version"></a>
  <img src="https://img.shields.io/badge/Release-v3.6.0--beta-0A84FF?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-4E525A?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/Arch-amd64%20%7C%20arm64-success?style=flat-square" alt="Architecture">
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="License">
</p>

---

## 📖 简介

**云枢 (YunShu) Web 版** 是专为现代化数据中心、家庭微型机房、All-in-One 虚拟化及私有云环境打造的多品牌服务器智能温控与混合集群监控运维中心。

告别旧式桌面端窗口限制，全新 Web 控制中心采用 **Apple HIG (Human Interface Guidelines)** 纯正拟态质感，支持手机、平板、PC 浏览器随时随地全功能无缝访问，通过 Docker 容器化即可一键部署到 PVE、Unraid、群晖 Synology、TrueNAS 或通用 Linux 宿主机上。

---

## ✨ 核心特性

* 🍎 **纯正 Apple HIG Web 设计**：
  * 精致流体半透明拟态（Liquid Glass）与层级投影，支持深色 / 浅色模式毫秒级无感切换。
  * 响应式侧边栏折叠轨、面包屑导航动态联动、HTML5 沉浸式全屏机房监控大屏。
* ⚡ **多品牌物理带外 (IPMI 2.0) 硬件温控引擎**：
  * 广泛兼容 **Dell (戴尔)、Inspur (浪潮)、Huawei (华为)、Supermicro (超微)、Lenovo (联想)** 等品牌服务器。
  * 提供「动态平滑温控曲线」、「手动调速矩阵」、「情景预设」、「原厂 BMC 托管」四大风道管理策略。
  * 集成 DCMI 单帧直读、SDR 本地高速缓存加速与 UDP 623 链路存活测活机制。
* 🐧 **系统内核探针 (SSH / Linux / PVE) 与批量运维**：
  * 零 Agent 侵入采集宿主机 CPU 算力负载、内存水线、Swap 换页与磁盘容量。
  * 支持硬件物理节点与宿主服务器一对一逻辑拓扑绑定。
  * 内置运维命令分发控制台，多端并发快速巡检。
* 🔒 **端到端企业级安全访问控制**：
  * **未登录零操作**：全站 `/api/*` 接口严格实施会话拦截，未鉴权请求一律 401 拦截。
  * **高强度加密存储**：密码采用 PBKDF2-HMAC-SHA256（100,000 次加盐哈希）计算，无明文泄露风险。
  * **防暴力破解**：单个 IP 认证失败 5 次自动触发 5 分钟安全锁止。
  * 支持实时更改管理员登录账号（用户名）与访问密码。

---

## 🐳 Docker 极速部署指南

Docker 镜像是最推荐的生产部署方式，镜像内已预置全套 Python 3.11 运行环境、`ipmitool` 依赖底层与中文字符集支持。

### 方式一：Docker Run 命令行运行 (最简便)

```bash
docker run -d \
  --name yunshu-web \
  --restart unless-stopped \
  --net=host \
  -v /opt/yunshu/config.ini:/app/config.ini \
  -v /opt/yunshu/data:/app/data \
  -v /opt/yunshu/logs:/app/logs \
  kongbai9420/yunshu-web:latest
```

> **网络模式建议**：
> * **强烈推荐使用 `--net=host`**：直接复用宿主机网络栈，避免 Docker 默认网桥 NAT 对 IPMI UDP 623 端口和带外通信造成的延迟与阻碍。
> * **端口映射模式**：若在不支持 host 网络的平台（如 Windows/macOS Docker Desktop），请使用 `-p 8080:8080` 启动。

---

### 方式二：Docker Compose 编排部署 (推荐)

在部署目录下创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  yunshu-web:
    image: kongbai9420/yunshu-web:latest
    container_name: yunshu-web
    restart: unless-stopped
    # 推荐 host 网络模式，保证与带外 BMC / IPMI 通信零 NAT 延迟
    network_mode: host
    # 若在非 Linux 宿主机上运行，可注释上面 network_mode 并启用端口映射：
    # ports:
    #   - "8080:8080"
    volumes:
      - ./config.ini:/app/config.ini
      - ./data:/app/data
      - ./logs:/app/logs
      - ./sdr_cache:/app/sdr_cache
    environment:
      - TZ=Asia/Shanghai
      - PYTHONUNBUFFERED=1
```

启动容器：
```bash
docker compose up -d
```

查看运行状态与日志：
```bash
docker compose logs -f
```

---

## 🔑 默认登录认证与安全说明

容器启动完成后，在浏览器中访问：
* 本地访问入口：`http://127.0.0.1:8080`
* 局域网访问入口：`http://<宿主机IP>:8080`

| 配置项 | 初始默认值 |
| :--- | :--- |
| **初始管理员账号** | `admin` |
| **初始访问密码** | `admin123` |

> 🛡️ **安全建议**：
> 首次登录系统后，请立即点击右上角管理员头像呼出卡片，进入**「修改账号与密码」**弹窗，将默认账号与密码更新为您专属的高强度凭据！

---

## 💻 本地源码 / Windows 原生运行

如果你希望直接在宿主机裸机运行（不使用 Docker）：

### 1. 安装依赖环境
确保已安装 Python 3.10+，执行依赖安装：
```bash
pip install -r requirements.txt
```

*(注意：在 Linux 下运行还需确保系统安装了 `ipmitool`，例如 `sudo apt install ipmitool` 或 `sudo yum install ipmitool`)*

### 2. 启动服务
* **Windows 环境**：直接双击根目录下的 **`启动Web服务.bat`** 即可。
* **命令行环境**：
  ```bash
  python run_web.py --host 0.0.0.0 --port 8080
  ```

---

## 🛠️ 目录与持久化挂载说明

| 宿主机路径 | 容器内路径 | 说明 |
| :--- | :--- | :--- |
| `./config.ini` | `/app/config.ini` | 核心配置文件（节点列表、温控曲线、告警规则等，缺省时自动生成） |
| `./data/` | `/app/data/` | 鉴权账户数据库持久化目录（存放加密的 `users.json`） |
| `./logs/` | `/app/logs/` | 运行日志按天分卷输出目录，超期自动安全轮转 |
| `./sdr_cache/` | `/app/sdr_cache/` | 硬件节点传感器静态仓库高速缓存 |

---

## 🚢 Docker Hub 多架构自动构建与发布

本项目通过 GitHub Actions 实现了与 Docker Hub 的全自动流水线同步：
* 支持 **`linux/amd64`** 和 **`linux/arm64`** 双主流架构；
* 每当代码打上 Release / Tag（如 `v3.6.0-beta.1`）时，GitHub Actions 会自动编译多架构镜像并同步推送到 `kongbai9420/yunshu-web:latest` 及对应版本标签中。

---

## 📄 开源许可

本项目遵循 [MIT 开源许可证](LICENSE)。
欢迎提交 Issue 与 Pull Request 共同完善！
