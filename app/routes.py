from flask import Blueprint, render_template, session, redirect, url_for, request, flash, Response, current_app
from app import db, bcrypt
from app.models import User, CCTV, DetectionLog, AbnormalBehaviorLog
from .utils import load_yolov8_model
import cv2
import logging

main = Blueprint('main', __name__)

@main.before_request
def require_login():
    # 로그인 상태를 확인하여 보호된 페이지 접근 제어
    if not session.get('logged_in') and request.endpoint not in ['main.login', 'main.authenticate', 'main.signup']:
        return redirect(url_for('main.login'))

@main.route('/')
def index():
    try:
        # 디버그 및 정보 로그
        current_app.logger.debug('Index route accessed')
        current_app.logger.info('Fetching CCTV data')

        # 데이터베이스에서 CCTV 데이터를 가져오기
        cctvs = CCTV.query.all()
        cctv_list = [cctv.to_dict() for cctv in cctvs] 

        current_app.logger.info(f'{len(cctv_list)} CCTV entries fetched')

        # 템플릿 렌더링
        return render_template('cctv.html', cctvs=cctv_list)

    except Exception as e:
        # 오류 발생 시 로그 기록
        current_app.logger.error('An error occurred while fetching CCTV data', exc_info=True)
        current_app.logger.critical(f'Critical error: {e}', exc_info=True)
        return f"An error occurred: {str(e)}", 500

@main.route('/video_feed/<int:camera_index>')
def video_feed(camera_index):
    def generate_frames():
        model = load_yolov8_model()
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise RuntimeError("웹캠을 열 수 없습니다.")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # YOLOv8로 탐지 및 박싱
            results = model.predict(source=frame, save=False, verbose=False)
            detections = results[0].boxes.data.cpu().numpy()

            for detection in detections:
                x1, y1, x2, y2, conf, cls = detection
                if int(cls) == 0 and conf >= 0.5:
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
                    label = f"Person: {conf:.2f}"
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # 프레임을 JPEG로 인코딩하여 스트리밍
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        cap.release()

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@main.route('/login')
def login():
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.clear()  # 세션 초기화
    flash("로그아웃되었습니다.")
    return redirect(url_for('main.login'))

@main.route('/authenticate', methods=['POST'])
def authenticate():
    userid = request.form.get('userid')
    password = request.form.get('password')

    # 데이터베이스에서 사용자 조회
    user = User.query.filter_by(userid=userid).first()

    if user and bcrypt.check_password_hash(user.password, password):
        # role이 'pending'인 경우 로그인 차단
        if user.role == 'pending':
            flash("계정 승인이 완료되지 않았습니다. 관리자에게 문의하세요.")
            return redirect(url_for('main.login'))
        
        # 로그인 성공 시 세션 설정
        session['logged_in'] = True
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_role'] = user.role
        flash(f"환영합니다, {user.name}님!")
        return redirect(url_for('main.index'))
    else:
        # 로그인 실패 처리
        flash("아이디 또는 비밀번호가 잘못되었습니다.")
        return redirect(url_for('main.login'))

@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        userid = request.form.get('userid')
        password = request.form.get('password')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')

        # 비밀번호 해싱
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # 사용자 생성 및 저장
        new_user = User(userid=userid, password=hashed_password, name=name, email=email, phone=phone, role='pending')
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("회원가입이 성공적으로 완료되었습니다.")
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            flash("회원가입 중 오류가 발생했습니다. 다시 시도해주세요.")
            return redirect(url_for('main.signup'))

    return render_template('signup.html')

# CCTV 목록 페이지
@main.route('/cctv-list')
def cctv_list():
    cctvs = CCTV.query.all()
    return render_template('cctv_list.html', cctvs=cctvs)

