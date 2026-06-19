import cv2
import numpy as np


class CourtMapper:
    def __init__(self, image_court_corners, court_dimensions=(6.1, 13.4)):
        """
        Initialize CourtMapper with court corners and dimensions
        Args:
            image_court_corners: List of 4 points [(x1,y1), ...] representing court corners in image
            court_dimensions: Tuple of (width, height) in meters, default badminton court size
        """
        self.image_court_corners = np.array(image_court_corners, dtype=np.float32)
        self.court_dimensions = court_dimensions
        # Adjust court_points to set origin at bottom-left corner
        court_points = np.array([
            [0, 0], [court_dimensions[0], 0],
            [court_dimensions[0], court_dimensions[1]], [0, court_dimensions[1]]
        ], dtype=np.float32)
        self.matrix = cv2.getPerspectiveTransform(self.image_court_corners, court_points)
        self.inv_matrix = cv2.getPerspectiveTransform(court_points, self.image_court_corners)

        self.compute_court_overlay()

    def image_to_court(self, point):
        """
        Transform image coordinates to court coordinates (meters)
        Args:
            point: (x,y) coordinates in image space
        Returns:
            Transformed (x,y) coordinates in court space
        """
        if not isinstance(point, (list, tuple, np.ndarray)) or not point:
            return []
        point = np.array(point, dtype=np.float32).reshape(-1, 1, 2)
        transformed_points = cv2.perspectiveTransform(point, self.matrix)
        return np.round(transformed_points[0][0], 2)

    def court_to_image(self, points):
        """
        Transform court coordinates (meters) to image coordinates
        Args:
            points: (x,y) coordinates in court space
        Returns:
            Transformed (x,y) coordinates in image space
        """
        if not isinstance(points, (list, tuple, np.ndarray)) or len(np.array(points).flatten()) == 0:
            return []

        points = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
        transformed_points = cv2.perspectiveTransform(points, self.inv_matrix)
        return np.round(transformed_points[0][0], 2)

    def compute_court_overlay(self):
        thirds = [2.033, 4.066]
        self.vertical_lines = []
        for x in thirds:
            top = np.array([x, 0])
            bottom = np.array([x, 13.4])
            top_image = self.court_to_image(top)
            bottom_image = self.court_to_image(bottom)
            self.vertical_lines.append((top_image, bottom_image))

        ninths = np.linspace(0, 13.4, 11)
        self.horizontal_lines = []
        for y in ninths:
            left = np.array([0, y])
            right = np.array([6.1, y])
            left_image = self.court_to_image(left)
            right_image = self.court_to_image(right)
            self.horizontal_lines.append((left_image, right_image))

        left_mid = np.array([0, 6.7])
        right_mid = np.array([6.1, 6.7])
        left_mid_image = self.court_to_image(left_mid)
        right_mid_image = self.court_to_image(right_mid)
        self.mid_height = int((left_mid_image[1] + right_mid_image[1]) / 2)

    def draw_court_overlay(self, image):
        overlay = image.copy()
        cv2.polylines(overlay, [self.image_court_corners.astype(int)], True, (0, 255, 0), 2)

        for line in self.vertical_lines:
            cv2.line(overlay, tuple(line[0].astype(int)), tuple(line[1].astype(int)), (0, 255, 0), 1)

        for line in self.horizontal_lines:
            cv2.line(overlay, tuple(line[0].astype(int)), tuple(line[1].astype(int)), (0, 255, 0), 1)

        return overlay, self.mid_height


def compute_expanded_roi(court_corners, image_shape):
    """
    Build a player-detection ROI from the four court corners.
    The ROI keeps horizontal padding modest and expands more vertically,
    then clamps to the image bounds.
    """
    height, width = image_shape[:2]
    points = np.array(court_corners, dtype=np.int32)
    min_x = int(np.min(points[:, 0]))
    max_x = int(np.max(points[:, 0]))
    min_y = int(np.min(points[:, 1]))
    max_y = int(np.max(points[:, 1]))

    court_width = max_x - min_x
    pad_x = max(12, int(court_width * 0.08))

    x1 = max(0, min_x - pad_x)
    y1 = 0
    x2 = min(width - 1, max_x + pad_x)
    y2 = height - 1
    return [(x1, y1), (x2, y2)]


