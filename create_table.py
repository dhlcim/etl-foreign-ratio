"""
DB 테이블 생성 — 최초 1회 실행
foreign_ratio 테이블을 생성한다.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

dbHost = os.getenv("DB_HOST", "localhost")
dbPort = int(os.getenv("DB_PORT", 3306))
dbUser = os.getenv("DB_USER", "")
dbPass = os.getenv("DB_PASS", "")
dbName = os.getenv("DB_NAME", "")

CREATE_FOREIGN_RATIO_SQL = """
CREATE TABLE IF NOT EXISTS foreign_ratio (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    ticker_name VARCHAR(50),
    foreign_holding_ratio DOUBLE,
    foreign_holding_qty BIGINT,
    close_price DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, ticker)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

if __name__ == "__main__":
    connStr = f"mysql+pymysql://{dbUser}:{dbPass}@{dbHost}:{dbPort}/{dbName}?charset=utf8mb4"
    engine = create_engine(connStr, echo=False)
    try:
        with engine.connect() as conn:
            ver = conn.execute(text("SELECT VERSION()")).fetchone()[0]
            print(f"DB 연결 성공 (MySQL {ver})")
            conn.execute(text(CREATE_FOREIGN_RATIO_SQL))
            print("foreign_ratio 테이블 생성/확인 완료")
            conn.commit()
            print("완료!")
    except Exception as e:
        print(f"오류 발생: {e}")
        raise