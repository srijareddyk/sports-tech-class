"""Shared helpers: webcam + YOLO pose model + drawing utilities."""
import math

import cv2
import numpy as np
from ultralytics import YOLO

# COCO keypoint indices returned by YOLO pose models
NOSE = 0
L_SHOULDER, R_SHOULDER = 5, 6
L_ELBOW, R_ELBOW = 7, 8
L_WRIST, R_WRIST = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANKLE, R_ANKLE = 15, 16

MIN_CONF = 0.5  # keypoint confidence threshold

FONT = cv2.FONT_HERSHEY_SIMPLEX
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
GREEN, RED, YELLOW = (80, 220, 80), (60, 60, 230), (0, 220, 255)


class PoseTracker:
    """Wraps a YOLO pose model and returns keypoints for the main person in frame."""

    def __init__(self, model="yolo11n-pose.pt"):
        self.model = YOLO(model)  # downloads weights on first run

    def track(self, frame):
        """Returns (keypoints[17x3] as x,y,conf, bbox[x1,y1,x2,y2], annotated_frame) or (None, None, frame)."""
        result = self.model(frame, verbose=False)[0]
        annotated = result.plot(boxes=False)
        if result.keypoints is None or len(result.boxes) == 0:
            return None, None, annotated
        # Pick the largest person (closest to camera)
        boxes = result.boxes.xyxy.cpu().numpy()
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        i = int(np.argmax(areas))
        kpts = result.keypoints.data[i].cpu().numpy()  # (17, 3)
        return kpts, boxes[i], annotated


def visible(kpts, *idx):
    return all(kpts[i][2] >= MIN_CONF for i in idx)


def angle(a, b, c):
    """Angle ABC in degrees, using the x,y of three keypoints."""
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    norm = math.hypot(*ba) * math.hypot(*bc)
    if norm == 0:
        return 180.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / norm))))


def open_camera(index=0):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera {index}. Try --camera 1")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap


def text(img, msg, org, scale=1.0, color=WHITE, thickness=2):
    """Text with a dark outline so it is readable on any background."""
    cv2.putText(img, msg, org, FONT, scale, BLACK, thickness + 4, cv2.LINE_AA)
    cv2.putText(img, msg, org, FONT, scale, color, thickness, cv2.LINE_AA)


def center_text(img, msg, y, scale=1.5, color=WHITE, thickness=3):
    (w, _), _ = cv2.getTextSize(msg, FONT, scale, thickness)
    text(img, msg, ((img.shape[1] - w) // 2, y), scale, color, thickness)
