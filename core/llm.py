import os
import tiktoken
from loguru import logger
from openai import OpenAI
from typing import Any, Dict
from core.config import load_settings


# ======================================================
# 🔹 Token Tracker (used in Streamlit)
# ======================================================
class TokenTracker:
    def __init__(self):
        self.reset()
        self.callback = None

    def reset(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.agents = []

    def log_agent(self, name: str, input_tokens: int, output_tokens: int, cost: float):
        """Log per-agent token usage and cost."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost
        self.agents.append({
            "agent": name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
        })
        if self.callback:
            self.callback(self.summary())

    def set_callback(self, cb):
        self.callback = cb

    def summary(self) -> Dict[str, Any]:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "approx_cost_usd": round(self.total_cost_usd, 4),
            "agents": self.agents,
        }


tracker = TokenTracker()


# ======================================================
# 🔹 Token / Cost Helpers
# ======================================================
def num_tokens_from_string(text: str, model: str = "gpt-4o") -> int:
    """Estimate token count."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text or ""))


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Approximate USD cost."""
    pricing = {
        "gpt-4o": {"in": 0.000005, "out": 0.000015},
        "gpt-4o-mini": {"in": 0.0000015, "out": 0.000002},
        "gpt-5": {"in": 0.000006, "out": 0.000018},
        "gpt-5-vision": {"in": 0.000007, "out": 0.000020},
    }
    p = pricing.get(model, pricing["gpt-4o"])
    return (input_tokens * p["in"]) + (output_tokens * p["out"])


# ======================================================
# 🔹 LLM Wrapper
# ======================================================
class LLMWrapper:
    def __init__(self, model_name: str, temperature: float = 0.3, max_tokens: int = 2000):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("Missing OPENAI_API_KEY in environment or .env")
        self.client = OpenAI(api_key=api_key)
        self.model = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def invoke(self, prompt: str, agent_name: str = "generic") -> str:
        """Invoke the LLM and return clean text (not ChatCompletion object)."""
        try:
            logger.info(f"[LLM] Invoking {self.model} for agent: {agent_name}")
            input_tokens = num_tokens_from_string(prompt, self.model)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # ✅ Extract only text
            output_text = response.choices[0].message.content.strip()
            output_tokens = num_tokens_from_string(output_text, self.model)
            cost = estimate_cost(self.model, input_tokens, output_tokens)

            tracker.log_agent(agent_name, input_tokens, output_tokens, cost)

            logger.info(
                f"[LLM] {agent_name} complete | Input: {input_tokens:,} | "
                f"Output: {output_tokens:,} | Cost: ${cost:.6f}"
            )

            # ✅ Return plain text
            return output_text

        except Exception as e:
            logger.exception(f"[LLM] Failed to invoke model: {e}")
            raise


# ======================================================
# 🔹 Factory Function (supports per-agent config)
# ======================================================
def get_llm(agent_name: str = "requirement") -> LLMWrapper:
    """
    Load model dynamically from settings.yaml or .env.
    Supports agent-specific model definitions like:
      agents:
        requirement:
          model: gpt-4o
        flow:
          model: gpt-4o-mini
    """
    settings = load_settings()

    agents_cfg = settings.get("agents", {})
    llm_cfg = settings.get("llm", {})

    # 🔧 Choose model by agent name → fall back to defaults
    model_name = (
        agents_cfg.get(agent_name, {}).get("model")
        or llm_cfg.get("model")
        or os.getenv("OPENAI_MODEL", "gpt-4o")
    )

    temperature = (
        llm_cfg.get("temperature")
        or float(os.getenv("OPENAI_TEMPERATURE", 0.3))
    )

    max_tokens = (
        llm_cfg.get("max_tokens")
        or int(os.getenv("OPENAI_MAX_TOKENS", 6000))
    )

    logger.info(f"[LLM] Using model: {model_name} (agent: {agent_name})")
    return LLMWrapper(model_name, temperature=temperature, max_tokens=max_tokens)
