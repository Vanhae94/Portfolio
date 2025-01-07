import datetime
import cv2
from ultralytics import YOLO

# 현재 시간 가져오기
def get_current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# YOLOv8 모델 로드
def load_yolov8_model(model_path="yolov8n.pt"):
    return YOLO(model_path)

# 실시간 yolo 및 박싱
def generate_webcam_data(frame):
    # YOLOv8 모델 로드
    model = load_yolov8_model()

    # YOLOv8 탐지 수행
    results = model.predict(source=frame, save=False, verbose=False)
    detections = results[0].boxes.data.cpu().numpy()

    # 검출된 객체에 대해 박싱
    for detection in detections:
        x1, y1, x2, y2, conf, cls = detection
        if int(cls) == 0 and conf >= 0.5:  # 사람 클래스 (ID: 0) 및 신뢰도 조건
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
            label = f"Person: {conf:.2f}"
            cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    return frame