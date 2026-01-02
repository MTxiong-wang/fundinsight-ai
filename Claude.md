# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 项目概述

**FundInsight AI (基金智析)** 是一个 CLI 工具，为中国的板块基金提供智能排名和推荐。工作流程：输入板块名称 → 搜索相关基金 → AI 评分排名 → 显示推荐表格。

## 常用命令

### 运行应用
```bash
# 分析特定板块
python main.py 消费      # 消费板块
python main.py 新能源     # 新能源板块
python main.py 半导体     # 半导体板块

# 测试完整流程（不调用 AI API，限制为 10 只基金）
python test_full_flow.py
```

### 开发环境搭建
```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，添加 API 密钥
```

### 测试
所有测试脚本位于 `tests/` 目录，不在根目录。
```bash
# 运行组件测试
python tests/test_morningstar_client.py
python tests/test_batch_fetch.py
python tests/test_csindex_scraper.py
```

## 架构设计

### 数据流程

应用遵循 4 步异步流程：

1. **中证指数爬虫** (`scrapers/csindex.py`)
   - 使用 Playwright 在 https://www.csindex.com.cn 搜索板块基金
   - 下载包含基金代码的 Excel 文件
   - 性能：每个板块约 5-10 秒

2. **晨星 API 客户端** (`scrapers/morningstar_client.py`)
   - 直接 HTTP API 调用（无需浏览器）
   - 使用 asyncio.Semaphore 并发获取（默认：10 个并发）
   - 关键端点：
     - `https://www.morningstar.cn/cn-api/v2/funds/{code}/common-data`
     - `https://www.morningstar.cn/cn-api/v2/funds/{code}/performance`
   - 性能：单只基金约 0.37 秒，50 只基金约 18 秒

3. **AI 评分系统** (`ai/scorer.py`, `ai/prompts.py`)
   - 调用配置的 AI 提供商（智谱AI、DeepSeek 或 OpenAI）
   - 评分维度（总分 100 分）：
     - 费用合理性（20 分）
     - 规模适中性（25 分）
     - 业绩表现（40 分）
     - 稳定性（15 分）
   - 返回包含排名和推荐理由的 JSON

4. **CLI 输出** (`main.py`)
   - 使用 Rich 库美化控制台输出，显示表格和面板
   - 显示最佳推荐摘要

### 关键设计决策

**直接 API 优于浏览器爬虫**：晨星客户端使用直接 HTTP API 调用而非浏览器自动化，性能提升 50-100 倍。

**费率估算策略**：由于 API 并不总是提供费率数据，使用基于基金类型的智能估算：
- ETF：0.5% 管理费
- 指数基金：0.5% 管理费
- 主动股票基金：1.5% 管理费
- 默认托管费：0.25%

**并发限流**：晨星 API 使用 `asyncio.Semaphore` 配合 0.5 秒延迟，在保持高吞吐量的同时避免被封禁。

**全面使用异步**：所有 I/O 操作都使用 async/await 以提升性能，从浏览器自动化到 HTTP 调用。

### 模块结构

- `scrapers/` - 数据采集层
  - `csindex.py` - 基于 Playwright 的中证指数爬虫
  - `morningstar_client.py` - 核心晨星 API 客户端，支持异步并发
  - `morningstar.py` - 简化的封装接口

- `ai/` - AI 评分层
  - `scorer.py` - 多提供商 AI 客户端（智谱AI、DeepSeek、OpenAI）
  - `prompts.py` - 结构化提示词模板

- `models/` - 数据模型
  - `fund.py` - Pydantic 模型（FundData, FundRanking）

- `config.py` - 配置管理，包含环境变量验证

- `main.py` - CLI 入口和工作流编排

## 配置说明

配置通过 `config.py` 管理，使用 `.env` 文件中的环境变量：

**必需设置**：
- `AI_PROVIDER` - 选择：`zhipu`、`deepseek` 或 `openai`
- 对应提供商的 API 密钥

**可选设置**：
- `HEADLESS` - 浏览器自动化模式（默认：true）
- `TIMEOUT` - 请求超时时间，单位毫秒（默认：30000）
- `CACHE_ENABLED` - 启用缓存（默认：true）
- `CACHE_TTL` - 缓存有效期，单位秒（默认：86400）

`Config.validate()` 方法确保执行前所需的 API 密钥已配置。

## 开发规范

**测试脚本位置**：所有临时测试脚本必须放在 `tests/` 目录，绝不能放在根目录。

**文档更新**：架构或实现方式变更后必须更新 README。

**错误处理**：所有爬虫应优雅处理失败，包含重试机制和详细的错误信息。

**费率估算**：当晨星 API 不提供费率数据时，使用基于基金类型的智能估算（参见 `scrapers/morningstar_client.py:estimate_fees()`）。

## 性能特征

