class YOLOPoseProcessor:
    """Ultralytics YOLO pose processor with COCO 17 keypoint output."""

    def __init__(self, model_path="yolo11n-pose.pt", device="auto", conf=0.25):
        from ultralytics import YOLO

        self.model_path = model_path
        self.conf = conf
        self.inference_name = "YOLO-Pose"
        if device in (None, "auto"):
            selected = "cpu"
            try:
                import torch
                if torch.cuda.is_available():
                    selected = 0
            except Exception:
                selected = "cpu"
            self.device = selected
        else:
            self.device = device

        print(f"Initializing YOLO pose model (model: {self.model_path}, device: {self.device})")
        self.model = YOLO(self.model_path)

    def process_frame(self, frame):
        result = self.model(frame, conf=self.conf, device=self.device, verbose=False)[0]
        if result.keypoints is None or result.keypoints.xy is None:
            return None, None

        keypoints = result.keypoints.xy
        scores = result.keypoints.conf
        if keypoints.shape[0] == 0:
            return None, None

        keypoints = keypoints.detach().cpu().numpy()
        scores = scores.detach().cpu().numpy() if scores is not None else None
        return keypoints, scores
