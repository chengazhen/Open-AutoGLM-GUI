# AutoGLM Phone Agent - 独立 UI 应用

完全模块化的 Gradio 图形界面，与原 agent 代码完全分离。

## 🚀 快速开始

### 1. 安装依赖

```bash
# 在项目根目录下
cd ui_app
pip install -r requirements.txt
```

### 2. 启动应用

```bash
python run_ui.py
```

### 3. 访问界面

打开浏览器访问: http://localhost:7860

## 📋 功能特性

- ✅ **完全独立**: 与原 agent 代码模块化分离
- ✅ **对话式交互**: 自然语言指令输入
- ✅ **参数配置**: 支持 base-url, model, apikey 等参数
- ✅ **实时监控**: 任务状态和进度显示
- ✅ **任务控制**: 支持停止和状态查看

## ⚙️ 配置示例

在"配置"标签页中设置以下参数:

```
Base URL: https://api.parasail.io/v1
Model: parasail-auto-glm-9b-multilingual
API Key: psk-santg8qngZFP-D1a89yB2sVSNQksmjIuL
Device Type: adb
Language: cn
```

## 💬 使用示例

1. 先在"配置"标签页设置参数并点击"更新配置"
2. 切换到"对话"标签页
3. 输入指令，例如:
   - "打开微信"
   - "打开美团搜索附近的火锅店"
   - "打开淘宝搜索无线耳机"

## 📁 目录结构

```
ui_app/
├── __init__.py          # 包初始化
├── config.py            # 配置管理模块
├── agent_wrapper.py     # Agent 包装器
├── gradio_app.py        # Gradio 主应用
├── run_ui.py           # 启动脚本
├── requirements.txt     # 依赖列表
└── README.md           # 说明文档
```

## 🔧 架构设计

- **config.py**: 独立的配置管理，支持环境变量和参数验证
- **agent_wrapper.py**: Agent 包装器，封装原 PhoneAgent 调用逻辑
- **gradio_app.py**: UI 主逻辑，对话界面和事件处理
- **run_ui.py**: 启动入口，独立运行

## ⚠️ 注意事项

1. 确保已按照主项目 README 配置好 ADB/HDC 环境
2. 首次使用需要在"配置"标签页设置正确的参数
3. 支持实时任务停止，但某些操作可能需要等待当前步骤完成
