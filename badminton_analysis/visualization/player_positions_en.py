import cv2
import json
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from collections import defaultdict

# 设置全局绘图风格为深色
plt.style.use('dark_background')

class PlayerPositionVisualizer:
    """
    Player Position Visualization Class
    """
    
    def __init__(self, detections_path, output_dir=None, court_width=6.1, court_length=13.4, fps=30):
        """
        Initialize the player position visualizer
        Args:
            detections_path: Path to detections.jsonl containing player position data
            output_dir: Output directory, defaults to visualizations subdirectory in the detection file's directory
            court_width: Badminton court width in meters (default: 6.1m)
            court_length: Badminton court length in meters (default: 13.4m)
        """
        self.detections_path = detections_path
        self.court_width = court_width
        self.court_length = court_length
        
        # Set output directory
        if output_dir is None:
            detections_dir = os.path.dirname(os.path.abspath(detections_path))
            self.output_dir = os.path.join(detections_dir, 'position_visualizations')
        else:
            self.output_dir = output_dir
            
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'heatmaps'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'scatter_plots'), exist_ok=True)
        
        # Movement statistics parameters
        self.fps = fps  # Video frame rate, used for speed calculation
        self.movement_stats = defaultdict(dict)
        self.MAX_SPEED = 8.0  # Human maximum speed limit (m/s)
        self.MIN_MOVEMENT = 0.05  # Minimum movement distance (m), below this value is considered noise
        self.MAX_FRAME_DISTANCE = 8.0 / self.fps  # Maximum frame-to-frame distance (m), based on max speed and fps
        
        # Load data
        self.df = self._load_data()
    
        # Court image parameters
        self.img_width = 610  # Image width (pixels)
        self.img_height = 1340  # Image height (pixels)
        
        # Heatmap grid parameters
        self.heatmap_grid_size = (30, 60)  # Grid size (width grid count, length grid count)
        
        # Color settings - 调整为在深色背景中更醒目的颜色
        self.upper_color = '#ff6363'  # Upper court player color (亮红色，在深色背景中更醒目)
        self.lower_color = '#63c6ff'  # Lower court player color (亮蓝色，在深色背景中更醒目)
        
        # 场地线条颜色 - 深色主题
        self.court_line_color = '#bbbbbb'  # 浅灰色，在深色背景中清晰可见
        
    def _calculate_movement_stats(self, upper_df, lower_df, rally_segments, frames):
        """Calculate movement statistics for each rally (average speed, maximum speed, total distance)"""
        self.movement_stats = defaultdict(dict)
        frame_times = frames / self.fps  # Convert frame numbers to time (seconds)
        
        # Calculate match-wide statistics
        all_upper = upper_df[upper_df['valid_coords']]
        all_lower = lower_df[lower_df['valid_coords']]
        
        # Match statistics
        if not all_upper.empty:
            self.movement_stats['match']['upper'] = self._calculate_player_stats(
                all_upper[['court_x', 'court_y']].values, 
                frame_times[all_upper.index].values
            )
            
        if not all_lower.empty:
            self.movement_stats['match']['lower'] = self._calculate_player_stats(
                all_lower[['court_x', 'court_y']].values, 
                frame_times[all_lower.index].values
            )
        
        # Calculate for each rally separately
        for rally_id, (start_idx, end_idx) in enumerate(rally_segments, 1):
            # Extract time and position data for current rally
            rally_times = frame_times[start_idx:end_idx].values
            
            # Upper court player data
            upper_rally = upper_df[(upper_df['rally_id'] == rally_id) & (upper_df['valid_coords'])]
            upper_positions = upper_rally[['court_x', 'court_y']].values
            
            # Lower court player data
            lower_rally = lower_df[(lower_df['rally_id'] == rally_id) & (lower_df['valid_coords'])]
            lower_positions = lower_rally[['court_x', 'court_y']].values
            
            # 计算上场球员统计数据
            if len(upper_positions) > 1:
                upper_stats = self._calculate_player_stats(upper_positions, rally_times)
                self.movement_stats[rally_id]['upper'] = upper_stats
            
            # 计算下场球员统计数据
            if len(lower_positions) > 1:
                lower_stats = self._calculate_player_stats(lower_positions, rally_times)
                self.movement_stats[rally_id]['lower'] = lower_stats
    
    def _calculate_player_stats(self, positions, times):
        """Calculate movement statistics for a single player"""
        # Initialize statistics
        stats = {
            'total_distance': 0.0,
            'max_speed': 0.0,
            'avg_speed': 0.0,
            'total_frames': len(positions)  # Total frames
        }
        
        # If less than 2 data points, cannot calculate statistics
        if len(positions) < 2:
            return stats
        
        # Calculate total distance and maximum speed
        total_valid_distance = 0.0
        max_speed = 0.0
        
        # Sampling interval, sample every 5 frames
        sample_interval = 5
        current_time = len(positions) - 1
        
        # Ensure at least one sampling point
        if current_time < sample_interval:
            sample_points = [0, current_time]
        else:
            # Create list of sampling points
            sample_points = list(range(0, current_time + 1, sample_interval))
            # Ensure the last point is included
            if current_time not in sample_points:
                sample_points.append(current_time)
        
        # Calculate distance between sampling points
        for i in range(len(sample_points) - 1):
            idx1 = sample_points[i]
            idx2 = sample_points[i + 1]
            
            p1 = positions[idx1]
            p2 = positions[idx2]
            
            # Calculate Euclidean distance (meters)
            dist = np.sqrt(((p2 - p1)**2).sum())
            
            # Calculate time difference (seconds)
            time_diff = times[idx2] - times[idx1] if idx2 < len(times) else (idx2 - idx1) / self.fps
            
            # Adjust maximum allowed distance based on time interval
            max_possible_distance = self.MAX_FRAME_DISTANCE * (idx2 - idx1)
            
            # Filter small movements and anomalies
            if dist > self.MIN_MOVEMENT and dist < max_possible_distance:
                # Accumulate valid distance
                total_valid_distance += dist
                
                # Calculate speed and update maximum speed
                if time_diff > 0:
                    speed = dist / time_diff
                    speed = min(speed, self.MAX_SPEED)  # Limit maximum speed
                    max_speed = max(max_speed, speed)
        
        # Update statistics
        stats['total_distance'] = round(total_valid_distance, 2)
        stats['max_speed'] = round(max_speed, 2)
        
        # Calculate average speed - use total distance divided by total time, considering stationary time
        total_time = times[-1] - times[0] if len(times) > 1 else stats['total_frames'] / self.fps
        if total_time > 0:
            stats['avg_speed'] = round(total_valid_distance / total_time, 2)
        
        return stats
    
    def _load_data(self):
        """Load detections.jsonl and convert to required format"""
        try:
            rows = []
            with open(self.detections_path, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    players = record.get("players", {})
                    upper = players.get("upper", {}) or {}
                    lower = players.get("lower", {}) or {}
                    upper_court = upper.get("court") or [None, None]
                    lower_court = lower.get("court") or [None, None]
                    rows.append({
                        "Frame": record.get("frame"),
                        "Upper_Court_X": upper_court[0],
                        "Upper_Court_Y": upper_court[1],
                        "Lower_Court_X": lower_court[0],
                        "Lower_Court_Y": lower_court[1],
                    })

            df = pd.DataFrame(rows)
            
            print(f"\nData fields: {df.columns.tolist()}")
            
            # Check required columns
            if 'Frame' not in df.columns or \
               'Upper_Court_X' not in df.columns or 'Upper_Court_Y' not in df.columns or \
               'Lower_Court_X' not in df.columns or 'Lower_Court_Y' not in df.columns:
                print("Error: Data file missing required columns like Frame, Upper_Court_X etc.")
                return pd.DataFrame()
            
            # Detect rallies based on frame gaps (similar to hit_point.py)
            print("Detecting rallies based on frame gaps...")
            frames = df['Frame'].astype(int).tolist()
            gaps = [frames[i+1] - frames[i] for i in range(len(frames)-1)]
            rally_breaks = [i+1 for i, gap in enumerate(gaps) if gap > 100]
            
            # Create rally segments
            rally_segments = []
            start_idx = 0
            
            for break_idx in rally_breaks:
                rally_segments.append((start_idx, break_idx))
                start_idx = break_idx
            
            # Add the last segment
            if start_idx < len(frames):
                rally_segments.append((start_idx, len(frames)))
            
            # Filter out short rallies (less than 150 frames)
            rally_segments = [(start, end) for start, end in rally_segments if end - start >= 150]
            
            print(f"Detected {len(rally_segments)} valid rallies")
            
            # Check coordinate ranges for normalization
            print("\nRaw coordinate ranges:")
            print(f"Upper_Court_X: {df['Upper_Court_X'].min()} to {df['Upper_Court_X'].max()}")
            print(f"Upper_Court_Y: {df['Upper_Court_Y'].min()} to {df['Upper_Court_Y'].max()}")
            print(f"Lower_Court_X: {df['Lower_Court_X'].min()} to {df['Lower_Court_X'].max()}")
            print(f"Lower_Court_Y: {df['Lower_Court_Y'].min()} to {df['Lower_Court_Y'].max()}")
            
            # Normalize coordinates to standard badminton court size (13.4m x 6.1m)
            print("\nNormalizing coordinates to standard court size...")
            
            # Create upper court player data with rally IDs
            upper_df = df[['Frame', 'Upper_Court_X', 'Upper_Court_Y']].copy()
            
            # Filter out negative coordinates - they won't participate in visualization
            # Use original coordinates
            upper_df['normalized_x'] = upper_df['Upper_Court_X']
            upper_df['normalized_y'] = upper_df['Upper_Court_Y']
            
            # Mark rows with negative coordinates for later filtering
            upper_df['valid_coords'] = (upper_df['normalized_x'] >= 0) & (upper_df['normalized_y'] >= 0)
            
            upper_df.rename(columns={
                'Frame': 'frame',
                'normalized_x': 'court_x',
                'normalized_y': 'court_y'
            }, inplace=True)
            upper_df['player_position'] = 'upper'
            
            # Assign rally IDs based on detected segments
            upper_df['rally_id'] = 0  # Default to 0 (no rally)
            for rally_id, (start, end) in enumerate(rally_segments, 1):
                mask = (upper_df.index >= start) & (upper_df.index < end)
                upper_df.loc[mask, 'rally_id'] = rally_id
            
            # Create lower court player data with rally IDs
            lower_df = df[['Frame', 'Lower_Court_X', 'Lower_Court_Y']].copy()
            
            # Use original coordinates
            lower_df['normalized_x'] = lower_df['Lower_Court_X']
            lower_df['normalized_y'] = lower_df['Lower_Court_Y']
            
            # Mark rows with negative coordinates for later filtering
            lower_df['valid_coords'] = (lower_df['normalized_x'] >= 0) & (lower_df['normalized_y'] >= 0)
            
            lower_df.rename(columns={
                'Frame': 'frame',
                'normalized_x': 'court_x',
                'normalized_y': 'court_y'
            }, inplace=True)
            lower_df['player_position'] = 'lower'
            
            # Assign same rally IDs to lower court player
            lower_df['rally_id'] = 0  # Default to 0 (no rally)
            for rally_id, (start, end) in enumerate(rally_segments, 1):
                mask = (lower_df.index >= start) & (lower_df.index < end)
                lower_df.loc[mask, 'rally_id'] = rally_id
            
            # 计算每个回合的移动统计数据
            self._calculate_movement_stats(upper_df, lower_df, rally_segments, df['Frame'])
            
            # Combine upper and lower court data
            combined_df = pd.concat([upper_df, lower_df], ignore_index=True)
            
            # Filter out invalid values, frames not in rallies, and negative coordinates
            combined_df = combined_df.dropna(subset=['court_x', 'court_y'])
            combined_df = combined_df[combined_df['rally_id'] > 0]
            combined_df = combined_df[combined_df['valid_coords'] == True]
            
            # Drop the temporary column as it's no longer needed
            combined_df = combined_df.drop('valid_coords', axis=1)
            
            print(f"\nData conversion complete, {len(combined_df)} records total")
            return combined_df
            
        except Exception as e:
            print(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()  # Return empty DataFrame
            
    def _create_court_image(self):
        """Create court background image"""
        # Create blank white image
        self.court_img = np.ones((self.img_height, self.img_width, 3), dtype=np.uint8) * 255
        
        # Calculate court area dimensions
        padding = 50  # Border padding in pixels
        court_img_width = self.img_width - 2 * padding
        court_img_height = self.img_height - 2 * padding
        
        # Court corners (in image coordinates)
        top_left = (padding, padding)
        top_right = (padding + court_img_width, padding)
        bottom_right = (padding + court_img_width, padding + court_img_height)
        bottom_left = (padding, padding + court_img_height)
        
        # Draw court outline
        cv2.line(self.court_img, top_left, top_right, (0, 0, 0), 2)
        cv2.line(self.court_img, top_right, bottom_right, (0, 0, 0), 2)
        cv2.line(self.court_img, bottom_right, bottom_left, (0, 0, 0), 2)
        cv2.line(self.court_img, bottom_left, top_left, (0, 0, 0), 2)
        
        # Draw net
        net_y = padding + court_img_height // 2
        cv2.line(self.court_img, (padding, net_y), (padding + court_img_width, net_y), (0, 0, 0), 1)
        
        # Draw center line
        center_x = padding + court_img_width // 2
        cv2.line(self.court_img, (center_x, padding), (center_x, padding + court_img_height), (0, 0, 0), 1)
        
        # Draw service courts
        upper_service_line_y = padding + int(court_img_height * 0.25)
        lower_service_line_y = padding + int(court_img_height * 0.75)
        
        cv2.line(self.court_img, (padding, upper_service_line_y), 
                 (padding + court_img_width, upper_service_line_y), (0, 0, 0), 1)
        cv2.line(self.court_img, (padding, lower_service_line_y),
                 (padding + court_img_width, lower_service_line_y), (0, 0, 0), 1)
        
        # Draw service line edges
        cv2.line(self.court_img,
                 (int(padding + court_img_width * 0.25), padding),
                 (int(padding + court_img_width * 0.25), upper_service_line_y), 
                 (0, 0, 0), 1)
        cv2.line(self.court_img,
                 (int(padding + court_img_width * 0.75), padding),
                 (int(padding + court_img_width * 0.75), upper_service_line_y), 
                 (0, 0, 0), 1)
        cv2.line(self.court_img,
                 (int(padding + court_img_width * 0.25), lower_service_line_y),
                 (int(padding + court_img_width * 0.25), padding + court_img_height), 
                 (0, 0, 0), 1)
        cv2.line(self.court_img,
                 (int(padding + court_img_width * 0.75), lower_service_line_y),
                 (int(padding + court_img_width * 0.75), padding + court_img_height), 
                 (0, 0, 0), 1)
                
        return self.court_img
        
    def _draw_court(self, ax=None):
        """在matplotlib图形上绘制标准羽毛球场地"""
        if ax is not None:
            plt.sca(ax)
        
        # 关键：反转Y轴以匹配真实球场方向（0在顶部，13.4在底部）
        plt.gca().invert_yaxis()
        
        # 标准羽毛球场地尺寸（米）
        doubles_width = self.court_width  # 双打场地宽度 (6.10米)
        court_length = self.court_length  # 场地长度 (13.40米)
        single_width = 0.46   # 单打线距离双打线的距离
        service_line = 1.98   # 发球线到网的距离
        back_service = 0.76   # 后发球线到底线的距离
        
        # 绘制场地外框（双打场地外框）
        court_rect = plt.Rectangle((0, 0), doubles_width, court_length, 
                                 fill=False, color=self.court_line_color, linewidth=4)
        plt.gca().add_patch(court_rect)
        
        # 绘制单打线
        plt.plot([single_width, single_width], [0, court_length], self.court_line_color, linewidth=4)
        plt.plot([doubles_width - single_width, doubles_width - single_width], 
                 [0, court_length], self.court_line_color, linewidth=4)
        
        # 绘制网线（中间在y=场地长度/2）
        plt.axhline(y=court_length/2, color=self.court_line_color, linestyle='--', linewidth=4)
        
        # 绘制中线（只画到发球线）
        plt.plot([doubles_width/2, doubles_width/2], [0, court_length/2-service_line], self.court_line_color, linewidth=4)  # 上半场
        plt.plot([doubles_width/2, doubles_width/2], [court_length/2+service_line, court_length], self.court_line_color, linewidth=4)  # 下半场
        
        # 绘制发球线
        # 前发球线（距网1.98米）
        plt.axhline(y=court_length/2-service_line, color=self.court_line_color, linestyle='-', linewidth=4)
        plt.axhline(y=court_length/2+service_line, color=self.court_line_color, linestyle='-', linewidth=4)
        
        # 后发球线（距底线0.76米）
        plt.axhline(y=back_service, color=self.court_line_color, linestyle='-', linewidth=4)
        plt.axhline(y=court_length-back_service, color=self.court_line_color, linestyle='-', linewidth=4)
        
        # 设置显示范围（带边距）
        plt.xlim(-0.5, doubles_width + 0.5)
        plt.ylim(court_length + 0.5, -0.5)  # 注意：Y轴范围是反向的
        
    def _court_to_image_coords(self, court_x, court_y):
        """Convert court coordinates to image coordinates"""
        img_x = int(court_x / self.court_width * self.img_width)
        img_y = int(court_y / self.court_length * self.img_height)
        return img_x, img_y
        
    def _generate_rally_visualizations(self):
        """Generate visualizations for each rally"""
        if self.df.empty:
            print("No data to visualize")
            return
            
        # Get all rally IDs
        rally_ids = self.df['rally_id'].unique()
        
        for rally_id in rally_ids:
            # Skip invalid rally IDs
            if pd.isna(rally_id):
                continue
                
            print(f"Processing visualizations for rally {rally_id}...")
            
            # Filter current rally data
            rally_df = self.df[self.df['rally_id'] == rally_id]
            
            # Separate upper and lower court players
            upper_df = rally_df[rally_df['player_position'] == 'upper']
            lower_df = rally_df[rally_df['player_position'] == 'lower']
            
            # Generate heatmap
            self._generate_heatmap(upper_df, lower_df, f"rally_{int(rally_id)}_heatmap.png")
            
            # Generate scatter plot
            self._generate_scatter_plot(upper_df, lower_df, f"rally_{int(rally_id)}_scatter.png")
            
        print("All rally visualizations generated")
            
    def _generate_match_visualizations(self):
        """Generate visualizations for the entire match"""
        if self.df.empty:
            print("No data to visualize")
            return
            
        print("Generating match-wide visualizations...")
        
        # Separate upper and lower court players
        upper_df = self.df[self.df['player_position'] == 'upper']
        lower_df = self.df[self.df['player_position'] == 'lower']
        
        # Generate heatmap
        self._generate_heatmap(upper_df, lower_df, "match_heatmap.png")
        
        # Generate scatter plot
        self._generate_scatter_plot(upper_df, lower_df, "match_scatter.png")
        
        print("Match-wide visualizations generated successfully")
            
    def _generate_heatmap(self, upper_df, lower_df, filename):
        """Generate heatmap"""
        plt.figure(figsize=(10, 16), facecolor='#1a1a1a')  # 设置深色背景
        
        # 在深色背景中创建更好的颜色映射 - 从透明到鲜明的颜色
        upper_cmap = LinearSegmentedColormap.from_list("upper_cmap", [(0, 0, 0, 0), self.upper_color])
        lower_cmap = LinearSegmentedColormap.from_list("lower_cmap", [(0, 0, 0, 0), self.lower_color])
        
        # Create court background
        self._draw_court()
        
        # Draw upper court heatmap if data available
        if not upper_df.empty:
            sns.kdeplot(
                x=upper_df['court_x'],
                y=upper_df['court_y'],
                cmap=upper_cmap,
                fill=True,
                alpha=1,           # 最大不透明度
                levels=12,        # 减少等高线数量，增加对比度
                thresh=0.01,      # 降低阈值，显示更多低密度区域
                bw_adjust=1     # 进一步减小带宽，使峰值更突出
            )
        
        # Draw lower court heatmap if data available
        if not lower_df.empty:
            sns.kdeplot(
                x=lower_df['court_x'],
                y=lower_df['court_y'],
                cmap=lower_cmap,
                fill=True,
                alpha=1,           # 最大不透明度
                levels=12,        # 减少等高线数量，增加对比度
                thresh=0.01,      # 降低阈值，显示更多低密度区域
                bw_adjust=1     # 进一步减小带宽，使峰值更突出
            )
        
        # 添加统计信息
        rally_id = None
        if 'rally_id' in upper_df.columns:
            rally_ids = upper_df['rally_id'].unique()
            if len(rally_ids) == 1 and rally_ids[0] != 0:
                rally_id = int(rally_ids[0])
        
        # 显示单个回合的统计或者整体统计
        if rally_id and rally_id in self.movement_stats:
            self._add_stats_to_plot(rally_id)
        else:
            # 如果是整场比赛数据，显示所有回合的总统计
            self._add_stats_to_plot(None)
        
        # Set plot properties - 适合深色背景的样式
        plt.xlim(0, self.court_width)
        plt.ylim(self.court_length, 0)  # Invert Y axis for correct orientation
        plt.title('Player Position Heatmap', color='white', fontsize=14)
        plt.xlabel('Court Width (meters)', color='white')
        plt.ylabel('Court Length (meters)', color='white')
        plt.tick_params(colors='white')  # 坐标轴刻度标签改为白色
        
        # Save plot
        save_path = os.path.join(self.output_dir, 'heatmaps', filename)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Heatmap saved to: {save_path}")
            
    def _add_stats_to_plot(self, rally_id=None):
        """Add statistics information to the plot
        Args:
            rally_id: Rally ID, if None then display overall statistics for all rallies
        """
        # If no statistics data, return directly
        if not self.movement_stats:
            return
        # 如果提供了rally_id但不存在，则返回
        if rally_id is not None and rally_id not in self.movement_stats:
            return
            
        # 创建信息文本
        if rally_id is not None:
            # 单个回合的统计信息
            stats = self.movement_stats[rally_id]
            info_text = f"Rally {rally_id} Statistics:\n"
            info_text += "---------------\n"
            
            # 上场球员统计
            if 'upper' in stats:
                upper_stats = stats['upper']
                info_text += f"Upper Court Player:\n"
                info_text += f"  Average Speed: {upper_stats['avg_speed']:.2f} m/s\n"
                info_text += f"  Maximum Speed: {upper_stats['max_speed']:.2f} m/s\n"
                info_text += f"  Distance Moved: {upper_stats['total_distance']:.2f} m\n"
            
            # 下场球员统计
            if 'lower' in stats:
                lower_stats = stats['lower']
                info_text += f"\nLower Court Player:\n"
                info_text += f"  Average Speed: {lower_stats['avg_speed']:.2f} m/s\n"
                info_text += f"  Maximum Speed: {lower_stats['max_speed']:.2f} m/s\n"
                info_text += f"  Distance Moved: {lower_stats['total_distance']:.2f} m\n"
        else:
            # 整场比赛的统计信息
            info_text = f"Match Statistics\n"
            info_text += "=================\n"
            
            # 计算所有回合的总统计数据
            upper_distances = []
            upper_speeds = []
            upper_avg_speeds = []
            lower_distances = []
            lower_speeds = []
            lower_avg_speeds = []
            
            for rally_stats in self.movement_stats.values():
                if 'upper' in rally_stats:
                    upper_distances.append(rally_stats['upper']['total_distance'])
                    if rally_stats['upper'].get('max_speed', 0) > 0:
                        upper_speeds.append(rally_stats['upper']['max_speed'])
                    if rally_stats['upper'].get('avg_speed', 0) > 0:
                        upper_avg_speeds.append(rally_stats['upper']['avg_speed'])
                        
                if 'lower' in rally_stats:
                    lower_distances.append(rally_stats['lower']['total_distance'])
                    if rally_stats['lower'].get('max_speed', 0) > 0:
                        lower_speeds.append(rally_stats['lower']['max_speed'])
                    if rally_stats['lower'].get('avg_speed', 0) > 0:
                        lower_avg_speeds.append(rally_stats['lower']['avg_speed'])
            
            # 添加上场球员信息
            info_text += f"Upper Court Player:\n"
            if upper_distances:
                total_distance = sum(upper_distances)
                info_text += f"  Total Distance: {total_distance:.2f} m\n"
                info_text += f"  Average Distance per Rally: {total_distance/len(upper_distances):.2f} m\n"
            if upper_avg_speeds:
                avg_speed = sum(upper_avg_speeds) / len(upper_avg_speeds)
                info_text += f"  Average Speed: {avg_speed:.2f} m/s\n"
            if upper_speeds:
                info_text += f"  Maximum Speed: {max(upper_speeds):.2f} m/s\n"
            
            # 添加下场球员信息
            info_text += f"\nLower Court Player:\n"
            if lower_distances:
                total_distance = sum(lower_distances)
                info_text += f"  Total Distance: {total_distance:.2f} m\n"
                info_text += f"  Average Distance per Rally: {total_distance/len(lower_distances):.2f} m\n"
            if lower_avg_speeds:
                avg_speed = sum(lower_avg_speeds) / len(lower_avg_speeds)
                info_text += f"  Average Speed: {avg_speed:.2f} m/s\n"
            if lower_speeds:
                info_text += f"  Maximum Speed: {max(lower_speeds):.2f} m/s\n"
        
        # 在图表中心右侧添加文本框，适合深色背景
        plt.text(0.98, 0.5, info_text,
                horizontalalignment='right',
                verticalalignment='center',
                transform=plt.gca().transAxes,
                bbox=dict(facecolor='#333333', alpha=0.75, boxstyle='round,pad=0.7', edgecolor='#666666'),
                fontsize=14,  # 进一步增大字体
                family='monospace',
                weight='bold',
                color='#ffffff')  # 白色文本适合深色背景
    
    def _generate_scatter_plot(self, upper_df, lower_df, filename):
        """Generate scatter plot"""
        plt.figure(figsize=(10, 16), facecolor='#1a1a1a')  # 设置深色背景
        
        # Create court background
        self._draw_court()
        
        # Draw scatter plot for upper court
        if not upper_df.empty:
            # Check if rally information is available
            if 'rally_id' in upper_df.columns:
                # Group by rally and plot with different colors
                for rally_id, rally_data in upper_df.groupby('rally_id'):
                    plt.scatter(
                        rally_data['court_x'], 
                        rally_data['court_y'],
                        alpha=0.7,
                        s=30,
                        marker='o',  # circle marker
                        color=self.upper_color,
                        label=f'Upper Court Rally {int(rally_id)}' if rally_id == upper_df['rally_id'].iloc[0] else "_nolegend_"
                    )
            else:
                plt.scatter(
                    upper_df['court_x'], 
                    upper_df['court_y'],
                    alpha=0.7,
                    s=30,
                    marker='o',
                    color=self.upper_color,
                    label='Upper Court Players'
                )
            
        # Draw scatter plot for lower court
        if not lower_df.empty:
            # Check if rally information is available
            if 'rally_id' in lower_df.columns:
                # Group by rally and plot with different colors
                for rally_id, rally_data in lower_df.groupby('rally_id'):
                    plt.scatter(
                        rally_data['court_x'], 
                        rally_data['court_y'],
                        alpha=0.7,
                        s=30,
                        marker='^',  # triangle marker
                        color=self.lower_color,
                        label=f'Lower Court Rally {int(rally_id)}' if rally_id == lower_df['rally_id'].iloc[0] else "_nolegend_"
                    )
            else:
                plt.scatter(
                    lower_df['court_x'], 
                    lower_df['court_y'],
                    alpha=0.7,
                    s=30,
                    marker='^',  # triangle marker
                    color=self.lower_color,
                    label='Lower Court Players'
                )
        
        # 添加统计信息
        rally_id = None
        if 'rally_id' in upper_df.columns:
            rally_ids = upper_df['rally_id'].unique()
            if len(rally_ids) == 1 and rally_ids[0] != 0:
                rally_id = int(rally_ids[0])
        
        # 显示单个回合的统计或者整体统计
        if rally_id and rally_id in self.movement_stats:
            self._add_stats_to_plot(rally_id)
        else:
            # 如果是整场比赛数据，显示所有回合的总统计
            self._add_stats_to_plot(None)
        
        # Set plot properties - 适合深色背景的样式
        plt.xlim(0, self.court_width)
        plt.ylim(self.court_length, 0)  # Invert Y axis for correct orientation
        plt.title('Player Position Scatter Plot', color='white', fontsize=14)
        plt.xlabel('Court Width (meters)', color='white')
        plt.ylabel('Court Length (meters)', color='white')
        plt.tick_params(colors='white')  # 坐标轴刻度标签改为白色
        plt.legend(loc='upper right', facecolor='#333333', edgecolor='#666666', labelcolor='white')
        
        # Save plot
        save_path = os.path.join(self.output_dir, 'scatter_plots', filename)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Scatter plot saved to: {save_path}")
    
    def visualize(self):
        """Execute visualization processing"""
        if self.df.empty:
            print("No data to visualize")
            return False
            
        try:
            # Generate visualizations for each rally
            self._generate_rally_visualizations()
            
            # Generate visualizations for the entire match
            self._generate_match_visualizations()
            
            return True
        except Exception as e:
            print(f"Error during visualization: {e}")
            return False
            
            
def analyze_player_positions(detections_path, output_dir=None, fps=30):
    """
    Analyze player position data and generate visualizations
    
    Args:
        detections_path: Path to detections.jsonl containing player position data
        output_dir: Output directory, defaults to visualizations subdirectory in the detection file's directory
        
    Returns:
        bool: Whether processing was successful
    """
    print(f"\nAnalyzing player position data: {detections_path}")
    
    # Create visualizer
    visualizer = PlayerPositionVisualizer(detections_path, output_dir, fps=fps)
    
    # Execute visualization
    success = visualizer.visualize()
    
    if success:
        print(f"Player position analysis complete, visualizations saved to: {visualizer.output_dir}")
    else:
        print("Player position analysis failed")
        
    return success


# 测试代码：允许直接运行该文件来测试可视化效果
if __name__ == "__main__":
    import sys
    from tkinter import Tk, filedialog
    
    # Use file dialog to select detection file
    print("Please select detections.jsonl file...")
    
    try:
        # Create hidden tkinter root window (for file dialog only)
        root = Tk()
        root.withdraw()
        
        # Set default directory
        default_dir = "results"
        if not os.path.exists(default_dir):
            default_dir = os.getcwd()
        
        # Open file selection dialog
        file_path = filedialog.askopenfilename(
            title="Select Player Position Detection File",
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")],
            initialdir=default_dir
        )
        
        # 如果用户取消选择，则退出
        if not file_path:
            print("No file selected, exiting program")
            sys.exit(0)
            
        # 调用分析函数
        success = analyze_player_positions(file_path)
        
        if success:
            print("\nVisualization test completed successfully")
        else:
            print("\nVisualization test failed")
            
    except Exception as e:
        print(f"\nTest error: {e}")
        
    finally:
        try:
            # 关闭tkinter窗口
            root.destroy()
        except:
            pass
        