- **中证指数爬虫**：5-10 秒（无法避免，需要浏览器）
- **晨星 API**：单只基金约 0.37 秒，通过 10 个并发请求优化
- **AI API**：因提供商而异（通常 5-30 秒）
- **大型板块**（如"消费"板块 2558 只基金）：预计总计 8-10 分钟

## 支持的 AI 提供商

- **智谱AI** (glm-4.7) - 默认提供商
- **DeepSeek** (deepseek-chat) - 经济实惠的替代方案
- **OpenAI** (gpt-4o-mini) - 高级选项

通过修改 `.env` 文件中的 `AI_PROVIDER` 切换提供商。

---

## 最近更新 (2025-01-02)

### 已修复的问题

#### 1. 业绩数据显示为空的Bug ✅
**问题**: 基金详细数据中，业绩数据(YTD、3年、5年收益率)全部显示为None

**根本原因**: `scrapers/morningstar_client.py` 中的数据提取逻辑错误
- `_fetch_api()` 已经返回了 `data` 对象（`data.get("data")`）
- 但在 `get_fund_data()` 中又检查了 `performance_data.get("data")`
- 导致访问了不存在的嵌套结构

**修复**: [morningstar_client.py:167-171](scrapers/morningstar_client.py#L167-L171)
```python
# 修复前
if performance_data and performance_data.get("data"):
    perf = performance_data["data"]

# 修复后
if performance_data:
    # performance_data is already the "data" object from _fetch_api
    day_end = performance_data.get("dayEnd", {})
```

**验证**: 现在可以正确获取到业绩数据
- YTD: 4.12%
- 3年收益: 30.95%
- 5年收益: 50.55%

---

#### 2. 表格格式优化 ✅
**改进**: 表格列现在显示分数/实际数据，更加直观

**格式示例**:
- 费用: `14.8/0.28% (0.20%+0.08%)` - 分数/总费率 (显性+隐性)
- 规模: `13.5/4.61亿` - 分数/规模
- 短期: `18.0/4.12%` - 分数/YTD收益率
- 长期: `22.0/50.55%` - 分数/长期收益率
- 基准: `9.0/✓(-5.07%)` - 分数/是否跑赢(超额收益)
- 稳定: `12.0/4.8年` - 分数/成立年限

**修改位置**: [main.py:211-279](main.py#L211-L279)

**优点**:
- 一次查看所有关键信息
- 明确显示分数对应的实际数据
- 费用列同时显示显性和隐性费率

---

#### 3. 日志优化 ✅
**改进**: 减少控制台噪音，批量抓取时只显示汇总信息

**修改前**:
```
处理批次 1/5 (基金 1-10)
已完成 8/10 (失败: 2)
处理批次 2/5 (基金 11-20)
...
失败的基金代码: 000001, 000002, ... (显示前10个)
```

**修改后**:
```
批量获取完成:
  成功: 48 只
  失败: 2 只
```

**详细信息**: 所有批次详情和失败基金代码都移到了DEBUG级别，需要时可以通过设置日志级别查看

**修改位置**: [scrapers/morningstar_client.py:320-356](scrapers/morningstar_client.py#L320-L356)

---

#### 4. 基金名称完整显示 ✅
**改进**: 表格中基金名称列宽度从30增加到40，显示完整名称

**修改位置**: [main.py:215](main.py#L215)
```python
table.add_column("名称", style="green", width=40)  # 从30增加到40
```

---

### 当前评分系统（相对评分）

所有维度都使用百分位排名，在当前批次基金内进行相对比较：

1. **费用合理性 (15分)** - 基于晨星API真实费率
   - 显性费用 = 管理费 + 托管费 + 申购费 + 赎回费 + 销售服务费
   - 隐性费用 = 交易成本 + 其它费用
   - 年度总费率 = 显性 + 隐性

2. **规模适中性 (15分)** - 基金规模
   - 理想区间: 2-50亿
   - 评分基于与理想规模中位数(26亿)的偏离度

3. **短期业绩 (20分)** - 今年以来收益率(YTD)

4. **长期业绩 (25分)** - 3年/5年年化收益率
   - 优先使用5年数据
   - 计算年化收益率后再比较

5. **跑赢基准 (10分)** - 超额收益大小
   - 基于跑赢基准的幅度(beats_benchmark_amount)
   - 不是简单的跑赢/未跑赢二值判断

6. **稳定性 (15分)** - 成立时间

---

### API数据结构注意

#### performance API
```json
{
  "_meta": {"response_status": "200011"},
  "data": {
    "dayEnd": {
      "returns": {"YTD": 4.11952, "Y3": 30.9545, "Y5": 50.54846},
      "benchmarkReturns": {"YTD": 9.18649}
    }
  }
}
```

**关键**: `_fetch_api()` 返回 `data.get("data")`，所以后续代码直接访问 `performance_data.get("dayEnd")`，不要再嵌套`.get("data")`
