from openai import AsyncOpenAI

from app.schemas.analysis import AnalysisOutput


class OpenAICompatibleAnalysisProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout_seconds: float = 120.0,
        max_retries: int = 1,
    ) -> None:
        self.model_name = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    async def analyze(self, prompt: str) -> AnalysisOutput:
        completion = await self._client.chat.completions.parse(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": ("你是品牌舆情分析模型。请严格按照给定的结构化格式返回分析结果。"),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format=AnalysisOutput,
        )

        result = completion.choices[0].message.parsed

        if result is None:
            raise ValueError("model did not return a structured analysis result")

        return result
