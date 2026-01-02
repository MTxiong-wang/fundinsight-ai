"""FundInsight AI - 板块基金智能排名工具"""
import asyncio
import argparse
import sys
import os
import logging
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler

from scrapers.csindex import search_sector_funds
from scrapers.morningstar_client import MorningstarClient
from ai.scorer import AIScorer
from models.fund import score_fund
from config import Config

# 配置日志
# 创建logs目录
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

# 配置日志系统
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # 文件处理器：记录所有日志到文件
        logging.FileHandler(
            log_dir / f"fundinsight_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        ),
        # 控制台处理器：只显示错误及以上级别
        RichHandler(
            rich_tracebacks=True,
            level=logging.ERROR,
            show_time=False,
            show_path=False
        )
    ]
)
logger = logging.getLogger(__name__)

console = Console()


def export_tool_scores_to_markdown(sector_name: str, scored_funds: list) -> str:
    """
    导出工具评分结果到Markdown文件（立即输出，不等待AI）

    Args:
        sector_name: 板块名称
        scored_funds: 评分后的基金列表

    Returns:
        output_file: 输出文件路径
    """
    # 创建输出目录: outputs/
    # 输出文件: outputs/板块名_日期.md
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{sector_name}_{date_str}.md"

    with open(output_file, 'w', encoding='utf-8') as f:
        # 标题
        f.write(f"# {sector_name}板块基金排名\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**基金总数**: {len(scored_funds)}只\n\n")
        f.write("---\n\n")

        # 工具评分结果
        f.write("## 工具评分结果（前20名）\n\n")
        f.write("### 评分标准（满分100分 - 相对评分）\n\n")
        f.write("- **费用合理性 (15分)**: 年度总费率越低得分越高\n")
        f.write("- **规模适中性 (15分)**: 规模越接近理想区间得分越高\n")
        f.write("- **短期业绩 (20分)**: 今年以来收益率越高得分越高\n")
        f.write("- **长期业绩 (25分)**: 5年收益率越高得分越高（无5年数据得默认12分）\n")
        f.write("- **跑赢基准 (10分)**: 超额收益越大得分越高\n")
        f.write("- **稳定性 (15分)**: 成立年限越长得分越高\n\n")

        f.write("### 排名表格\n\n")
        # 使用详细列名，增加基金类型和晨星比较基准列
        f.write("| 排名 | 代码 | 名称 | 类型 | 总评分 | 费用合理性(15分) | 规模适中性(15分) | 近一年涨幅(20分) | 近五年涨幅(25分) | 超额收益(10分) | 成立时间(15分) | 晨星比较基准 |\n")
        f.write("|------|------|------|------|--------|------------------|------------------|------------------|------------------|------------------|------------------|----------|\n")

        for i, item in enumerate(scored_funds[:20], 1):
            fund = item["fund"]
            score = item["score"]
            breakdown = item["breakdown"]

            # 基金类型
            fund_type = fund.fund_type if fund.fund_type else "未知"

            # 费用列
            explicit_fee = fund.management_fee + fund.custody_fee + (fund.subscription_fee or 0) + (fund.sales_service_fee or 0)
            implicit_fee = (fund.transaction_cost or 0) + (fund.other_fees or 0)
            fee_col = f"{breakdown['费用合理性']:.1f} / {fund.total_annual_fee * 100:.2f}% (显性{explicit_fee * 100:.2f}%+隐性{implicit_fee * 100:.2f}%)"

            # 规模列
            scale_col = f"{breakdown['规模适中性']:.1f} / {fund.scale:.2f}亿"

            # 短期业绩列
            ytd_col = f"{breakdown['短期业绩(YTD)']:.1f} / {fund.yearly_return:.2f}%" if fund.yearly_return else f"{breakdown['短期业绩(YTD)']:.1f} / N/A"

            # 长期业绩列（只显示5年数据）
            if fund.return_5year is not None:
                long_term_col = f"{breakdown['长期业绩(5年)']:.1f} / {fund.return_5year:.2f}%"
            else:
                long_term_col = f"{breakdown['长期业绩(5年)']:.1f} / N/A"

            # 超额收益列
            if fund.beats_benchmark is not None and fund.beats_benchmark_amount is not None:
                benchmark_col = f"{breakdown['跑赢基准']:.1f} / {'跑赢' if fund.beats_benchmark else '未跑赢'} ({fund.beats_benchmark_amount:+.2f}%)"
            elif fund.beats_benchmark is not None:
                benchmark_col = f"{breakdown['跑赢基准']:.1f} / {'跑赢' if fund.beats_benchmark else '未跑赢'}"
            else:
                benchmark_col = f"{breakdown['跑赢基准']:.1f} / N/A"

            # 成立时间列
            if fund.establish_date:
                try:
                    date_obj = datetime.strptime(fund.establish_date, "%Y-%m-%d")
                    years = (datetime.now() - date_obj).days / 365.25
                    stability_col = f"{breakdown['稳定性']:.1f} / {years:.1f}年 ({fund.establish_date})"
                except:
                    stability_col = f"{breakdown['稳定性']:.1f} / {fund.establish_date}"
            else:
                stability_col = f"{breakdown['稳定性']:.1f} / N/A"

            # 比较基准列
            benchmark_name = fund.benchmark if fund.benchmark else "N/A"

            f.write(f"| {i} | {fund.code} | {fund.name} | {fund_type} | {score:.1f} | {fee_col} | {scale_col} | {ytd_col} | {long_term_col} | {benchmark_col} | {stability_col} | {benchmark_name} |\n")

    console.print(f"[green]✅ 工具评分已保存到: {output_file}[/green]")
    return str(output_file)


