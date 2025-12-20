"""
配置管理模块
支持 base-url, model, apikey 等参数的管理
"""

from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class AgentConfig:
    """Agent 配置类"""
    base_url: str = "https://api.parasail.io/v1"
    model: str = "parasail-auto-glm-9b-multilingual"
    api_key: str = "psk-santg8qngZFP-D1a89yB2sVSNQksmjIuL"
    device_type: str = "adb"  # adb, hdc, ios
    device_id: Optional[str] = None
    lang: str = "cn"
    max_steps: int = 100
    verbose: bool = True

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """从环境变量创建配置"""
        return cls(
            base_url=os.getenv("PHONE_AGENT_BASE_URL", "https://api.parasail.io/v1"),
            model=os.getenv("PHONE_AGENT_MODEL", "parasail-auto-glm-9b-multilingual"),
            api_key=os.getenv("PHONE_AGENT_API_KEY", "psk-santg8qngZFP-D1a89yB2sVSNQksmjIuL"),
            device_type=os.getenv("PHONE_AGENT_DEVICE_TYPE", "adb"),
            device_id=os.getenv("PHONE_AGENT_DEVICE_ID"),
            lang=os.getenv("PHONE_AGENT_LANG", "cn"),
            max_steps=int(os.getenv("PHONE_AGENT_MAX_STEPS", "100")),
        )

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "api_key": self.api_key,
            "device_type": self.device_type,
            "device_id": self.device_id,
            "lang": self.lang,
            "max_steps": self.max_steps,
            "verbose": self.verbose,
        }

    def validate(self) -> tuple[bool, str]:
        """验证配置是否有效"""
        if not self.base_url:
            return False, "Base URL 不能为空"
        
        if not self.model:
            return False, "Model 不能为空"
        
        if self.device_type not in ["adb", "hdc", "ios"]:
            return False, "Device type 必须是 adb, hdc 或 ios"
        
        if self.max_steps <= 0:
            return False, "Max steps 必须大于 0"
        
        return True, "配置验证通过"
