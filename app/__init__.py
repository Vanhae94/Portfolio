import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from ultralytics import YOLO

# .env 파일 로드
load_dotenv()

# 데이터베이스 객체 생성
db = SQLAlchemy()

# Bcrypt 객체 생성
bcrypt = Bcrypt()

# Migrate 객체 생성
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # yolo모델
    app.yolo_model = YOLO('yolov8n.pt') 
    
    # 설정 로드
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

    # SQLALCHEMY_DATABASE_URI 확인
    if not app.config['SQLALCHEMY_DATABASE_URI']:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set. Check your .env file.")

    # 데이터베이스 초기화
    db.init_app(app)

    # Flask-Migrate 초기화
    migrate.init_app(app, db)
    # 로그 설정
    setup_logging(app)

    # 블루프린트 등록
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app


def setup_logging(app):
    """Set up logging for the Flask application."""
    # 로그 디렉토리 생성
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로그 파일 핸들러 설정
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)  # 10MB, 5개의 백업
    file_handler.setLevel(logging.INFO)

    # 로그 포맷 지정
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    file_handler.setFormatter(formatter)

    # Flask 기본 로거에 핸들러 추가
    app.logger.addHandler(file_handler)

def setup_detection_logging():
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    detection_log_file = os.path.join(log_dir, 'detection_logs.log')
    detection_handler = logging.FileHandler(detection_log_file)
    detection_handler.setLevel(logging.INFO)
    detection_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s'
    )
    detection_handler.setFormatter(detection_formatter)
    
    detection_logger = logging.getLogger('detection')
    detection_logger.setLevel(logging.INFO)
    detection_logger.addHandler(detection_handler)
    return detection_logger

detection_logger = setup_detection_logging()