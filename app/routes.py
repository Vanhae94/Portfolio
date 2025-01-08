from flask import Blueprint, render_template, session, redirect, url_for, request, flash, Response, current_app, jsonify
from app import db, bcrypt
from app.models import User, CCTV, DetectionLog, AbnormalBehaviorLog
from .utils import generate_webcam_data
from datetime import datetime
import cv2
import os
import re

main = Blueprint('main', __name__)

@main.before_request
def require_login():
    # 로그인 상태를 확인하여 보호된 페이지 접근 제어
    if not session.get('logged_in') and request.endpoint not in ['main.login', 'main.authenticate', 'main.signup']:
        return redirect(url_for('main.login'))

@main.route('/')
def index():
    try:
        # CCTV 데이터를 데이터베이스에서 가져오기
        cctvs = CCTV.query.all()
        cctv_ids = [cctv.cctv_id for cctv in cctvs]
        
        # home.html 렌더링 시 CCTV ID 데이터 전달
        return render_template('home.html', cctv_ids=cctv_ids)
    
    except Exception as e:
        # 오류 발생 시 로그 기록 및 사용자에게 메시지 표시
        current_app.logger.error(f"Error fetching CCTV data: {e}", exc_info=True)
        return f"An error occurred while fetching CCTV data: {e}", 500

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

#cctv 삭제 기능
@main.route('/delete-cctv/<int:cctv_id>', methods=['POST'])
def delete_cctv(cctv_id):
    cctv = CCTV.query.get(cctv_id)
    if cctv:
        try:
            db.session.delete(cctv)
            db.session.commit()
            flash(f"{cctv.location} (ID: {cctv.cctv_id})이 삭제되었습니다.")
        except Exception as e:
            db.session.rollback()
            flash("CCTV 삭제 중 오류가 발생했습니다.")
    else:
        flash("존재하지 않는 CCTV입니다.")
    return redirect(url_for('main.cctv_list'))


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

@main.route('/capture/<cctv_id>', methods=['POST'])
def capture_cctv(cctv_id):
    try:
        # cctv_id에서 숫자를 추출하고 -1 계산
        try:
            webcam_index = int(''.join(filter(str.isdigit, cctv_id))) - 1
        except ValueError:
            raise ValueError(f"유효하지 않은 CCTV ID: {cctv_id}")

        # 데이터베이스에서 CCTV 위치 조회
        cctv = CCTV.query.filter_by(cctv_id=cctv_id).first()
        if not cctv:
            raise ValueError(f"CCTV ID {cctv_id}에 해당하는 데이터가 없습니다.")
        
        location = cctv.location.replace(" ", "_")  # 공백 제거 및 파일명 안전화

        # 해당 웹캠 인덱스로 비디오 스트림 열기
        cap = cv2.VideoCapture(webcam_index)
        if not cap.isOpened():
            raise RuntimeError(f"CCTV {cctv_id}에 접근할 수 없습니다. (웹캠 인덱스: {webcam_index})")

        # 프레임 읽기
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError(f"CCTV {cctv_id}의 프레임을 읽을 수 없습니다.")
        
        # 캡쳐 파일 저장 경로 생성
        timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M')
        file_name = f"{location}_{timestamp}.jpg"
        file_path = os.path.join(current_app.root_path, 'static/images/cctv_capture', file_name)
        
        # 디렉토리 생성 (없을 경우)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 이미지 저장
        cv2.imwrite(file_path, frame)
        cap.release()

        # 성공 응답
        return jsonify({"success": True, "file_path": file_name})
    except Exception as e:
        current_app.logger.error(f"CCTV 캡쳐 중 오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

#마지막 접근 라우트
@main.route('/update-last-access/<cctv_id>', methods=['POST'])
def update_last_access(cctv_id):
    # CCTV 모델에서 해당 ID 검색
    cctv = CCTV.query.filter_by(cctv_id=cctv_id).first()
    if not cctv:
        return jsonify({"error": f"CCTV ID '{cctv_id}' not found"}), 404

    # 현재 시간으로 last_access 업데이트
    cctv.last_access = datetime.utcnow()
    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Last access updated", "last_access": cctv.last_access.isoformat()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@main.route('/focus-webcam/<cctv_id>')
def focus_webcam(cctv_id):
    cctv = CCTV.query.filter_by(cctv_id=cctv_id).first()
    if not cctv:
        flash(f"CCTV ID '{cctv_id}'에 해당하는 데이터가 없습니다.")
        return redirect(url_for('main.cctv_list'))  # CCTV 목록 페이지로 리다이렉트
    return render_template('webcam_focus.html', cctv=cctv)
