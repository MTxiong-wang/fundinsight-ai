"""
测试完整费用计算（以515890为例）
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.morningstar_client import MorningstarClient
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


async def test_fee_calculation():
    """测试完整费用计算"""
    fund_code = "515890"

    console.print(f"\n[bold cyan]={'='*80}[/bold cyan]")
    console.print(f"[bold cyan]测试基金 {fund_code} 的完整费用计算[/bold cyan]")
    console.print(f"[bold cyan]={'='*80}[/bold cyan]\n")

    # 获取基金数据
    async with MorningstarClient(max_concurrent=10, request_delay=0.5) as client:
        fund = await client.get_fund_data(fund_code)

        if not fund:
            console.print("[red]获取基金数据失败[/red]")
            return

        # 显示基础信息
        console.print(Panel.fit(
            f"[bold]基金代码:[/bold] {fund.code}\n"
            f"[bold]基金名称:[/bold] {fund.name}\n"
            f"[bold]基金规模:[/bold] {fund.scale}亿元\n"
            f"[bold]今年收益:[/bold] {fund.yearly_return}%\n"
            f"[bold]成立日期:[/bold] {fund.establish_date}",
            title="基础信息",
            border_style="cyan"
        ))

        # 创建费用明细表
        console.print("\n[bold yellow]费用明细表[/bold yellow]\n")

        # 显性费用表
        explicit_table = Table(title="显性费用（合同中明确披露）", show_header=True, header_style="bold magenta")
        explicit_table.add_column("费用类型", style="cyan", width=20)
        explicit_table.add_column("费率", style="yellow", width=15)
        explicit_table.add_column("说明", style="white", width=40)

        explicit_table.add_row("管理费", f"{fund.management_fee * 100:.2f}%", "基金公司收取，用于管理费用")
        explicit_table.add_row("托管费", f"{fund.custody_fee * 100:.2f}%", "托管银行收取，用于资产保管")
        explicit_table.add_row("申购费", f"{fund.subscription_fee * 100:.2f}%", "一次性费用，购买时支付")
        explicit_table.add_row("赎回费", f"{fund.redemption_fee * 100:.2f}%", "一次性费用，卖出时支付（与持有时间相关）")
        explicit_table.add_row("销售服务费", f"{fund.sales_service_fee * 100:.2f}%", "销售机构收取（通常A类无，C类有）")

        console.print(explicit_table)

        # 隐性费用表
        implicit_table = Table(title="隐性费用（不在合同中明确披露，需要估算）", show_header=True, header_style="bold magenta")
        implicit_table.add_column("费用类型", style="cyan", width=20)
        implicit_table.add_column("费率", style="yellow", width=15)
        implicit_table.add_column("说明", style="white", width=40)

        implicit_table.add_row(
            "交易成本",
            f"{fund.transaction_cost * 100:.2f}%",
            "根据换手率估算（股票佣金+印花税+冲击成本）"
        )
        implicit_table.add_row(
            "其它费用",
            f"{fund.other_fees * 100:.2f}%",
            "审计费、律师费、信息披露费、上市年费等"
        )

        console.print("\n")
        console.print(implicit_table)

        # 费用汇总表
        console.print("\n[bold yellow]费用汇总[/bold yellow]\n")

        summary_table = Table(show_header=True, header_style="bold green")
        summary_table.add_column("项目", style="cyan", width=25)
        summary_table.add_column("费率", style="yellow", width=15)
        summary_table.add_column("占比", style="green", width=15)

        # 计算各项费用占比
        total_explicit = fund.management_fee + fund.custody_fee + fund.sales_service_fee
        total_implicit = fund.transaction_cost + fund.other_fees
        total = fund.total_annual_fee

        summary_table.add_row("显性费用小计", f"{total_explicit * 100:.2f}%", f"{total_explicit / total * 100:.1f}%")
        summary_table.add_row("隐性费用小计", f"{total_implicit * 100:.2f}%", f"{total_implicit / total * 100:.1f}%")
        summary_table.add_row("", "", "")
        summary_table.add_row(
            "[bold]年度总费率[/bold]",
            f"[bold]{total * 100:.2f}%[/bold]",
            "[bold]100%[/bold]"
        )

        console.print(summary_table)

        # 费用评分
        console.print("\n[bold yellow]费用评分[/bold yellow]\n")

        fee_pct = total * 100
        if fee_pct < 0.8:
            score = 20
            rating = "[green]优秀（低费率）[/green]"
        elif fee_pct < 1.2:
            score = 16
            rating = "[cyan]良好（费率适中）[/cyan]"
        elif fee_pct < 1.8:
            score = 13
            rating = "[yellow]一般（标准费率）[/yellow]"
        elif fee_pct < 2.5:
            score = 10
            rating = "[orange1]偏高（考虑优化）[/orange1]"
        else:
            score = 7
            rating = "[red]过高（建议回避）[/red]"

        console.print(f"年度总费率: [bold]{fee_pct:.2f}%[/bold]")
        console.print(f"费用评分: [bold]{score}/20[/bold]")
        console.print(f"评级: {rating}")

        # 费用对比（同类基金）
        console.print("\n[bold yellow]费用对比（估算）[/bold yellow]\n")

        compare_table = Table(show_header=True, header_style="bold magenta")
        compare_table.add_column("基金类型", style="cyan", width=20)
        compare_table.add_column("预估总费率", style="yellow", width=15)
        compare_table.add_column("对比", style="green", width=30)

        compare_table.add_row(
            "ETF/指数基金",
            "0.7%-1.0%",
            f"本基金({fee_pct:.2f}%) {'更低' if fee_pct < 1.0 else '相近' if fee_pct < 1.2 else '更高'}"
        )
        compare_table.add_row(
            "主动股票基金",
            "1.8%-2.5%",
            f"本基金({fee_pct:.2f}%) {'更低' if fee_pct < 1.8 else '相近' if fee_pct < 2.5 else '更高'}"
        )

        console.print(compare_table)

        # 费用优化建议
        console.print("\n[bold yellow]费用优化建议[/bold yellow]\n")

        if fee_pct < 0.8:
            console.print("[green]这款基金的费用非常低廉，主要是ETF或指数基金的优势。[/green]")
            console.print("[green]建议：长期持有，享受低费率优势。[/green]")
        elif fee_pct < 1.2:
            console.print("[cyan]这款基金的费用适中，低于大多数主动基金。[/cyan]")
            console.print("[cyan]建议：可以考虑投资，费用不是主要劣势。[/cyan]")
        elif fee_pct < 1.8:
            console.print("[yellow]这款基金的费用属于标准水平，主动基金通常在这个范围。[/yellow]")
            console.print("[yellow]建议：如果业绩优秀，可以接受这个费用水平。[/yellow]")
        elif fee_pct < 2.5:
            console.print("[orange1]这款基金的费用偏高，可能是高换手率的主动基金。[/orange1]")
            console.print("[orange1]建议：需要评估业绩是否足以覆盖高费用成本。[/orange1]")
        else:
            console.print("[red]警告：这款基金的费用过高！[/red]")
            console.print("[red]建议：谨慎考虑，除非有非常突出的长期业绩。[/red]")

        console.print("\n")


if __name__ == "__main__":
    asyncio.run(test_fee_calculation())
