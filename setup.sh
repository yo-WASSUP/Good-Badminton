#!/bin/bash
# Good-Badminton 项目环境配置脚本（GPU版本）

set -e

echo "================================================"
echo "Good-Badminton GPU环境配置"
echo "================================================"

# 激活虚拟环境
source .venv/bin/activate

# 1. 安装GPU版本PyTorch（CUDA 12.1）
echo ""
echo "步骤 1/3: 安装PyTorch GPU版本..."
# 注意：requirements.txt 写的 torch==2.5.1 在 PyTorch 索引中不存在；Python 3.8 实际可用的最高 cu121 版本是 2.4.1
pip install torch==2.4.1+cu121 torchvision==0.19.1+cu121 --index-url https://download.pytorch.org/whl/cu121

# 2. 安装其他依赖（排除torch和torchvision）
echo ""
echo "步骤 2/3: 安装其他依赖..."
pip install opencv-python==4.10.0.84
pip install opencv-contrib-python==4.10.0.84
pip install 'numpy>=1.21.6,<2.0'
pip install 'pillow>=9.2.0,<12.0'
pip install 'ultralytics>=8.0.0'
pip install 'rtmlib>=0.0.1'
pip install 'pandas>=1.3.0'
pip install 'matplotlib>=3.5.0'
pip install 'seaborn>=0.11.0'
pip install 'moviepy>=1.0.3,<2.0'
pip install 'scipy>=1.7.0'
pip install 'scikit-learn>=1.0.0'
pip install 'openpyxl>=3.0.0'

# 3. 安装ONNX Runtime GPU版本
echo ""
echo "步骤 3/3: 安装ONNX Runtime GPU版本..."
# Python 3.8 上 onnxruntime-gpu 最高只到 1.19.2（README 写的 1.20.1 需要 Python 3.9+）
pip install onnxruntime-gpu==1.19.2

# 验证安装
echo ""
echo "================================================"
echo "验证GPU支持..."
echo "================================================"
echo ""
echo "PyTorch GPU状态:"
python -c "import torch; print(f'  PyTorch版本: {torch.__version__}'); print(f'  CUDA可用: {torch.cuda.is_available()}'); print(f'  GPU名称: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"不可用\"}')"

echo ""
echo "ONNX Runtime状态:"
python -c "import onnxruntime as ort; print(f'  版本: {ort.__version__}'); providers = ort.get_available_providers(); print(f'  可用Provider: {providers}'); print(f'  GPU支持: {\"CUDAExecutionProvider\" in providers}')"

echo ""
echo "================================================"
echo "✅ GPU环境配置完成！"
echo "================================================"
echo ""
echo "📌 下一步操作："
echo ""
echo "1. 下载模型权重："
echo "   访问: https://github.com/yo-WASSUP/Good-Badminton/releases/latest"
echo "   下载 yolo11s-ball.pt 文件"
echo "   创建 weights/ 目录并放入模型文件"
echo ""
echo "2. 准备测试视频："
echo "   将羽毛球比赛视频放到 videos/ 目录"
echo ""
echo "3. 运行测试："
echo "   source .venv/bin/activate"
echo "   python main.py --video-path videos/你的视频.mp4"
echo ""
