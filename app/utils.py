import datetime
import cv2
import requests
from ultralytics import YOLO
from app.models import Setting
from flask import current_app
from app import db
from app.models import DetectionLog
import os

# 현재 시간 가져오기
def get_current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# YOLOv8 모델 로드 /객체
def load_yolov8_model_1(model_path="yolo_models/yolov8n.pt"):
    return YOLO(model_path)

# YOLOv8 모델 로드 / 밀집도
def load_yolov8_model_2(model_path="yolo_models/bestyolo.pt"):
    return YOLO(model_path)

# YOLOv8 모델 로드 / 이상행동
def load_yolov8_model_3(model_path="yolo_models/dummy.pt"):
    return YOLO(model_path)


# 실시간 yolo 및 박싱
def generate_webcam_data(frame,model):

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

#과밀도
def calculate_overcrowding_level(density):
    settings = Setting.query.order_by(Setting.level).all()
    if not settings:
        current_app.logger.warning("No settings found. Using default thresholds.")
        default_levels = [(1, 0.5), (2, 0.8), (3, 1.0)]  # 기본값
        settings = [Setting(level=level, max_density=max_density) for level, max_density in default_levels]

    for setting in settings:
        if density <= setting.max_density:
            return f"Level {setting.level}"
    return "Overcrowded"


#자동캡쳐
def trigger_capture(cctv_id, density, threshold):
    if density > threshold:
        capture_url = f"http://127.0.0.1:5000/save-capture"
        try:
            response = requests.post(capture_url, json={"cctv_id": cctv_id})
            if response.status_code == 200:
                print(f"자동 캡처 성공 for CCTV {cctv_id}")
            else:
                print(f"자동 캡처 실패: {response.text}")
        except Exception as e:
            print(f"캡처 요청 중 오류 발생: {str(e)}")
            
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

def annotate_frame_with_density(frame, density):
    color = (0, 0, 255) if density > 0.5 else (0, 255, 0)
    cv2.putText(
        frame,
        f"Density: {density:.2f}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        2
    )
    return frame

def save_frame_capture(frame, cctv_id, density, overcrowding_level, object_count):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{cctv_id}_{timestamp}.jpg"
    save_path = os.path.join('static', 'captures', filename)

    # 폴더가 없으면 생성
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    try:
        cv2.imwrite(save_path, frame)
        current_app.logger.info(f"Captured frame saved at {save_path}")
    except Exception as e:
        current_app.logger.error(f"Error saving captured frame: {str(e)}")
        return


    # DetectionLog에 정보 저장
    try:
        new_log = DetectionLog(
            cctv_id=cctv_id,
            density_level=f"{density:.2f}",
            overcrowding_level=overcrowding_level,
            object_count=object_count,
            image_url=save_path
        )
        db.session.add(new_log)
        db.session.commit()
        current_app.logger.info(f"DetectionLog added: {new_log}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving DetectionLog: {str(e)}")