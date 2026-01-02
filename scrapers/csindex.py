"""中证指数官网爬虫 - 获取板块相关基金"""
import asyncio
import os
import logging
import pandas as pd
from playwright.async_api import async_playwright
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


async def search_sector_funds(sector_name: str) -> list:
    """
    在中证指数官网搜索板块,获取相关基金代码列表

    Args:
        sector_name: 板块名称,如"新能源"、"半导体"

    Returns:
        基金代码列表,如["516160", "516790", ...]
    """
    logger.info(f"正在搜索中证指数官网: {sector_name}")

    # 设置下载路径
    download_path = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_path, exist_ok=True)

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            # 1. 访问中证指数官网
            console.print("[dim]访问 https://www.csindex.com.cn ...[/dim]")
            await page.goto("https://www.csindex.com.cn/#/indices/indexProduct", timeout=60000)
            await asyncio.sleep(5)

            # 2. 查找搜索框
            console.print("[dim]查找搜索框...[/dim]")

            # 尝试多种选择器
            search_selectors = [
                "input[placeholder*='搜索']",
                "input[placeholder*='输入']",
                ".el-input__inner",
                "input[type='text']",
                "#app input[type='text']",
            ]

            search_input = None
            for selector in search_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for elem in elements:
                        if await elem.is_visible():
                            search_input = elem
                            console.print(f"[green]找到搜索框: {selector}[/green]")
                            break
                    if search_input:
                        break
                except Exception as e:
                    continue

            if not search_input:
                # 最后尝试:获取第一个可见的text输入框
                console.print("[yellow]尝试查找第一个可见的输入框...[/yellow]")
                all_inputs = await page.query_selector_all("input")
                for inp in all_inputs:
                    try:
                        is_visible = await inp.is_visible()
                        input_type = await inp.get_attribute("type")
                        placeholder = await inp.get_attribute("placeholder")
                        if is_visible and (input_type == "text" or input_type == "search" or
                                                (placeholder and ("搜索" in placeholder or "输入" in placeholder))):
                            search_input = inp
                            console.print(f"[green]找到输入框 (type={input_type}, placeholder={placeholder})[/green]")
                            break
                    except:
                        continue

            if not search_input:
                console.print("[red]未找到搜索框[/red]")
                await browser.close()
                return []

            # 3. 输入板块名称并触发搜索
            console.print(f"[dim]输入板块名称: {sector_name}[/dim]")

            try:
                # 点击搜索框
                await search_input.click(timeout=5000)
                await asyncio.sleep(0.5)

                # 清空并输入
                await search_input.fill("")
                await search_input.type(sector_name, delay=50)
                await asyncio.sleep(1)

                # 尝试多种方式触发搜索
                # 方式1: 按Enter键
                try:
                    await search_input.press("Enter")
                    console.print("[dim]已按Enter键[/dim]")
                except:
                    pass

                # 方式2: 触发blur事件
                await asyncio.sleep(0.5)
                try:
                    await search_input.blur()
                    console.print("[dim]已触发blur事件[/dim]")
                except:
                    pass

                # 方式3: 触发键盘事件
                try:
                    await page.keyboard.press("Enter")
                    console.print("[dim]已触发页面Enter事件[/dim]")
                except:
                    pass

            except Exception as e:
                console.print(f"[red]输入失败: {e}[/red]")
                await browser.close()
                return []

            # 4. 等待搜索结果加载
            console.print("[dim]等待搜索结果加载...[/dim]")
            await asyncio.sleep(5)

            # 5. 查找并点击搜索结果
            console.print("[dim]查找搜索结果...[/dim]")

            # 等待搜索结果出现
            try:
                # 等待包含sector_name的搜索结果出现
                await page.wait_for_selector(f"text={sector_name}", timeout=10000)
                console.print(f"[green]找到包含'{sector_name}'的搜索结果[/green]")
            except:
                console.print(f"[yellow]未找到包含'{sector_name}'的文本结果，尝试查找其他搜索结果...[/yellow]")

            # 查找搜索结果项
            result_selectors = [
                f".search-result:has-text('{sector_name}')",
                f".result-item:has-text('{sector_name}')",
                f"li:has-text('{sector_name}')",
                f"div:has-text('{sector_name}')",
                f"a:has-text('{sector_name}')",
            ]

            clicked_result = False
            for selector in result_selectors:
                try:
                    results = await page.query_selector_all(selector)
                    if results:
                        # 点击第一个匹配的结果
                        await results[0].click()
                        console.print(f"[green]已点击搜索结果: {selector}[/green]")
                        clicked_result = True
                        break
                except:
                    continue

            if not clicked_result:
                console.print("[yellow]未找到可点击的搜索结果，尝试直接使用导出按钮...[/yellow]")

            # 6. 等待页面加载
            console.print("[dim]等待页面加载...[/dim]")
            await asyncio.sleep(5)

            # 7. 查找导出按钮
            console.print("[dim]查找导出按钮...[/dim]")

            export_selectors = [
                "button:has-text('导出')",
                "button:has-text('下载')",
                ".export-button",
                ".download-btn",
                "span:has-text('导出')",
            ]

            export_button = None
            for selector in export_selectors:
                try:
                    buttons = await page.query_selector_all(selector)
                    for btn in buttons:
                        if await btn.is_visible():
                            btn_text = await btn.inner_text()
                            console.print(f"[dim]找到按钮: '{btn_text.strip()}' ({selector})[/dim]")
                            if "导出" in btn_text or "下载" in btn_text:
                                export_button = btn
                                console.print(f"[green]选择导出按钮: {selector}[/green]")
                                break
                    if export_button:
                        break
                except Exception as e:
                    logger.debug(f"尝试{selector}失败: {e}")
                    continue

            if not export_button:
                logger.warning("未找到导出按钮，尝试查找表格中的导出功能...")

                # 尝试查找表格并直接读取数据
                try:
                    logger.debug("尝试直接读取页面表格数据...")
                    await asyncio.sleep(3)

                    # 查找表格
                    tables = await page.query_selector_all("table")
                    if tables:
                        logger.debug(f"找到{len(tables)}个表格")

                        # 尝试从第一个表格读取数据
                        table_data = await tables[0].inner_text()
                        logger.debug(f"表格数据预览:\n{table_data[:500]}")

                        # 解析表格数据
                        lines = table_data.split('\n')
                        fund_codes = []
                        for line in lines[1:20]:  # 跳过表头，读取前20行
                            parts = line.split()
                            if parts and len(parts[0]) == 6 and parts[0].isdigit():
                                fund_codes.append(parts[0])

                        if fund_codes:
                            logger.info(f"从表格提取到 {len(fund_codes)} 个基金代码")
                            await browser.close()
                            return fund_codes
                except Exception as e:
                    logger.error(f"读取表格失败: {e}")

                await browser.close()
                return []

            # 8. 点击导出按钮并下载文件
            logger.debug("点击导出按钮...")

            try:
                async with page.expect_download(timeout=30000) as download_info:
                    await export_button.evaluate('el => el.click()')

                download = await download_info.value

                # 保存文件
                file_path = os.path.join(download_path, download.suggested_filename)
                await download.save_as(file_path)

                logger.info(f"文件已下载: {file_path}")

            except Exception as e:
                logger.error(f"下载失败: {e}")
                await browser.close()
                return []

            # 9. 读取Excel文件并提取基金代码
            logger.debug("读取Excel文件...")

            try:
                df = pd.read_excel(file_path)

                logger.debug(f"文件列名: {list(df.columns)}")
                logger.debug(f"总行数: {len(df)}")

                # 查找基金代码列（可能的列名）
                fund_code_column = None
                possible_columns = ['基金代码', '产品代码', '代码', 'Code', 'CODE']

                for col in df.columns:
                    for possible in possible_columns:
                        if possible in str(col):
                            fund_code_column = col
                            logger.debug(f"找到基金代码列: {col}")
                            break
                    if fund_code_column:
                        break

                if fund_code_column:
                    # 提取基金代码和基金名称
                    fund_codes = []
                    fund_names = {}

                    # 查找基金名称列
                    fund_name_column = None
                    possible_name_columns = ['产品名称', '基金名称', '名称', 'Name', 'name']
                    for col in df.columns:
                        for possible in possible_name_columns:
                            if possible in str(col):
                                fund_name_column = col
                                break
                        if fund_name_column:
                            break

                    # 提取数据
                    for _, row in df.iterrows():
                        code = str(row[fund_code_column]).replace('.0', '').strip()

                        # 跳过无效代码
                        if code == 'nan' or not code or code == 'None':
                            continue

                        # 提取纯数字代码（去除可能的后缀如 "KS Equity"）
                        import re
                        code_match = re.search(r'\d{6}', code)
                        if code_match:
                            clean_code = code_match.group()
                            # 避免重复添加
                            if clean_code not in fund_codes:
                                fund_codes.append(clean_code)

                            # 提取基金名称
                            if fund_name_column:
                                name = str(row[fund_name_column]).strip()
                                fund_names[clean_code] = name
                            else:
                                fund_names[clean_code] = f"基金{clean_code}"

                    logger.info(f"成功提取 {len(fund_codes)} 只基金代码")
                    logger.debug(f"前10个基金代码: {fund_codes[:10]}")

                    # 保存基金名称映射到文件，供后续使用
                    import json
                    mapping_file = os.path.join(download_path, "fund_names_mapping.json")
                    with open(mapping_file, 'w', encoding='utf-8') as f:
                        json.dump(fund_names, f, ensure_ascii=False, indent=2)
                    logger.debug(f"基金名称映射已保存到: {mapping_file}")

                    await browser.close()
                    return fund_codes
                else:
                    logger.warning("未找到基金代码列")
                    logger.debug(f"显示前10行数据:\n{df.head(10)}")

                    # 尝试使用第一列
                    if len(df.columns) > 0:
                        first_col = df.columns[0]
                        fund_codes = df[first_col].dropna().astype(str).tolist()
                        fund_codes = [code.replace('.0', '') for code in fund_codes if code != 'nan' and len(code) == 6]
                        logger.warning(f"使用第一列提取到 {len(fund_codes)} 个数据")
                        await browser.close()
                        return fund_codes

                    await browser.close()
                    return []

            except Exception as e:
                logger.error(f"读取Excel失败: {e}")
                await browser.close()
                return []

        except Exception as e:
            logger.error(f"爬取中证指数失败: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()
            return []


async def test_csindex_scraper():
    """测试中证指数爬虫"""
    sector = "消费"
    funds = await search_sector_funds(sector)
    console.print(f"\n[cyan]找到 {len(funds)} 只基金:[/cyan]")
    for code in funds[:10]:  # 只显示前10个
        console.print(f"  - {code}")
    if len(funds) > 10:
        console.print(f"  ... 还有 {len(funds) - 10} 只基金")


if __name__ == "__main__":
    asyncio.run(test_csindex_scraper())