def append_ai_results_to_markdown(output_file: str, ai_result: str):
    """
    将AI评分结果追加到已存在的Markdown文件

    Args:
        output_file: Markdown文件路径
        ai_result: AI评分结果
    """
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write("\n---\n\n")
        f.write("## AI评分结果\n\n")
        f.write(ai_result)
        f.write("\n")

    console.print(f"[green]✅ AI评分结果已追加到: {output_file}[/green]")


def export_to_markdown(sector_name: str, scored_funds: list, ai_result: str = None):
    """
    导出结果到Markdown文件（兼容旧接口，内部调用新函数）

    Args:
        sector_name: 板块名称
        scored_funds: 评分后的基金列表
        ai_result: AI评分结果（可选）
    """
    # 先输出工具评分
    output_file = export_tool_scores_to_markdown(sector_name, scored_funds)

    # 如果有AI结果，追加到文件
    if ai_result:
        append_ai_results_to_markdown(output_file, ai_result)


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   FundInsight AI - 基金智析                               ║
║   板块基金智能排名工具                                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")


async def analyze_sector(sector_name: str):
    """
    分析板块基金的主流程

    Args:
        sector_name: 板块名称，如"新能源"、"半导体"
    """
    console.print(Panel.fit(f"🎯 分析板块: {sector_name}", style="bold green"))
    console.print()

    # 步骤1: 搜索板块基金
    with console.status(f"[bold green]正在搜索 {sector_name} 板块基金...") as status:
        fund_codes = await search_sector_funds(sector_name)

        if not fund_codes:
            console.print("[red]❌ 未找到相关基金[/red]")
            return

        console.print(f"✅ 找到 [cyan]{len(fund_codes)}[/cyan] 只基金")

    # 步骤2: 抓取基金数据
    console.print()
    with console.status("[bold green]正在抓取基金数据...", spinner="dots") as status:
        # 传递基金名称映射文件路径
        fund_names_file = os.path.join(os.getcwd(), "downloads", "fund_names_mapping.json")

        async with MorningstarClient(
            max_concurrent=10,
            request_delay=0.5,
            fund_names_file=fund_names_file
        ) as client:
            funds = await client.batch_get_fund_data(fund_codes)

        if not funds:
            console.print("[red]❌ 未能获取任何基金数据[/red]")
            return

        console.print(f"✅ 成功获取 [cyan]{len(funds)}[/cyan] 只基金的数据")

    # 显示基金列表预览
    console.print()
    console.print("[dim]基金列表预览:[/dim]")
    for fund in funds[:3]:  # 显示前3个
        console.print(f"  • {fund.code} {fund.name} - 规模{fund.scale}亿")
    if len(funds) > 3:
        console.print(f"  ... 还有 {len(funds) - 3} 只基金")

    # 步骤3: 我们工具的评分排名
    logger.info("开始工具评分排名...")

    # 使用我们的评分标准对基金进行评分（相对评分）
    scored_funds = []
    for fund in funds:
        score, breakdown = score_fund(fund, all_funds=funds)
        scored_funds.append({
            "fund": fund,
            "score": score,
            "breakdown": breakdown
        })

    # 按分数排序
    scored_funds.sort(key=lambda x: x["score"], reverse=True)

    logger.info(f"工具评分完成，共 {len(scored_funds)} 只基金")

    # 步骤4: 立即输出工具评分到Markdown
    console.print()
    output_file = export_tool_scores_to_markdown(sector_name, scored_funds)

    # 步骤5: AI 评分排名并追加到Markdown
    console.print()
    scorer = AIScorer()
    ai_result = None
    with console.status("[bold green]AI 正在分析评分...", spinner="dots2"):
        ai_result = await scorer.rank_funds_with_ai(sector_name, funds)

    # 如果AI评分成功，追加到文件
    if ai_result:
        append_ai_results_to_markdown(output_file, ai_result)


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="FundInsight AI - 板块基金智能排名工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py 新能源
  python main.py 半导体
  python main ai 医疗
        """
    )

    parser.add_argument(
        "sector",
        help="板块名称（如：新能源、半导体、医疗等）"
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version="FundInsight AI v1.0.0"
    )

    args = parser.parse_args()

    try:
        # 验证配置
        Config.validate()

        # 打印横幅
        print_banner()

        # 执行分析
        asyncio.run(analyze_sector(args.sector))

    except ValueError as e:
        console.print(f"[red]配置错误: {e}[/red]")
        console.print("\n[dim]提示: 请复制 .env.example 为 .env 并配置 API密钥[/dim]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]用户取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]发生错误: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
