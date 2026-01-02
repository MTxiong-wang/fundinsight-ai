"""晨星基金API客户端 - 高效获取基金数据"""
import asyncio
import logging
import sys
import os
from typing import Optional, Dict, List
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from models.fund import FundData
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


class MorningstarClient:
    """晨星基金API客户端"""

    def __init__(self, max_concurrent: int = 10, request_delay: float = 0.5, fund_names_file: str = None):
        """
        初始化客户端

        Args:
            max_concurrent: 最大并发数
            request_delay: 请求间隔(秒)
            fund_names_file: 基金名称映射文件路径
        """
        self.base_url = "https://www.morningstar.cn/cn-api/v2/funds"
        self.max_concurrent = max_concurrent
        self.request_delay = request_delay
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.client: Optional[httpx.AsyncClient] = None
        self.fund_names = self._load_fund_names(fund_names_file)

    def _load_fund_names(self, fund_names_file: str) -> dict:
        """加载基金名称映射"""
        if fund_names_file and os.path.exists(fund_names_file):
            try:
                import json
                with open(fund_names_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载基金名称映射失败: {e}")
        return {}

    async def __aenter__(self):
        """进入上下文管理器"""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        if self.client:
            await self.client.aclose()

    async def _fetch_api(self, fund_code: str, endpoint: str) -> Optional[Dict]:
        """
        获取API数据

        Args:
            fund_code: 基金代码
            endpoint: API端点

        Returns:
            JSON数据或None
        """
        async with self.semaphore:
            url = f"{self.base_url}/{fund_code}/{endpoint}"

            try:
                response = await self.client.get(url)
                response.raise_for_status()

                data = response.json()

                # 检查响应状态
                if data.get("_meta", {}).get("response_status") == "200011":
                    return data.get("data")
                else:
                    logger.warning(f"API返回异常状态: {fund_code} - {endpoint}")
                    return None

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"基金不存在: {fund_code}")
                elif e.response.status_code == 429:
                    logger.warning(f"请求过于频繁，等待后重试: {fund_code}")
                    await asyncio.sleep(5)
                else:
                    logger.error(f"HTTP错误 {e.response.status_code}: {fund_code}")
                return None

            except Exception as e:
                logger.error(f"请求失败: {fund_code} - {endpoint} - {e}")
                return None

            finally:
                # 添加延迟避免请求过快
                await asyncio.sleep(self.request_delay)

    async def get_fund_data(self, fund_code: str) -> Optional[FundData]:
        """
        获取基金完整数据

        Args:
            fund_code: 基金代码

        Returns:
            FundData对象或None
        """
        logger.debug(f"获取基金数据: {fund_code}")

        # 并发获取3个API数据
        common_data, performance_data, fees_data = await asyncio.gather(
            self._fetch_api(fund_code, "common-data"),
            self._fetch_api(fund_code, "performance"),
            self._fetch_api(fund_code, "fees"),
            return_exceptions=True
        )

        # 检查是否成功获取数据
        if not common_data:
            logger.error(f"无法获取基金 {fund_code} 的基础数据")
            return None

        try:
            # 提取基础数据
            # 优先使用中证下载的基金名称
            name = self.fund_names.get(fund_code)
            if not name:
                # 尝试从晨星API获取
                name = (common_data.get("name") or
                       common_data.get("fundName") or
                       f"基金{fund_code}")

            # 判断基金类型（场内/场外）- 基于代码前缀
            # 场内基金：51/588(上交所ETF)、159(深交所ETF)、16(LOF)、15(封闭式)
            # 场外基金：其他前缀（00/01等）
            if fund_code.startswith('51') or fund_code.startswith('588') or \
               fund_code.startswith('159') or fund_code.startswith('16') or \
               fund_code.startswith('15'):
                fund_type = "场内"
            else:
                fund_type = "场外"

            establish_date = common_data.get("inceptionDate", "")

            # 规模（元转亿元）
            fund_size_raw = common_data.get("fundSize", 0)
            scale = round(fund_size_raw / 100000000, 2) if fund_size_raw else 0.0

            # 基准指数 - 从performance API获取benchmarkName（晨星比较基准）
            benchmark = performance_data.get("benchmarkName", "") if performance_data else ""

            # 提取费用数据（从fees API获取真实数据）
            fees_info = self._extract_fees_data(fees_data)

            # 提取业绩数据
            yearly_return = None
            return_3year = None
            return_5year = None
            benchmark_return = None
            beats_benchmark = None
            beats_benchmark_amount = None

            if performance_data:
                # performance_data is already the "data" object from _fetch_api
                day_end = performance_data.get("dayEnd", {})
                returns = day_end.get("returns", {})
                benchmark_returns = day_end.get("benchmarkReturns", {})

                # 今年以来收益
                yearly_return = returns.get("YTD")
                # 3年和5年收益
                return_3year = returns.get("Y3")
                return_5year = returns.get("Y5")

                benchmark_return = benchmark_returns.get("YTD")

                if yearly_return is not None and benchmark_return is not None:
                    beats_benchmark = yearly_return > benchmark_return
                    beats_benchmark_amount = yearly_return - benchmark_return

                # 转换为百分比
                if yearly_return is not None:
                    yearly_return = round(yearly_return, 2)
                if return_3year is not None:
                    return_3year = round(return_3year, 2)
                if return_5year is not None:
                    return_5year = round(return_5year, 2)
                if benchmark_return is not None:
                    benchmark_return = round(benchmark_return, 2)
                if beats_benchmark_amount is not None:
                    beats_benchmark_amount = round(beats_benchmark_amount, 2)

            # 创建FundData对象（使用fees API的真实费用数据）
            fund_data = FundData(
                code=fund_code,
                name=name,
                management_fee=fees_info["management_fee"],
                custody_fee=fees_info["custody_fee"],
                subscription_fee=fees_info["subscription_fee"],
                redemption_fee=fees_info["redemption_fee"],
                sales_service_fee=fees_info["sales_service_fee"],
                transaction_cost=fees_info["transaction_cost"],
                other_fees=fees_info["other_fees"],
                total_annual_fee=fees_info["total_annual_fee"],
                scale=scale,
                yearly_return=yearly_return,
                return_3year=return_3year,
                return_5year=return_5year,
                establish_date=establish_date,
                benchmark=benchmark,
                beats_benchmark=beats_benchmark,
                beats_benchmark_amount=beats_benchmark_amount,
                fund_type=fund_type
            )

            logger.info(f"[OK] {fund_code}: {name}")
            return fund_data

        except Exception as e:
            logger.error(f"解析基金数据失败: {fund_code} - {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_fees_data(self, fees_data: dict) -> dict:
        """
        从fees API提取费用数据

        Args:
            fees_data: fees API返回的数据

        Returns:
            dict: {
                "management_fee": 管理费(小数形式，如0.0015表示0.15%),
                "custody_fee": 托管费,
                "subscription_fee": 申购费,
                "redemption_fee": 赎回费,
                "sales_service_fee": 销售服务费,
                "transaction_cost": 交易成本,
                "other_fees": 其它费用,
                "total_annual_fee": 年度总费率
            }
        """
        # 默认值（当API无数据时使用）
        default_fees = {
            "management_fee": 0.0015,  # 0.15%
            "custody_fee": 0.0005,     # 0.05%
            "subscription_fee": 0.0,   # ETF无申购费
            "redemption_fee": 0.0,     # 假设长期持有
            "sales_service_fee": 0.0,  # 通常无
            "transaction_cost": 0.0,
            "other_fees": 0.0,
            "total_annual_fee": 0.002  # 0.2%
        }

        if not fees_data or not fees_data.get("fees"):
            logger.warning("fees API返回数据为空，使用默认值")
            return default_fees

        try:
            fees = fees_data["fees"]

            # 从API提取数据（API返回的是百分比值，如0.15表示0.15%）
            # 需要转换为小数形式（0.15% -> 0.0015）
            management_fee = (fees.get("managementFee") or 0.15) / 100
            custody_fee = (fees.get("custodianFee") or 0.05) / 100
            sales_service_fee = (fees.get("distributionFee") or 0) / 100

            # 隐性费用（hiddenCost = tradeCost + otherCost）
            transaction_cost = (fees.get("tradeCost") or 0) / 100
            other_fees = (fees.get("otherCost") or 0) / 100

            # 申购费和赎回费（API中可能没有，使用默认值）
            # ETF通常无申购费，赎回费根据持有时间而定
            subscription_fee = 0.0
            redemption_fee = 0.0

            # 年度总费率 = 管理费 + 托管费 + 销售服务费 + 交易成本 + 其它费用
            total_annual_fee = (
                management_fee +
                custody_fee +
                sales_service_fee +
                transaction_cost +
                other_fees
            )

            return {
                "management_fee": management_fee,
                "custody_fee": custody_fee,
                "subscription_fee": subscription_fee,
                "redemption_fee": redemption_fee,
                "sales_service_fee": sales_service_fee,
                "transaction_cost": transaction_cost,
                "other_fees": other_fees,
                "total_annual_fee": total_annual_fee
            }

        except Exception as e:
            logger.error(f"解析费用数据失败: {e}")
            return default_fees

    async def batch_get_fund_data(
        self,
        fund_codes: List[str],
        show_progress: bool = True
    ) -> List[FundData]:
        """
        批量获取基金数据

        Args:
            fund_codes: 基金代码列表
            show_progress: 是否显示进度

        Returns:
            基金数据列表
        """
        total = len(fund_codes)
        funds = []
        failed = []

        # 分批处理
        batch_size = self.max_concurrent
        for i in range(0, total, batch_size):
            batch = fund_codes[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            # Debug logging for batch details
            logger.debug(f"处理批次 {batch_num}/{total_batches} (基金 {i+1}-{min(i+batch_size, total)})")

            # 并发获取本批次数据
            batch_results = await asyncio.gather(
                *[self.get_fund_data(code) for code in batch],
                return_exceptions=True
            )

            # 收集结果
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    failed.append(batch[j])
                    logger.debug(f"基金 {batch[j]} 获取失败: {result}")
                elif result is not None:
                    funds.append(result)

        # 只显示汇总信息
        console.print(f"\n[cyan]批量获取完成:[/cyan]")
        console.print(f"  成功: [green]{len(funds)}[/green] 只")
        console.print(f"  失败: [red]{len(failed)}[/red] 只")

        if failed:
            logger.debug(f"失败的基金代码: {', '.join(failed)}")

        return funds


async def test_client():
    """测试API客户端"""
    fund_code = "515890"

    console.print(f"[cyan]测试获取基金 {fund_code} 的数据[/cyan]\n")

    async with MorningstarClient(max_concurrent=5, request_delay=0.5) as client:
        fund_data = await client.get_fund_data(fund_code)

        if fund_data:
            console.print(f"\n[cyan]基金数据:[/cyan]")
            console.print(f"  代码: {fund_data.code}")
            console.print(f"  名称: {fund_data.name}")
            console.print(f"  规模: {fund_data.scale}亿")
            console.print(f"  管理费: {fund_data.management_fee}%")
            console.print(f"  托管费: {fund_data.custody_fee}%")
            console.print(f"  成立日期: {fund_data.establish_date}")
            console.print(f"  今年收益: {fund_data.yearly_return}%")
            console.print(f"  基准: {fund_data.benchmark}")
            console.print(f"  跑赢基准: {fund_data.beats_benchmark}")
            if fund_data.beats_benchmark_amount is not None:
                console.print(f"  跑赢幅度: {fund_data.beats_benchmark_amount}%")

        # 测试批量获取
        console.print(f"\n[cyan]测试批量获取[/cyan]\n")
        test_codes = ["515890", "516160", "000001"]
        funds = await client.batch_get_fund_data(test_codes)

        console.print(f"\n[cyan]批量获取结果:[/cyan]")
        for fund in funds:
            console.print(f"  {fund.code} - {fund.name} - {fund.scale}亿")


if __name__ == "__main__":
    asyncio.run(test_client())
