"""
设备连接管理器
提供设备连接状态检查、预检查和实时监控功能
"""

import threading
import time
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from enum import Enum

from phone_agent.device_factory import DeviceFactory, DeviceType


class DeviceStatus(Enum):
    """设备连接状态"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    UNAUTHORIZED = "unauthorized"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    status: DeviceStatus
    device_type: str
    model: Optional[str] = None
    last_check: Optional[float] = None
    error_message: Optional[str] = None


class DeviceManager:
    """设备连接管理器"""
    
    def __init__(self):
        self._devices_cache: Dict[str, DeviceInfo] = {}
        self._last_scan_time: float = 0
        self._scan_interval: float = 5.0  # 扫描间隔（秒）
        self._monitoring_thread: Optional[threading.Thread] = None
        self._monitoring_active: bool = False
        self._status_callbacks: List[Callable[[Dict[str, DeviceInfo]], None]] = []
        self._lock = threading.Lock()
    
    def add_status_callback(self, callback: Callable[[Dict[str, DeviceInfo]], None]):
        """添加状态变化回调"""
        with self._lock:
            self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[Dict[str, DeviceInfo]], None]):
        """移除状态变化回调"""
        with self._lock:
            if callback in self._status_callbacks:
                self._status_callbacks.remove(callback)
    
    def _notify_status_change(self):
        """通知状态变化"""
        with self._lock:
            for callback in self._status_callbacks:
                try:
                    callback(self._devices_cache.copy())
                except Exception as e:
                    print(f"状态回调执行失败: {e}")
    
    def scan_devices(self, device_type: str = "adb", force_refresh: bool = False) -> Dict[str, DeviceInfo]:
        """
        扫描设备
        
        Args:
            device_type: 设备类型 (adb, hdc, ios)
            force_refresh: 是否强制刷新
            
        Returns:
            设备信息字典
        """
        current_time = time.time()
        
        # 检查是否需要刷新缓存
        if not force_refresh and (current_time - self._last_scan_time) < self._scan_interval:
            return self._devices_cache.copy()
        
        try:
            # 根据设备类型创建工厂
            if device_type == "adb":
                factory_type = DeviceType.ADB
            elif device_type == "hdc":
                factory_type = DeviceType.HDC
            elif device_type == "ios":
                factory_type = DeviceType.IOS
            else:
                factory_type = DeviceType.ADB
            
            factory = DeviceFactory(factory_type)
            raw_devices = factory.list_devices()
            
            new_devices = {}
            
            for device in raw_devices:
                # 转换状态
                if device.status == "device":
                    status = DeviceStatus.CONNECTED
                elif device.status == "unauthorized":
                    status = DeviceStatus.UNAUTHORIZED
                elif device.status == "offline":
                    status = DeviceStatus.OFFLINE
                else:
                    status = DeviceStatus.UNKNOWN
                
                device_info = DeviceInfo(
                    device_id=device.device_id,
                    status=status,
                    device_type=device_type,
                    model=getattr(device, 'model', None),
                    last_check=current_time
                )
                
                new_devices[device.device_id] = device_info
            
            # 检查设备变化
            old_devices = set(self._devices_cache.keys())
            new_device_ids = set(new_devices.keys())
            
            # 标记断开连接的设备
            for device_id in old_devices - new_device_ids:
                if device_id in self._devices_cache:
                    self._devices_cache[device_id].status = DeviceStatus.DISCONNECTED
                    self._devices_cache[device_id].last_check = current_time
            
            # 更新缓存
            with self._lock:
                self._devices_cache.update(new_devices)
                self._last_scan_time = current_time
            
            # 如果有设备变化，通知回调
            if old_devices != new_device_ids:
                self._notify_status_change()
            
            return self._devices_cache.copy()
            
        except Exception as e:
            print(f"扫描设备失败: {e}")
            return self._devices_cache.copy()
    
    def get_device_status(self, device_id: str, device_type: str = "adb") -> Optional[DeviceInfo]:
        """
        获取特定设备状态
        
        Args:
            device_id: 设备ID
            device_type: 设备类型
            
        Returns:
            设备信息或None
        """
        # 先尝试从缓存获取
        if device_id in self._devices_cache:
            device_info = self._devices_cache[device_id]
            # 如果缓存较新，直接返回
            if device_info.last_check and (time.time() - device_info.last_check) < self._scan_interval:
                return device_info
        
        # 刷新设备列表
        devices = self.scan_devices(device_type, force_refresh=True)
        return devices.get(device_id)
    
    def check_device_connection(self, device_id: Optional[str] = None, device_type: str = "adb") -> tuple[bool, str, Optional[DeviceInfo]]:
        """
        检查设备连接状态
        
        Args:
            device_id: 设备ID，None表示检查任意可用设备
            device_type: 设备类型
            
        Returns:
            (是否连接, 状态消息, 设备信息)
        """
        devices = self.scan_devices(device_type, force_refresh=True)
        
        if not devices:
            return False, "未检测到任何设备", None
        
        # 如果指定了设备ID
        if device_id:
            if device_id not in devices:
                return False, f"设备 {device_id} 未连接", None
            
            device_info = devices[device_id]
            if device_info.status == DeviceStatus.CONNECTED:
                return True, f"设备 {device_id} 已连接", device_info
            elif device_info.status == DeviceStatus.UNAUTHORIZED:
                return False, f"设备 {device_id} 未授权，请在设备上允许USB调试", device_info
            elif device_info.status == DeviceStatus.OFFLINE:
                return False, f"设备 {device_id} 离线", device_info
            else:
                return False, f"设备 {device_id} 状态未知: {device_info.status.value}", device_info
        
        # 检查是否有可用设备
        connected_devices = [d for d in devices.values() if d.status == DeviceStatus.CONNECTED]
        
        if connected_devices:
            device_info = connected_devices[0]
            return True, f"检测到 {len(connected_devices)} 个可用设备，使用: {device_info.device_id}", device_info
        
        # 检查是否有未授权设备
        unauthorized_devices = [d for d in devices.values() if d.status == DeviceStatus.UNAUTHORIZED]
        if unauthorized_devices:
            return False, f"检测到 {len(unauthorized_devices)} 个未授权设备，请在设备上允许USB调试", None
        
        # 检查是否有离线设备
        offline_devices = [d for d in devices.values() if d.status == DeviceStatus.OFFLINE]
        if offline_devices:
            return False, f"检测到 {len(offline_devices)} 个离线设备", None
        
        return False, f"检测到 {len(devices)} 个设备，但都不可用", None
    
    def get_available_devices(self, device_type: str = "adb") -> List[str]:
        """
        获取可用设备列表
        
        Args:
            device_type: 设备类型
            
        Returns:
            可用设备ID列表
        """
        devices = self.scan_devices(device_type)
        return [
            device_id for device_id, device_info in devices.items()
            if device_info.status == DeviceStatus.CONNECTED
        ]
    
    def start_monitoring(self, device_type: str = "adb", interval: float = 5.0):
        """
        开始设备状态监控
        
        Args:
            device_type: 设备类型
            interval: 监控间隔（秒）
        """
        if self._monitoring_active:
            return
        
        self._scan_interval = interval
        self._monitoring_active = True
        
        def monitor_loop():
            while self._monitoring_active:
                try:
                    self.scan_devices(device_type, force_refresh=True)
                    time.sleep(interval)
                except Exception as e:
                    print(f"设备监控异常: {e}")
                    time.sleep(interval)
        
        self._monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitoring_thread.start()
    
    def stop_monitoring(self):
        """停止设备状态监控"""
        self._monitoring_active = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=1.0)
    
    def get_device_summary(self, device_type: str = "adb") -> str:
        """
        获取设备状态摘要
        
        Args:
            device_type: 设备类型
            
        Returns:
            设备状态摘要字符串
        """
        devices = self.scan_devices(device_type)
        
        if not devices:
            return "❌ 未检测到任何设备"
        
        connected = sum(1 for d in devices.values() if d.status == DeviceStatus.CONNECTED)
        unauthorized = sum(1 for d in devices.values() if d.status == DeviceStatus.UNAUTHORIZED)
        offline = sum(1 for d in devices.values() if d.status == DeviceStatus.OFFLINE)
        disconnected = sum(1 for d in devices.values() if d.status == DeviceStatus.DISCONNECTED)
        
        summary_parts = []
        
        if connected > 0:
            summary_parts.append(f"✅ {connected} 个已连接")
        
        if unauthorized > 0:
            summary_parts.append(f"🔒 {unauthorized} 个未授权")
        
        if offline > 0:
            summary_parts.append(f"📴 {offline} 个离线")
        
        if disconnected > 0:
            summary_parts.append(f"❌ {disconnected} 个已断开")
        
        return f"📱 设备状态: {', '.join(summary_parts)}"


# 全局设备管理器实例
_device_manager: Optional[DeviceManager] = None


def get_device_manager() -> DeviceManager:
    """获取全局设备管理器实例"""
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager()
    return _device_manager
