from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), default='pending', nullable=False)
    
    def __repr__(self):
        return f'<User {self.name}>'

class CCTV(db.Model):
    __tablename__ = 'cctvs'
    id = db.Column(db.Integer, primary_key=True)
    cctv_id = db.Column(db.String(50), unique=True, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_access = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "cctv_id": self.cctv_id,
            "location": self.location,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "last_access": self.last_access.isoformat() if self.last_access else None,
        }



class DetectionLog(db.Model):
    __tablename__ = 'detection_logs'
    id = db.Column(db.Integer, primary_key=True)
    detection_time = db.Column(db.DateTime, default=datetime.utcnow)  # 탐지 시간
    cctv_id = db.Column(db.Integer, db.ForeignKey('cctvs.id'), nullable=False)  # CCTV 참조
    density_level = db.Column(db.String(50), nullable=False)  # 밀집 정도
    overcrowding_level = db.Column(db.String(50), nullable=False)  # 과밀 수준
    object_count = db.Column(db.Integer, nullable=False)  # 감지된 객체 수
    image_url = db.Column(db.String(255), nullable=False)  # 이미지 링크

    # 관계 설정
    cctv = db.relationship('CCTV', backref=db.backref('detection_logs', lazy=True))

class AbnormalBehaviorLog(db.Model):
    __tablename__ = 'abnormal_behavior_logs'
    id = db.Column(db.Integer, primary_key=True)
    detection_time = db.Column(db.DateTime, default=datetime.utcnow)  # 탐지 시간
    cctv_id = db.Column(db.Integer, db.ForeignKey('cctvs.id'), nullable=False)  # CCTV 참조
    image_url = db.Column(db.String(255), nullable=False)  # 이미지 링크
    fall_status = db.Column(db.String(50), nullable=False, default="정상")  # 쓰러짐 상태 (예: "정상", "쓰러짐")

    # 관계 설정
    cctv = db.relationship('CCTV', backref=db.backref('abnormal_behavior_logs', lazy=True))
