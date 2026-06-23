#!/usr/bin/env python3
"""
自动从视频中挑选一帧合适的「比赛画面」作为球场模板。

用法:
    python make_template.py videos/xxx.mp4 [templates/xxx.png]

原理:
    1. 在视频不同时间点抽多帧
    2. 用项目的 auto_detect_court_corners 筛掉回放/特写等非比赛画面
    3. 选一帧并验证它对其他比赛帧的模板匹配分 >= 0.75
    4. 保存为模板图

成功后打印模板路径（供外层脚本捕获）。
"""
import os
import sys
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from badminton_analysis.court.detector import auto_detect_court_corners

MATCH_THRESHOLD = 0.75


def grab_frame(cap, t_sec):
    cap.set(cv2.CAP_PROP_POS_MSEC, t_sec * 1000)
    ok, frame = cap.read()
    return frame if ok else None


def main():
    if len(sys.argv) < 2:
        print("用法: python make_template.py <视频路径> [模板输出路径]", file=sys.stderr)
        sys.exit(2)

    video = sys.argv[1]
    if not os.path.exists(video):
        print(f"找不到视频: {video}", file=sys.stderr)
        sys.exit(1)

    name = os.path.splitext(os.path.basename(video))[0]
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join("templates", f"{name}.png")

    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps if fps else 0
    if duration <= 0:
        print("无法读取视频时长", file=sys.stderr)
        sys.exit(1)

    # 在 10%~90% 之间均匀取 12 个采样点，避开片头/片尾
    n_samples = 12
    times = [duration * (0.1 + 0.8 * i / (n_samples - 1)) for i in range(n_samples)]

    candidates = []  # (t, frame)
    for t in times:
        frame = grab_frame(cap, t)
        if frame is None:
            continue
        base = cv2.resize(frame, (1080, 720))
        corners, _, _ = auto_detect_court_corners(base)
        ok = corners is not None and len(corners) == 4
        print(f"  {t:5.1f}s: {'检测到球场 ✓' if ok else '未检测到 ✗'}")
        if ok:
            candidates.append((t, frame))

    if not candidates:
        print("\n未能在任何采样帧检测到球场。可能原因: 机位非标准、画质问题。", file=sys.stderr)
        print("可手动截一帧标准比赛画面存到 templates/ 后用 --template-path 指定。", file=sys.stderr)
        cap.release()
        sys.exit(3)

    # 选中间那个候选帧（通常最稳），验证它对其他候选帧的匹配分
    pick_t, pick_frame = candidates[len(candidates) // 2]
    tmpl_gray = cv2.cvtColor(pick_frame, cv2.COLOR_BGR2GRAY)
    scores = []
    for t, frame in candidates:
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        tr = cv2.resize(tmpl_gray, (g.shape[1], g.shape[0]))
        scores.append(cv2.matchTemplate(g, tr, cv2.TM_CCOEFF_NORMED).max())
    min_score = min(scores)
    print(f"\n选用 {pick_t:.1f}s 处的帧作模板，对其余比赛帧最低匹配分: {min_score:.3f}")

    if min_score < MATCH_THRESHOLD:
        print(f"警告: 最低匹配分 < {MATCH_THRESHOLD}，机位可能不稳定，模板仍会保存但识别可能不准。", file=sys.stderr)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    cv2.imwrite(out_path, pick_frame)
    cap.release()
    print(f"TEMPLATE_SAVED={out_path}")


if __name__ == "__main__":
    main()
