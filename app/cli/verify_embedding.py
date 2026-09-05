import asyncio
import math

from app.providers.dependencies import get_embedding_provider


async def verify_embedding() -> None:
    provider = get_embedding_provider()
    vector = await provider.embed_text("BC-D200 水下巡检机器人发生密封故障")

    print(f"model={provider.model_name}")
    print(f"dimensions={len(vector)}")
    print(f"l2_norm={math.sqrt(sum(value * value for value in vector)):.6f}")
    print(f"preview={[round(value, 6) for value in vector[:5]]}")


if __name__ == "__main__":
    asyncio.run(verify_embedding())
