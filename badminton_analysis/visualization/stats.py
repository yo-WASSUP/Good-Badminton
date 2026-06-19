import cv2
import numpy as np
import os
from PIL import Image, ImageDraw, ImageFont

class StatsVisualizer:
    """
    统计信息可视化器，负责绘制文本和球员统计信息面板
    """
    
    def __init__(self, frame_width, frame_height, language='zh'):
        """
        初始化统计信息可视化器
        
        参数:
            frame_width: 视频帧宽度
            frame_height: 视频帧高度
            language: 语言设置 ('zh' 或 'en')
        """
        self.language = language
        self.frame_width = frame_width
        self.frame_height = frame_height
        
        # 计算缩放因子，基于1920x1080的参考分辨率
        self.scale_factor = 2 * min(self.frame_width / 1920.0, self.frame_height / 1080.0)
        # 缩放字体和尺寸
        self.font_scale = max(0.4, 0.5 * self.scale_factor)
        self.thickness = max(1, int(1 * self.scale_factor))
        self.line_height = max(15, int(20 * self.scale_factor))
        self.panel_width = max(180, int(180 * self.scale_factor))
        self.panel_height = max(150, int(200 * self.scale_factor))
        self.margin = max(5, int(10 * self.scale_factor))
        
        # 背景设置
        self.background_color = (0, 0, 0)
        self.background_alpha = 0.5
        self.font_path = self._find_chinese_font()
        self._font_cache = {}
        
        # 语言文本配置
        self.texts = {
            'zh': {
                'rally': '回合',
                'upper_player': '上场球员',
                'lower_player': '下场球员',
                'stats': '统计',
                'current_speed': '当前速度',
                'current_rally': '当前回合',
                'match_total': '比赛总计',
                'distance': '移动距离',
                'avg_speed': '平均速度',
                'max_speed': '最大速度',
                'total_distance': '总距离',
                'unit_speed': '米/秒',
                'unit_distance': '米'
            },
            'en': {
                'rally': 'Rally',
                'upper_player': 'Upper Player',
                'lower_player': 'Lower Player',
                'stats': 'Stats',
                'current_speed': 'Current Speed',
                'current_rally': 'Current Rally',
                'match_total': 'Match Total',
                'distance': 'Distance',
                'avg_speed': 'Avg Speed',
                'max_speed': 'Max Speed',
                'total_distance': 'Total Distance',
                'unit_speed': 'm/s',
                'unit_distance': 'm'
            }
        }

    def _find_chinese_font(self):
        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/simkai.ttf",
            "C:/Windows/Fonts/msyh.ttc",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
        return None

    def _get_font(self, font_scale):
        font_size = max(8, int(font_scale * 30))
        if font_size not in self._font_cache:
            self._font_cache[font_size] = ImageFont.truetype(self.font_path, font_size)
        return self._font_cache[font_size]

    def _draw_text_batch(self, frame, text_items):
        if not text_items:
            return
        if self.language == 'en' or self.font_path is None:
            for text, position, font_scale, color, thickness in text_items:
                cv2.putText(
                    frame,
                    text,
                    position,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    color,
                    thickness,
                    cv2.LINE_AA,
                )
            return

        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        for text, position, font_scale, color, _thickness in text_items:
            draw.text(position, text, font=self._get_font(font_scale), fill=(color[2], color[1], color[0]))
        frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    def add_text(self, frame, text, position, font_scale, color, thickness):
        """
        向图像添加文本（支持中英文）
        
        参数:
            frame: 视频帧
            text: 要添加的文本
            position: 文本位置 (x, y)
            font_scale: 字体大小缩放因子
            color: 文本颜色 (B, G, R)
            thickness: 文本粗细
        """
        if self.language == 'en':
            # 英文使用OpenCV默认字体
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(frame, text, position, font, font_scale, color, thickness, cv2.LINE_AA)
        else:
            if self.font_path is None:
                # 如果找不到中文字体，使用OpenCV英文显示作为后备
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(frame, text, position, font, font_scale, color, thickness, cv2.LINE_AA)
                return
            
            # 创建PIL图像以绘制文本
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            font = self._get_font(font_scale)
            draw.text(position, text, font=font, fill=(color[2], color[1], color[0]))
            
            # 将PIL图像转回OpenCV格式并替换原始帧
            frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    def draw_player_stats(self, frame, movement_stats, rally_count):
        """
        在画面上显示球员统计信息，包括当前回合和整场比赛数据
        
        参数:
            frame: 视频帧
            movement_stats: 球员统计信息
            rally_count: 当前回合数
        """
        # 计算回合数显示位置，基于视频尺寸
        rally_pos_y = int(self.panel_height + self.frame_height * 0.1) # 第一个面板下方
              
        # 使用语言配置显示回合数
        text_items = []
        rally_text = f"{self.texts[self.language]['rally']}: {rally_count}"
        text_items.append((rally_text, (self.margin, rally_pos_y), self.font_scale*1.5, (0, 165, 255), self.thickness+2))
        
        # 绘制上半场球员统计
        self._draw_player_panel(frame, self.texts[self.language]['upper_player'], movement_stats.get('upper', {}), 
                               self.margin, int(self.frame_height * 0.05), self.panel_width, self.panel_height, 
                               (0, 255, 255), self.font_scale, self.thickness, self.line_height, 
                               self.background_color, self.background_alpha, text_items)
        
        # 绘制下半场球员统计
        self._draw_player_panel(frame, self.texts[self.language]['lower_player'], movement_stats.get('lower', {}), 
                               self.margin, int(self.frame_height * 0.55), 
                               self.panel_width, self.panel_height, (255, 0, 255), self.font_scale, self.thickness, 
                               self.line_height, self.background_color, self.background_alpha, text_items)
        self._draw_text_batch(frame, text_items)
    
    def _draw_player_panel(self, frame, player_name, stats, x_pos, y_pos, panel_width, panel_height, 
                          color, font_scale, thickness, line_height, bg_color, bg_alpha, text_items=None):
        """
        绘制单个球员信息面板
        
        参数:
            frame: 视频帧
            player_name: 球员名称
            stats: 球员统计信息
            x_pos, y_pos: 面板位置
            panel_width, panel_height: 面板尺寸
            color: 球员颜色
            font_scale, thickness, line_height: 字体参数
            bg_color, bg_alpha: 背景颜色和透明度
        """
        margin = max(5, int(panel_width * 0.05))
        
        # 绘制面板背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (x_pos-margin, y_pos-margin), 
                     (x_pos+panel_width+margin, y_pos+panel_height+margin), 
                     bg_color, -1)
        cv2.addWeighted(overlay, bg_alpha, frame, 1 - bg_alpha, 0, frame)
        
        # 球员标题
        title_text = f"{player_name} {self.texts[self.language]['stats']}:"
        self._queue_or_draw_text(frame, text_items, title_text, (x_pos, y_pos), font_scale*1.1, color, thickness+1)
        
        # 当前速度
        current_speed_text = f"{self.texts[self.language]['current_speed']}: {stats.get('current_speed', 0):.2f} {self.texts[self.language]['unit_speed']}"
        self._queue_or_draw_text(frame, text_items, current_speed_text, (x_pos, y_pos + line_height), font_scale, (255, 255, 255), thickness)
        
        # 当前回合统计
        y_rally = y_pos + 2*line_height
        rally_title = f"{self.texts[self.language]['current_rally']}:"
        self._queue_or_draw_text(frame, text_items, rally_title, (x_pos, y_rally), font_scale, (255, 255, 255), thickness)
        
        distance_text = f" {self.texts[self.language]['distance']}: {stats.get('rally_distance', 0):.2f} {self.texts[self.language]['unit_distance']}"
        self._queue_or_draw_text(frame, text_items, distance_text, (x_pos, y_rally + line_height), font_scale, (255, 255, 255), thickness)
        
        avg_speed_text = f" {self.texts[self.language]['avg_speed']}: {stats.get('rally_avg_speed', 0):.2f} {self.texts[self.language]['unit_speed']}"
        self._queue_or_draw_text(frame, text_items, avg_speed_text, (x_pos, y_rally + 2*line_height), font_scale, (255, 255, 255), thickness)
        
        max_speed_text = f" {self.texts[self.language]['max_speed']}: {stats.get('rally_max_speed', 0):.2f} {self.texts[self.language]['unit_speed']}"
        self._queue_or_draw_text(frame, text_items, max_speed_text, (x_pos, y_rally + 3*line_height), font_scale, (255, 255, 255), thickness)
        
        # 整场比赛统计
        y_match = y_rally + 4*line_height
        match_title = f"{self.texts[self.language]['match_total']}:"
        self._queue_or_draw_text(frame, text_items, match_title, (x_pos, y_match), font_scale, (255, 255, 255), thickness)
        
        total_distance_text = f" {self.texts[self.language]['total_distance']}: {stats.get('match_distance', 0):.2f} {self.texts[self.language]['unit_distance']}"
        self._queue_or_draw_text(frame, text_items, total_distance_text, (x_pos, y_match + line_height), font_scale, (255, 255, 255), thickness)
        
        match_avg_speed_text = f" {self.texts[self.language]['avg_speed']}: {stats.get('match_avg_speed', 0):.2f} {self.texts[self.language]['unit_speed']}"
        self._queue_or_draw_text(frame, text_items, match_avg_speed_text, (x_pos, y_match + 2*line_height), font_scale, (255, 255, 255), thickness)
        
        match_max_speed_text = f" {self.texts[self.language]['max_speed']}: {stats.get('match_max_speed', 0):.2f} {self.texts[self.language]['unit_speed']}"
        self._queue_or_draw_text(frame, text_items, match_max_speed_text, (x_pos, y_match + 3*line_height), font_scale, (255, 255, 255), thickness)

    def _queue_or_draw_text(self, frame, text_items, text, position, font_scale, color, thickness):
        if text_items is None:
            self.add_text(frame, text, position, font_scale, color, thickness)
        else:
            text_items.append((text, position, font_scale, color, thickness))
