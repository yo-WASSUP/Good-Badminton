# Good-Badminton: AI 羽毛球比赛分析助手 🏸

<div align="center">

[![GitHub stars](https://img.shields.io/github/stars/yo-WASSUP/Good-Badminton?style=social)](https://github.com/yo-WASSUP/Good-Badminton/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/yo-WASSUP/Good-Badminton?style=social)](https://github.com/yo-WASSUP/Good-Badminton/network/members)
[![GitHub license](https://img.shields.io/github/license/yo-WASSUP/Good-Badminton)](https://github.com/yo-WASSUP/Good-Badminton/blob/main/LICENSE)

**基于计算机视觉的羽毛球比赛视频分析工具**

[中文](README.md)

</div>

## 🆕 更新日志

- **2026-06-17**：整理项目介绍文档。
- **当前版本**：支持球员姿态检测、羽毛球检测、球场坐标映射、轨迹统计、热力图/散点图和带标注视频输出。
- **实验功能**：击球点分析和技术动作统计仍在迭代中，适合研究和二次开发使用。

## 🔮 开发计划

- [x] 羽毛球比赛视频逐帧分析
- [x] RTMPose / RTMO / YOLO Pose 多姿态模型支持
- [x] YOLO 羽毛球检测模型接入
- [x] 手动球场标注与球场坐标映射
- [x] 球员移动轨迹、速度、距离和回合统计
- [x] 中文 / 英文可视化文字
- [x] 热力图、散点图和检测数据导出
- [ ] 更稳定的击球点识别
- [ ] 更完整的技术动作统计
- [ ] 自动球场关键点检测
- [ ] 批量视频分析工作流

---

## ✨ 功能特点

- **球员姿态检测** - 支持 RTMPose、RTMO 和 Ultralytics YOLO Pose，识别人体关键点和骨架。
- **羽毛球检测** - 使用 YOLO 模型检测羽毛球位置，并在输出视频中绘制轨迹。
- **球场坐标映射** - 手动标注球场关键点，将图像坐标映射到标准球场坐标。
- **球员位置追踪** - 分别追踪上半场和下半场球员位置，记录移动轨迹。
- **回合检测** - 根据连续球场视图自动判断回合开始和结束，并在视频叠加层和检测数据中记录回合编号。
- **运动统计分析** - 统计移动距离、当前速度、最大速度和回合数量。
- **可视化输出** - 生成带骨架、轨迹、统计信息和球场轨迹的分析视频。
- **位置图表** - 自动生成球员位置热力图和散点图。
- **中英文显示** - 可通过 `--language zh/en` 切换可视化文字。
- **本地运行** - 视频、模型和分析结果都保存在本地。

## 📋 系统要求

- Python 3.8+
- FFmpeg，并已加入系统 `PATH`
- OpenCV / PyTorch / Ultralytics / RTMLib / ONNX Runtime
- 推荐 NVIDIA GPU；CPU 可以运行，但视频分析速度会明显变慢
- 羽毛球 YOLO 检测权重 `weights/yolo11s-ball.pt`，计划随项目 Release 一起开源发布

## 🚀 安装指南

默认依赖使用 CPU 版 PyTorch 和 ONNX Runtime，兼容性最好，建议先用 CPU 环境跑通完整流程。

### Windows

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### GPU 加速（Windows / NVIDIA）

前置要求：

- 已安装 NVIDIA 显卡驱动，`nvidia-smi` 可以正常输出显卡信息。
- 推荐使用 CUDA 12.1 对应的 PyTorch wheel。
- 如果遇到 DLL 加载失败，先安装或修复 Microsoft Visual C++ Redistributable 2015-2022 x64。

PowerShell：

```bash
.\.venv\Scripts\activate

pip uninstall -y torch torchvision onnxruntime onnxruntime-gpu
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install onnxruntime-gpu==1.20.1
```

验证 GPU 是否生效：

```bash
python -c "import torch; print('torch:', torch.__version__); print('cuda:', torch.cuda.is_available()); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'not available')"
python -c "import onnxruntime as ort; print(ort.__version__); print(ort.get_available_providers())"
```

期望看到：

```text
cuda: True
CUDAExecutionProvider
```

> 注意：安装 GPU 版 ONNX Runtime 后，`pip check` 可能提示 `rtmlib requires onnxruntime, which is not installed`。只要 provider 验证能看到 `CUDAExecutionProvider`，就不要再安装 CPU 版 `onnxruntime`，否则可能覆盖 GPU 包。

切回 CPU 版：

```bash
pip install --force-reinstall -r requirements.txt
```

## 📦 模型准备

羽毛球检测默认使用本项目计划开源发布的 YOLO 权重。下载或训练得到权重后，请放到：

```text
weights/yolo11s-ball.pt
```

RTMPose 可以使用本地 ONNX 模型文件：

```text
weights/yolox_nano_8xb8-300e_humanart-40f6f0d0.onnx
weights/rtmpose-s_simcc-body7_pt-body7_420e-256x192-acd4a1ef_20230504.onnx
```

如果你从 Release 下载权重，保持文件名为 `yolo11s-ball.pt` 即可直接运行；也可以通过 `--ball-model` 指向其他自训练权重。`weights/` 目录本身可放置本地模型文件，较大的权重文件建议通过 GitHub Release 发布。`rtmlib` 的 RTMPose 文件如果本地不存在，可能会尝试在线下载。

## 📝 使用指南

### 基础运行

```bash
python main.py --video-path videos/lindan2008-round17.mp4
```

### 第一次运行流程

1. 准备输入视频和羽毛球检测权重。默认权重路径是 `weights/yolo11s-ball.pt`，项目计划在 Release 中开源发布该权重。
2. 运行基础命令：

```bash
python main.py --video-path videos/lindan2008-round17.mp4
```

3. 如果没有传 `--template-path`，程序会弹出文件选择框，让你选择一张球场模板图。模板图通常选视频里视角稳定、球场线清楚的一帧。
4. 程序会打开球场标注窗口。按图片顶部提示，依次点击球场四个角点：左上、右上、右下、左下。
5. 点完四个点后，窗口会显示绿色球场框和蓝色姿态检测 ROI 框。ROI 由程序根据球场自动生成。
6. 标注结果会保存到 `results/<视频文件名>/court_annotations.txt`。同一个输出目录下再次运行会复用这个文件，不会重复要求标注。
7. 分析结束后，查看 `results/<视频文件名>/detect_<视频文件名>.mp4`、`detections.jsonl` 和 `position_visualizations/`。

为什么要标注球场四点：

- 四个角点用于建立图像坐标到标准羽毛球场坐标的映射。
- 球员过滤主要依赖球场坐标，能把观众、裁判、场外人员过滤掉。
- 上下半场球员判断、移动距离、速度、回合统计、热力图和散点图都依赖这个映射。
- 回合检测基于球场模板匹配：连续多帧识别为比赛视图时开始回合，连续多帧离开比赛视图时结束回合。
- 姿态检测 ROI 只用于减少推理区域和提升速度；它会自动从球场范围扩展生成。
- 羽毛球检测仍在整帧上执行，轨迹显示会按球场横向范围加 padding 做基础过滤。

如果你换了视频视角、裁切方式或模板图，需要删除对应输出目录里的 `court_annotations.txt`，重新标注四点。

### 回合检测说明

程序会用球场模板图做比赛视图判断，并自动维护回合状态：

- 连续多帧匹配到球场视图时，判定新回合开始。
- 连续多帧没有匹配到球场视图时，判定当前回合结束。
- 回合编号会写入 `detections.jsonl`，并显示在输出视频的统计叠加层中。
- 每个回合开始时会重置该回合内的移动距离、速度等统计，整场统计继续累计。
- 这个逻辑依赖模板图和四点球场标注；如果模板图选得不准，回合切分也会不准。

### 姿态模型选择

```bash
# 默认：两阶段 RTMPose balanced
python main.py --video-path path/to/video.mp4 --pose-family rtmpose --pose-mode balanced

# 更轻量的一阶段 RTMO
python main.py --video-path path/to/video.mp4 --pose-family rtmo --pose-mode lightweight

# 使用 Ultralytics YOLO Pose
python main.py --video-path path/to/video.mp4 --pose-family yolo-pose --yolo-pose-model yolo11n-pose.pt
```

RTMPose 模型档位：

- `lightweight`：速度优先。
- `balanced`：默认配置，速度和效果折中。
- `performance`：更大模型，速度更慢，通常更适合追求检测质量。

### 常用参数

```text
--video-path                 输入视频路径，必填
--output-dir                 输出目录，默认 results/<视频文件名>
--ball-model                 YOLO 羽毛球检测模型路径，默认 weights/yolo11s-ball.pt
--pose-family                姿态模型族：rtmpose、rtmo 或 yolo-pose
--pose-mode                  RTMPose 档位：lightweight、balanced、performance
--yolo-pose-model            YOLO pose 模型路径或模型名，默认 yolo11n-pose.pt
--template-path              球场模板图路径；不传时会弹出文件选择框
--pose-roi true|false                是否显示姿态检测 ROI 框，默认 true
--display true|false                 是否显示 OpenCV 预览窗口，默认 true
--skeletons true|false               是否显示人体骨架，默认 true
--player-trajectories true|false     是否显示球员轨迹，默认 true
--court-trajectory true|false        是否显示球场轨迹叠加层，默认 true
--shuttlecock-trajectory true|false  是否显示羽毛球轨迹，默认 true
--player-stats true|false            是否显示球员统计信息，默认 true
--performance-stats                  打印性能耗时
--save-images                        保存处理后的每帧图像
--visualize-positions true|false     是否生成热力图和散点图，默认 true
--audio true|false                   是否保留原视频音频，默认 true
--language {zh,en}           选择界面语言
```

## 📊 输出结果

默认输出到 `results/<视频文件名>/`：

- `metadata.json`：视频、模型、球场标注和输出文件元数据。
- `detections.jsonl`：逐帧检测记录，包含回合编号、球员、手部、球场坐标、速度和羽毛球坐标。
- `detect_<视频文件名>.mp4`：带骨架、轨迹、统计信息和回合编号叠加层的输出视频。
- `court_annotations.txt`：球场标注坐标缓存。
- `position_visualizations/heatmaps/`：球员位置热力图。
- `position_visualizations/scatter_plots/`：球员位置散点图。

## 🧩 项目结构

```text
main.py              # 命令行入口和参数解析，保持 python main.py ... 的运行方式
badminton_analysis/
├── cli.py           # 兼容转发入口
├── system.py        # 视频分析主流程 BadmintonAnalysisSystem
├── court/           # 球场标注与坐标映射
├── data/            # JSON / JSONL 输出
├── detection/       # 羽毛球检测与姿态检测
├── media/           # 视频音频处理
├── tracking/        # 球员追踪
└── visualization/   # 视频叠加层、统计图和位置图
```

## 📚 相关文档

- [球员位置可视化说明](docs/player-position-visualization.md)

## 🙏 致谢

感谢 TrackNetV2 羽毛球数据集。

## 📄 许可证

本项目代码使用 Apache License 2.0，详见 [LICENSE](LICENSE)。`weights/yolo11s-ball.pt` 羽毛球检测权重计划随项目开源发布；权重文件的许可证和使用限制请以发布时的 Release 说明为准。