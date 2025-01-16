import datetime
import cv2
import requests
from ultralytics import YOLO
from app import db
from app.models import DetectionLog, AbnormalBehaviorLog
import os
from datetime import datetime
from pytz import timezone
import time


# 현재 시간 가져오기
def get_current_time():
    return datetime.datetime.now(timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')

def load_yolov8_model_1(model_path="yolo_models/yolov8n.pt"):
    return YOLO(model_path)

def load_yolov8_model_2(model_path="yolo_models/bestyolo.pt"):
    return YOLO(model_path)

def load_yolov8_model_3(model_path="yolo_models/dummy.pt"):
    return YOLO(model_path)

models = {
    'object': None,
    'density': None,
    'behavior': None
}

def load_model(model_type):
    try:
        if model_type == 'object' and models['object'] is None:
            models['object'] = load_yolov8_model_1()  
        elif model_type == 'density' and models['density'] is None:
            models['density'] = load_yolov8_model_2()  
        elif model_type == 'behavior' and models['behavior'] is None:
            models['behavior'] = load_yolov8_model_3()  
        elif model_type not in ['object', 'density', 'behavior']:
            raise ValueError("Unknown model type")
        return models[model_type]
    except Exception as e:
        raise Exception(f"Model loading failed: {str(e)}")

# 실시간 yolo 및 박싱
def generate_webcam_data(frame, model):
    results = model.predict(source=frame, save=False, verbose=False)
    detections = results[0].boxes.data.cpu().numpy()

    object_count = 0

    for detection in detections:
        x1, y1, x2, y2, conf, cls = detection
        if conf >= 0.5:
            object_count += 1
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
            label = f"ID {int(cls)}: {conf:.2f}"
            cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    density = object_count
    return frame, density

            
def get_latest_frame(cctv_id):
    device_index = int(cctv_id.replace('CCTV', '')) - 1
    cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)  # DirectShow 백엔드 사용
    if not cap.isOpened():
        raise ValueError(f"Unable to open device {device_index}")

    for _ in range(3):  # 최대 3회 재시도
        ret, frame = cap.read()
        if ret:
            cap.release()
            return frame

    cap.release()
    raise ValueError("Failed to capture frame after multiple attempts.")

def calculate_density(frame, model):
    """
    YOLO 모델로 밀집도를 계산합니다.
    :param frame: 현재 프레임
    :param model: YOLO 모델 객체
    :return: 밀집도 값
    """
    results = model.predict(frame)  # YOLO 모델 추론
    try:
        detections = results[0].boxes.data.cpu().numpy()  # YOLOv8 박스 데이터 추출
    except AttributeError:
        raise ValueError("Unexpected results format from YOLO model. Check the model's predict method output.") 

    # 사람 클래스(class_id = 0)만 필터링
    person_count = sum(1 for *_, class_id in detections if int(class_id) == 0)
    frame_area = frame.shape[0] * frame.shape[1]  # 프레임 면적
    density = person_count / frame_area  # 단순한 밀집도 계산 (개수/면적)

    return density
        
def generate_frames(model, model_type, device_index, thresholds, cctv_id):
    video_capture = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
    max_retries = 5  # 최대 재시도 횟수
    retry_interval = 1  # 재시도 간 대기 시간 (초)
    
    while True:
        retries = 0
        success, frame = video_capture.read()

        # 프레임을 성공적으로 읽지 못하면 재시도
        while not success and retries < max_retries:
            print(f"Failed to read frame, retrying... ({retries + 1}/{max_retries})")
            time.sleep(retry_interval)  # 일정 시간 대기
            success, frame = video_capture.read()
            retries += 1
        
        if not success:
            # 프레임 읽기 실패 시, 스트리밍을 종료합니다.
            print("Unable to read frame. Stopping streaming.")
            break

        # YOLO 탐지 수행 및 프레임 처리
        frame, density = generate_webcam_data(frame, model)

        # 디버깅용 로그
        print(f"Processing with model_type: {model_type}, Density: {density}")

        # 모델 타입이 'density'로 설정된 경우
        if model_type == "density":
            # 밀도 기반 자동 캡처 트리거
            for level, threshold in thresholds.items():
                if density > threshold:
                    trigger_capture(cctv_id, frame, density, level, model_type)

        # 모델 타입이 'behavior'로 설정된 경우
        elif model_type == "behavior":
            if density > 0:
                trigger_capture(cctv_id, frame, density=None, level=None, model_type=model_type)

        # 프레임 전송
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    video_capture.release()

def trigger_capture(cctv_id, frame, density=None, level=None, model_type=None):
    base_dir = os.getcwd()
    save_dir = os.path.join(base_dir, "app", "static", "images", "cctv_capture", model_type or "unknown")
    os.makedirs(save_dir, exist_ok=True)

    timestamp = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d_%H%M%S")
    file_name = f"{cctv_id}_{timestamp}.jpg"
    save_path = os.path.join(save_dir, file_name)

    print(f"저장 경로: {save_path}")

    try:
        result = cv2.imwrite(save_path, frame)
        if result:
            print(f"자동 캡처 성공: {save_path}")

            # 로그 저장
            if model_type == "density" and density is not None and level is not None:
                save_detection_log(cctv_id, density, level, save_path)
            elif model_type == "behavior":
                save_abnormalBehavior_log(cctv_id, save_path)
            else:
                print(f"모델 타입 '{model_type}'이(가) 유효하지 않거나 필요한 파라미터가 없습니다.")
        else:
            print(f"자동 캡처 실패: {save_path}")
    except Exception as e:
        print(f"자동 캡처 실패: {save_path}, 에러: {str(e)}")

def save_detection_log(cctv_id, density, level, save_path):
    try:
        detection_log = DetectionLog(
            detection_time=datetime.now(timezone('Asia/Seoul')),  # 올바른 시간대 설정
            cctv_id=cctv_id,
            density_level=str(level),
            object_count=density,
            image_url=save_path
        )
        db.session.add(detection_log)
        db.session.commit()
        print(f"DetectionLog에 저장됨: {save_path}")
    except Exception as e:
        print(f"DetectionLog 저장 실패: {str(e)}")

def save_abnormalBehavior_log(cctv_id, save_path):
    try:
        abnormalBehavior_log = AbnormalBehaviorLog(
            detection_time=datetime.now(timezone('Asia/Seoul')),  # 올바른 시간대 설정
            cctv_id=cctv_id,
            image_url=save_path,
            fall_status="쓰러짐"
        )
        db.session.add(abnormalBehavior_log)
        db.session.commit()
        print(f"AbnormalBehaviorLog에 저장됨: {save_path}")
    except Exception as e:
        print(f"AbnormalBehaviorLog 저장 실패: {str(e)}")
