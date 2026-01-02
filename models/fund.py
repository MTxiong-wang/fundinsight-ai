"""基金数据模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FundData(BaseModel):
    """基金基础数据"""
    code: str = Field(..., description="基金代码")
    name: str = Field(..., description="基金名称")
    # 显性费率
    management_fee: float = Field(..., description="管理费(%)")
    custody_fee: float = Field(..., description="托管费(%)")
    subscription_fee: Optional[float] = Field(None, description="申购费(%)")
    redemption_fee: Optional[float] = Field(None, description="赎回费(%)")
    sales_service_fee: Optional[float] = Field(0.0, description="销售服务费(%)")
    # 隐性费率
    transaction_cost: Optional[float] = Field(0.0, description="交易成本(%)，根据换手率估算")
    other_fees: Optional[float] = Field(0.0, description="其它费用(%)，包括审计、律师、信息披露等")
    total_annual_fee: Optional[float] = Field(None, description="年度总费率(%)，包括所有费用")
    # 基金数据
    scale: float = Field(..., description="规模(亿元)")
    yearly_return: Optional[float] = Field(None, description="今年以来收益率(%)")
    return_3year: Optional[float] = Field(None, description="近3年收益率(%)")
    return_5year: Optional[float] = Field(None, description="近5年收益率(%)")
    establish_date: Optional[str] = Field(None, description="成立日期 (YYYY-MM-DD)")
    benchmark: Optional[str] = Field(None, description="基准指数")
    beats_benchmark: Optional[bool] = Field(None, description="是否跑赢基准")
    beats_benchmark_amount: Optional[float] = Field(None, description="跑赢基准幅度(%)")
    fund_type: Optional[str] = Field(None, description="基金类型: 场内(ETF/LOF)或场外")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "515890",
                "name": "博时中证红利ETF",
                "management_fee": 0.5,
                "custody_fee": 0.25,
                "subscription_fee": 0.0,
                "redemption_fee": 0.0,
                "sales_service_fee": 0.0,
                "transaction_cost": 0.03,
                "other_fees": 0.2,
                "total_annual_fee": 0.98,
                "scale": 4.61,
                "yearly_return": 4.12,
                "establish_date": "2020-03-20",
                "benchmark": "中证红利指数收益率",
                "beats_benchmark": False,
                "beats_benchmark_amount": -5.07
            }
        }


class FundRanking(BaseModel):
    """基金排名结果"""
    rank: int = Field(..., description="排名")
    code: str = Field(..., description="基金代码")
    name: str = Field(..., description="基金名称")
    score: float = Field(..., description="综合评分 (0-100)")
    reasoning: str = Field(..., description="推荐理由")

    class Config:
        json_schema_extra = {
            "example": {
                "rank": 1,
                "code": "516160",
                "name": "某某新能源ETF",
                "score": 85.5,
                "reasoning": "该基金费用低廉(0.6%)，规模适中(50亿)，今年以来收益达20.5%，显著跑赢基准5.2个百分点..."
            }
        }


def score_fund(fund: FundData, all_funds: List[FundData] = None) -> tuple[float, dict]:
    """
    对基金进行综合评分（相对评分）

    评分维度（满分100分）：
    1. 费用合理性 (15分) - 年度总费率（相对评分，百分位排名）
    2. 规模适中性 (15分) - 基金规模（相对评分，越接近理想规模越好）
    3. 短期业绩 (20分) - 今年以来收益（相对评分，百分位排名）
    4. 长期业绩 (25分) - 3年/5年收益（相对评分，百分位排名）
    5. 跑赢基准 (10分) - 超额收益大小（相对评分，百分位排名）
    6. 稳定性 (15分) - 成立时间（相对评分，百分位排名）

    Args:
        fund: 基金数据
        all_funds: 同批次所有基金（用于相对评分）
                   如果不提供，则使用绝对评分（降级处理）

    Returns:
        (总分, 评分明细)
    """
    scores = {}
    total_score = 0.0

    # 如果没有提供all_funds，使用绝对评分（降级处理）
    if all_funds is None:
        all_funds = [fund]

    # 1. 费用合理性 (15分) - 相对评分
    fee_score = _score_fees_relative(fund, all_funds)
    scores["费用合理性"] = fee_score
    total_score += fee_score

    # 2. 规模适中性 (15分) - 相对评分
    scale_score = _score_scale_relative(fund, all_funds)
    scores["规模适中性"] = scale_score
    total_score += scale_score

    # 3. 短期业绩 (20分) - 相对评分
    short_term_score = _score_short_term_performance_relative(fund, all_funds)
    scores["短期业绩(YTD)"] = short_term_score
    total_score += short_term_score

    # 4. 长期业绩 (25分) - 相对评分（只用5年数据）
    long_term_score = _score_long_term_performance_relative(fund, all_funds)
    scores["长期业绩(5年)"] = long_term_score
    total_score += long_term_score

    # 5. 跑赢基准 (10分) - 相对评分（基于超额收益）
    benchmark_score = _score_beats_benchmark_relative(fund, all_funds)
    scores["跑赢基准"] = benchmark_score
    total_score += benchmark_score

    # 6. 稳定性 (15分) - 相对评分
    stability_score = _score_stability_relative(fund, all_funds)
    scores["稳定性"] = stability_score
    total_score += stability_score

    return total_score, scores


def _score_fees(total_annual_fee: Optional[float]) -> float:
    """
    费用合理性评分 (15分)

    评分标准（按年度总费率）：
    - 总费用 < 0.8%：13-15分 （优秀：主要是指数基金、ETF）
    - 总费用 0.8%-1.2%：11-12分 （良好：指数基金、低费率主动基金）
    - 总费用 1.2%-1.8%：9-10分 （一般：主动基金）
    - 总费用 1.8%-2.5%：6-8分 （偏高：高换手率主动基金）
    - 总费用 > 2.5%：0-5分 （过高：建议回避）
    """
    if total_annual_fee is None:
        return 8.0  # 默认中等分数

    fee_pct = total_annual_fee * 100  # 转换为百分比

    if fee_pct < 0.8:
        # 13-15分，线性映射
        return 13 + (0.8 - fee_pct) / 0.8 * 2
    elif fee_pct < 1.2:
        # 11-12分
        return 11 + (1.2 - fee_pct) / 0.4 * 1
    elif fee_pct < 1.8:
        # 9-10分
        return 9 + (1.8 - fee_pct) / 0.6 * 1
    elif fee_pct < 2.5:
        # 6-8分
        return 6 + (2.5 - fee_pct) / 0.7 * 2
    else:
        # 0-5分
        return max(0, 5 - (fee_pct - 2.5) / 0.5 * 5)


def _score_scale(scale: float) -> float:
    """
    规模适中性评分 (15分)

    评分标准：
    - 2-50亿为最佳规模区间：12-15分
    - 小于2亿或大于50亿：8-11分
    - 小于1亿（清盘风险）：0-7分
    """
    if 2 <= scale <= 50:
        # 最佳区间，12-15分
        if scale < 10:
            return 12 + (scale - 2) / 8 * 3
        elif scale < 30:
            return 15
        else:
            return 15 - (scale - 30) / 20 * 3
    elif scale < 2:
        # 小于2亿
        if scale < 1:
            return 7 * scale  # 0-7分
        else:
            return 7 + (scale - 1) * 4  # 7-11分
    else:  # scale > 50
        # 大于50亿，8-11分
        return max(8, 11 - (scale - 50) / 50 * 3)


def _score_short_term_performance(yearly_return: Optional[float]) -> float:
    """
    短期业绩评分 (20分) - 今年以来收益

    评分标准：
    - 今年以来收益 > 20%：18-20分
    - 今年以来收益 10%-20%：15-17分
    - 今年以来收益 0%-10%：12-14分
    - 今年以来收益 < 0%：0-11分
    """
    if yearly_return is None:
        return 10.0  # 默认中等分数

    if yearly_return > 20:
        return 18 + min(2, (yearly_return - 20) / 10 * 2)
    elif yearly_return > 10:
        return 15 + (yearly_return - 10) / 10 * 2
    elif yearly_return > 0:
        return 12 + yearly_return / 10 * 2
    else:
        return max(0, 11 * (1 + yearly_return / 20))


def _score_long_term_performance(
    return_3year: Optional[float],
    return_5year: Optional[float]
) -> float:
    """
    长期业绩评分 (25分) - 3年和5年收益

    评分标准：
    - 优先使用5年收益，其次3年收益
    - 年化收益 > 15%：22-25分
    - 年化收益 10%-15%：18-21分
    - 年化收益 5%-10%：14-17分
    - 年化收益 0%-5%：10-13分
    - 年化收益 < 0%：0-9分
    """
    # 优先使用5年收益
    long_term_return = return_5year if return_5year is not None else return_3year

    if long_term_return is None:
        return 12.0  # 默认中等分数

    # 计算年化收益率
    if return_5year is not None:
        annualized_return = (1 + return_5year / 100) ** (1/5) - 1
    elif return_3year is not None:
        annualized_return = (1 + return_3year / 100) ** (1/3) - 1
    else:
        return 12.0

    annualized_pct = annualized_return * 100

    if annualized_pct > 15:
        return 22 + min(3, (annualized_pct - 15) / 5 * 3)
    elif annualized_pct > 10:
        return 18 + (annualized_pct - 10) / 5 * 3
    elif annualized_pct > 5:
        return 14 + (annualized_pct - 5) / 5 * 3
    elif annualized_pct > 0:
        return 10 + annualized_pct / 5 * 3
    else:
        return max(0, 9 * (1 + annualized_pct / 10))


def _score_beats_benchmark(beats_benchmark: Optional[bool]) -> float:
    """
    跑赢基准评分 (10分) - 已废弃，使用相对评分版本

    评分标准：
    - 跑赢基准：10分
    - 未跑赢或无数据：0分
    """
    if beats_benchmark is True:
        return 10.0
    else:
        return 0.0


def _score_beats_benchmark_relative(fund: FundData, all_funds: List[FundData]) -> float:
    """
    跑赢基准相对评分 (10分) - 基于超额收益大小

    评分标准（按百分位，超额收益越高越好）：
    - 前10%（超额收益最高）：9-10分
    - 前10%-30%：7-8分
    - 前30%-70%：5-6分
    - 前70%-90%：2-4分
    - 后10%（超额收益最低或为负）：0-1分
    """
    # 获取所有有效超额收益（跑赢基准的幅度）
    excess_returns = []
    for f in all_funds:
        if f.beats_benchmark_amount is not None:
            excess_returns.append(f.beats_benchmark_amount)

    if not excess_returns or fund.beats_benchmark_amount is None:
        return 5.0  # 默认中等分数

    # 计算百分位排名（超额收益越高，排名越高）
    percentile = sum(1 for r in excess_returns if r <= fund.beats_benchmark_amount) / len(excess_returns)

    # 映射到分数
    if percentile >= 0.9:  # 前10%
        return 9 + (percentile - 0.9) / 0.1 * 1
    elif percentile >= 0.7:  # 前10%-30%
        return 7 + (percentile - 0.7) / 0.2 * 1
    elif percentile >= 0.3:  # 前30%-70%
        return 5 + (percentile - 0.3) / 0.4 * 1
    elif percentile >= 0.1:  # 前70%-90%
        return 2 + (percentile - 0.1) / 0.2 * 2
    else:  # 后10%
        return max(0, percentile / 0.1)


def _score_stability(establish_date: Optional[str]) -> float:
    """
    稳定性评分 (15分)

    评分标准：
    - 成立3年以上：12-15分
    - 成立1-3年：8-11分
    - 成立1年以下：0-7分
    """
    if not establish_date:
        return 8.0  # 默认中等分数

    try:
        # 解析日期
        date_obj = datetime.strptime(establish_date, "%Y-%m-%d")
        years = (datetime.now() - date_obj).days / 365.25

        if years >= 3:
            return 12 + min(3, (years - 3) / 2 * 3)
        elif years >= 1:
            return 8 + (years - 1) / 2 * 3
        else:
            return years * 7
    except:
        return 8.0


# ==================== 相对评分函数 ====================

def _score_fees_relative(fund: FundData, all_funds: List[FundData]) -> float:
    """
    费用合理性相对评分 (15分)

    评分标准（按百分位，费用越低越好）：
    - 前10%（费用最低）：13-15分
    - 前10%-30%：11-12分
    - 前30%-70%：9-10分
    - 前70%-90%：6-8分
    - 后10%（费用最高）：0-5分
    """
    # 获取所有有效费用
    fees = [f.total_annual_fee for f in all_funds if f.total_annual_fee is not None]

    if not fees or fund.total_annual_fee is None:
        return 8.0  # 默认中等分数

    # 计算百分位排名（费用越低，排名越高）
    percentile = sum(1 for f in fees if f >= fund.total_annual_fee) / len(fees)

    # 映射到分数
    if percentile >= 0.9:  # 前10%
        return 13 + (percentile - 0.9) / 0.1 * 2
    elif percentile >= 0.7:  # 前10%-30%
        return 11 + (percentile - 0.7) / 0.2 * 1
    elif percentile >= 0.3:  # 前30%-70%
        return 9 + (percentile - 0.3) / 0.4 * 1
    elif percentile >= 0.1:  # 前70%-90%
        return 6 + (percentile - 0.1) / 0.2 * 2
    else:  # 后10%
        return max(0, 5 * percentile / 0.1)


def _score_scale_relative(fund: FundData, all_funds: List[FundData]) -> float:
    """
    规模适中性相对评分 (15分)

    评分标准（按百分位，规模越接近中位数越好）：
    - 计算每只基金规模与理想区间中位数的偏离度
    - 偏离度最小的前30%：12-15分
    - 偏离度中等的前30%-70%：9-11分
    - 偏离度最大的后30%：0-8分
    """
    # 获取所有规模
    scales = [f.scale for f in all_funds if f.scale is not None]

    if not scales or fund.scale is None:
        return 8.0  # 默认中等分数

    # 计算理想区间的中位数（2-50亿的中位数是26亿）
    ideal_scale = 26.0

    # 计算每只基金的偏离度（越接近ideal_scale越好）
    deviations = [abs(s - ideal_scale) for s in scales]
    fund_deviation = abs(fund.scale - ideal_scale)

    # 计算百分位排名（偏离度越小，排名越高）
    percentile = sum(1 for d in deviations if d >= fund_deviation) / len(deviations)

    # 映射到分数
    if percentile >= 0.7:  # 前30%（偏离度最小）
        return 12 + (percentile - 0.7) / 0.3 * 3
    elif percentile >= 0.3:  # 中间40%
        return 9 + (percentile - 0.3) / 0.4 * 2
    else:  # 后30%（偏离度最大）
        return (percentile / 0.3) * 8


def _score_short_term_performance_relative(fund: FundData, all_funds: List[FundData]) -> float:
    """
    短期业绩相对评分 (20分) - 今年以来收益

    评分标准（按百分位，收益越高越好）：
    - 前10%（收益最高）：18-20分
    - 前10%-30%：15-17分
    - 前30%-70%：12-14分
    - 前70%-90%：8-11分
    - 后10%（收益最低）：0-7分
    """
    # 获取所有有效收益率
    returns = [f.yearly_return for f in all_funds if f.yearly_return is not None]

    if not returns or fund.yearly_return is None:
        return 10.0  # 默认中等分数

    # 计算百分位排名（收益越高，排名越高）
    percentile = sum(1 for r in returns if r <= fund.yearly_return) / len(returns)

    # 映射到分数
    if percentile >= 0.9:  # 前10%
        return 18 + (percentile - 0.9) / 0.1 * 2
    elif percentile >= 0.7:  # 前10%-30%
        return 15 + (percentile - 0.7) / 0.2 * 2
    elif percentile >= 0.3:  # 前30%-70%
        return 12 + (percentile - 0.3) / 0.4 * 2
    elif percentile >= 0.1:  # 前70%-90%
        return 8 + (percentile - 0.1) / 0.2 * 3
    else:  # 后10%
        return max(0, 7 * percentile / 0.1)


def _score_long_term_performance_relative(fund: FundData, all_funds: List[FundData]) -> float:
    """
    长期业绩相对评分 (25分) - 5年收益

    评分标准（按百分位，年化收益越高越好）：
    - 前10%（收益最高）：22-25分
    - 前10%-30%：18-21分
    - 前30%-70%：14-17分
    - 前70%-90%：10-13分
    - 后10%（收益最低）：0-9分

    注意：只使用5年数据，没有5年数据的基金得默认中等分(12分)
    """
    # 只使用5年数据计算年化收益率
    annualized_returns = []

    for f in all_funds:
        if f.return_5year is not None:
            # 计算5年年化收益率
            long_term_return = (1 + f.return_5year / 100) ** (1/5) - 1
            annualized_returns.append(long_term_return * 100)  # 转为百分比

    if not annualized_returns:
        return 12.0  # 默认中等分数

    # 计算当前基金的5年年化收益率
    if fund.return_5year is None:
        return 12.0  # 没有5年数据，得默认中等分

    fund_return = (1 + fund.return_5year / 100) ** (1/5) - 1
    fund_return_pct = fund_return * 100

    # 计算百分位排名（收益越高，排名越高）
    percentile = sum(1 for r in annualized_returns if r <= fund_return_pct) / len(annualized_returns)

    # 映射到分数
    if percentile >= 0.9:  # 前10%
        return 22 + (percentile - 0.9) / 0.1 * 3
    elif percentile >= 0.7:  # 前10%-30%
        return 18 + (percentile - 0.7) / 0.2 * 3
    elif percentile >= 0.3:  # 前30%-70%
        return 14 + (percentile - 0.3) / 0.4 * 3
    elif percentile >= 0.1:  # 前70%-90%
        return 10 + (percentile - 0.1) / 0.2 * 3
    else:  # 后10%
        return max(0, 9 * percentile / 0.1)


def _score_stability_relative(fund: FundData, all_funds: List[FundData]) -> float:
    """
    稳定性相对评分 (15分) - 成立时间

    评分标准（按百分位，成立时间越长越好）：
    - 前10%（成立最久）：12-15分
    - 前10%-30%：10-11分
    - 前30%-70%：8-9分
    - 前70%-90%：5-7分
    - 后10%（成立最短）：0-4分
    """
    # 计算所有基金的成立年限
    ages = []

    for f in all_funds:
        if f.establish_date:
            try:
                date_obj = datetime.strptime(f.establish_date, "%Y-%m-%d")
                years = (datetime.now() - date_obj).days / 365.25
                ages.append(years)
            except:
                pass

    if not ages:
        return 8.0  # 默认中等分数

    # 计算当前基金的成立年限
    if not fund.establish_date:
        return 8.0  # 默认中等分数

    try:
        date_obj = datetime.strptime(fund.establish_date, "%Y-%m-%d")
        fund_age = (datetime.now() - date_obj).days / 365.25

        # 计算百分位排名（成立越久，排名越高）
        percentile = sum(1 for a in ages if a <= fund_age) / len(ages)

        # 映射到分数
        if percentile >= 0.9:  # 前10%
            return 12 + (percentile - 0.9) / 0.1 * 3
        elif percentile >= 0.7:  # 前10%-30%
            return 10 + (percentile - 0.7) / 0.2 * 1
        elif percentile >= 0.3:  # 前30%-70%
            return 8 + (percentile - 0.3) / 0.4 * 1
        elif percentile >= 0.1:  # 前70%-90%
            return 5 + (percentile - 0.1) / 0.2 * 2
        else:  # 后10%
            return max(0, 4 * percentile / 0.1)
    except:
        return 8.0
