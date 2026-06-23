#!/usr/bin/env bash
# 一键分析羽毛球视频：自动生成球场模板，然后跑完整分析。
#
# 用法:
#   ./analyze.sh videos/你的视频.mp4
#   ./analyze.sh videos/你的视频.mp4 templates/已有模板.png   # 跳过自动生成，用指定模板
#
# 产物输出在 outputs/<视频名>/

set -euo pipefail

# 切换到脚本所在目录（项目根）
cd "$(dirname "$(readlink -f "$0")")"

if [[ $# -lt 1 ]]; then
  echo "用法: $0 <视频路径> [模板路径]"
  echo "示例: $0 videos/test_video.mp4"
  exit 2
fi

VIDEO="$1"
if [[ ! -f "$VIDEO" ]]; then
  echo "✗ 找不到视频文件: $VIDEO"
  exit 1
fi

# 激活虚拟环境
if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "✗ 没找到 .venv 虚拟环境，请先运行 setup.sh"
  exit 1
fi

NAME="$(basename "${VIDEO%.*}")"

# 1) 确定模板：用户指定就用指定的，否则自动生成
if [[ $# -ge 2 ]]; then
  TEMPLATE="$2"
  if [[ ! -f "$TEMPLATE" ]]; then
    echo "✗ 找不到指定模板: $TEMPLATE"
    exit 1
  fi
  echo "==> 使用指定模板: $TEMPLATE"
else
  TEMPLATE="templates/${NAME}.png"
  if [[ -f "$TEMPLATE" ]]; then
    echo "==> 已存在模板，复用: $TEMPLATE"
  else
    echo "==> 自动生成球场模板..."
    OUT="$(python make_template.py "$VIDEO" "$TEMPLATE")"
    echo "$OUT"
    if ! echo "$OUT" | grep -q "TEMPLATE_SAVED="; then
      echo "✗ 模板生成失败，请手动截一帧比赛画面存到 $TEMPLATE 后重试。"
      exit 3
    fi
  fi
fi

# 2) 跑完整分析
echo "==> 开始分析视频: $VIDEO"
python main.py \
  --video-path "$VIDEO" \
  --template-path "$TEMPLATE" \
  --pose-family yolo-pose \
  --yolo-pose-model weights/yolo11n-pose.pt \
  --display false \
  --skeletons true \
  --player-trajectories true \
  --court-trajectory true \
  --shuttlecock-trajectory true \
  --player-stats true \
  --visualize-positions true \
  --language zh

echo ""
echo "==> 完成！产物在: outputs/${NAME}/"
echo "    分析视频: outputs/${NAME}/detect_${NAME}.mp4"
