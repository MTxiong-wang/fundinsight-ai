# FundInsight AI (基金智析)

> 智能板块基金分析与排名 CLI 工具

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## 功能简介

输入板块名称 → 自动搜索基金 → 双重评分排名 → 输出推荐表格

**核心特性**：
- 🚀 **高性能**: 晨星API直接调用，速度比传统爬虫快50-100倍
- 📊 **双重评分**: 工具评分 + AI评分，提供客观全面的投资参考
- 💰 **真实费率**: 从晨星API获取真实费用，包括显性和隐性费用
- 🎯 **相对评分**: 百分位排名，公平比较同板块基金
- 🤖 **多AI支持**: 智谱AI、DeepSeek、OpenAI

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/fundinsight-ai.git
cd fundinsight-ai

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，添加你的 AI API 密钥
```

### 使用

```bash
# 分析消费板块
python main.py 消费

# 分析红利板块
python main.py 红利

# 分析新能源板块
python main.py 新能源
```

**输出位置**: `outputs/{板块名}_{日期}.md`

## 技术架构

### 数据流程

```
用户输入板块名
    ↓
【1】中证指数官网搜索
    - 使用 Playwright 自动化浏览器
    - 下载板块基金Excel列表
    - 提取基金代码和名称
    ↓
【2】晨星API批量获取
    - 异步并发请求（默认10并发）
    - 获取真实费率、业绩、规模等数据
    - 基于代码前缀判断基金类型（场内/场外）
    ↓
【3】工具评分排名
    - 相对评分机制（百分位排名）
    - 6个维度综合评分（满分100分）
    - 输出前20名到MD文件
    ↓
【4】AI评分排名
    - 传递完整数据给AI
    - AI独立分析和评分
    - 追加AI结果到MD文件
    ↓
【5】完成
    - 输出文件: outputs/{板块名}_{日期}.md
    - Prompt文件: outputs/{板块名}_{日期}_prompt.md
```

### 项目结构

```
fundinsight-ai/
├── main.py                    # 主程序入口
├── config.py                  # 配置管理
├── requirements.txt           # 依赖列表
├── .env.example               # 环境变量示例
│
├── scrapers/                  # 数据采集层
│   ├── csindex.py            # 中证指数爬虫 (Playwright)
│   ├── morningstar_client.py # 晨星API客户端 (核心)
│   └── morningstar.py        # 晨星爬虫接口
│
├── ai/                        # AI评分层
│   ├── scorer.py             # AI评分器（多提供商支持）
│   └── prompts.py            # Prompt模板
│
├── models/                    # 数据模型
│   └── fund.py               # Pydantic数据模型
│
└── tests/                     # 测试脚本
    ├── test_batch_fetch.py   # 批量获取测试
    ├── test_complete_fees.py # 费用数据测试
    ├── test_csindex.py       # 中证爬虫测试
    ├── test_csindex_api.py   # 中证API测试
    └── test_fund_data.py     # 基金数据测试
```

## 评分标准（满分100分）

### 相对评分机制

所有维度使用**百分位排名**，在同板块基金内进行比较：

### 工具评分维度

| 维度 | 分数 | 说明 |
|------|------|------|
| 费用合理性 | 15分 | 基于晨星API真实费率（显性+隐性） |
| 规模适中性 | 15分 | 基金规模（理想区间2-50亿） |
| 短期业绩 | 20分 | 今年以来收益率(YTD) |
| 长期业绩 | 25分 | 5年年化收益率（无5年数据得12分） |
| 跑赢基准 | 10分 | 超额收益大小 |
| 稳定性 | 15分 | 成立时间 |

### 百分位评分规则

- **前10%**: 高分区间（各维度最高分的90%）
- **前10%-30%**: 良好区间
- **前30%-70%**: 中等区间
- **后30%**: 低分区间

## 关键技术实现

### 1. 基金类型判断

**基于基金代码前缀**（准确率高）：

| 类型 | 代码前缀 | 说明 |
|------|----------|------|
| 场内ETF | 51, 588 | 上交所ETF（主板/科创板） |
| 场内ETF | 159 | 深交所ETF |
| 场内LOF | 16 | LOF基金 |
| 场内封闭 | 15 | 封闭式基金 |
| 场外 | 00, 01 | 其他前缀 |

### 2. 晨星API端点

```python
# 基础信息
https://www.morningstar.cn/cn-api/v2/funds/{code}/common-data

# 业绩数据（包含benchmarkName）
https://www.morningstar.cn/cn-api/v2/funds/{code}/performance

