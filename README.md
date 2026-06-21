cat > README.md << 'ENDOFFILE'
# 외국인 보유비율 ETL 시스템

종목별 외국인 보유비율 데이터를 수집하고 관리하는 ETL 파이프라인입니다. 시가총액 상위 300개 종목을 대상으로, 과거 2년치 데이터 백필과 매일 신규 데이터 자동 수집 기능을 제공합니다.

## 시스템 흐름도

```
pykrx (KRX 정보데이터시스템)
 -> 과거 2년치 백필 (1회성)

KIS Open API (한국투자증권)
 -> 매일 신규 데이터 수집 (크론탭 자동 실행)

두 데이터 모두 -> MySQL UPSERT (날짜+종목코드 기준 중복 방지) -> foreign_ratio 테이블
```

백필 데이터와 일별 수집 데이터가 같은 테이블에 합쳐지며, 날짜와 종목코드가 같으면 갱신(UPDATE), 다르면 신규 추가(INSERT)됩니다.

## 주요 기능

- 시가총액 상위 300개 종목(KOSPI+KOSDAQ) 자동 선정
- 과거 2년치 외국인 보유비율 일괄 백필
- 매일 16시 신규 데이터 자동 수집 및 적재
- KIS API 토큰 캐싱으로 불필요한 재발급 방지
- 휴장일 자동 감지 및 수집 스킵
- 네트워크 오류 발생 시 자동 재시도

## 기술 스택

### 데이터 수집

- KIS Open API (한국투자증권)
- pykrx (KRX 정보데이터시스템)
- FinanceDataReader

### 데이터베이스

- MySQL 8.0
- SQLAlchemy

### 자동화

- crontab

### 개발환경

- Python 3.12 (venv)
- WSL2 (Ubuntu 24.04)
- VS Code Remote-SSH

## 프로젝트 구조

```
etl-foreign-ratio/
├─ kis_common.py          # 공통 유틸 (토큰 캐싱, 휴장일 체크, 재시도)
├─ create_table.py        # DB 테이블 생성
├─ backfill_2years.py     # 과거 2년치 백필 (pykrx)
├─ collect_daily.py       # 매일 신규분 수집 (KIS API)
├─ requirements.txt       # 패키지 목록
├─ .env                   # DB 접속 정보 (git 미포함)
├─ secret.json            # API 인증키 (git 미포함)
├─ logs/                  # 크론탭 실행 로그
└─ README.md
```

## 실행 방법

Python 3.12, MySQL 8.0이 설치되어 있어야 합니다.

```
git clone https://github.com/dhlcim/etl-foreign-ratio.git
cd etl-foreign-ratio
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 환경변수 설정

`.env`와 `secret.json` 파일을 직접 작성합니다.

`.env` 예시:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=your_password
DB_NAME=foreign_ratio_db
```

`secret.json` 예시:

```
{
  "KIS_APPKEY": "your_kis_appkey",
  "KIS_APPSECRET": "your_kis_appsecret",
  "KIS_CANO": "your_account_number",
  "KIS_PRDT_CD": "01",
  "URL_BASE": "https://openapivts.koreainvestment.com:29443",
  "KRX_ID": "your_krx_id",
  "KRX_PW": "your_krx_password"
}
```

## 데이터 수집 실행

```
# DB 테이블 생성 (최초 1회)
python3 create_table.py

# 과거 2년치 백필 (최초 1회)
python3 backfill_2years.py

# 매일 신규 수집 (크론탭에 등록되어 자동 실행됨)
python3 collect_daily.py
```

## 크론탭 설정

```
0 16 * * 1-5 cd /home/etl/etl-foreign-ratio && /home/etl/etl-foreign-ratio/.venv/bin/python3 collect_daily.py
```

평일 16시(장마감 후)에 자동 실행됩니다.

## 데이터베이스 구조

`foreign_ratio` 테이블에 종목별 일자별 외국인 보유비율이 저장됩니다. 날짜와 종목코드 조합을 유일하게 관리하며, 같은 조합으로 다시 저장하면 새로 추가하지 않고 기존 값을 수정합니다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| date | DATE (PK) | 기준일 |
| ticker | VARCHAR(10) (PK) | 종목코드 |
| ticker_name | VARCHAR(50) | 종목명 |
| foreign_holding_ratio | DOUBLE | 외국인 보유율(%) |
| foreign_holding_qty | BIGINT | 외국인 보유 수량 |
| close_price | DOUBLE | 종가 |
| created_at | TIMESTAMP | 데이터 생성 시각 |

## 데이터베이스 조회 방법

MySQL에 직접 접속해서 확인할 수 있습니다.

```
mysql -u root -p
```

접속 후 테이블 목록을 확인합니다.

```
USE foreign_ratio_db;
SHOW TABLES;
```

전체 데이터 건수를 확인합니다.

```
SELECT COUNT(*) FROM foreign_ratio;
```

특정 종목의 최근 외국인 보유율 추이를 조회합니다.

```
SELECT date, ticker_name, foreign_holding_ratio
FROM foreign_ratio
WHERE ticker = '005930'
ORDER BY date DESC
LIMIT 10;
```

## 참고

- 누적 데이터: 142,651건 (시가총액 상위 300종목 x 약 2년치)
- 매일 신규 적재: 약 300건/일
- KIS 모의투자 계좌는 연속 호출 제한이 있어 종목당 1.5초 간격으로 호출합니다.
- 외국인 보유율 현재가 API는 과거 날짜 조회를 지원하지 않아 과거 데이터는 pykrx로 수집합니다.
- 수집 범위는 시가총액 상위 300종목으로 한정되어 있습니다.

---

2026 ETL Foreign Ratio Project.
ENDOFFILE