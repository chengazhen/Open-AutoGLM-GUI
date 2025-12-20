"""
配置管理模块
支持 base-url, model, apikey 等参数的管理
"""

from dataclasses import dataclass
from typing import Optional
import os
from pathlib import Path
import yaml


@dataclass
class AgentConfig:
    """Agent 配置类"""
    base_url: str
    model: str
    api_key: str
    device_type: str = "adb"  # adb, hdc, ios
    device_id: Optional[str] = None
    lang: str = "cn"
    max_steps: int = 100
    verbose: bool = True
    console_output: bool = True  # 是否同时输出到控制台

    @classmethod
    def from_file(cls, config_path: Optional[str] = None) -> "AgentConfig":
        """从配置文件创建配置"""
        if config_path is None:
            # 默认使用项目根目录的 config.yaml
            config_path = Path(__file__).parent.parent / "config.yaml"
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        return cls(
            base_url=config_data.get("base_url"),
            model=config_data.get("model"),
            api_key=config_data.get("api_key"),
            device_type=config_data.get("device_type"),
            device_id=config_data.get("device_id"),
            lang=config_data.get("lang"),
            max_steps=config_data.get("max_steps"),
            verbose=config_data.get("verbose"),
            console_output=config_data.get("console_output"),
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
            "console_output": self.console_output,
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
