"""AI Prompt 模板"""

SECTOR_RANKING_PROMPT = """你是专业的基金分析师，请对"{sector}"板块的以下基金进行分析。

## 基金列表
{fund_list}

## 评分维度

请从以下维度对基金进行综合评分（使用相对评分，在本批次基金内进行比较）：

1. **费用合理性** - 综合考虑显性费用和隐性费用，费用越低得分越高
2. **规模适中性** - 基金规模大小，规模过小有清盘风险，规模过大可能影响灵活性
3. **短期业绩** - 今年以来收益表现
4. **长期业绩** - 3年/5年长期收益表现，根据实际情况灵活使用可用数据
5. **跑赢基准** - 跑赢基准幅度（超额收益）越大得分越高
6. **稳定性** - 基金成立时间，成立时间越长稳定性越好

## 评分要求

1. **相对评分**：请在当前批次的基金内进行相对比较，不要使用绝对标准
   - 例如：费用最低的前10%基金应该获得最高分（13-15分），而不是看绝对费率是否低于0.8%
   - 例如：收益最高的前10%基金应该获得最高分（18-20分），而不是看绝对收益率是否超过20%

2. **百分位评分**：使用百分位来确定分数
   - 前10%：高分区间
   - 前10%-30%：良好区间
   - 前30%-70%：中等区间
   - 后30%：低分区间

3. **综合判断**：在评分时综合考虑各项指标的合理性和可投资价值

## 输出要求

请以表格形式输出前20名基金，使用与工具评分相同的详细格式：

| 排名 | 代码 | 名称 | 类型 | 评分 | 费用合理性 | 规模适中性 | 近一年涨幅 | 近五年涨幅 | 超额收益 | 成立时间 | 晨星比较基准 | 推荐理由 |
|------|------|------|------|------|-----------|-----------|-----------|-----------|---------|---------|----------|----------|
| 1 | 515890 | 博时中证红利ETF | 场内 | 88.5 | 14.8/0.28% (显性0.20%+隐性0.08%) | 13.5/4.61亿 | 18.0/4.12% | 22.0/50.55% | 9.0/跑赢(-5.07%) | 12.0/4.8年 | 沪深300相对价值全收益 | 费用低廉，规模适中，长期业绩优秀 |
| 2 | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

**列格式说明**：
- **类型**: 场内(ETF/LOF) 或 场外
- **费用合理性**: 分数/总费率 (显性费率+隐性费率)
- **规模适中性**: 分数/规模（亿元）
- **近一年涨幅**: 分数/今年收益率（%）
- **近五年涨幅**: 分数/长期收益率（%），根据可用数据灵活使用3年或5年
- **超额收益**: 分数/跑赢基准幅度（%），正数表示跑赢，负数表示未跑赢
- **成立时间**: 分数/成立年限（年）（成立日期）
- **晨星比较基准**: 晨星API返回的比较基准指数名称
- **推荐理由**: 简要说明关键优势（50字以内）

**重要**：
1. 使用相对评分，在本批次基金内进行比较
2. 确保评分合理、客观
3. 表格格式清晰易读，包含所有列
4. 只输出前20名
"""


def format_fund_list(funds: list) -> str:
    """格式化基金列表用于Prompt，包含完整费用信息和收益率"""
    lines = []
    for fund in funds:
        # 基金类型
        fund_type = fund.fund_type if fund.fund_type else "未知"

        # 费用信息
        fee_line = (
            f"  类型: {fund_type}\n"
            f"  显性费用: 管理费{fund.management_fee}%, 托管费{fund.custody_fee}%, "
            f"申购费{fund.subscription_fee}%, 赎回费{fund.redemption_fee}%\n"
            f"  隐性费用: 交易成本{fund.transaction_cost * 100:.2f}%, 其它费用{fund.other_fees * 100:.2f}%\n"
            f"  年度总费率: {fund.total_annual_fee * 100:.2f}%"
        )

        # 业绩信息
        performance_line = f"  规模: {fund.scale}亿, 今年以来收益: {fund.yearly_return}%, "
        if fund.return_3year is not None:
            performance_line += f"近3年收益: {fund.return_3year}%, "
        if fund.return_5year is not None:
            performance_line += f"近5年收益: {fund.return_5year}%, "
        performance_line += f"成立日期: {fund.establish_date}"

        # 跑赢基准信息（包含幅度）
        if fund.beats_benchmark_amount is not None:
            performance_line += f", 跑赢基准幅度: {fund.beats_benchmark_amount:+.2f}%"
        elif fund.beats_benchmark is not None:
            performance_line += f", 跑赢基准: {'是' if fund.beats_benchmark else '否'}"

        # 比较基准
        benchmark_line = f"  比较基准: {fund.benchmark}" if fund.benchmark else ""

        line = (
            f"- {fund.code} {fund.name}\n"
            f"{fee_line}\n"
            f"{performance_line}\n"
            f"{benchmark_line}"
        )
        lines.append(line)

    return "\n\n".join(lines)
