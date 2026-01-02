"""测试中证指数网站API"""
import asyncio
import json
from playwright.async_api import async_playwright

def print_msg(msg, color="white"):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "blue": "\033[94m",
        "dim": "\033[90m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, '')}{msg}{colors['reset']}")


async def analyze_csindex_api():
    """分析中证指数网站的API"""
    sector_name = "消费"
    print_msg(f"正在分析中证指数网站API: {sector_name}", "cyan")

    async with async_playwright() as p:
        # 监听网络请求
        api_requests = []

        def log_request(request):
            """记录所有API请求"""
            url = request.url
            # 过滤API请求
            if any(keyword in url.lower() for keyword in ['api', 'ajax', 'data', 'query', 'search']):
                api_requests.append({
                    'method': request.method,
                    'url': url,
                    'resource_type': request.resource_type
                })

        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        # 设置请求监听
        page.on("request", log_request)

        try:
            print_msg("\n访问中证指数官网...", "yellow")
            url = "https://www.csindex.com.cn/#/indices/indexProduct"
            await page.goto(url, timeout=60000)

            # 等待页面加载
            await asyncio.sleep(3)

            # 输入搜索关键词
            print_msg(f"输入搜索: {sector_name}", "yellow")

            # 查找搜索框
            search_selectors = ["input[type='text']", ".el-input__inner"]
            search_input = None

            for selector in search_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for elem in elements:
                        if await elem.is_visible():
                            search_input = elem
                            break
                    if search_input:
                        break
                except:
                    continue

            if search_input:
                # 输入搜索
                await search_input.click()
                await asyncio.sleep(0.5)
                await search_input.evaluate(f'el => el.value = "{sector_name}"')
                await search_input.evaluate('el => el.dispatchEvent(new Event("input", { bubbles: true }))')
                await search_input.evaluate('el => el.dispatchEvent(new Event("change", { bubbles: true }))')

                print_msg("等待搜索结果和API调用...", "cyan")
                await asyncio.sleep(10)

            # 分析收集到的API请求
            print_msg("\n发现API请求:", "blue")
            print(f"共收集到 {len(api_requests)} 个API相关请求\n")

            # 去重并分类
            unique_apis = {}
            for req in api_requests:
                url = req['url']
                # 提取URL的关键部分
                if '/api/' in url or 'query' in url or 'search' in url:
                    key = url.split('?')[0]  # 去除参数
                    if key not in unique_apis:
                        unique_apis[key] = req

            print(f"发现 {len(unique_apis)} 个唯一API端点:\n")

            for i, (url, req) in enumerate(unique_apis.items(), 1):
                print(f"{i}. {req['method']} - {url}")

                # 尝试访问这个API
                try:
                    print_msg(f"  -> 测试访问...", "dim")

                    # 复制请求头
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Referer": "https://www.csindex.com.cn/"
                    }

                    response = await page.request.get(url, headers=headers)

                    if response:
                        status = response.status
                        print_msg(f"  状态码: {status}", "green" if status == 200 else "yellow")

                        if status == 200:
                            try:
                                # 尝试解析JSON
                                data = await response.json()
                                print_msg(f"  返回JSON数据!", "green")

                                # 保存到文件
                                filename = f"csindex_api_{i}.json"
                                with open(filename, 'w', encoding='utf-8') as f:
                                    json.dump(data, f, ensure_ascii=False, indent=2)

                                print_msg(f"  已保存: {filename}", "dim")

                                # 显示数据预览
                                json_str = json.dumps(data, ensure_ascii=False, indent=2)
                                if len(json_str) < 300:
                                    print_msg(f"  数据: {json_str}", "dim")
                                else:
                                    print_msg(f"  数据预览: {json_str[:200]}...", "dim")

                            except:
                                # 不是JSON
                                text = await response.text()
                                if len(text) < 200:
                                    print_msg(f"  文本: {text}", "dim")
                                else:
                                    print_msg(f"  文本预览: {text[:200]}...", "dim")

                except Exception as e:
                    print_msg(f"  访问失败: {e}", "red")

                print()

            # 等待观察
            print_msg("\n浏览器将保持打开20秒，请手动检查网络请求...", "yellow")
            print_msg("提示: 打开开发者工具(F12) -> Network标签，查看XHR/Fetch请求", "cyan")
            await asyncio.sleep(20)

            await browser.close()

        except Exception as e:
            print_msg(f"错误: {e}", "red")
            import traceback
            traceback.print_exc()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_csindex_api())
