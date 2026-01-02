"""Test if fund data has performance values"""
import asyncio
import sys
sys.path.insert(0, '.')

from scrapers.morningstar_client import MorningstarClient
from rich.console import Console

console = Console()

async def test():
    fund_code = "515890"
    console.print(f"[cyan]Testing fund {fund_code}[/cyan]")

    async with MorningstarClient(max_concurrent=1, request_delay=0.5) as client:
        fund = await client.get_fund_data(fund_code)

        if fund:
            console.print("\n[bold]Fund Data:[/bold]")
            console.print(f"  Code: {fund.code}")
            console.print(f"  Name: {fund.name}")
            console.print(f"  Scale: {fund.scale}亿")
            console.print(f"  Yearly Return (YTD): {fund.yearly_return}%")
            console.print(f"  3-Year Return: {fund.return_3year}%")
            console.print(f"  5-Year Return: {fund.return_5year}%")
            console.print(f"  Management Fee: {fund.management_fee * 100}%")
            console.print(f"  Custody Fee: {fund.custody_fee * 100}%")
            console.print(f"  Total Annual Fee: {fund.total_annual_fee * 100 if fund.total_annual_fee else 'N/A'}%")

            # Check if values are None
            console.print("\n[bold]Value Check:[/bold]")
            console.print(f"  yearly_return is None: {fund.yearly_return is None}")
            console.print(f"  return_3year is None: {fund.return_3year is None}")
            console.print(f"  return_5year is None: {fund.return_5year is None}")

asyncio.run(test())
