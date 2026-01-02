"""晨星基金爬虫 - 获取基金详细数据（已升级为API版本）"""
import asyncio
from typing import Optional
from rich.console import Console
from models.fund import FundData
from scrapers.morningstar_client import MorningstarClient

console = Console()


async def get_fund_data(fund_code: str) -> Optional[FundData]:
    """
    从晨星基金获取基金详细数据（使用高效API）

    Args:
        fund_code: 基金代码，如"516160"

    Returns:
        FundData 对象，失败返回 None
    """
    # 使用新的API客户端
    async with MorningstarClient(max_concurrent=5, request_delay=0.5) as client:
        return await client.get_fund_data(fund_code)


async def batch_get_fund_data(fund_codes: list) -> list:
    """
    批量获取基金数据（使用高效API并发）

    Args:
        fund_codes: 基金代码列表

    Returns:
        基金数据列表
    """
    console.print(f"[cyan]使用高效API并发获取 {len(fund_codes)} 只基金数据...[/cyan]\n")

    # 使用新的API客户端批量获取
    async with MorningstarClient(max_concurrent=10, request_delay=0.5) as client:
        funds = await client.batch_get_fund_data(fund_codes, show_progress=True)

    console.print(f"\n[green]批量获取完成，共 {len(funds)} 只基金[/green]")
    return funds


async def test_morningstar_scraper():
    """测试晨星爬虫"""
    fund_codes = ["515890", "516160", "000001"]
    funds = await batch_get_fund_data(fund_codes)

    console.print(f"\n[cyan]测试结果:[/cyan]")
    for fund in funds:
        console.print(f"  {fund.code} - {fund.name} - 规模{fund.scale}亿")


if __name__ == "__main__":
    asyncio.run(test_morningstar_scraper())