# 费用数据（真实费率）
https://www.morningstar.cn/cn-api/v2/funds/{code}/fees
```

### 3. 费用数据结构

```python
{
    "managementFee": 0.15,      # 管理费
    "custodianFee": 0.05,       # 托管费
    "subscriptionFee": 0.0,     # 申购费
    "redemptionFee": 0.0,       # 赎回费
    "salesServiceFee": 0.0,     # 销售服务费
    "transactionCost": 0.01648, # 交易成本（隐性）
    "otherFees": 0.06408,       # 其它费用（隐性）
    "totalAnnualFee": 0.28056   # 年度总费率
}
```

## 配置说明

### 环境变量

创建 `.env` 文件：

```bash
# AI提供商选择: zhipu | deepseek | openai
AI_PROVIDER=zhipu

# 智谱AI
ZHIPU_API_KEY=your_zhipu_api_key
ZHIPU_MODEL=glm-4.7

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-chat

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# 爬虫配置
HEADLESS=true
TIMEOUT=30000

# 缓存配置
CACHE_ENABLED=true
CACHE_TTL=86400
```

### AI模型选择

| 提供商 | 模型 | 说明 |
|--------|------|------|
| 智谱AI | glm-4.7 | 默认推荐，性价比高 |
| DeepSeek | deepseek-chat | 经济实惠 |
| OpenAI | gpt-4o-mini | 高级选项 |

## 性能指标

| 操作 | 耗时 |
|------|------|
| 中证指数搜索 | 5-10秒 |
| 晨星API获取 | 50只基金约18秒 |
| AI评分 | 5-30秒（取决于提供商） |
| **总计** | **大型板块（2558只基金）约8-10分钟** |

## 输出示例

### 工具评分表格

| 排名 | 代码 | 名称 | 类型 | 总评分 | 费用合理性 | 规模适中性 | 近一年涨幅 | 近五年涨幅 | 超额收益 | 成立时间 | 晨星比较基准 |
|------|------|------|------|--------|-----------|-----------|-----------|-----------|---------|---------|----------|
| 1 | 515890 | 博时中证红利ETF | 场内 | 88.5 | 14.8/0.28% | 13.5/4.61亿 | 18.0/4.12% | 22.0/50.55% | 9.0/-5.07% | 12.0/4.8年 | 沪深300相对价值全收益 |

**列格式说明**：
- 费用合理性: `分数/总费率 (显性+隐性)`
- 规模适中性: `分数/规模（亿元）`
- 近一年涨幅: `分数/YTD收益率`
- 近五年涨幅: `分数/5年收益率`
- 超额收益: `分数/超额收益率（%）`
- 成立时间: `分数/成立年限（年）`

## 依赖项

- **playwright**: 浏览器自动化
- **httpx**: 异步HTTP客户端
- **pandas**: Excel解析
- **pydantic**: 数据验证
- **rich**: CLI美化
- **python-dotenv**: 环境变量管理
- **zhipuai**: 智谱AI SDK
- **openai**: OpenAI SDK

## 最近更新

### 2025-01-02

**功能改进**：
- ✅ 长期业绩只使用5年数据（避免不公平比较）
- ✅ 基金类型判断改为基于代码前缀（准确率提升）
- ✅ 比较基准改为晨星benchmarkName（更准确）
- ✅ 日志系统：全部写入文件，只ERROR到终端
- ✅ 工具评分立即输出MD，不等待AI
- ✅ AI Prompt保存到outputs文件夹

**Bug修复**：
- ✅ 修复业绩数据显示为空的问题
- ✅ 修复表格显示格式
- ✅ 优化日志输出

## 开发规范

1. **测试脚本位置**: 所有测试脚本放在 `tests/` 目录，不要放在根目录
2. **文档更新**: 架构或实现变更后必须更新README和Claude.md
3. **错误处理**: 所有爬虫必须优雅处理失败，包含重试机制
4. **代码风格**: 遵循PEP 8，使用类型提示

## 测试

```bash
# 测试中证指数爬虫
python tests/test_csindex.py

# 测试晨星批量获取
python tests/test_batch_fetch.py

# 测试费用数据
python tests/test_complete_fees.py

# 测试基金数据
python tests/test_fund_data.py
```

## 故障排除

### 常见问题

**Q: 中证指数爬虫失败？**
- 确保已安装Playwright浏览器: `playwright install chromium`
- 检查网络连接
- 尝试设置 `HEADLESS=false` 查看浏览器过程

**Q: 晨星API请求失败？**
- 检查并发设置（默认10个并发）
- 增加请求延迟（默认0.5秒）
- 查看日志文件获取详细错误信息

**Q: AI评分失败？**
- 检查API密钥是否正确
- 确认API提供商可用
- 查看日志文件 `logs/fundinsight_*.log`

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 作者

FundInsight AI Team

---

**免责声明**: 本工具仅供学习参考，不构成投资建议。投资有风险，选择需谨慎。
