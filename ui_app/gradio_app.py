"""
Gradio UI 主应用
对话式界面，支持参数配置和实时交互
"""

import gradio as gr
import json
import time
from typing import List, Tuple, Optional
import threading

from ui_app.config import AgentConfig
from ui_app.agent_wrapper import AgentWrapper


class GradioApp:
    """Gradio 应用主类"""
    
    def __init__(self):
        self.agent_wrapper: Optional[AgentWrapper] = None
        self.current_config = AgentConfig.from_file()
        self.chat_history: List[dict] = []
        
    def update_config(self, base_url: str, model: str, api_key: str, device_type: str, 
                     device_id: str, lang: str, max_steps: int, console_output: bool) -> Tuple[str, gr.Dropdown]:
        """更新配置并刷新设备列表"""
        try:
            # 创建新配置
            new_config = AgentConfig(
                base_url=base_url.strip() if base_url else "http://localhost:8000/v1",
                model=model.strip() if model else "autoglm-phone-9b",
                api_key=api_key.strip() if api_key else "EMPTY",
                device_type=device_type,
                device_id=device_id.strip() if device_id else None,
                lang=lang,
                max_steps=max_steps,
                verbose=True,
                console_output=console_output
            )
            
            # 验证配置
            is_valid, msg = new_config.validate()
            if not is_valid:
                return f"❌ 配置验证失败: {msg}", gr.Dropdown(choices=[])
            
            # 更新配置
            self.current_config = new_config
            self.agent_wrapper = AgentWrapper(self.current_config)
            
            # 获取设备列表
            devices = self.agent_wrapper.get_available_devices()
            device_choices = devices if devices else []
            
            # 测试连接
            success, test_msg = self.agent_wrapper.test_connection()
            
            # 构建状态消息
            if devices:
                device_info = f"\n\n📱 **检测到 {len(devices)} 个设备**: {', '.join(devices)}"
            else:
                device_info = "\n\n⚠️ **未检测到设备**，请确保设备已连接并开启调试模式"
            
            if success:
                status_msg = f"✅ 配置更新成功！{test_msg}{device_info}"
            else:
                status_msg = f"⚠️ 配置已更新，但连接测试失败: {test_msg}{device_info}"
            
            return status_msg, gr.Dropdown(choices=device_choices, value=device_id if device_id in device_choices else (device_choices[0] if device_choices else None))
                
        except Exception as e:
            return f"❌ 配置更新失败: {str(e)}", gr.Dropdown(choices=[])
    
    
    def chat_with_agent(self, message: str, history: List[dict]):
        """与 Agent 对话 - 支持流式输出"""
        if not message.strip():
            yield history, ""
            return
        
        if not self.agent_wrapper:
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": "❌ 请先配置 Agent 参数"})
            yield history, ""
            return
        
        # 添加用户消息到历史
        history.append({"role": "user", "content": message})
        yield history, ""
        
        # 创建一个详细的执行日志
        execution_log = []
        current_response = "## 📋 执行详情\n\n🚀 **正在启动任务...**"
        
        # 添加初始的助手消息
        history.append({"role": "assistant", "content": current_response})
        yield history, ""
        
        try:
            # 执行任务
            result_generator = self.agent_wrapper.run_task_async(message)
            final_result = ""
            
            # 实时处理执行步骤
            for step_info in result_generator:
                if isinstance(step_info, dict):
                    # 格式化步骤信息
                    step_type = step_info.get("type", "info")
                    step_message = step_info.get("message", "")
                    timestamp = step_info.get("timestamp", time.time())
                    
                    # 根据步骤类型添加不同的图标和格式
                    if step_type == "start":
                        formatted_step = f"🚀 **开始执行** - {step_message}"
                    elif step_type == "thinking":
                        formatted_step = step_message  # 思考过程已经包含完整格式
                    elif step_type == "thinking_start":
                        formatted_step = step_message
                    elif step_type == "performance":
                        formatted_step = step_message  # 性能指标已经包含完整格式
                    elif step_type == "performance_start":
                        formatted_step = step_message
                    elif step_type == "action":
                        formatted_step = step_message  # 执行动作已经包含完整格式
                    elif step_type == "action_start":
                        formatted_step = step_message
                    elif step_type == "operation":
                        formatted_step = step_message
                    elif step_type == "step_separator":
                        formatted_step = step_message
                    elif step_type == "takeover":
                        formatted_step = step_message  # 人工接管已经包含完整格式
                    elif step_type == "success":
                        formatted_step = f"✅ **任务完成** - {step_message}"
                        final_result = step_message
                    elif step_type == "error":
                        formatted_step = f"❌ **执行错误** - {step_message}"
                        final_result = step_message
                    elif step_type == "stop":
                        formatted_step = f"⏹️ **任务停止** - {step_message}"
                        final_result = step_message
                    else:
                        formatted_step = f"ℹ️ **信息** - {step_message}"
                    
                    execution_log.append(formatted_step)
                else:
                    # 兼容旧格式
                    formatted_step = f"ℹ️ {step_info}"
                    execution_log.append(formatted_step)
                    final_result = str(step_info)
                
                # 实时更新显示内容
                current_response = "## 📋 执行详情\n\n" + "\n\n".join(execution_log)
                
                # 如果还在执行中，添加进度指示
                if step_type not in ["success", "error", "stop"]:
                    current_response += "\n\n⏳ **执行中...**"
                
                # 更新历史记录中的最后一条助手消息
                history[-1] = {"role": "assistant", "content": current_response}
                yield history, ""
            
            # 构建最终的回复内容
            if execution_log:
                final_response = "## 📋 执行详情\n\n" + "\n\n".join(execution_log)
                if final_result and not any("任务完成" in log for log in execution_log):
                    final_response += f"\n\n## 🎯 最终结果\n{final_result}"
            else:
                final_response = final_result or "❓ 任务完成，但没有返回详细信息"
            
            # 最终更新
            history[-1] = {"role": "assistant", "content": final_response}
            yield history, ""
                
        except Exception as e:
            error_msg = f"❌ **执行失败**\n\n```\n{str(e)}\n```"
            history[-1] = {"role": "assistant", "content": error_msg}
            yield history, ""
    
    def stop_current_task(self) -> str:
        """停止当前任务"""
        if self.agent_wrapper and self.agent_wrapper.is_running:
            self.agent_wrapper.stop_task()
            return "⏹️ 任务已停止"
        else:
            return "ℹ️ 当前没有运行中的任务"
    
    def get_available_devices_list(self, device_type: str) -> gr.Dropdown:
        """获取可用设备列表"""
        try:
            # 创建临时配置来获取设备列表
            temp_config = AgentConfig(
                base_url=self.current_config.base_url,
                model=self.current_config.model,
                api_key=self.current_config.api_key,
                device_type=device_type,
                device_id=None,
                lang=self.current_config.lang,
                max_steps=self.current_config.max_steps,
                verbose=True,
                console_output=self.current_config.console_output
            )
            temp_wrapper = AgentWrapper(temp_config)
            devices = temp_wrapper.get_available_devices()
            return gr.Dropdown(choices=devices if devices else [], value=None)
        except Exception as e:
            print(f"获取设备列表失败: {str(e)}")
            return gr.Dropdown(choices=[], value=None)
    
    def get_status_info(self) -> str:
        """获取状态信息"""
        if not self.agent_wrapper:
            return "❌ Agent 未初始化"
        
        status = self.agent_wrapper.get_status()
        return f"""
**当前状态:**
- 运行状态: {'🟢 运行中' if status['is_running'] else '🔴 空闲'}
- Agent 状态: {'✅ 已创建' if status['agent_created'] else '❌ 未创建'}
- Base URL: {status['config']['base_url']}
- Model: {status['config']['model']}
- Device Type: {status['config']['device_type']}
- Language: {status['config']['lang']}
"""
    
    def create_interface(self):
        """创建 Gradio 界面"""
        with gr.Blocks(title="AutoGLM Phone Agent UI") as app:
            gr.Markdown("# 🤖 AutoGLM Phone Agent 对话界面")
            gr.Markdown("独立的图形界面，支持对话式交互和参数配置")
            
            with gr.Tabs():
                # 配置标签页
                with gr.TabItem("⚙️ 配置"):
                    gr.Markdown("## Agent 配置")
                    
                    with gr.Row():
                        with gr.Column():
                            base_url_input = gr.Textbox(
                                label="Base URL",
                                value=self.current_config.base_url,
                                placeholder="https://api.parasail.io/v1",
                                info="模型 API 地址"
                            )
                            model_input = gr.Textbox(
                                label="Model",
                                value=self.current_config.model,
                                placeholder="parasail-auto-glm-9b-multilingual",
                                info="模型名称"
                            )
                            api_key_input = gr.Textbox(
                                label="API Key",
                                value=self.current_config.api_key,
                                placeholder="psk-santg8qngZFP-D1a89yB2sVSNQksmjIuL",
                                type="password",
                                info="API 密钥"
                            )
                        
                        with gr.Column():
                            device_type_input = gr.Dropdown(
                                label="Device Type",
                                choices=["adb", "hdc", "ios"],
                                value=self.current_config.device_type,
                                info="设备类型"
                            )
                            device_id_input = gr.Dropdown(
                                label="Device ID",
                                choices=[],
                                value=self.current_config.device_id or None,
                                allow_custom_value=True,
                                info="选择或输入设备 ID，留空自动检测"
                            )
                            refresh_devices_btn = gr.Button("🔄 刷新设备列表", size="sm")
                            lang_input = gr.Dropdown(
                                label="Language",
                                choices=["cn", "en"],
                                value=self.current_config.lang,
                                info="界面语言"
                            )
                            max_steps_input = gr.Slider(
                                label="Max Steps",
                                minimum=10,
                                maximum=500,
                                value=self.current_config.max_steps,
                                step=10,
                                info="每个任务最大步数"
                            )
                            console_output_input = gr.Checkbox(
                                label="终端日志输出",
                                value=self.current_config.console_output,
                                info="是否同时在终端显示执行日志"
                            )
                    
                    with gr.Row():
                        update_config_btn = gr.Button("🔄 更新配置", variant="primary")
                    
                    config_status = gr.Markdown("ℹ️ **配置说明**：\n- 🔄 **更新配置**：应用配置到当前会话")
                
                # 对话标签页
                with gr.TabItem("💬 对话"):
                    gr.Markdown("## 与 Agent 对话")
                    gr.Markdown("输入自然语言指令，Agent 将自动执行手机操作")
                    
                    chatbot = gr.Chatbot(
                        height=500,
                        placeholder="Agent 回复将显示在这里...",
                        show_label=False
                    )
                    
                    with gr.Row():
                        msg_input = gr.Textbox(
                            placeholder="输入指令，例如：打开微信发消息给张三",
                            show_label=False,
                            scale=4
                        )
                        send_btn = gr.Button("📤 发送", variant="primary", scale=1)
                        stop_btn = gr.Button("⏹️ 停止", variant="stop", scale=1)
                    
                    # 示例指令
                    gr.Markdown("### 💡 示例指令")
                    example_commands = [
                        "打开微信",
                        "打开美团搜索附近的火锅店", 
                        "打开淘宝搜索无线耳机",
                        "打开抖音刷视频",
                        "查看当前屏幕内容"
                    ]
                    
                    with gr.Row():
                        for cmd in example_commands:
                            gr.Button(cmd, size="sm").click(
                                lambda x=cmd: x, outputs=msg_input
                            )
                
                # 日志标签页
                with gr.TabItem("📋 状态"):
                    gr.Markdown("## 系统状态")
                    status_display = gr.Markdown(self.get_status_info())
                    refresh_status_btn = gr.Button("🔄 刷新状态")
            
            # 事件绑定
            update_config_btn.click(
                fn=self.update_config,
                inputs=[base_url_input, model_input, api_key_input, device_type_input, 
                       device_id_input, lang_input, max_steps_input, console_output_input],
                outputs=[config_status, device_id_input]
            )
            
            # 设备类型改变时刷新设备列表
            device_type_input.change(
                fn=self.get_available_devices_list,
                inputs=[device_type_input],
                outputs=[device_id_input]
            )
            
            # 手动刷新设备列表
            refresh_devices_btn.click(
                fn=self.get_available_devices_list,
                inputs=[device_type_input],
                outputs=[device_id_input]
            )
            
            send_btn.click(
                fn=self.chat_with_agent,
                inputs=[msg_input, chatbot],
                outputs=[chatbot, msg_input]
            )
            
            msg_input.submit(
                fn=self.chat_with_agent,
                inputs=[msg_input, chatbot],
                outputs=[chatbot, msg_input]
            )
            
            stop_btn.click(
                fn=self.stop_current_task,
                outputs=config_status
            )
            
            refresh_status_btn.click(
                fn=self.get_status_info,
                outputs=status_display
            )
        
        return app


def main():
    """主函数"""
    app_instance = GradioApp()
    interface = app_instance.create_interface()
    
    print("🚀 启动 AutoGLM Phone Agent UI...")
    print("📱 访问地址: http://localhost:7862")
    print("⚙️ 现在使用默认的 Parasail API 配置")
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        show_error=True,
        quiet=False,
        theme=gr.themes.Soft()
    )


if __name__ == "__main__":
    main()