def annotate_court(image):
    """
    Interactive tool to annotate court corners on an image.
    Returns court corners plus an automatically expanded ROI.
    """
    if not isinstance(image, np.ndarray):
        print("Error: Invalid image input")
        return None, None, None

    original_height, original_width = image.shape[:2]
    fixed_size = (1080, 720)
    base_image = cv2.resize(image, fixed_size)

    corners = []
    mid_height = [680]
    window_name = "Court annotation"
    guide_lines = [
        "Click 4 court corners in order: 1 top-left, 2 top-right, 3 bottom-right, 4 bottom-left",
        "Use the actual court boundary lines. ROI is generated automatically. Press ESC to cancel.",
    ]

    print("请按顺序点击球场 4 个角点：左上、右上、右下、左下。")
    print("窗口图片顶部会显示点击顺序；ROI 会自动生成，不需要手动标注。")

    def draw_guidance(canvas, extra_line=None):
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (fixed_size[0], 92), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.58, canvas, 0.42, 0, canvas)

        y = 28
        for line in guide_lines:
            cv2.putText(canvas, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)
            y += 28
        if extra_line:
            cv2.putText(canvas, extra_line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (80, 220, 255), 2, cv2.LINE_AA)

    def render_annotation_view(extra_line=None):
        view = base_image.copy()
        draw_guidance(view, extra_line)
        for idx, point in enumerate(corners, start=1):
            cv2.circle(view, point, 5, (0, 0, 255), -1)
            cv2.putText(view, str(idx), (point[0] + 8, point[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2, cv2.LINE_AA)
        if len(corners) > 1:
            cv2.polylines(view, [np.array(corners, dtype=np.int32)], False, (0, 255, 255), 2)
        return view

    def show_auto_roi():
        court_mapper = CourtMapper(corners)
        overlay, mid_height_int = court_mapper.draw_court_overlay(render_annotation_view("Done. Green = court, blue = pose ROI."))
        mid_height[0] = mid_height_int
        roi_corners = compute_expanded_roi(corners, overlay.shape)
        cv2.rectangle(overlay, roi_corners[0], roi_corners[1], (255, 0, 0), 3)
        cv2.putText(
            overlay,
            "Auto ROI: pose detection area",
            (roi_corners[0][0], max(116, roi_corners[0][1] - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 0, 0),
            2,
            cv2.LINE_AA,
        )
        cv2.imshow(window_name, overlay)
        print("已自动生成 ROI（球员姿态检测范围），无须手动选择。")

    def mouse_callback(event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN or len(corners) >= 4:
            return

        corners.append((x, y))
        if len(corners) == 4:
            show_auto_roi()
            cv2.setMouseCallback(window_name, lambda *args: None)
        else:
            cv2.imshow(window_name, render_annotation_view(f"Next point: {len(corners) + 1}"))

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)
    cv2.imshow(window_name, render_annotation_view("Next point: 1"))

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or len(corners) == 4:
            break

    cv2.destroyAllWindows()

    if len(corners) != 4:
        print("未完成球场范围标注，请重试。")
        return None, None, None

    roi_corners = compute_expanded_roi(corners, base_image.shape)
    scale_x = original_width / fixed_size[0]
    scale_y = original_height / fixed_size[1]

    original_corners = [(int(x * scale_x), int(y * scale_y)) for x, y in corners]
    original_roi_corners = [(int(x * scale_x), int(y * scale_y)) for x, y in roi_corners]
    original_mid_height = int(mid_height[0] * scale_y)
    return original_corners, original_roi_corners, original_mid_height

if __name__ == "__main__":
    image_path = r'images/Weixin Screenshot_00001.png'
    corners = [(426, 385), (861, 382), (996, 667), (288, 668)]
    court_mapper = CourtMapper(corners)
    centroids = [(1400, 1000), (700, 600), (800, 980)]
    image = cv2.imread(image_path)
    image, mid = court_mapper.draw_court_overlay(image)
    cv2.imshow("image", image)
    cv2.waitKey()
    for centroid in centroids:
        mapped_positions = court_mapper.image_to_court(centroid)


