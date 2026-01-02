"""测试中证指数网站结构"""
import asyncio
from playwright.async_api import async_playwright

# 使用print避免rich库的编码问题
def print_msg(msg, color="white"):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "dim": "\033[90m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{msg}{colors['reset']}")


async def analyze_page_structure():
    """分析中证指数网站页面结构"""
    print_msg("正在访问中证指数官网...", "yellow")

    async with async_playwright() as p:
        # 启动浏览器（非headless模式，方便观察）
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 访问中证指数官网
            await page.goto("https://www.csindex.com.cn/#/indices/indexProduct", timeout=60000)
            print_msg("页面加载成功", "green")

            # 等待页面加载完成
            await asyncio.sleep(5)

            # 截图保存
            await page.screenshot(path="csindex_homepage.png")
            print_msg("已保存页面截图: csindex_homepage.png", "green")

            # 尝试查找搜索框
            print_msg("\n正在查找搜索框...", "cyan")

            # 尝试多种可能的搜索框定位方式
            search_selectors = [
                "input[placeholder*='搜索']",
                "input[placeholder*='输入']",
                ".el-input__inner",
                "input[type='text']",
                "[class*='search'] input",
                "[id*='search'] input",
                "input.search-input",
            ]

            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        print_msg(f"找到搜索框: {selector}", "green")
                        break
                except:
                    continue

            if not search_input:
                print_msg("未找到搜索框，列出所有输入元素...", "yellow")
                inputs = await page.query_selector_all("input")
                print_msg(f"找到 {len(inputs)} 个input元素", "dim")

                for i, inp in enumerate(inputs):
                    input_type = await inp.get_attribute("type")
                    input_placeholder = await inp.get_attribute("placeholder")
                    input_class = await inp.get_attribute("class")
                    print(f"  Input {i+1}: type={input_type}, placeholder={input_placeholder}, class={input_class}")

            # 等待用户观察
            print_msg("\n浏览器将保持打开30秒，请观察页面结构...", "yellow")
            await asyncio.sleep(30)

            await browser.close()

        except Exception as e:
            print_msg(f"错误: {e}", "red")
            await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_page_structure())
