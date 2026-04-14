<p align="center">
  <h1 align="center">🌾 三亚市天涯区智慧农业生态监测平台</h1>
  <p align="center">
    <strong>Sanya Tianya Smart Agriculture Ecological Monitoring Platform</strong>
  </p>
  <p align="center">
    面向热带农业生态环境的全域感知 · 智能分析 · 可视化决策支持系统
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/Vite-5.4-646CFF?logo=vite&logoColor=white" />
  <img src="https://img.shields.io/badge/ECharts-5.5-AA344D?logo=apacheecharts&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-Async-003B57?logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/License-Private-red" />
</p>

---

## 📖 目录

- [项目简介](#-项目简介)
- [系统架构](#-系统架构)
- [功能模块](#-功能模块)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [环境要求](#-环境要求)
- [配置文件准备](#%EF%B8%8F-配置文件准备)
- [启动指令](#-启动指令)
- [API 接口文档](#-api-接口文档)
- [数据库设计](#-数据库设计)
- [数据采集机制](#-数据采集机制)
- [报告生成系统](#-报告生成系统)
- [规划功能：数据库可视化大屏](#-规划功能数据库可视化大屏)
- [规划功能：数据统计与报告自动生成系统](#-规划功能数据统计与报告自动生成系统)
- [开发计划路线图](#-开发计划路线图)

---

## 🌟 项目简介

**三亚市天涯区智慧农业生态监测平台** 是一套面向海南三亚天涯区热带农业的全栈物联网 (IoT) 生态监测系统。系统通过对接第三方硬件平台（智慧农林科技 `zhnlkj.com`），**自动化、周期性**地从多类型田间监测设备中采集数据，经清洗、存储和聚合后，在前端以**科技感大屏可视化**的方式实时呈现，并提供**周/月/自定义周期的多格式报告导出**能力。

### 核心价值

| 🎯 目标 | 📋 说明 |
|---------|---------|
| **实时感知** | 每 30 分钟自动采集气象、土壤、虫情、孢子等多维度数据 |
| **可视呈现** | 深色科技大屏，GIS 地图 + ECharts 图表实时展示 |
| **智能分析** | 预留 AI (Claude) 接口，可对监测数据进行风险评估与建议 |
| **报告输出** | 自动聚合统计数据，支持 JSON / HTML / Excel 多格式导出 |
| **设备管控** | 实时监控 7 类设备在线状态，超时自动告警 |

---

## 🏗 系统架构

```
                          ┌─────────────────────────────────────────┐
                          │          三方硬件平台 (zhnlkj.com)        │
                          │   虫情灯 · 孢子仪 · 气象站 · 墒情仪 ...    │
                          └──────────────────┬──────────────────────┘
                                             │ HTTPS / JWT
                          ┌──────────────────▼──────────────────────┐
                          │        Backend (FastAPI + Python)        │
                          │                                         │
                          │  ┌─────────────┐   ┌────────────────┐   │
                          │  │  Collectors  │   │   Scheduler    │   │
                          │  │  (采集器层)   │   │ (APScheduler)  │   │
                          │  └──────┬──────┘   └───────┬────────┘   │
                          │         │                   │            │
                          │  ┌──────▼──────────────────▼────────┐   │
                          │  │        SQLite (aiosqlite)         │   │
                          │  │  7 张数据表 + 1 张采集日志表         │   │
                          │  └──────┬───────────────────────────┘   │
                          │         │                               │
                          │  ┌──────▼──────────────────────────┐    │
                          │  │         Routers (API 层)         │    │
                          │  │  sensor · insect · summary ·    │    │
                          │  │  report                         │    │
                          │  └──────┬──────────────────────────┘    │
                          │         │                               │
                          │  ┌──────▼──────────────────────────┐    │
                          │  │       Services (服务层)           │    │
                          │  │  ReportService · AI Report      │    │
                          │  └─────────────────────────────────┘    │
                          └──────────────────┬──────────────────────┘
                                             │ REST API (JSON)
                          ┌──────────────────▼──────────────────────┐
                          │        Frontend (React + Vite)          │
                          │                                         │
                          │  ┌─────────────────────────────────┐    │
                          │  │    科技风大屏可视化界面             │    │
                          │  │  地图中心 · 气象面板 · 虫情面板    │    │
                          │  │  孢子面板 · 墒情面板 · 设备状态    │    │
                          │  └─────────────────────────────────┘    │
                          └─────────────────────────────────────────┘
```

---

## 🧩 功能模块

### ✅ 已实现功能

#### 1. 多源数据自动采集

- **智能虫情测报灯** — 自动识别害虫种类与数量，支持图像捕获
- **孢子捕捉仪** — 监测空气中病害孢子浓度
- **气象传感器** — 温度、湿度、风速/风向、降雨量、气压、光照
- **墒情传感器** — 多层土壤湿度 (10cm/20cm/40cm) 与地温

#### 2. 科技感大屏可视化

- 🗺 **GIS 地图中心** — 基于天地图 + Leaflet 的设备分布地图，标注监测点位
- 📊 **ECharts 实时图表** — 气象趋势、虫情趋势、孢子趋势、墒情趋势动态图
- 🎨 **深色科技 UI** — 毛玻璃面板、发光边框、霓虹角标、悬浮动效
- 📡 **设备状态面板** — 实时监控 7 类设备运行状态 (在线/超时/离线)
- ⏱ **30 秒轮询** — 前端自动轮询刷新数据，无需手动操作

#### 3. 定时采集与调度

- 基于 `APScheduler` 的异步定时任务，默认每 **30 分钟**采集一次
- 支持**手动触发**采集（调试用 API）
- 启动时自动执行首次数据采集
- JWT Token 缓存与自动刷新

#### 4. 报告生成系统

- **周报 / 月报 / 自定义周期** — 灵活的时间范围查询
- **多格式导出**：
  - `JSON` — 结构化 API 返回，便于二次开发
  - `HTML` — 科技风独立网页报告，可直接打开浏览
  - `Excel` — 多 Sheet 专业表格（综合汇总 + 各维度明细）
- **聚合统计** — 温度均值/极值、降雨量累计、虫种排行、孢子趋势等

#### 5. AI 分析预留

- 预留 Claude (Anthropic) API 接口
- 配置 API Key 后可自动生成智能分析报告
- 风险等级评估、农作物影响分析、防治建议

### 🔲 预留功能（已建模/待接入）

| 模块 | 数据表 | 状态 |
|------|--------|------|
| 水质/面源污染监测 | `water_quality_records` | 已建表 ⏳ |
| 雨量专用监测 | `rainfall_records` | 已建表 ⏳ |
| 4G 雨量计 | — | 待接入 |
| 地表径流监测 | — | 待接入 |
| 测防仪数据 | — | API 已对接 (Code 配置完成) |
| 苗情摄像机 | — | API 已对接 (Code 配置完成) |

---

## 🔧 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | ≥ 3.11 | 运行时 |
| **FastAPI** | 0.115.0 | Web 框架，自动生成 OpenAPI 文档 |
| **Uvicorn** | 0.30.0 | ASGI 服务器 |
| **SQLAlchemy** | 2.0.35 | 异步 ORM，支持新式 `Mapped` 类型注解 |
| **aiosqlite** | 0.20.0 | SQLite 异步驱动 |
| **httpx** | 0.27.2 | 异步 HTTP 客户端 (采集器用) |
| **APScheduler** | 3.10.4 | 定时任务调度器 |
| **Pydantic Settings** | 2.5.2 | 环境变量与配置管理 |
| **Pandas** | 2.2.3 | 数据分析 |
| **Jinja2** | 3.1.4 | HTML 报告模板引擎 |
| **openpyxl** | 3.1.5 | Excel 文件生成 |
| **uv** | latest | 极速 Python 包管理器 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18.3.1 | UI 框架 |
| **Vite** | 5.4.8 | 构建工具 + 开发服务器 |
| **ECharts** | 5.5.1 | 数据可视化图表 |
| **echarts-for-react** | 3.0.2 | ECharts React 集成 |
| **Leaflet** | 1.9.4 | 地图引擎 |
| **react-leaflet** | 4.2.1 | Leaflet React 集成 |
| **Day.js** | 1.11.13 | 日期处理 |
| **CSS Modules** | — | 组件级样式隔离 |

---

## 📁 项目结构

```
sanya_eco_monitor/
├── README.md                              # 本文件
├── start_backend.sh                       # 后端快捷启动脚本
├── start_frontend.sh                      # 前端快捷启动脚本
├── http通讯.postman_collection.json         # Postman API 调试集合
├── 平台HTTP接口v3.pdf                       # 第三方平台接口文档
├── 智能孢子捕捉仪.png                       # 设备图片
├── 智能虫情测报灯.png                       # 设备图片
│
├── backend/                               # ── 后端服务 ──
│   ├── main.py                            # FastAPI 应用入口，生命周期管理
│   ├── config.py                          # Pydantic Settings 配置中心
│   ├── database.py                        # SQLAlchemy 异步引擎与会话
│   ├── models.py                          # 数据模型 (7 张数据表 + 日志表)
│   ├── scheduler.py                       # APScheduler 定时采集任务
│   ├── pyproject.toml                     # Python 项目依赖声明
│   ├── requirements.txt                   # 备用依赖列表
│   ├── .env.example                       # 环境变量模板
│   ├── sanya_eco.db                       # SQLite 数据库文件 (运行时生成)
│   │
│   ├── collectors/                        # 数据采集器层
│   │   ├── base.py                        # HTTP 客户端基类 (JWT 缓存/刷新)
│   │   ├── insect.py                      # 虫情 + 孢子 数据采集
│   │   └── sensor.py                      # 气象 + 墒情 数据采集
│   │
│   ├── routers/                           # API 路由层
│   │   ├── insect.py                      # 虫情/孢子查询接口
│   │   ├── sensor.py                      # 气象/墒情查询接口
│   │   ├── summary.py                     # 综合概览 + 设备状态接口
│   │   └── report.py                      # 报告生成接口 (JSON/HTML/Excel)
│   │
│   └── services/                          # 业务服务层
│       ├── report_service.py              # 报告聚合 + Excel/HTML 生成 (1000+ 行)
│       └── ai_report.py                   # AI 智能分析服务 (Claude API 预留)
│
└── frontend/                              # ── 前端应用 ──
    ├── index.html                         # 入口 HTML (天地图/Leaflet CDN)
    ├── vite.config.js                     # Vite 配置 (代理 → localhost:8001)
    ├── package.json                       # Node 依赖
    ├── .env.example                       # 前端环境变量模板
    │
    └── src/
        ├── main.jsx                       # React 入口
        ├── App.jsx                        # 主布局 (三栏大屏)
        ├── App.module.css                 # 主布局样式
        ├── index.css                      # 全局设计系统 (CSS 变量/Panel/组件)
        │
        ├── components/
        │   ├── Header.jsx                 # 顶部标题栏 (含手动采集按钮)
        │   ├── Header.module.css          # 标题栏样式
        │   ├── MapCenter.jsx              # GIS 地图中心 (天地图 + 标记)
        │   ├── MapCenter.module.css       # 地图区域样式
        │   ├── CenterMap.jsx              # 地图备用组件
        │   ├── WeatherPanel.jsx           # 气象监测面板
        │   ├── SoilPanel.jsx              # 土壤墒情面板
        │   ├── InsectPanel.jsx            # 虫情测报面板
        │   ├── SporePanel.jsx             # 孢子捕捉面板
        │   └── DeviceStatus.jsx           # 设备运行状态面板
        │
        ├── hooks/
        │   └── usePolling.js              # 自动轮询 Hook (30s 间隔)
        │
        └── utils/
            └── api.js                     # API 请求封装
```

---

## 💻 环境要求

在启动项目之前，请确保您的计算机上已安装以下依赖项：

| 依赖 | 最低版本 | 说明 |
|------|---------|------|
| **Python** | ≥ 3.11 | 后端运行时 |
| **Node.js** | ≥ 18.x | 前端构建 |
| **uv** | latest | Python 极速包管理器 |

安装 `uv`：
```bash
pip install uv
# 或
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## ⚙️ 配置文件准备

在启动服务之前，您需要先配置前端和后端的环境变量。

### 1. 后端配置

在 `backend` 目录下，找到 `.env.example`，将其复制并重命名为 `.env`，然后填写实际配置参数：

```bash
# 路径：backend/.env

# ─── 第三方平台账号 ───
PLATFORM_BASE_URL=https://zhnlkj.com/iotSmasrt
PLATFORM_USERNAME=zhnl
PLATFORM_PASSWORD=123456

# ─── 设备编码 ───
INSECT_CODE=PBCR48F-340838-0001       # 智能虫情测报灯
SPORE_CODE=BZ202411200001              # 孢子捕捉仪
WEATHER_CODE=16110669                  # 气象传感器
SOIL_CODE=16110670                     # 墒情传感器
PREVENTION_CODE=864249073501866        # 测防仪
SEEDLING_CODE=FM9400487                # 苗情摄像机

# ─── 系统配置 ───
COLLECT_INTERVAL_MINUTES=30            # 数据采集间隔（分钟）
DEBUG=false                            # 调试模式

# ─── AI 分析（可选）───
ANTHROPIC_API_KEY=                     # Claude API 密钥，留空则使用占位提示
```

### 2. 前端配置

在 `frontend` 目录下，找到 `.env.example`，将其复制并重命名为 `.env`，然后填写天地图 API 密钥：

```bash
# 路径：frontend/.env

# 天地图 API 密钥（申请地址: https://unicloud.tianditu.gov.cn）
VITE_TIANDITU_KEY=your_tianditu_api_key_here
```

---

## 🚀 启动指令

### 方式一：使用快捷启动脚本 (Bash 终端)

打开终端，在项目根目录下分别开两个窗口：

```bash
# Terminal 1 — 启动后端
bash start_backend.sh

# Terminal 2 — 启动前端
bash start_frontend.sh
```

### 方式二：手动分步启动 (适用于所有终端)

**启动后端 (Terminal 1)**
```bash
cd backend

# 安装并同步依赖（uv 会自动创建 .venv 并安装 pyproject.toml 中的依赖）
uv sync

# 启动 FastAPI 服务
uv run uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**启动前端 (Terminal 2)**
```bash
cd frontend

# 安装 Node 依赖
npm install

# 启动 Vite 开发服务器
npm run dev
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 🖥 **前端大屏** | http://localhost:5175 |
| 🔧 **后端 API** | http://localhost:8001 |
| 📚 **Swagger 文档** | http://localhost:8001/docs |
| 📘 **ReDoc 文档** | http://localhost:8001/redoc |

---

## 📡 API 接口文档 (包含返回数据说明)

### 综合概览

| 方法 | 路径 | 说明 | 返回数据结构简述 |
|------|------|------|----------------|
| `GET` | `/api/summary/overview` | 大屏首屏所有关键指标一次性返回 | `{"data": {"weather": {...}, "soil": {...}, "insect": {...}, "spore": {...}, "insect_trend": [...], "collect_logs": [...], "runoff_stations": {...}, "water_quality": {...}, "rain_gauges": {...}}}` |
| `GET` | `/api/summary/device-status` | 所有设备（虫情、孢子、气象、径流、水质等）在线状态 | `{"data": [{"name": "设备名", "code": "标识码", "status": "online/offline", "last_data": "ISO时间"}, ...]}` |
| `GET` | `/api/health` | 健康检查 | `{"status": "ok", "title": "项目名称"}` |

### 虫情 / 孢子

| 方法 | 路径 | 参数 | 说明 | 返回数据结构简述 |
|------|------|------|------|----------------|
| `GET` | `/api/insect/latest` | — | 最新虫情记录 | `{"data": {"collection_time": "...", "total_count": 120, "species_data": {"稻飞虱": 50...}, "image_url": "..."}}` |
| `GET` | `/api/insect/trend` | `days=7` | 近 N 天虫情每日汇总趋势 | `{"data": [{"date": "2023-10-01", "total": 150, "species": {...}}, ...]}` |
| `GET` | `/api/insect/species-stats`| `days=7` | 各虫种统计排行（主要用于饼图） | `{"data": [{"name": "二化螟", "value": 300}, ...]}` |
| `GET` | `/api/insect/combined-trend`| `days=30` | 近 N 天虫情与孢子联合趋势（柱状+折线图用）| `{"data": [{"date": "2023-10-01", "insect": 150, "spore": 50}, ...]}` |
| `GET` | `/api/insect/species-heatmap`| `days=14` | 近 N 天虫种热力图矩阵数据 | `{"data": {"dates": [...], "species": [...], "values": [[0,0,10],...]}}` |
| `GET` | `/api/insect/spore/latest` | — | 最新孢子记录 | `{"data": {"collection_time": "...", "total_count": 50, "spore_data": {...}, "image_url": "..."}}` |
| `GET` | `/api/insect/spore/trend` | `days=7` | 近 N 天孢子趋势 | `{"data": [{"date": "2023-10-01", "total": 45}, ...]}` |

### 传感器 (气象 / 墒情 / 径流 / 雨量 / 水质)

| 方法 | 路径 | 参数 | 说明 | 返回数据结构简述 |
|------|------|------|------|----------------|
| `GET` | `/api/sensor/weather/latest` | — | 最新气象数据 | `{"data": {"temperature": 28.5, "humidity": 70, "wind_speed": 2.5, "wind_direction": "东南", "rainfall": 0, "pressure": 1010, "light": 30000}}` |
| `GET` | `/api/sensor/weather/trend` | `hours=24` | 近 N 小时气象趋势（逐条记录）| `{"data": [{"time": "...", "temperature": 25, "humidity": 80, ...}, ...]}` |
| `GET` | `/api/sensor/weather/daily` | `days=30` | 近 N 天逐日气象聚合（日均温湿度、日累计降雨）| `{"data": [{"date": "...", "avg_temp": 28.1, "avg_humidity": 75.2, "total_rainfall": 12.5}, ...]}` |
| `GET` | `/api/sensor/weather/wind-rose` | `days=7` | 风向频率与平均风速（风玫瑰图用）| `{"data": [{"direction": "西北", "count": 10, "frequency": 15.5, "avg_speed": 3.2}, ...]}` |
| `GET` | `/api/sensor/soil/latest` | — | 最新墒情数据 | `{"data": {"collection_time": "...", "moisture_10cm": 35.2, "moisture_20cm": 38.1, "moisture_40cm": 40.5, "temperature_10cm": 26.5}}` |
| `GET` | `/api/sensor/soil/trend` | `hours=24` | 近 N 小时墒情趋势（逐条记录）| `{"data": [{"time": "...", "moisture_10cm": 35, ...}, ...]}` |
| `GET` | `/api/sensor/soil/daily` | `days=30` | 近 N 天逐日墒情聚合（日均值）| `{"data": [{"date": "...", "moisture_10cm": 35.5, "moisture_20cm": 38.0, "moisture_40cm": 40.2}, ...]}` |
| `GET` | `/api/sensor/rainfall/latest` | — | 最新单体雨量计数据 | `{"data": {"collection_time": "...", "rainfall": 12.5}}` |
| `GET` | `/api/sensor/runoff/latest` | — | 最新单体径流监测站数据 | `{"data": {"collection_time": "...", "flow_rate": 1.5, "total_flow": 1500.5}}` |

### 综合分析 (AI 与生态指数)

| 方法 | 路径 | 参数 | 说明 | 返回数据结构简述 |
|------|------|------|------|----------------|
| `GET` | `/api/analysis/eco-index` | — | 交叉多源数据计算得出的综合健康与风险指数 | `{"data": {"pest_risk": 45, "growth_suitability": 85, "irrigation_urgency": 20, "eco_health": 88, "alerts": [{"level": "warning", "msg": "...风"}], "meta": {...}}}` |

### 报告生成与管理

| 方法 | 路径 | 参数 | 说明 | 返回数据结构简述 |
|------|------|------|------|----------------|
| `GET` | `/api/report/weekly` | `end?` | 周报 JSON 数据 | `{"data": {"period": {"start":"...","end":"..."}, "weather_summary": {...}, "insect_summary": {...}, ...}}` |
| `GET` | `/api/report/monthly` | `end?` | 月报 JSON 数据 | `{"data": {"period": {"start":"...","end":"..."}, "weather_summary": {...}, "insect_summary": {...}, ...}}` |
| `GET` | `/api/report/custom` | `start`, `end` | 自定周期 JSON 数据 | `{"data": {...}}` (结构同周/月报) |
| `GET` | `/api/report/weekly/html` | `end?` | 周报 HTML 下载 | 返回 `text/html` 文件流 |
| `GET` | `/api/report/monthly/html` | `end?` | 月报 HTML 下载 | 返回 `text/html` 文件流 |
| `GET` | `/api/report/ai-analysis` | `end?` | AI 智能分析周报文案 | `{"data": {"analysis": "大模型返回的Markdown文案", "period": {...}}}` |
| `GET` | `/api/report/list` | — | 获取已生成的报告文件列表 | `{"data": [{"id": 1, "title": "...", "report_type": "weekly", "has_html": true, "has_docx": true, ...}, ...]}` |
| `POST`| `/api/report/generate` | `report_type`, `end?` | 后台触发生成指定类型（daily/weekly/m..）的报告 | `{"status": "ok", "message": "Report generated successfully."}` |
| `DEL` | `/api/report/{report_id}` | — | 删除已生成报告 | `{"status": "ok"}` |
| `GET` | `/api/report/download/{id}/{format}`| `{format}`=html/docx | 下载已生成的格式报告文件 | 返回指定文件的二进制流 |

### 系统操作

| 方法 | 路径 | 说明 | 返回数据结构简述 |
|------|------|------|----------------|
| `POST` | `/api/collect/trigger` | 手动触发一次全量数据采集（调试用） | `{"status": "ok", "message": "采集完成"}` |
| `GET` | `/api/debug/settings` | 返回后端实际请求配置的基础URL（调试用）| `{"PLATFORM_BASE_URL": "...", "SENSOR_BASE_URL": "..."}` |

### 📄 接口真实数据返回示例

为方便前端对接与二次开发，以下列出核心接口当前实际运行中拉取到的真实数据样例（<details>内可展开查看 JSON）：

<details>
<summary><b>1. 综合概览数据 `/api/summary/overview`</b></summary>

```json
{
  "data": {
    "weather": {
      "temperature": 21.4,
      "humidity": 79.8,
      "wind_speed": 1.1,
      "wind_direction": "297.0",
      "rainfall": 0.2,
      "updated_at": "2026-04-10T12:39:00"
    },
    "soil": {
      "moisture_10cm": 0.0,
      "moisture_20cm": null,
      "moisture_40cm": null,
      "updated_at": "2026-04-10T12:39:00"
    },
    "insect": {
      "total_today": 0,
      "latest_count": 0,
      "top_species": [],
      "image_url": null,
      "updated_at": "2026-04-10T12:43:41"
    },
    "runoff_stations": {
      "16132920": { "flow_rate": 0.0, "water_level": 0.0, "updated_at": "2026-04-10T12:43:42" }
    },
    "water_quality": {
      "ph": 7.2,
      "do": 6.21,
      "updated_at": "2026-04-10T12:43:57"
    },
    "collect_logs": [
      {
        "task": "wq_16116030",
        "status": "success",
        "count": 1,
        "time": "2026-04-10T12:43:51"
      }
    ]
  }
}
```
</details>

<details>
<summary><b>2. 设备监控状态 `/api/summary/device-status`</b></summary>

```json
{
  "data": [
    {
      "name": "智能虫情测报灯",
      "code": "insect",
      "status": "online",
      "last_data": "2026-04-10T12:43:41"
    },
    {
      "name": "面源污染监测站",
      "code": "water",
      "status": "pending",
      "last_data": null
    }
  ]
}
```
</details>

<details>
<summary><b>3. 气象实时数据 `/api/sensor/weather/latest`</b></summary>

```json
{
  "data": {
    "collection_time": "2026-04-10T12:39:00",
    "temperature": 21.4,
    "humidity": 79.8,
    "wind_speed": 1.1,
    "wind_direction": "297.0",
    "rainfall": 0.2,
    "pressure": 954.0,
    "light": 14010.0
  }
}
```
</details>

<details>
<summary><b>4. 生态健康指数 `/api/analysis/eco-index`</b></summary>

```json
{
  "data": {
    "pest_risk": 5,
    "growth_suitability": 80,
    "irrigation_urgency": 24,
    "eco_health": 84,
    "alerts": [
      {
        "level": "info",
        "msg": "当前气候土壤条件优良，适宜作物生长"
      }
    ],
    "meta": {
        "avg_insects_7d": 0.0,
        "temperature": 21.4,
        "humidity": 79.8
    },
    "computed_at": "2026-04-10T12:56:46"
  }
}
```
</details>

<details>
<summary><b>5. 面源污染监测（水质）实时源格式与大屏解析</b></summary>

对接的第三方硬件接口（以水质站 `16116030` 为例）真实拉取包含详细具体指标的源数据 `eleLists`。我们将其提炼并在系统展示的格式如下：

| 监测参数 | 原生数据名 (`eName`) | 实时数值格式示例 | 数据单位 (`eUnit`) |
| :--- | :--- | :--- | :--- |
| **PH** | PH | 7.15 | *(无)* |
| **电导率** | 电导率 | 0 | μS/cm |
| **COD (化学需氧量)** | COD | 88.08 | mg/L |
| **氨氮** | 氨氮 | 53.89 | mg/L |
| **浊度** | 浊度 | 9.5 | NTU |
| **溶解氧** | 溶解氧 | 6.20 | mg/L |
| **水温** | 水温 | 27.3 | ℃ |
| **总磷** | 总磷 | 0.201 | mg/L |
| **总氮** | 总氮 | 32.767 | mg/L |

**三方源数据拉取示例 (`eleLists` 结构)：**
```json
{
  "datetime": "2026-04-10 13:08:56",
  "deviceId": "16116030",
  "eleLists": [
    { "eValue": "7.15", "eName": "PH", "eUnit": "" },
    { "eValue": "0", "eName": "电导率", "eUnit": "μS/cm" },
    { "eValue": "88.08", "eName": "COD", "eUnit": "mg/L" },
    { "eValue": "53.89", "eName": "氨氮", "eUnit": "mg/L" },
    { "eValue": "9.5", "eName": "浊度", "eUnit": "NTU" }
  ]
}
```
</details>

---

## 🗄 数据库设计

系统使用 **SQLite** (异步模式) 作为持久化存储，共 **8 张数据表**：

### 核心数据表

```
┌─────────────────────────────────────────────────────────────┐
│                      insect_records (虫情测报)                │
├─────────────┬──────────┬────────────────────────────────────┤
│ id          │ INTEGER  │ 主键自增                            │
│ device_code │ STRING   │ 设备编码                            │
│ collection_time │ DATETIME │ 采集时间                        │
│ total_count │ INTEGER  │ 害虫总数                            │
│ species_data│ JSON     │ 各虫种数量 {"二化螟": 12, ...}       │
│ image_url   │ TEXT     │ 害虫图片 URL                        │
│ raw_data    │ JSON     │ 原始响应数据                         │
│ created_at  │ DATETIME │ 记录创建时间                         │
└─────────────┴──────────┴────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      spore_records (孢子捕捉)                │
├─────────────┬──────────┬────────────────────────────────────┤
│ 字段结构与 insect_records 类似                                 │
│ spore_data  │ JSON     │ 孢子分类数据                         │
└─────────────┴──────────┴────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    weather_records (气象数据)                 │
├─────────────┬──────────┬────────────────────────────────────┤
│ temperature │ FLOAT    │ 温度 °C                             │
│ humidity    │ FLOAT    │ 湿度 %                              │
│ wind_speed  │ FLOAT    │ 风速 m/s                            │
│ wind_direction│ STRING │ 风向                                │
│ rainfall    │ FLOAT    │ 降雨量 mm                            │
│ pressure    │ FLOAT    │ 气压 hPa                            │
│ light       │ FLOAT    │ 光照强度 lux                         │
└─────────────┴──────────┴────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      soil_records (墒情数据)                  │
├─────────────┬──────────┬────────────────────────────────────┤
│ moisture_10cm│ FLOAT   │ 10cm 土壤湿度                        │
│ moisture_20cm│ FLOAT   │ 20cm 土壤湿度                        │
│ moisture_40cm│ FLOAT   │ 40cm 土壤湿度                        │
│ temperature_10cm│ FLOAT│ 10cm 地温                            │
└─────────────┴──────────┴────────────────────────────────────┘
```

### 预留数据表

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `water_quality_records` | 水质/面源污染 | pH、溶解氧、电导率、浊度、氨氮、总磷 |
| `rainfall_records` | 雨量专用 | 小时雨量、日雨量 |

### 系统表

| 表名 | 说明 |
|------|------|
| `collect_logs` | 数据采集日志 (任务名、状态、记录数、时间) |

---

## 🔄 数据采集机制

```
┌──────────────┐     JWT Login      ┌──────────────────┐
│   Scheduler  │ ──────────────────► │  zhnlkj.com API  │
│  (每30分钟)   │ ◄────── Token ──── │                  │
│              │                     │  /getBugWarmByCode│
│              │  authenticated GET  │  /getSensorByCode │
│              │ ──────────────────► │                  │
│              │ ◄──── JSON data ─── │                  │
└──────┬───────┘                     └──────────────────┘
       │
       │  Parse + Store
       ▼
┌──────────────┐
│   SQLite DB  │
│  + CollectLog│
└──────────────┘
```

**采集流程详解：**

1. **定时触发** — APScheduler 每 30 分钟执行 `_run_all_collectors()`
2. **Token 管理** — JWT Token 缓存 30 分钟，过期前 60 秒自动刷新
3. **数据拉取** — 向三方平台发起时间范围查询（最近 2 小时数据）
4. **字段映射** — 将平台传感器字段名映射到本地模型字段
5. **入库存储** — 新增记录写入 SQLite，同时记录采集日志
6. **错误隔离** — 单项采集失败不影响其他任务，错误记入日志

---

## 📊 报告生成系统

当前系统已实现的报告生成能力（`backend/services/report_service.py`，1000+ 行核心逻辑）：

### 聚合指标

| 维度 | 计算指标 |
|------|---------|
| **气象** | 平均温度、最高/最低温度、平均湿度、累计降雨量 |
| **墒情** | 10cm/20cm/40cm 各层平均墒情 |
| **虫情** | 捕获总数、虫种排行 (Top 10)、每日趋势 |
| **孢子** | 捕获总数、每日趋势 |

### 导出格式

| 格式 | 特点 |
|------|------|
| **JSON** | 结构化数据，适合前端展示与二次开发 |
| **HTML** | 自包含深色科技风网页，无需外部依赖即可打开 |
| **Excel** | 4 个 Sheet：综合汇总 / 虫情明细 / 气象明细 / 墒情明细，专业排版 |

---

## 📺 规划功能：数据库可视化大屏

> 🚧 **开发阶段：方案设计中**

在现有大屏的基础上，规划开发一套**独立的数据库可视化大屏系统**，直接对接数据库进行深度可视化分析。

### 设计目标

构建一个多场景、多维度的**数据可视化驾驶舱**，支持投屏展示（1920×1080 / 4K），为管理层和决策者提供直观的数据支撑。

### 大屏布局规划

```
┌─────────────────────────────────────────────────────────────────┐
│                    三亚天涯区智慧农业数据驾驶舱                      │
├────────────┬───────────────────────────────┬────────────────────┤
│            │                               │                    │
│  数据总览   │       GIS 空间分析地图          │   实时告警中心      │
│  KPI 卡片   │   设备热力图 / 气象云图         │   滚动告警列表      │
│            │                               │   告警等级分布      │
│────────────┤                               ├────────────────────│
│            │                               │                    │
│  气象趋势   │                               │   虫情种群分析      │
│  多指标叠加  │                               │   饼图 + 排行榜    │
│  面积图     │                               │                    │
│────────────┼───────────────────────────────┼────────────────────│
│            │                               │                    │
│  墒情矩阵   │      数据采集健康度仪表盘        │   孢子浓度曲线     │
│  热力色阶   │   采集成功率 / 数据完整性        │   风险等级警示      │
│            │                               │                    │
└────────────┴───────────────────────────────┴────────────────────┘
```

### 核心功能模块

| 模块 | 功能 | 技术方案 |
|------|------|---------|
| **数据总览区** | 总设备数、今日采集量、总记录数、在线率等 KPI 卡片 | ECharts 数字翻牌器 + CSS 动画 |
| **GIS 空间分析** | 设备分布地图 + 气象数据热力图叠加 | Leaflet + 天地图 + 自定义图层 |
| **气象趋势中心** | 温湿度/风速/降雨多指标叠加面积图，支持 7/30/90 天切换 | ECharts 折线/面积混合图 |
| **虫情种群分析** | 害虫种群分布饼图 + Top N 排行榜 + 日/周对比 | ECharts 南丁格尔玫瑰图 |
| **墒情矩阵视图** | 多层土壤含水量热力矩阵，色阶映射干旱/适宜/过湿 | ECharts 热力图 |
| **孢子浓度曲线** | 孢子浓度趋势 + 阈值预警线 + 风险等级颜色映射 | ECharts 区域折线图 |
| **采集健康度** | 数据采集成功率仪表盘 + 失败任务列表 | ECharts 仪表盘 + 表格 |
| **实时告警中心** | 基于阈值的自动告警，滚动列表展示 | WebSocket / 轮询 + CSS 动画 |

### 专属后端接口（需新增）

```
GET  /api/dashboard/kpi                  # 核心 KPI 聚合数据
GET  /api/dashboard/geo-heatmap          # GIS 热力图数据
GET  /api/dashboard/weather-multi-trend  # 多指标气象趋势 (7/30/90天)
GET  /api/dashboard/insect-species-rank  # 虫种排行与分布
GET  /api/dashboard/soil-heatmatrix      # 墒情热力矩阵数据
GET  /api/dashboard/spore-risk           # 孢子浓度与风险等级
GET  /api/dashboard/collect-health       # 采集健康度统计
GET  /api/dashboard/alerts               # 实时告警列表
WS   /ws/dashboard/live                  # WebSocket 实时推送 (可选)
```

### 技术方案

- **前端**：新增独立路由页面 `/dashboard`，全屏自适应 (CSS `scale` 适配)
- **图表引擎**：ECharts 5.5 + echarts-gl (3D 可能用到)
- **数据刷新**：WebSocket 实时推送 或 10 秒高频轮询
- **自适应**：支持 1920×1080 / 2560×1440 / 3840×2160 分辨率
- **主题**：与现有大屏统一深色科技风

---

## 📈 规划功能：数据统计与报告自动生成系统

> 🚧 **开发阶段：方案设计中**

在现有报告生成能力的基础上，构建一套**数据驱动的智能统计分析与自动报告系统**，通过多维度数据分析得出结论性洞察，自动生成标准化专业报告。

### 设计目标

从"手动查看数据"升级为"**系统自动分析 → 输出结论 → 生成报告**"的智能化流程。

### 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                   数据统计与报告自动生成系统                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐    │
│  │ 数据源层  │ ──►│ 统计分析引擎  │ ──►│  报告生成引擎     │    │
│  │          │    │              │    │                  │    │
│  │ SQLite DB│    │ • 描述统计    │    │ • 模板渲染       │    │
│  │ 实时采集  │    │ • 趋势分析    │    │ • 图表嵌入       │    │
│  │ 历史归档  │    │ • 异常检测    │    │ • 多格式导出     │    │
│  │          │    │ • 相关性分析  │    │ • 定时发布       │    │
│  │          │    │ • 预测模型    │    │                  │    │
│  └──────────┘    └──────┬───────┘    └────────┬─────────┘    │
│                         │                      │              │
│                  ┌──────▼──────────────────────▼─────────┐    │
│                  │            AI 分析层 (Claude)           │    │
│                  │  • 综合风险评估  • 防治建议生成          │    │
│                  │  • 异常原因推断  • 趋势预测解读          │    │
│                  └──────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 核心分析模块

#### 1. 描述性统计分析

| 分析维度 | 统计指标 | 输出 |
|---------|---------|------|
| **气象** | 均值/极值/标准差/百分位数 | 趋势图 + 统计卡片 |
| **墒情** | 各层平均/干旱天数/灌溉建议 | 色阶矩阵 + 建议文本 |
| **虫情** | 种群密度/增长率/优势种/多样性指数 | 排行榜 + 种群动态图 |
| **孢子** | 浓度趋势/爆发预警阈值 | 风险等级仪表盘 |

#### 2. 趋势分析与预测

- **时间序列分解** — 分离季节性、趋势性、随机波动
- **移动平均** — 7 天/30 天滑动窗口平滑
- **同比/环比** — 与上周期对比，自动计算变化率
- **简单预测** — 基于历史趋势的短期预测 (3~7 天)

#### 3. 异常检测

```
异常检测规则引擎：
├── 阈值告警        → 温度 > 38°C / 湿度 < 20% 等
├── 统计异常        → 超出 μ ± 3σ 范围
├── 突变检测        → 相邻时段变化率 > 阈值
└── 组合规则        → 高温 + 低湿 + 高虫情 = 高风险
```

#### 4. 相关性分析

- 气温 ↔ 虫情数量 相关性
- 湿度 ↔ 孢子浓度 相关性
- 降雨量 ↔ 墒情变化 相关性
- 多因子综合分析

#### 5. AI 智能分析 (Claude API)

配置 API Key 后自动启用：

- **综合风险评估** — 基于多维度数据的病虫害风险等级判定
- **防治建议生成** — 针对当前态势的具体防治措施建议
- **异常原因推断** — AI 分析数据异常的可能原因
- **趋势预测解读** — 专业化的趋势分析结论

### 自动报告类型

| 报告类型 | 频率 | 包含内容 |
|---------|------|---------|
| **日报 (Daily Brief)** | 每日凌晨 | 前日数据概况 + 异常标记 + 设备状态 |
| **周报 (Weekly Report)** | 每周一 | 7 天聚合趋势 + 环比分析 + 风险评估 |
| **月报 (Monthly Report)** | 每月 1 日 | 30 天深度分析 + 同比对比 + AI 智能建议 |
| **专题报告 (Thematic)** | 按需触发 | 虫情爆发分析 / 干旱预警 / 极端天气影响评估 |
| **告警报告 (Alert Report)** | 实时触发 | 异常事件详情 + 影响范围 + 应急建议 |

### 报告导出格式

| 格式 | 特点 |
|------|------|
| **PDF** | 正式报告格式，含图表嵌入，可直接打印 |
| **Word (DOCX)** | 可编辑格式，便于二次修改 |
| **HTML** | 交互式网页报告，含可缩放图表 |
| **Excel** | 原始数据 + 统计汇总，便于自定义分析 |
| **Markdown** | 轻量级格式，适合归档与版本管理 |

### 自动化分发

```
定时任务 (Cron/APScheduler)
    │
    ├── 生成报告
    │
    ├── 发送邮件（SMTP）
    │   ├── 管理员 → 完整版报告
    │   └── 负责人 → 摘要版报告
    │
    ├── 推送消息
    │   ├── 企业微信 / 钉钉 Webhook
    │   └── 短信通知 (异常告警)
    │
    └── 存档
        └── 本地文件系统 / 云存储
```

### 新增后端接口（规划）

```
# ─── 统计分析接口 ───
GET  /api/stats/descriptive          # 描述性统计
GET  /api/stats/trend-analysis       # 趋势分析
GET  /api/stats/anomaly-detection    # 异常检测结果
GET  /api/stats/correlation          # 相关性分析
GET  /api/stats/prediction           # 简单趋势预测

# ─── 自动报告接口 ───
POST /api/auto-report/generate       # 手动触发报告生成
GET  /api/auto-report/list           # 历史报告列表
GET  /api/auto-report/{id}/download  # 下载指定报告
PUT  /api/auto-report/schedule       # 配置自动生成计划
GET  /api/auto-report/templates      # 报告模板管理

# ─── AI 分析接口 ───
POST /api/ai/analyze                 # 触发 AI 综合分析
GET  /api/ai/risk-assessment         # 当前风险评估
GET  /api/ai/recommendations         # AI 防治建议
```

---

## 🗺 开发计划路线图

```
Phase 1 ✅ 基础平台 (已完成)
├── IoT 设备数据采集与存储
├── 科技风大屏可视化
├── 实时监控与设备状态
├── 基础报告生成 (JSON/HTML/Excel)
└── AI 分析接口预留

Phase 2 🔨 数据库可视化大屏 (规划中)
├── 独立数据驾驶舱页面
├── KPI 卡片与翻牌器
├── GIS 空间分析与热力图
├── 多维度图表矩阵
├── 采集健康度仪表盘
└── 实时告警系统

Phase 3 🔨 数据统计与自动报告 (规划中)
├── 描述性统计分析引擎
├── 趋势分析与异常检测
├── 相关性分析模块
├── AI 智能分析集成 (Claude)
├── 多格式自动报告生成 (PDF/Word/HTML/Excel)
├── 定时自动生成与邮件分发
└── 报告归档与管理

Phase 4 📋 扩展功能 (远期)
├── 水质/面源污染监测接入
├── 雨量计 / 地表径流设备接入
├── 移动端适配
├── 多区域/多项目支持
└── 用户权限管理系统
```

---

## 📄 许可证

本项目为私有项目，仅供授权使用。

---

<p align="center">
  <em>三亚市天涯区智慧农业生态监测平台 © 2024-2026</em>
</p>
