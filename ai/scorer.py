"""AI 评分器 - 使用大模型进行基金评分和排名"""
import json
import asyncio
import logging
from typing import List
from pathlib import Path
from datetime import datetime
import httpx
from rich.console import Console
from models.fund import FundData, FundRanking
from ai.prompts import SECTOR_RANKING_PROMPT, format_fund_list
from config import Config

logger = logging.getLogger(__name__)

console = Console()


class AIScorer:
    """AI 评分器"""

    def __init__(self):
        self.provider = Config.AI_PROVIDER
        self.api_key = self._get_api_key()
        self.model = self._get_model()

    def _get_api_key(self) -> str:
        """获取API密钥"""
        if self.provider == "zhipu":
            return Config.ZHIPU_API_KEY
        elif self.provider == "deepseek":
            return Config.DEEPSEEK_API_KEY
        elif self.provider == "openai":
            return Config.OPENAI_API_KEY
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    def _get_model(self) -> str:
        """获取AI模型"""
        if self.provider == "zhipu":
            return Config.ZHIPU_MODEL
        elif self.provider == "deepseek":
            return Config.DEEPSEEK_MODEL
        elif self.provider == "openai":
            return Config.OPENAI_MODEL
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    async def rank_funds_with_ai(
        self,
        sector_name: str,
        funds: List[FundData]
    ) -> List[FundRanking]:
        """
        使用AI对基金进行评分和排名

        Args:
            sector_name: 板块名称
            funds: 基金数据列表

        Returns:
            排名后的基金列表
        """
        logger.info(f"正在使用 {self.provider} AI 进行评分...")

        # 格式化基金列表
        fund_list_str = format_fund_list(funds)

        # 构造Prompt
        prompt = SECTOR_RANKING_PROMPT.format(
            sector=sector_name,
            fund_list=fund_list_str
        )

        # 保存prompt到outputs文件夹
        date_str = datetime.now().strftime("%Y%m%d")
        output_dir = Path("outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = output_dir / f"{sector_name}_{date_str}_prompt.md"

        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(f"# {sector_name}板块 - AI分析Prompt\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**AI提供商**: {self.provider}\n")
            f.write(f"**AI模型**: {self.model}\n\n")
            f.write("---\n\n")
            f.write(prompt)

        logger.info(f"AI Prompt已保存到: {prompt_file}")

        try:
            if self.provider == "zhipu":
                result = await self._call_zhipu(prompt)
            elif self.provider == "deepseek":
                result = await self._call_deepseek(prompt)
            elif self.provider == "openai":
                result = await self._call_openai(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # 解析结果并返回AI结果字符串
            ai_result = self._parse_ai_result(result)

            return ai_result

        except Exception as e:
            logger.error(f"AI 评分失败: {e}")
            return ""

    async def _call_zhipu(self, prompt: str) -> str:
        """调用智谱AI"""
        from zhipuai import ZhipuAI

        client = ZhipuAI(api_key=self.api_key)

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=self.model,  # 使用配置的模型
            messages=[
                {"role": "system", "content": "你是专业的基金分析师，擅长数据分析和投资建议。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # 降低随机性
        )

        return response.choices[0].message.content

    async def _call_deepseek(self, prompt: str) -> str:
        """调用DeepSeek"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,  # 使用配置的模型
                    "messages": [
                        {"role": "system", "content": "你是专业的基金分析师。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def _call_openai(self, prompt: str) -> str:
        """调用OpenAI"""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)

        response = await client.chat.completions.create(
            model=self.model,  # 使用配置的模型
            messages=[
                {"role": "system", "content": "你是专业的基金分析师。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )

        return response.choices[0].message.content

    def _parse_ai_result(self, result: str) -> str:
        """解析AI返回的结果（表格格式）并返回结果字符串"""
        try:
            # AI结果将输出到MD文件，不再打印到终端
            # 返回结果字符串，供导出使用
            return result

        except Exception as e:
            # 只在出错时打印错误信息到终端
            console.print(f"[red]解析AI结果失败: {e}[/red]")
            return result


async def test_ai_scorer():
    """测试AI评分器"""
    from models.fund import FundData

    # 创建模拟基金数据
    funds = [
        FundData(
            code="516160",
            name="新能源ETF",
            management_fee=0.5,
            custody_fee=0.1,
            scale=50.0,
            yearly_return=20.5,
            establish_date="2019-05-20",
            beats_benchmark=True,
            beats_benchmark_amount=5.2
        ),
        FundData(
            code="516790",
            name="新能源龙头",
            management_fee=1.5,
            custody_fee=0.25,
            scale=5.0,
            yearly_return=18.0,
            establish_date="2021-03-15",
            beats_benchmark=True,
            beats_benchmark_amount=2.8
        ),
    ]

    scorer = AIScorer()
    rankings = await scorer.rank_funds_with_ai("新能源", funds)

    console.print(f"\n[cyan]排名结果:[/cyan]")
    for rank in rankings:
        console.print(f"{rank.rank}. {rank.name} - {rank.score}分")
        console.print(f"   理由: {rank.reasoning}\n")


if __name__ == "__main__":
    asyncio.run(test_ai_scorer())
