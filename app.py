from app import create_app, db

# 애플리케이션 생성
app = create_app()

# 데이터베이스 생성 및 초기화
with app.app_context():
    db.create_all()

# 서버 실행
if __name__ == "__main__":
    app.run(debug=True)
