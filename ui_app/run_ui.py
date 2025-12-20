#!/usr/bin/env python3
"""
启动脚本 - AutoGLM Phone Agent UI
独立运行的 Gradio 界面应用
"""

import sys
import os

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui_app.gradio_app import main

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AutoGLM Phone Agent - 独立 UI 应用")
    print("=" * 60)
    print("📋 功能特性:")
    print("  ✅ 完全模块化，与原 agent 代码分离")
    print("  ✅ 对话式交互界面")
    print("  ✅ 支持参数配置 (base-url, model, apikey)")
    print("  ✅ 实时任务状态监控")
    print("  ✅ 支持任务停止和状态查看")
    print("=" * 60)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 应用已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)
