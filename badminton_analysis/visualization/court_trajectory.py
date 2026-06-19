import cv2
import numpy as np
from collections import deque
import matplotlib.pyplot as plt
from matplotlib import cm

class CourtTrajectoryVisualizer:
    def __init__(self, width=200, height=400):
        """
        初始化球场轨迹可视化器
        Args:
            width: 初始小球场图像宽度（将根据视频帧尺寸动态调整）
            height: 初始小球场图像高度（将根据视频帧尺寸动态调整）
        """
        self.default_width = width
        self.default_height = height
        self.width = width
        self.height = height
        
        # 创建初始小型球场图像（将在draw_overlay中根据视频尺寸重新创建）
        self.court_overlay = self._create_court_overlay(self.width, self.height)
        
        # 球场标准尺寸（米）
        self.doubles_width = 6.10  # 双打场地宽度
        self.court_length = 13.40  # 场地长度
        
        # 每回合数据存储
        self.rally_positions = {
            'upper': [],  # 每个元素是一个回合的位置集合
            'lower': []
        }
        self.current_rally = {
            'upper': [],  # 当前回合的位置集合
            'lower': []
        }
        self.current_rally_id = 0  # 当前回合ID
    
    def _create_court_overlay(self, width, height):
        """
        创建小型球场图像
        Args:
            width: 小球场图像宽度
            height: 小球场图像高度
        """
        # 创建透明图像
        court = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 标准羽毛球场地尺寸（米）
        doubles_width = 6.10  # 双打场地宽度
        court_length = 13.40  # 场地长度
        single_width = 0.46   # 单打线距离双打线的距离
        service_line = 1.98   # 发球线到网的距离
        back_service = 0.76   # 后发球线到底线的距离
        line_width = 0.1     # 标准界线宽度
        center_line_width = 0.1  # 中线宽度
        
        # 计算缩放比例
        scale_x = (width - 20) / doubles_width
        scale_y = (height - 20) / court_length
        scale = min(scale_x, scale_y)
        
        # 计算偏移量使球场居中
        offset_x = int((width - doubles_width * scale) / 2)
        offset_y = int((height - court_length * scale) / 2)
        
        # 绘制球场线
        def scale_point(x, y):
            return (int(x * scale + offset_x), int(y * scale + offset_y))
        
        # 计算线宽（像素）
        line_width_px = max(1, int(line_width * scale))
        center_line_width_px = max(1, int(center_line_width * scale))
        
        # 绘制外框
        cv2.rectangle(court, 
                     scale_point(0, 0), 
                     scale_point(doubles_width, court_length), 
                     (70, 62, 63), line_width_px)

        # 绘制单打线
        cv2.line(court,
                scale_point(single_width, 0),
                scale_point(single_width, court_length),
                (70, 62, 63), line_width_px)
        cv2.line(court,
                scale_point(doubles_width - single_width, 0),
                scale_point(doubles_width - single_width, court_length),
                (70, 62, 63), line_width_px)
        
        # 绘制中线
        cv2.line(court,
                scale_point(doubles_width/2, 0),
                scale_point(doubles_width/2, court_length/2-service_line),
                (70, 62, 63), center_line_width_px)
        cv2.line(court,
                scale_point(doubles_width/2, court_length/2+service_line),
                scale_point(doubles_width/2, court_length),
                (70, 62, 63), center_line_width_px)
        
        # 绘制网线（虚线）
        net_y = int(court_length/2 * scale + offset_y)
        dash_length = 4  # 虚线长度（像素）
        for x in range(0, width, dash_length * 2):
            start_x = x
            end_x = min(x + dash_length, width)
            cv2.line(court, (start_x, net_y), (end_x, net_y), (70, 62, 63), line_width_px)
        
        # 绘制发球线
        # 前发球线
        cv2.line(court,
                scale_point(0, court_length/2-service_line),
                scale_point(doubles_width, court_length/2-service_line),
                (70, 62, 63), line_width_px)
        cv2.line(court,
                scale_point(0, court_length/2+service_line),
                scale_point(doubles_width, court_length/2+service_line),
                (70, 62, 63), line_width_px)
        
        # 后发球线
        cv2.line(court,
                scale_point(0, back_service),
                scale_point(doubles_width, back_service),
                (70, 62, 63), line_width_px)
        cv2.line(court,
                scale_point(0, court_length-back_service),
                scale_point(doubles_width, court_length-back_service),
                (70, 62, 63), line_width_px)
        
        return court

    def draw_overlay(self, frame, court_history):
        """
        在视频帧上绘制球场和球员轨迹
        Args:
            frame: 视频帧
            court_history: 包含'upper'和'lower'键的字典，值为球员在球场坐标系中的历史位置列表
        """
        try:
            # 获取视频帧尺寸计算缩放因子
            frame_height, frame_width = frame.shape[:2]
            # 计算缩放因子，基于1920x1080的参考分辨率
            scale_factor = min(frame_width / 1920.0, frame_height / 1080.0) * 1.5  # 增加系数使轨迹更明显
            
            # 根据视频尺寸计算小球场大小
            court_overlay_width = int(self.default_width * scale_factor)
            court_overlay_height = int(self.default_height * scale_factor)
            
            # 如果尺寸发生了变化，重新创建球场图像
            if court_overlay_width != self.width or court_overlay_height != self.height:
                self.width = court_overlay_width
                self.height = court_overlay_height
                self.court_overlay = self._create_court_overlay(self.width, self.height)
            
            # 创建球场图像副本
            overlay = self.court_overlay.copy()
            
            # 获取小球场的实际绘制区域（排除边距）
            height, width = overlay.shape[:2]
            margin = max(5, int(10 * scale_factor))  # 调整边距
            court_width = width - margin*2  
            court_height = height - margin*2
            
            # 计算偏移量
            offset_x = margin
            offset_y = margin
            
            # 标准羽毛球场地尺寸（米）
            doubles_width = 6.10  # 双打场地宽度
            court_length = 13.40  # 场地长度
            
            # 绘制球员轨迹（合并上下方球员的逻辑）
            for position, color in [('upper', (0, 255, 255)), ('lower', (255, 0, 255))]:
                if position in court_history:
                    history = court_history[position]
                    # 将deque转换为列表以便处理
                    history_list = list(history)
                    
                    for i, pos in enumerate(history_list):
                        if pos is not None and len(pos) >= 2:
                            # 将球场坐标归一化，然后转换为小球场坐标
                            x_norm = pos[0] / doubles_width
                            y_norm = pos[1] / court_length
                            
                            x = int(x_norm * court_width + offset_x)
                            y = int(y_norm * court_height + offset_y)
                            
                            if 0 <= x < width and 0 <= y < height:
                                # 计算半径，越新的点半径越大，根据视频尺寸缩放
                                radius_min = max(2, int(2 * scale_factor))
                                radius_max = max(3, int(5 * scale_factor))
                                radius = int(radius_min + (i / len(history_list)) * (radius_max - radius_min)) if len(history_list) > 1 else radius_min
                                cv2.circle(overlay, (x, y), radius, color, -1)  # upper:黄青色, lower:品红色
                
            # 将球场叠加到视频帧的右上角
            h, w = overlay.shape[:2]
            # 计算放置位置，根据视频尺寸缩放边距
            padding = max(10, int(20 * scale_factor))
            # 确保ROI区域在frame的有效范围内
            if frame.shape[0] >= padding+h and frame.shape[1] >= padding+w:
                roi = frame[padding:padding+h, frame.shape[1]-w-padding:frame.shape[1]-padding]
                if roi.shape == overlay.shape:
                    # 应用半透明效果
                    cv2.addWeighted(overlay, 0.7, roi, 0.3, 0, roi)
                    frame[padding:padding+h, frame.shape[1]-w-padding:frame.shape[1]-padding] = roi
                
        except Exception as e:
            print(f"绘制球场轨迹出错: {e}")
            
        return frame

if __name__ == '__main__':
    # 创建可视化器实例
    visualizer = CourtTrajectoryVisualizer(width=200, height=400)
    
    # 获取球场图像
    court = visualizer._create_court_overlay()
    
    # 显示图像
    cv2.imshow('Court Overlay', court)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # 保存图像
    cv2.imwrite('court_overlay.png', court)