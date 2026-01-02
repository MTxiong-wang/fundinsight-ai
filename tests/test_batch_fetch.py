"""测试批量爬取基金数据"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.morningstar_client import MorningstarClient
from rich.console import Console

console = Console()


async def test_batch_fetch():
    """测试批量爬取前50个基金"""

    # 从之前获取的消费板块基金列表中读取前50个
    fund_codes = [
        "589130", "026163", "025755", "026183", "026295",
        "026147", "025488", "563930", "025727", "026229",
        "024383", "025435", "024600", "520810", "025576",
        "026083", "563790", "024225", "025866", "588410",
        "588420", "588430", "589150", "562070", "024992",
        "159136", "025334", "025911", "589210", "517950",
        "025690", "563850", "159139", "159140", "516250",
        "023514", "026059", "024760", "520780", "159142",
        "563960", "025954", "026093", "025804", "025723",
        "159141", "025958", "025763", "025308", "024715"
    ]

    console.print(f"[cyan]开始批量爬取 {len(fund_codes)} 只基金...[/cyan]\n")

    async with MorningstarClient(max_concurrent=10, request_delay=0.5) as client:
        funds = await client.batch_get_fund_data(fund_codes, show_progress=True)

    console.print(f"\n[cyan]爬取完成![/cyan]")
    console.print(f"成功: [green]{len(funds)}[/green] 只基金\n")

    # 显示前10只基金
    console.print("[cyan]前10只基金数据:[/cyan]")
    for i, fund in enumerate(funds[:10], 1):
        console.print(f"\n{i}. {fund.code} - {fund.name}")
        console.print(f"   规模: {fund.scale}亿 | 收益: {fund.yearly_return}% | 费率: {fund.management_fee + fund.custody_fee}%")
        console.print(f"   成立: {fund.establish_date} | 基准: {fund.benchmark}")

    # 保存到文件
    import json
    data = [fund.model_dump() for fund in funds]
    with open("funds_batch_result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    console.print(f"\n[green]数据已保存到: funds_batch_result.json[/green]")


if __name__ == "__main__":
    import time
    start = time.time()
    asyncio.run(test_batch_fetch())
    elapsed = time.time() - start
    console.print(f"\n[cyan]总耗时: {elapsed:.2f}秒[/cyan]")
