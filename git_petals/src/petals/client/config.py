from dataclasses import dataclass
from typing import List, Optional

from petals.constants import DTYPE_MAP

@dataclass
class DistributedConfig:
    """Configuration for distributed model inference."""

    # Model configuration
    model_name_or_path: str
    num_blocks: int
    torch_dtype: str = "float32"
    quant_type: str = "none"

    # Server configuration
    initial_peers: List[str] = None
    num_handlers: int = 8
    inference_max_length: int = 2048

    # Timeouts
    request_timeout: float = 30.0
    session_timeout: float = 300.0
    step_timeout: float = 60.0
    health_check_interval: float = 10.0

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.initial_peers is None:
            self.initial_peers = []

        if self.num_blocks <= 0:
            raise ValueError("num_blocks must be positive")

        if self.num_handlers <= 0:
            raise ValueError("num_handlers must be positive")

        if self.inference_max_length <= 0:
            raise ValueError("inference_max_length must be positive")

        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")

        if self.session_timeout <= 0:
            raise ValueError("session_timeout must be positive")

        if self.step_timeout <= 0:
            raise ValueError("step_timeout must be positive")

        if self.health_check_interval <= 0:
            raise ValueError("health_check_interval must be positive")

        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        if self.retry_delay <= 0:
            raise ValueError("retry_delay must be positive")

# For backward compatibility
ClientConfig = DistributedConfig
