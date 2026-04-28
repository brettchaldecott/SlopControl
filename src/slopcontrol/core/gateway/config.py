"""Gateway configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field


@dataclass
class GatewayConfig:
    """Configuration for the local LLM gateway.

    All upstream provider credentials are loaded from environment.
    The gateway exposes a unified OpenAI-compatible endpoint at
    ``gateway_url + /v1/chat/completions``.
    """

    # Where the FastAPI gateway itself listens
    gateway_host: str = "127.0.0.1"
    gateway_port: int = 8000

    # Fallback chain: comma-separated "provider:model" entries.
    # Example: "kimi:moonshot-v1-8k,qwen:qwen-max,glm:glm-4-plus,ollama:llama3"
    llm_chain: str = "kimi:moonshot-v1-8k,qwen:qwen-max,glm:glm-4-plus,ollama:llama3"

    # ── Upstream providers ─────────────────────────────────────────────
    # Kimi (Moonshot AI)
    kimi_api_key: str | None = None
    kimi_api_url: str = "https://api.moonshot.cn/v1"

    # Qwen (Alibaba DashScope)
    qwen_api_key: str | None = None
    qwen_api_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # GLM (Zhipu AI)
    glm_api_key: str | None = None
    glm_api_url: str = "https://open.bigmodel.cn/api/paas/v4"

    # Grok/XAI
    grok_api_key: str | None = None
    grok_api_url: str = "https://api.x.ai/v1"

    # OpenCode
    opencode_api_key: str | None = None
    opencode_api_url: str = "https://opencode.ai/zen/v1"

    # OpenAI (native)
    openai_api_key: str | None = None
    openai_api_url: str = "https://api.openai.com/v1"

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        """Load configuration from environment variables."""
        return cls(
            gateway_host=os.environ.get("SLOPCONTROL_GATEWAY_HOST", cls.gateway_host),
            gateway_port=int(os.environ.get("SLOPCONTROL_GATEWAY_PORT", cls.gateway_port)),
            llm_chain=os.environ.get("SLOPCONTROL_LLM_CHAIN", cls.llm_chain),
            kimi_api_key=os.environ.get("KIMI_API_KEY"),
            kimi_api_url=os.environ.get("KIMI_API_URL", cls.kimi_api_url),
            qwen_api_key=os.environ.get("QWEN_API_KEY"),
            qwen_api_url=os.environ.get("QWEN_API_URL", cls.qwen_api_url),
            glm_api_key=os.environ.get("GLM_API_KEY"),
            glm_api_url=os.environ.get("GLM_API_URL", cls.glm_api_url),
            grok_api_key=os.environ.get("GROK_API_KEY"),
            grok_api_url=os.environ.get("GROK_API_URL", cls.grok_api_url),
            opencode_api_key=os.environ.get("OPENCODE_API_KEY"),
            opencode_api_url=os.environ.get("OPENCODE_API_URL", cls.opencode_api_url),
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            openai_api_url=os.environ.get("OPENAI_API_URL", cls.openai_api_url),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", cls.ollama_base_url),
        )

    def get_provider_base_url(self, provider: str) -> str | None:
        """Return the base API URL for an upstream provider."""
        mapping = {
            "kimi": self.kimi_api_url,
            "qwen": self.qwen_api_url,
            "glm": self.glm_api_url,
            "grok": self.grok_api_url,
            "opencode": self.opencode_api_url,
            "openai": self.openai_api_url,
        }
        return mapping.get(provider.lower())

    def get_provider_api_key(self, provider: str) -> str | None:
        """Return the API key for an upstream provider."""
        mapping = {
            "kimi": self.kimi_api_key,
            "qwen": self.qwen_api_key,
            "glm": self.glm_api_key,
            "grok": self.grok_api_key,
            "opencode": self.opencode_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
        }
        return mapping.get(provider.lower())

    @property
    def gateway_url(self) -> str:
        """Full gateway URL (e.g. ``http://127.0.0.1:8000``)."""
        return f"http://{self.gateway_host}:{self.gateway_port}"
