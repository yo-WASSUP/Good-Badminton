import cv2
import time
import numpy as np

try:
    import torch
except Exception:
    torch = None


class ShuttlecockTracker:
    """Detect the shuttlecock, maintain trajectory points, and draw them."""

    def __init__(self, yolo_ball_model, trajectory_length=30, show_trajectory=True, show_performance_stats=False):
        self.yolo_ball_model = yolo_ball_model
        self.trajectory_length = trajectory_length
        self.show_trajectory = show_trajectory
        self.show_performance_stats = show_performance_stats
        self.shuttlecock_trajectory = []

        if torch is not None and hasattr(torch, 'cuda') and torch.cuda.is_available():
            self.ultra_device = 0
        else:
            self.ultra_device = 'cpu'

    def detect_ball(self, frame, conf=0.2):
        t0 = time.time()
        try:
            ball_results = self.yolo_ball_model(frame, conf=conf, device=self.ultra_device, verbose=False)[0]
        except TypeError:
            ball_results = self.yolo_ball_model(frame, conf=conf, verbose=False)[0]

        if self.show_performance_stats:
            print(f"YOLO shuttlecock inference took {time.time() - t0:.2f} sec")

        if ball_results.boxes.xywh.shape[0] < 1:
            return [0, 0]

        return ball_results.boxes.xywh[0][:2].cpu().int().tolist()

    def update_trajectory(self, ball_position, roi_corners=None):
        if ball_position == [0, 0]:
            return

        # The ball detector runs on the full frame. Keep only the x-range around
        # the court so obvious side detections do not pollute the trajectory.
        if roi_corners is not None:
            if not (roi_corners[0][0] < ball_position[0] < roi_corners[1][0]):
                return

        self.shuttlecock_trajectory.append(tuple(ball_position))

        if len(self.shuttlecock_trajectory) > self.trajectory_length:
            self.shuttlecock_trajectory.pop(0)

    def draw_trajectory(self, frame):
        if not self.shuttlecock_trajectory:
            return

        t0 = time.time()
        color = (87, 108, 255)

        for i, point in enumerate(self.shuttlecock_trajectory):
            radius = int(3 + (i / len(self.shuttlecock_trajectory)) * 4)
            cv2.circle(frame, point, radius, color, thickness=-1)

        latest_point = self.shuttlecock_trajectory[-1]
        cv2.circle(frame, latest_point, 6, (0, 165, 255), thickness=-1)

        if self.show_performance_stats:
            print(f"Drawing shuttlecock trajectory took {time.time() - t0:.2f} sec")

    def handle_visualization(self, frame):
        if self.show_trajectory and self.shuttlecock_trajectory:
            self.draw_trajectory(frame)

    def clear_trajectory(self):
        self.shuttlecock_trajectory = []

    def get_trajectory(self):
        return self.shuttlecock_trajectory