import os
import cv2
import sys
import numpy as np
from rtmlib import Body, draw_skeleton

class RTMPoseProcessor:
    """RTMPose pose detection processor"""
    
    def __init__(self, mode='balanced', backend='onnxruntime', device='auto', pose_family='rtmpose'):
        self.show_skeleton = True
        self.conf_threshold = 0.5
        self.pose_family = pose_family
        self.inference_name = "RTMO" if pose_family == "rtmo" else "RTMPose"
        try:
            import onnxruntime as ort
            ort.set_default_logger_severity(3)
        except Exception:
            pass
        # 设备自动检测：优先使用 CUDA（若可用）
        if device in (None, 'auto'):
            selected = 'cpu'
            try:
                import torch  # noqa: F401
                # noinspection PyUnresolvedReferences
                if torch.cuda.is_available():
                    selected = 'cuda'
            except Exception:
                selected = 'cpu'
            self.device = selected
        else:
            self.device = device
        self.backend = backend
        
        # Initialize RTMPose model
        self.init_rtmpose(mode)
        
        self.keypoint_mapping = self.get_keypoint_mapping()
    
    def get_models_dir(self):
        """Get model file directory, compatible with development and packaged environments"""
        if getattr(sys, 'frozen', False):
            # Packaged environment, model files are in temp directory
            base_path = sys._MEIPASS
            models_dir = os.path.join(base_path, 'weights')
        else:
            # Development environment, model files are in project directory
            models_dir = './weights'
        
        return models_dir
    
    def init_rtmpose(self, mode='balanced'):
        """Initialize RTMPose model"""
        try:
            print(f"Initializing pose model (family: {self.pose_family}, mode: {mode}, backend: {self.backend}, device: {self.device})")
            if self.pose_family == 'rtmo':
                self.wholebody = Body(
                    pose='rtmo',
                    mode=mode,
                    backend=self.backend,
                    device=self.device
                )
                print("RTMO model initialization successful")
                return
            
            # Check if local model files exist
            models_dir = self.get_models_dir()
            if os.path.exists(models_dir):
                # Try to use local models
                det_model = os.path.join(models_dir, 'yolox_nano_8xb8-300e_humanart-40f6f0d0.onnx')
                
                # Select different pose detection models based on mode
                if mode == 'lightweight':
                    pose_model = os.path.join(models_dir, 'rtmpose-t_simcc-body7_pt-body7_420e-256x192-026a1439_20230504.onnx')
                    pose_input_size = (192, 256)
                elif mode == 'performance':
                    pose_model = os.path.join(models_dir, 'rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.onnx')
                    pose_input_size = (192, 256)
                else:  # balanced
                    pose_model = os.path.join(models_dir, 'rtmpose-s_simcc-body7_pt-body7_420e-256x192-acd4a1ef_20230504.onnx')
                    pose_input_size = (192, 256)
                
                if os.path.exists(det_model) and os.path.exists(pose_model):
                    print(f"Using local model files ({mode} mode)")
                    self.wholebody = Body(
                        det=det_model,
                        det_input_size=(416, 416),
                        pose=pose_model,
                        pose_input_size=pose_input_size,
                        backend=self.backend,
                        device=self.device
                    )
                    print("RTMPose local model initialization successful")
                    return
                else:
                    print("Local model files incomplete, using online download")
            else:
                print("models directory doesn't exist, using online download")
            
            # Use online download
            self.wholebody = Body(
                mode=mode,
                backend=self.backend,
                device=self.device
            )
            print("RTMPose online model initialization successful")
            
        except Exception as e:
            print(f"RTMPose initialization failed on device {self.device}: {e}")
            self.wholebody = None
            # 尝试回退到 CPU
            if self.device != 'cpu':
                try:
                    print("Falling back to CPU for RTMPose...")
                    self.device = 'cpu'
                    # Retry initialization on CPU
                    print(f"Initializing pose model (family: {self.pose_family}, mode: {mode}, backend: {self.backend}, device: {self.device})")
                    if self.pose_family == 'rtmo':
                        self.wholebody = Body(
                            pose='rtmo',
                            mode=mode,
                            backend=self.backend,
                            device=self.device
                        )
                        print("RTMO CPU model initialization successful")
                        return
                    models_dir = self.get_models_dir()
                    if os.path.exists(models_dir):
                        det_model = os.path.join(models_dir, 'yolox_nano_8xb8-300e_humanart-40f6f0d0.onnx')
                        if mode == 'lightweight':
                            pose_model = os.path.join(models_dir, 'rtmpose-t_simcc-body7_pt-body7_420e-256x192-026a1439_20230504.onnx')
                            pose_input_size = (192, 256)
                        elif mode == 'performance':
                            pose_model = os.path.join(models_dir, 'rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.onnx')
                            pose_input_size = (192, 256)
                        else:
                            pose_model = os.path.join(models_dir, 'rtmpose-s_simcc-body7_pt-body7_420e-256x192-acd4a1ef_20230504.onnx')
                            pose_input_size = (192, 256)
                        if os.path.exists(det_model) and os.path.exists(pose_model):
                            self.wholebody = Body(
                                det=det_model,
                                det_input_size=(416, 416),
                                pose=pose_model,
                                pose_input_size=pose_input_size,
                                backend=self.backend,
                                device=self.device
                            )
                            print("RTMPose CPU model initialization successful")
                            return
                    # Fallback to online as last resort
                    self.wholebody = Body(
                        mode=mode,
                        backend=self.backend,
                        device=self.device
                    )
                    print("RTMPose CPU online model initialization successful")
                except Exception as e2:
                    print(f"RTMPose CPU fallback also failed: {e2}")

    def get_keypoint_mapping(self):
        """Get keypoint mapping (COCO 17 keypoint format)"""
        # RTMPose and YOLO both use COCO 17 keypoint format, same order
        # 0: nose, 1: left_eye, 2: right_eye, 3: left_ear, 4: right_ear
        # 5: left_shoulder, 6: right_shoulder, 7: left_elbow, 8: right_elbow
        # 9: left_wrist, 10: right_wrist, 11: left_hip, 12: right_hip
        # 13: left_knee, 14: right_knee, 15: left_ankle, 16: right_ankle
        return list(range(17))  # 1:1 mapping
    
    def update_model(self, mode='balanced'):
        """Update model"""
        print(f"Updating RTMPose model to mode: {mode}")
        self.init_rtmpose(mode)
        print(f"RTMPose processor updated to mode: {mode}")
    
    def process_frame(self, frame):
        """Process single frame for pose detection.
        Returns:
            keypoints: None or numpy.ndarray with shape (N, 17, 2) for N persons
            scores:    None or numpy.ndarray with shape (N, 17)
        """
        if self.wholebody is None:
            return None, None

        # Size check, resize if frame is too large
        h, w = frame.shape[:2]
        # RTMPose is suitable for higher resolution, but limit for performance
        if w > 640 or h > 640:
            scale = min(640 / w, 640 / h)
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
            scale_factor = scale
        else:
            scale_factor = 1.0

        keypoints_all = None
        scores_all = None

        try:
            # Use RTMPose for pose detection
            detected_keypoints, scores = self.wholebody(frame)

            # Normalize to numpy arrays with consistent shapes
            if detected_keypoints is not None and len(detected_keypoints) > 0:
                kp = np.asarray(detected_keypoints)
                # If single person (17,2), expand to (1,17,2)
                if kp.ndim == 2 and kp.shape[0] >= 17 and kp.shape[1] >= 2:
                    kp = kp[None, ...]

                # Scale back to original size if resized
                if scale_factor != 1.0:
                    kp = kp / scale_factor

                # Handle scores
                if scores is not None:
                    sc = np.asarray(scores)
                    if sc.ndim == 1 and sc.shape[0] >= 17:
                        sc = sc[None, ...]
                else:
                    sc = None

                # Filter low-confidence keypoints per person
                if sc is not None and sc.shape[0] == kp.shape[0]:
                    mask = sc > self.conf_threshold  # shape (N,17)
                    # Broadcast to (N,17,2): where low confidence -> set to 0
                    kp = np.where(mask[..., None], kp, 0)

                keypoints_all = kp
                scores_all = sc

        except Exception as e:
            print(f"RTMPose processing failed: {e}")

        return keypoints_all, scores_all
    
    def set_skeleton_visibility(self, show):
        """Set skeleton display state"""
        self.show_skeleton = show
        print(f"RTMPose skeleton display: {'On' if show else 'Off'}")

