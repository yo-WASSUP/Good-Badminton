import argparse
import os

from badminton_analysis.system import BadmintonAnalysisSystem, load_runtime_dependencies



def main():
    parser = argparse.ArgumentParser(description='羽毛球比赛视频分析系统')
    parser.add_argument('--video-path', required=True, type=str, help='输入视频文件路径')
    parser.add_argument('--output-dir', default=None, type=str, help='输出目录，默认 results/<视频文件名>')
    parser.add_argument('--ball-model', default='weights/yolo11s-ball.pt', type=str, help='YOLO 羽毛球检测模型路径')
    parser.add_argument('--pose-family', default='rtmpose', choices=['rtmpose', 'rtmo', 'yolo-pose'], help='姿态模型族')
    parser.add_argument('--pose-mode', default='balanced', choices=['lightweight', 'balanced', 'performance'], help='RTMPose 模型档位')
    parser.add_argument('--yolo-pose-model', default='yolo11n-pose.pt', type=str, help='YOLO pose 模型路径或模型名')
    parser.add_argument('--template-path', default=None, type=str, help='球场模板图像路径；不提供时会弹出文件选择框')
    parser.add_argument('--pose-roi', choices=['true', 'false'], default='true', help='是否显示姿态检测 ROI 框，默认 true')
    parser.add_argument('--display', choices=['true', 'false'], default='true', help='是否显示视频窗口，默认 true')
    parser.add_argument('--skeletons', choices=['true', 'false'], default='true', help='是否显示人体骨架，默认 true')
    parser.add_argument('--player-trajectories', choices=['true', 'false'], default='true', help='是否显示球员轨迹，默认 true')
    parser.add_argument('--court-trajectory', choices=['true', 'false'], default='true', help='是否显示球场轨迹，默认 true')
    parser.add_argument('--shuttlecock-trajectory', choices=['true', 'false'], default='true', help='是否显示羽毛球轨迹，默认 true')
    parser.add_argument('--player-stats', choices=['true', 'false'], default='true', help='是否显示球员统计信息，默认 true')
    parser.add_argument('--save-images', action='store_true', default=False, help='保存处理后的图像')
    parser.add_argument('--performance-stats', action='store_true', default=False, help='显示性能统计信息')
    parser.add_argument('--visualize-positions', choices=['true', 'false'], default='true', help='是否生成球员位置热力图和散点图，默认 true')
    parser.add_argument('--audio', choices=['true', 'false'], default='true', help='是否保留原视频音频，默认 true')
    parser.add_argument('--language', default='zh', choices=['zh', 'en'], help='选择界面语言 (zh/en)')
    args = parser.parse_args()

    load_runtime_dependencies()

    if args.language == 'en':
        from badminton_analysis.visualization.player_positions_en import analyze_player_positions
    else:
        from badminton_analysis.visualization.player_positions_zh import analyze_player_positions

    system = BadmintonAnalysisSystem(
        args.video_path,
        show_display=args.display == 'true',
        show_skeletons=args.skeletons == 'true',
        show_player_trajectories=args.player_trajectories == 'true',
        show_court_trajectory=args.court_trajectory == 'true',
        show_shuttlecock_trajectory=args.shuttlecock_trajectory == 'true',
        show_player_stats=args.player_stats == 'true',
        show_performance_stats=args.performance_stats,
        save_images=args.save_images,
        language=args.language,
        output_dir=args.output_dir,
        ball_model_path=args.ball_model,
        template_path=args.template_path,
        pose_mode=args.pose_mode,
        pose_family=args.pose_family,
        yolo_pose_model=args.yolo_pose_model,
        show_pose_roi=args.pose_roi == 'true'
    )

    system.keep_audio = args.audio == 'true'
    system.process_video()

    if args.visualize_positions == 'true':
        print("\n开始生成球员位置可视化...")
        analyze_player_positions(system.detections_path, os.path.join(system.save_dir, 'position_visualizations'), fps=system.fps)
        print("球员位置可视化完成")

if __name__ == "__main__":
    main()
