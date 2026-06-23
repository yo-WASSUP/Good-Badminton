#!/bin/bash
# 快速测试脚本 - 验证环境是否正确配置

echo "=========================================="
echo "Good-Badminton 环境验证"
echo "=========================================="
echo ""

# 激活虚拟环境
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "❌ 虚拟环境不存在"
    exit 1
fi

echo ""
echo "检查关键依赖..."
echo ""

# 检查Python版本
python_version=$(python --version 2>&1)
echo "Python: $python_version"

# 检查FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg: $(ffmpeg -version | head -n1 | cut -d' ' -f3)"
else
    echo "❌ FFmpeg 未安装"
fi

echo ""
echo "检查GPU支持..."
echo ""

# 检查PyTorch
python << 'EOF'
try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
    if torch.cuda.is_available():
        print(f"✅ CUDA: 可用")
        print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
        print(f"   显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        print("⚠️  CUDA: 不可用（将使用CPU）")
except ImportError:
    print("❌ PyTorch 未安装")
EOF

# 检查ONNX Runtime
python << 'EOF'
try:
    import onnxruntime as ort
    providers = ort.get_available_providers()
    print(f"✅ ONNX Runtime: {ort.__version__}")
    if 'CUDAExecutionProvider' in providers:
        print(f"✅ CUDA Provider: 可用")
    else:
        print(f"⚠️  CUDA Provider: 不可用（将使用CPU）")
except ImportError:
    print("❌ ONNX Runtime 未安装")
EOF

echo ""
echo "检查必要文件..."
echo ""

# 检查模型权重
if [ -f "weights/yolo11s-ball.pt" ]; then
    size=$(ls -lh weights/yolo11s-ball.pt | awk '{print $5}')
    echo "✅ 羽毛球检测模型: weights/yolo11s-ball.pt ($size)"
else
    echo "❌ 羽毛球检测模型缺失: weights/yolo11s-ball.pt"
    echo "   请从 https://github.com/yo-WASSUP/Good-Badminton/releases/latest 下载"
fi

# 检查视频文件
video_count=$(ls -1 videos/*.mp4 2>/dev/null | wc -l)
if [ $video_count -gt 0 ]; then
    echo "✅ 找到 $video_count 个视频文件:"
    ls -lh videos/*.mp4 | awk '{print "   - " $9 " (" $5 ")"}'
else
    echo "⚠️  videos/ 目录中没有视频文件"
    echo "   请将测试视频放入 videos/ 目录"
fi

echo ""
echo "检查其他依赖..."
echo ""

# 检查其他Python包
python << 'EOF'
packages = [
    'cv2', 'numpy', 'PIL', 'ultralytics', 'rtmlib',
    'pandas', 'matplotlib', 'seaborn', 'moviepy'
]
for pkg in packages:
    try:
        if pkg == 'PIL':
            import PIL
            mod = PIL
        elif pkg == 'cv2':
            import cv2
            mod = cv2
        else:
            mod = __import__(pkg)
        version = getattr(mod, '__version__', '已安装')
        print(f"✅ {pkg:15s}: {version}")
    except ImportError:
        print(f"❌ {pkg:15s}: 未安装")
EOF

echo ""
echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""

# 给出下一步建议
if [ ! -f "weights/yolo11s-ball.pt" ]; then
    echo "⚠️  下一步: 下载模型权重"
    echo "   访问: https://github.com/yo-WASSUP/Good-Badminton/releases/latest"
    echo "   下载 yolo11s-ball.pt 并放到 weights/ 目录"
    echo ""
elif [ $video_count -eq 0 ]; then
    echo "⚠️  下一步: 准备测试视频"
    echo "   将羽毛球比赛视频复制到 videos/ 目录"
    echo ""
else
    echo "✅ 环境准备就绪！可以开始运行分析"
    echo ""
    echo "运行命令:"
    echo "   source .venv/bin/activate"
    echo "   python main.py --video-path videos/$(ls videos/*.mp4 2>/dev/null | head -n1 | xargs basename)"
    echo ""
fi
