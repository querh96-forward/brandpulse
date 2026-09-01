from typing import Protocol

from app.schemas.analysis import AnalysisOutput


class AnalysisProvider(Protocol):
    model_name: str

    async def analyze(self, prompt: str) -> AnalysisOutput: ...
