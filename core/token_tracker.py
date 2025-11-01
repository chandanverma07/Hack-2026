from core.logger import init_logger
from datetime import datetime

logger = init_logger()

# Default cost per 1K tokens (USD)
OPENAI_PRICING = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
}

class TokenTracker:
    def __init__(self):
        self.data = {}
        self.total_input_tokens = 0s
        self.total_output_tokens = 0
        self._callback = None  # used to update UI (like Streamlit sidebar)

    def set_callback(self, func):
        """Attach a live update callback (e.g., Streamlit progress bar)."""
        self._callback = func

    def record(self, agent_name: str, input_t: int, output_t: int, model: str):
        """Record tokens and update live sidebar if callback is set."""
        self.data[agent_name] = {
            "input_tokens": input_t,
            "output_tokens": output_t,
            "model": model,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.total_input_tokens += input_t
        self.total_output_tokens += output_t
        logger.info(f"[Tokens] {agent_name}: input={input_t}, output={output_t}")
        if self._callback:
            self._callback(self.summary())  # live UI update

    def calc_cost(self) -> float:
        total = 0.0
        for _, rec in self.data.items():
            m = rec["model"]
            price = OPENAI_PRICING.get(m, OPENAI_PRICING["gpt-4o-mini"])
            total += ((rec["input_tokens"] / 1000) * price["input"]) + (
                (rec["output_tokens"] / 1000) * price["output"]
            )
        return round(total, 6)

    def summary(self) -> dict:
        return {
            "agents": self.data,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "approx_cost_usd": self.calc_cost(),
        }

    def reset(self):
        self.data.clear()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
