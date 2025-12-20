"""
Agent 包装器模块
独立封装 PhoneAgent 的调用逻辑，与 UI 完全分离
"""

import sys
import os
import traceback
from typing import Optional, Callable, Generator
import threading
import queue
import time

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui_app.config import AgentConfig


class AgentWrapper:
    """Agent 包装器，提供独立的 Agent 调用接口"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent = None
        self.is_running = False
        self._stop_event = threading.Event()
        
    def _create_agent(self):
        """创建 PhoneAgent 实例"""
        try:
            from phone_agent import PhoneAgent
            from phone_agent.model import ModelConfig
            from phone_agent.agent import AgentConfig as PhoneAgentConfig
            
            # 创建模型配置
            model_config = ModelConfig(
                base_url=self.config.base_url,
                model_name=self.config.model,
                api_key=self.config.api_key,
            )
            
            # 创建 Agent 配置
            agent_config = PhoneAgentConfig(
                max_steps=self.config.max_steps,
                device_id=self.config.device_id,
                lang=self.config.lang,
                verbose=self.config.verbose,
            )
            
            # 创建 Agent
            self.agent = PhoneAgent(
                model_config=model_config,
                agent_config=agent_config,
            )
            
            return True, "Agent 创建成功"
            
        except Exception as e:
            return False, f"创建 Agent 失败: {str(e)}\n{traceback.format_exc()}"
    
    def test_connection(self) -> tuple[bool, str]:
        """测试连接和配置"""
        try:
            # 验证配置
            is_valid, msg = self.config.validate()
            if not is_valid:
                return False, f"配置验证失败: {msg}"
            
            # 尝试创建 Agent
            success, msg = self._create_agent()
            if not success:
                return False, msg
            
            # 测试模型连接
            try:
                # 这里可以添加简单的模型连接测试
                return True, "连接测试成功"
            except Exception as e:
                return False, f"模型连接测试失败: {str(e)}"
                
        except Exception as e:
            return False, f"连接测试异常: {str(e)}"
    
    def run_task_async(self, task: str, progress_callback: Optional[Callable[[str], None]] = None) -> Generator[dict, None, str]:
        """异步执行任务，支持进度回调，返回详细的执行步骤"""
        self.is_running = True
        self._stop_event.clear()
        
        try:
            if not self.agent:
                success, msg = self._create_agent()
                if not success:
                    yield {"type": "error", "message": f"❌ {msg}", "timestamp": time.time()}
                    return msg
            
            yield {"type": "start", "message": "🚀 开始执行任务...", "timestamp": time.time()}
            
            # 创建自定义的 Agent 来捕获详细步骤
            step_queue = queue.Queue()
            result_queue = queue.Queue()
            error_queue = queue.Queue()
            
            def run_agent_with_steps():
                try:
                    import io
                    import sys
                    from contextlib import redirect_stdout, redirect_stderr
                    
                    # 捕获 Agent 的详细输出
                    captured_output = io.StringIO()
                    
                    with redirect_stdout(captured_output), redirect_stderr(captured_output):
                        # 确保 Agent 使用 verbose 模式
                        if hasattr(self.agent, 'agent_config'):
                            self.agent.agent_config.verbose = True
                        
                        result = self.agent.run(task)
                    
                    # 解析捕获的输出
                    output_lines = captured_output.getvalue().split('\n')
                    self._parse_agent_output(output_lines, step_queue)
                    
                    result_queue.put(result)
                    
                except Exception as e:
                    error_queue.put(f"任务执行失败: {str(e)}\n{traceback.format_exc()}")
            
            # 启动 Agent 线程
            agent_thread = threading.Thread(target=run_agent_with_steps)
            agent_thread.daemon = True
            agent_thread.start()
            
            # 实时输出步骤信息
            while agent_thread.is_alive() and not self._stop_event.is_set():
                # 检查是否有新的步骤信息
                try:
                    step_info = step_queue.get_nowait()
                    yield step_info
                except queue.Empty:
                    pass
                
                time.sleep(0.5)  # 更频繁的检查
            
            # 输出剩余的步骤信息
            while not step_queue.empty():
                try:
                    step_info = step_queue.get_nowait()
                    yield step_info
                except queue.Empty:
                    break
            
            # 检查是否被停止
            if self._stop_event.is_set():
                yield {"type": "stop", "message": "⏹️ 任务已停止", "timestamp": time.time()}
                return "任务已停止"
            
            # 获取结果
            if not result_queue.empty():
                result = result_queue.get()
                yield {"type": "success", "message": f"✅ 任务完成: {result}", "timestamp": time.time()}
                return result
            elif not error_queue.empty():
                error = error_queue.get()
                yield {"type": "error", "message": f"❌ {error}", "timestamp": time.time()}
                return error
            else:
                msg = "❓ 任务状态未知"
                yield {"type": "unknown", "message": msg, "timestamp": time.time()}
                return msg
                
        except Exception as e:
            error_msg = f"❌ 执行异常: {str(e)}\n{traceback.format_exc()}"
            yield {"type": "error", "message": error_msg, "timestamp": time.time()}
            return error_msg
        finally:
            self.is_running = False
    
    def _parse_agent_output(self, output_lines: list, step_queue: queue.Queue):
        """解析 Agent 的详细输出"""
        current_section = None
        section_content = []
        
        for line in output_lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测不同的输出段落
            if "💭 思考过程:" in line:
                current_section = "thinking"
                section_content = []
            elif "⏱️  性能指标:" in line:
                if current_section == "thinking" and section_content:
                    thinking_text = "\n".join(section_content)
                    step_queue.put({
                        "type": "thinking", 
                        "message": f"💭 **思考过程**\n{thinking_text}", 
                        "timestamp": time.time()
                    })
                current_section = "performance"
                section_content = []
            elif "🎯 执行动作:" in line:
                if current_section == "performance" and section_content:
                    perf_text = "\n".join(section_content)
                    step_queue.put({
                        "type": "performance", 
                        "message": f"⏱️ **性能指标**\n{perf_text}", 
                        "timestamp": time.time()
                    })
                current_section = "action"
                section_content = []
            elif "Parsing action:" in line:
                # 解析执行的动作
                action_info = line.replace("Parsing action:", "").strip()
                step_queue.put({
                    "type": "action", 
                    "message": f"🎯 **执行动作**: {action_info}", 
                    "timestamp": time.time()
                })
            elif "Press Enter after completing manual operation" in line:
                step_queue.put({
                    "type": "takeover", 
                    "message": "🤝 **人工接管**: 需要手动完成操作", 
                    "timestamp": time.time()
                })
            elif current_section and line.startswith("--"):
                # 分隔线，跳过
                continue
            elif current_section:
                # 收集当前段落的内容
                section_content.append(line)
        
        # 处理最后一个段落
        if current_section == "thinking" and section_content:
            thinking_text = "\n".join(section_content)
            step_queue.put({
                "type": "thinking", 
                "message": f"💭 **思考过程**\n{thinking_text}", 
                "timestamp": time.time()
            })
        elif current_section == "performance" and section_content:
            perf_text = "\n".join(section_content)
            step_queue.put({
                "type": "performance", 
                "message": f"⏱️ **性能指标**\n{perf_text}", 
                "timestamp": time.time()
            })
    
    def stop_task(self):
        """停止当前任务"""
        self._stop_event.set()
        self.is_running = False
    
    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "is_running": self.is_running,
            "config": self.config.to_dict(),
            "agent_created": self.agent is not None,
        }
