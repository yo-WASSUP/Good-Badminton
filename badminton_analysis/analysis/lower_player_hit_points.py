import csv
from typing import Dict, Tuple, List
import numpy as np
import cv2
from ..court.mapper import CourtMapper
import openpyxl
import os
from PIL import Image
import logging
from PIL import ImageDraw, ImageFont
import time
logger = logging.getLogger(__name__)

class ShuttlecockAnalyzer:
    def __init__(self, detect_csv_path, video_path, roi_corners, corners, player_1_hand, player_2_hand, player_region, max_distance: int = 180):
        self.file_path = detect_csv_path
        self.video_path = video_path
        self.image_save_path = os.path.join(os.path.dirname(self.file_path), "hit_points")
        os.makedirs(self.image_save_path, exist_ok=True)
        self.max_distance = max_distance
        self.min_y = roi_corners[0][1] - 100
        self.roi_corners = roi_corners
        self.player_1_hand = player_1_hand
        self.player_2_hand = player_2_hand
        self.player_region = player_region
        self.court_mapper = CourtMapper(corners)
        self.video_fps = 30
        self.last_end_frame = None

        print("start analyzing")

    def extract_shuttlecock_coordinates(self):
        coordinates_list = []
        current_dict = {}
        last_frame = None

        with open(self.file_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header row
            for row in reader:
                frame = int(row[0])
                ball_x = int(row[11])
                ball_y = int(row[12])
                upper_court_x = float(row[3])
                upper_court_y = float(row[4])
                lower_court_x = float(row[8])
                lower_court_y = float(row[9])
                if self.player_1_hand == 'right':
                    upper_hand_x = float(row[15])
                    upper_hand_y = float(row[16])
                else:
                    upper_hand_x = float(row[13])
                    upper_hand_y = float(row[14])
                if self.player_2_hand == 'right':
                    lower_hand_x = float(row[19])
                    lower_hand_y = float(row[20])
                else:
                    lower_hand_x = float(row[17])
                    lower_hand_y = float(row[18])
                detect_frame_count = int(row[21])
                if last_frame is not None and frame - last_frame > 100:
                    # 将比赛分段获取
                    if len(current_dict) > 150:
                        coordinates_list.append(current_dict)
                    current_dict = {}

                current_dict[frame] = (ball_x, ball_y, upper_court_x, upper_court_y, lower_court_x, lower_court_y,
                                       upper_hand_x, upper_hand_y, lower_hand_x, lower_hand_y, detect_frame_count)
                last_frame = frame

        # 将最后一个字典保存
        if len(current_dict) > 150:
            coordinates_list.append(current_dict)

        return coordinates_list

    @staticmethod
    def distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        return np.linalg.norm(np.array(p1) - np.array(p2))

    def filter_coordinates(self, coordinates):
        """
        过滤并清理羽毛球轨迹坐标数据
        
        Args:
            coordinates (dict): 包含帧索引和坐标的字典
                              格式: {frame_idx: (x, y, ...), ...}
        
        Returns:
            dict: 过滤后的坐标字典
            
        过滤规则:
        1. 移除续重复的坐标点
        """
        if not coordinates:
            return {}
        try:
            # 定义零坐标，但最后一个元素为保持不变      
            ZERO_COORD = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            def is_valid_position(pos):
                return pos[:2] != (0, 0)
                
            def get_valid_position(positions, index, direction):
                """获取有效的前/后帧位置"""
                pos = positions[index + direction]
                if not is_valid_position(pos):
                    pos = positions[index + 2*direction]
                return pos
            
            avg_distances = {}
            first_index = list(coordinates.keys())[0]
            filtered_data = coordinates.copy()
            
            for index in range(2, len(coordinates) - 2):
                i = index + first_index
                current_pos = coordinates[i]
                
                # 过滤连续重复帧
                if current_pos[:2] == coordinates[i + 1][:2]:
                    filtered_data[i] = ZERO_COORD
                    continue
            
                # 获前后帧位置
                prev_pos = get_valid_position(coordinates, i, -1)
                next_pos = get_valid_position(coordinates, i, 1)
                
                # 距离过滤 暂时没用上
                if all(is_valid_position(pos) for pos in [current_pos, prev_pos, next_pos]):
                    avg_dist = (self.distance(current_pos[:2], next_pos[:2]) +
                               self.distance(current_pos[:2], prev_pos[:2])) / 2
                    avg_distances[i] = avg_dist
            return filtered_data
        except Exception as e:
            logger.error(f"Error filtering coordinates: {e}")
            return coordinates  # 返回原始数据作为fallback

    # 找击球点
    def find_potential_hits(self, filtered_data):
        potential_hits = []
        coordinates = list(filtered_data.items())
        # 找先向下后向上的帧
        for i in range(2, len(coordinates) - 2):
            frame, pos = coordinates[i]
            pre_frame, prev_pos = coordinates[i - 1]
            if prev_pos[:2] == (0, 0):
                pre_frame, prev_pos = coordinates[i - 2]
            fore_frame, fore_pos = coordinates[i + 1]
            if fore_pos[:2] == (0, 0):
                fore_frame, fore_pos = coordinates[i + 2]
            # 过滤掉无效的点
            if pos[:2] == (0, 0) or pos[:2] == prev_pos[:2] or pos[:2] == fore_pos[:2]:
                continue
            if (pos[1] > fore_pos[1] and pos[1] > prev_pos[1] and prev_pos[1] != 0 and fore_pos[1] != 0):
                potential_hits.append((frame, pos))

        # 每15帧保留一个最低点
        filtered_hits = []
        i = 0
        while i < len(potential_hits):
            current_hit = potential_hits[i]
            j = i + 1
            while j < len(potential_hits) and potential_hits[j][0] - current_hit[0] <= 15:
                if potential_hits[j][1][1] > current_hit[1][1]:
                    current_hit = potential_hits[j]
                j += 1
            filtered_hits.append(current_hit)
            i = j

        # 把击球点分为前后两个人
        upper_potential_hits = []
        for hit in filtered_hits:
            # 如果运动员的手在有效区域内，且球离上方运动员的手更近，则认为是上方击球点
            if hit[1][6:8] != self.roi_corners[0] and hit[1][8:10] != self.roi_corners[0] \
                    and self.distance(hit[1][:2], hit[1][6:8]) < self.distance(hit[1][:2], hit[1][8:10]):
                upper_potential_hits.append(hit)
        lower_filtered_hits_set = set(filtered_hits)
        upper_potential_hits_set = set(upper_potential_hits)

        lower_filtered_hits_final = list(lower_filtered_hits_set - upper_potential_hits_set)
        lower_filtered_hits_final = sorted(lower_filtered_hits_final)

        return lower_filtered_hits_final

 
    def extract_and_create_video(self, video_path, frame1, frame2, output_path, timestamp):
        print(f"Extracting video from {frame1} to {frame2}")
        start_time = time.time()
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print("Error: Could not open video file")
            return
                
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # Prepare font parameters once
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        font_thickness = 2
        text_size = cv2.getTextSize(timestamp, font, font_scale, font_thickness)[0]
        text_y = text_size[1]

        for frame_idx in range(frame1, frame2 + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue

            # Add timestamp
            cv2.rectangle(frame, (width // 2 - text_size[0] // 2 - 10, height - text_y - 10), (width // 2 + text_size[0] // 2 + 10, height), (0, 0, 0), -1)
            cv2.putText(frame, timestamp, (width // 2 - text_size[0] // 2, height + 2), font, font_scale, (255, 255, 255), font_thickness)
            # Write frame
            out.write(frame)

        cap.release()
        out.release()
        
        print(f"Video saved to: {output_path} ({time.time() - start_time:.2f}s)")

    def find_missed_hits(self, filtered_data, lower_hits):
        """
        补充查找可能漏掉的击球点，每隔2秒插入一个有效点
        
        Returns:
            Tuple[List, List]: 返回两个列表 (original_hits, supplementary_hits)
        """
        if not filtered_data:
            return lower_hits, []
        
        coordinates = list(filtered_data.items())
        supplementary_hits = []  # 新增的补充击球点列表
        
        # 获取回合的起始和结束帧
        start_frame = coordinates[0][0]
        end_frame = coordinates[-1][0]
        
        # 将帧数转换为秒数
        max_interval_seconds = 2  # 最大间隔2秒
        insert_interval_seconds = 2  # 每隔2秒插入一个点
        
        # 转换为帧数
        max_interval_frames = max_interval_seconds * self.video_fps
        insert_interval_frames = insert_interval_seconds * self.video_fps
        
        def find_valid_frame(target_frame, search_range=15):
            """在目标帧附近找到最近的有效帧"""
            for offset in range(search_range + 1):
                # 先检查目标帧后面的帧
                forward_frame = target_frame + offset
                if forward_frame in filtered_data and filtered_data[forward_frame][:2] != (0, 0):
                    return forward_frame, filtered_data[forward_frame]
                
                # 再检查目标帧前面的帧
                backward_frame = target_frame - offset
                if backward_frame in filtered_data and filtered_data[backward_frame][:2] != (0, 0):
                    return backward_frame, filtered_data[backward_frame]
            return None
        
        # 检查回合开始到第一个击球点的间隔
        if lower_hits and (lower_hits[0][0] - start_frame) > max_interval_frames:
            interval = lower_hits[0][0] - start_frame
            num_inserts = int(interval // insert_interval_frames)
            
            for j in range(num_inserts):
                insert_frame = start_frame + (j + 1) * insert_interval_frames
                valid_frame = find_valid_frame(insert_frame)
                if valid_frame:
                    supplementary_hits.append(valid_frame)
        
        # 检查相邻击球点之间的间隔
        for i in range(1, len(lower_hits)):
            current_frame = lower_hits[i][0]
            prev_frame = lower_hits[i-1][0]
            interval = current_frame - prev_frame
            
            if interval > max_interval_frames:
                num_inserts = int((interval - max_interval_frames) // insert_interval_frames)
                
                for j in range(num_inserts):
                    insert_frame = prev_frame + (j + 1) * insert_interval_frames
                    valid_frame = find_valid_frame(insert_frame)
                    if valid_frame:
                        supplementary_hits.append(valid_frame)
        
        # 检查最后一个击球点到回合结束的间隔
        if lower_hits and (end_frame - lower_hits[-1][0]) > max_interval_frames:
            interval = end_frame - lower_hits[-1][0]
            num_inserts = int(interval // insert_interval_frames)
            
            for j in range(num_inserts):
                insert_frame = lower_hits[-1][0] + (j + 1) * insert_interval_frames
                if insert_frame >= end_frame:
                    break
                valid_frame = find_valid_frame(insert_frame)
                if valid_frame:
                    supplementary_hits.append(valid_frame)
        
        # 排序并去重
        supplementary_hits = list(set(supplementary_hits))
        supplementary_hits.sort(key=lambda x: x[0])
        
        return lower_hits, supplementary_hits

    def data_statistics(self, lower_hits, supplementary_hits, round_index):
        # 合并所有击球点并按帧数排序
        all_hits = lower_hits + supplementary_hits
        all_hits.sort(key=lambda x: x[0])  # 按帧数排序
        
        for hit_index, hit in enumerate(all_hits):
            hit_index += 1
            if self.player_region == 'lower':
                detect_frame_count_1 = hit[1][-1]-10
                detect_frame_count_2 = detect_frame_count_1 + 2*self.video_fps
            else:
                detect_frame_count_1 = hit[1][-1]+self.video_fps
                detect_frame_count_2 = detect_frame_count_1 + 2*self.video_fps
            
            # 修改：如果存在上一个结束帧，调整当前起始帧
            if self.last_end_frame is not None:
                detect_frame_count_1 = self.last_end_frame + 1  # 紧接上一个片段
                detect_frame_count_2 = detect_frame_count_1 + 2*self.video_fps

            frame_count = hit[0]
            time_count = frame_count / self.video_fps
            timestamp = f"{int(time_count // 3600):02d}:{int((time_count % 3600) // 60):02d}:{int(time_count % 60):02d}.{int((time_count % 1) * 100):02d}"
            
            # 判断是否为补充击球点
            is_supplementary = hit in supplementary_hits
            # 在文件名末尾添加标记
            filename = f"{round_index}_{hit_index}_{frame_count}"
            if is_supplementary:
                filename += "_supp"
            filename += ".mp4"
            output_path = os.path.join(self.image_save_path, filename)
            
            self.extract_and_create_video(
                video_path=self.video_path, 
                frame1=detect_frame_count_1, 
                frame2=detect_frame_count_2, 
                output_path=output_path, 
                timestamp=timestamp
            )

            # 更新最后的结束帧
            self.last_end_frame = detect_frame_count_2

    def analyze(self):
        coordinates_list = self.extract_shuttlecock_coordinates()
        for round_index, coordinates in enumerate(coordinates_list): 
            round_index += 1
            filtered_data = self.filter_coordinates(coordinates)
            lower_hits = self.find_potential_hits(filtered_data)
            print(f'第{round_index}回合:')
            print(f'回合起始帧: {list(filtered_data.keys())[0]}')
            print(f'回合结束帧: {list(filtered_data.keys())[-1]}')
            print('原始击球点:', [hit[0] for hit in lower_hits])
            
            # 补充查找可能漏掉的击球点
            original_hits, supplementary_hits = self.find_missed_hits(filtered_data, lower_hits)
            print('补充击球点:', [hit[0] for hit in supplementary_hits])
            print('------------------------')

            self.data_statistics(original_hits, supplementary_hits, round_index)

        self.last_end_frame = None  # 重置每次分析开始时的最后结束帧

# Example usage
if __name__ == "__main__":
    # 定义基础路径和视频名称
    base_path = 'results'
    # video_name = 'youtube3_clip1'  # 只需修改这个变量
    video_name = 'youtube1_clip1'  # 只需修改这个变量
    player_region = 'lower'
   
    # 构建完整路径
    result_folder = f'{base_path}/{video_name}'
    file_path = f'{result_folder}/detect_{video_name}.csv'
    video_path = f'{result_folder}/detect_{video_name}.mp4'
    court_annotation_path = f'{result_folder}/court_annotations.txt'

    # 读取场地标注数据
    with open(court_annotation_path, 'r') as file:
        data = file.read().replace('\n', '')
    corners, roi_corners = map(eval, [
        data.split('corners=')[1].split(']')[0] + ']', 
        data.split('roi_corners=')[1].split(']')[0] + ']'
    ])

    analyzer = ShuttlecockAnalyzer(detect_csv_path=file_path, video_path=video_path, roi_corners=roi_corners, corners=corners, player_1_hand='right', player_2_hand='right', player_region=player_region)
    analyzer.analyze()
