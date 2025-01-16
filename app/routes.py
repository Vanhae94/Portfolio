from flask import Blueprint, render_template, session, redirect, url_for, request, flash, Response, current_app, jsonify,  stream_with_context
from app import db, bcrypt
from app.models import User, CCTV, DetectionLog, AbnormalBehaviorLog, Setting
from .utils import get_latest_frame, calculate_density, generate_frames, load_model
from datetime import datetime
from pytz import timezone
import cv2
import os
import base64

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
            # CCTV가 삭제되기 전에 관련된 로그들을 수동으로 삭제
            DetectionLog.query.filter_by(cctv_id=cctv.cctv_id).delete()
            AbnormalBehaviorLog.query.filter_by(cctv_id=cctv.id).delete()

            # CCTV 삭제
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
    page = request.args.get('page', 1, type=int)

    # 데이터베이스에서 이상행동 감지 데이터 조회 (페이지네이션 10개 항목)
    logs = AbnormalBehaviorLog.query.join(CCTV).add_columns(
        AbnormalBehaviorLog.id,
        AbnormalBehaviorLog.detection_time,
        CCTV.location,
        AbnormalBehaviorLog.image_url,
        AbnormalBehaviorLog.fall_status
    ).order_by(AbnormalBehaviorLog.detection_time.desc()).paginate(page=page, per_page=10, error_out=False)  # 페이지네이션 (1페이지, 10개 항목)

    # 템플릿 렌더링
    return render_template('abnormal_behavior.html', logs=logs)   

@main.route('/warning')
def density_stats():
    # 페이지 번호를 쿼리 문자열에서 가져오기 (기본값: 1)
    page = request.args.get('page', 1, type=int)

    # 밀집도 통계 데이터 조회 (페이지네이션 10개 항목)
    logs = DetectionLog.query.join(CCTV).add_columns(
        DetectionLog.id,
        DetectionLog.detection_time,
        CCTV.location,
        DetectionLog.density_level,
        DetectionLog.object_count,
        DetectionLog.image_url
    ).order_by(DetectionLog.detection_time.desc()).paginate(page=page, per_page=10, error_out=False) # 페이지네이션 (1페이지, 10개 항목)

    return render_template('warning.html', logs=logs)


@main.route('/save-capture', methods=['POST'])
def save_capture():
    data = request.json
    cctv_id = data.get("cctv_id")
    image_data = data.get("image_data")

    if not cctv_id or not image_data:
        return jsonify({"error": "Missing data"}), 400

    # 이미지 데이터 디코딩
    header, encoded = image_data.split(",", 1)
    image_binary = base64.b64decode(encoded)

    # 파일 저장 경로 및 이름 설정
    timestamp = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d%H%M%S")
    filename = f"{cctv_id}_{timestamp}.jpg"
    save_dir = os.path.join("app", "static", "images", "cctv_capture")
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, filename)

    # 파일 저장
    try:
        with open(filepath, "wb") as f:
            f.write(image_binary)
        return jsonify({"message": "Image saved successfully", "filename": filename}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#마지막 접근 라우트
@main.route('/update-last-access/<cctv_id>', methods=['POST'])
def update_last_access(cctv_id):
    # CCTV 모델에서 해당 ID 검색
    cctv = CCTV.query.filter_by(cctv_id=cctv_id).first()
    if not cctv:
        return jsonify({"error": f"CCTV ID '{cctv_id}' not found"}), 404

    # 현재 시간으로 last_access 업데이트
    cctv.last_access = datetime.now(timezone('Asia/Seoul'))
    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Last access updated", "last_access": cctv.last_access.isoformat()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@main.route('/focus-webcam/<cctv_id>')
def webcam_focus(cctv_id):
    # CCTV ID로 CCTV 데이터를 검색
    cctv = CCTV.query.filter_by(cctv_id=cctv_id).first()
    if not cctv:
        flash(f"CCTV ID '{cctv_id}'에 해당하는 데이터가 없습니다.")
        return redirect(url_for('main.cctv_list'))  # CCTV 목록 페이지로 리다이렉트

    return render_template('webcam_focus.html', cctv=cctv)

@main.route('/video-stream/<cctv_id>/<model_type>')
def video_stream(cctv_id, model_type):
    # 장치 인덱스 계산
    try:
        device_index = int(cctv_id.replace('CCTV', '')) - 1
    except ValueError:
        return jsonify({"error": "Invalid CCTV ID format"}), 400

    # 설정값 가져오기
    settings = Setting.query.order_by(Setting.level).all()
    thresholds = {setting.level: setting.max_density for setting in settings}
    
    # 모델 로드
    try:
        model = load_model(model_type)  # 모델을 한번만 로드
    except Exception as e:
        return jsonify({"error": f"Failed to load YOLO model: {str(e)}"}), 500

    # 스트리밍을 위해 모델과 함께 새로 프레임을 생성
    return Response(
        stream_with_context(generate_frames(model, model_type, device_index, thresholds, cctv_id)),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@main.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        level = request.form.get('level')
        max_density = request.form.get('max_density')
        description = request.form.get('description')

        # 기존 레벨 수정/추가
        setting = Setting.query.filter_by(level=level).first()
        if not setting:
            setting = Setting(level=level, max_density=max_density, description=description)
            db.session.add(setting)
        else:
            setting.max_density = max_density
            setting.description = description
        
        try:
            db.session.commit()
            flash("설정이 성공적으로 업데이트되었습니다.")
        except Exception as e:
            db.session.rollback()
            flash(f"설정 업데이트 중 오류가 발생했습니다: {e}")

        return redirect(url_for('main.settings'))

    settings = Setting.query.order_by(Setting.level).all()
    return render_template('settings.html', settings=settings)

@main.route('/add-setting', methods=['GET', 'POST'])
def add_setting():
    if request.method == 'POST':
        level = request.form.get('level')
        max_density = request.form.get('max_density')
        description = request.form.get('description')

        # 새 설정 추가
        new_setting = Setting(level=level, max_density=max_density, description=description)
        try:
            db.session.add(new_setting)
            db.session.commit()
            flash("새 설정이 성공적으로 추가되었습니다.")
        except Exception as e:
            db.session.rollback()
            flash(f"설정 추가 중 오류가 발생했습니다: {e}")

        return redirect(url_for('main.settings'))

    return render_template('add_setting.html')

@main.route('/edit-setting/<int:setting_id>', methods=['GET'])
def edit_setting(setting_id):
    setting = Setting.query.get_or_404(setting_id)
    return render_template('edit_setting.html', setting=setting)

@main.route('/update-setting/<int:setting_id>', methods=['POST'])
def update_setting(setting_id):
    setting = Setting.query.get_or_404(setting_id)
    setting.max_density = request.form.get('max_density')
    setting.description = request.form.get('description')

    try:
        db.session.commit()
        flash(f"'{setting.level}' 단계 설정이 성공적으로 수정되었습니다.")
    except Exception as e:
        db.session.rollback()
        flash(f"설정 수정 중 오류가 발생했습니다: {e}")
    
    return redirect(url_for('main.settings'))

@main.route('/delete-setting/<int:setting_id>', methods=['POST'])
def delete_setting(setting_id):
    setting = Setting.query.get_or_404(setting_id)
    try:
        db.session.delete(setting)
        db.session.commit()
        flash(f"'{setting.level}' 단계 설정이 성공적으로 삭제되었습니다.")
    except Exception as e:
        db.session.rollback()
        flash(f"설정 삭제 중 오류가 발생했습니다: {e}")
    
    return redirect(url_for('main.settings'))