# CCTV 등록 페이지
@main.route('/cctv-register', methods=['GET', 'POST'])
def cctv_register():
    if request.method == 'POST':
        cctv_id = request.form.get('cctv_id')
        location = request.form.get('location')

        # 중복 확인
        existing_cctv = CCTV.query.filter_by(cctv_id=cctv_id).first()
        if existing_cctv:
            flash("이미 사용 중인 CCTV ID입니다.")
            return redirect(url_for('main.cctv_register'))

        # 새로운 CCTV 객체 생성
        new_cctv = CCTV(
            cctv_id=cctv_id,
            location=location,
        )

        try:
            db.session.add(new_cctv)
            db.session.commit()
            flash("CCTV가 성공적으로 등록되었습니다.")
        except Exception as e:
            db.session.rollback()
            flash(f"CCTV 등록 중 오류가 발생했습니다: {e}")

        return redirect(url_for('main.cctv_list'))

    # 자동 생성할 cctv_id 계산
    last_cctv = CCTV.query.order_by(CCTV.id.desc()).first()
    next_cctv_id = f"CCTV{int(last_cctv.cctv_id.replace('CCTV', '')) + 1}" if last_cctv else "CCTV1"

    return render_template('cctv_register.html', next_cctv_id=next_cctv_id)


# 사용자 관리 페이지
@main.route('/user-management', methods=['GET', 'POST'])
def user_management():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('role')
        user = User.query.get(user_id)

        if user:
            user.role = new_role
            try:
                db.session.commit()
                flash(f"{user.name}의 역할이 '{new_role}'로 변경되었습니다.")
            except Exception as e:
                db.session.rollback()
                flash("역할 변경 중 오류가 발생했습니다.")
        return redirect(url_for('main.user_management'))

    # 사용자 목록 표시
    users = User.query.all()
    return render_template('user_management.html', users=users)

# 사용자 삭제
@main.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        try:
            db.session.delete(user)
            db.session.commit()
            flash(f"{user.name}가 삭제되었습니다.")
        except Exception as e:
            db.session.rollback()
            flash("사용자 삭제 중 오류가 발생했습니다.")
    return redirect(url_for('main.user_management'))

@main.route('/detection-logs')
def detection_logs():
    # 객체 탐지 로그와 관련된 CCTV 정보를 가져옵니다.
    logs = DetectionLog.query.join(CCTV).add_columns(
        DetectionLog.id,
        DetectionLog.detection_time,
        CCTV.location,
        DetectionLog.image_url
    ).all()
    return render_template('detection_logs.html', logs=logs)

@main.route('/add-detection-log', methods=['POST'])
def add_detection_log():
    cctv_id = request.form.get('cctv_id')
    image_url = request.form.get('image_url')

    new_log = DetectionLog(cctv_id=cctv_id, image_url=image_url)
    try:
        db.session.add(new_log)
        db.session.commit()
        return redirect(url_for('main.detection_logs'))
    except Exception as e:
        db.session.rollback()
        return str(e), 500

@main.route('/abnormal-behavior')
def abnormal_behavior():
    """
    이상행동 감지 데이터를 조회하고 템플릿으로 렌더링합니다.
    """
    # 데이터베이스에서 이상행동 감지 데이터 조회
    logs = AbnormalBehaviorLog.query.join(CCTV).add_columns(
        AbnormalBehaviorLog.id,
        AbnormalBehaviorLog.detection_time,
        CCTV.location,
        AbnormalBehaviorLog.image_url,
        AbnormalBehaviorLog.fall_status
    ).all()

    # 템플릿 렌더링
    return render_template('abnormal_behavior.html', logs=logs)    

@main.route('/warning')
def density_stats():
    # 밀집도 통계 데이터 조회
    logs = DetectionLog.query.join(CCTV).add_columns(
        DetectionLog.id,
        DetectionLog.detection_time,
        CCTV.location,
        DetectionLog.density_level,
        DetectionLog.overcrowding_level,
        DetectionLog.object_count,
        DetectionLog.image_url
    ).all()
    return render_template('warning.html', logs=logs)
