# 📊 ETL Foreign Ratio Project

> 국내 주식 종목별 외국인 보유비율을 매일 자동 수집해 쌓아가는 ETL 파이프라인

**한 줄 요약**: 시가총액 상위 300개 종목의 외국인 보유율을 KIS Open API + pykrx로 수집하여 MySQL에 저장하고, 크론탭으로 매일 자동 갱신합니다.

## 목차
- [사전 준비물](#사전-준비물)
- [동작 원리](#동작-원리)
- [결과물](#결과물)
- [기술 스택](#기술-스택)
- [사용법](#사용법)
- [DB 스키마](#db-스키마)
- [파일 구조](#파일-구조)
- [알려진 제약사항](#알려진-제약사항)
- [확장 가능성](#확장-가능성)

## 사전 준비물
- Python 3.12
- MySQL 8.0 (로컬 또는 원격)
- [KIS Developers](https://apiportal.koreainvestment.com) 계정 + APPKEY/APPSECRET 발급
- [data.krx.co.kr](https://data.krx.co.kr) 계정 (pykrx 외국인 보유율 조회용)

## 동작 원리

\`\`\`mermaid
flowchart TD
    A[pykrx<br/>과거 2년치 백필] --> C[(MySQL<br/>foreign_ratio_db)]
    B[KIS Open API<br/>매일 신규 수집] --> D{UPSERT<br/>중복 체크}
    D -->|기존 날짜| E[UPDATE]
    D -->|신규 날짜| F[INSERT]
    E --> C
    F --> C
    C --> G[크론탭<br/>평일 16:00 자동 실행]
    G --> B
\`\`\`

처음 실행 시 2년치 과거 데이터를 한 번에 채우고(백필), 이후로는 매일 16:00에 오늘자 데이터만 자동으로 추가됩니다.

## 결과물
- 누적 데이터: **142,651건** (시가총액 상위 300종목 × 약 2년치)
- 매일 신규 적재: 약 300건/일

## 기술 스택
| 영역 | 사용 기술 |
|---|---|
| 언어 | Python 3.12 (venv) |
| DB | MySQL 8.0 |
| 시세/보유율 API | KIS Open API (한국투자증권), pykrx |
| 자동화 | crontab |
| 개발환경 | WSL2(Ubuntu 24.04) + VS Code Remote-SSH |

## 사용법

\`\`\`bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. .env, secret.json 작성 (아래 예시 참고)

# 3. DB 테이블 생성 (최초 1회)
python3 create_table.py

# 4. 과거 2년치 백필 (최초 1회)
python3 backfill_2years.py

# 5. 매일 신규 수집 (크론탭에 등록되어 자동 실행됨)
python3 collect_daily.py
\`\`\`

### .env 예시
\`\`\`
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=your_password
DB_NAME=foreign_ratio_db
\`\`\`

### secret.json 예시
\`\`\`json
{
  "KIS_APPKEY": "your_kis_appkey",
  "KIS_APPSECRET": "your_kis_appsecret",
  "KIS_CANO": "your_account_number",
  "KIS_PRDT_CD": "01",
  "URL_BASE": "https://openapivts.koreainvestment.com:29443",
  "KRX_ID": "your_krx_id",
  "KRX_PW": "your_krx_password"
}
\`\`\`

## ⏰ 크론탭 설정
\`\`\`
0 16 * * 1-5 cd /home/etl/etl-foreign-ratio && /home/etl/etl-foreign-ratio/.venv/bin/python3 collect_daily.py >> logs/daily_$(date +\%Y\%m\%d).log 2>&1
\`\`\`
평일 16:00(장마감 후) 자동 실행

## DB 스키마

\`\`\`mermaid
erDiagram
  FOREIGN_RATIO {
    date date PK
    string ticker PK
    string ticker_name
    double foreign_holding_ratio
    bigint foreign_holding_qty
    double close_price
    timestamp created_at
  }
\`\`\`

## 파일 구조
| 파일 | 역할 |
|---|---|
| `kis_common.py` | 공통 유틸 (토큰 캐싱 · 휴장일 체크 · API 재시도) |
| `create_table.py` | DB 테이블 생성 |
| `backfill_2years.py` | 과거 2년치 백필 (pykrx) |
| `collect_daily.py` | 매일 신규분 수집 (KIS API, 크론탭 등록 대상) |
| `.env` / `secret.json` | DB·API 인증 정보 (git 미포함) |

## 알려진 제약사항
- KIS 모의투자 계좌는 **연속 API 호출 제한이 낮아**, 종목당 1.5초 간격으로 호출하도록 설계됨 (300종목 기준 약 7~8분 소요)
- 외국인 보유율 "현재가" API(`inquire-price`)는 **과거 날짜 조회 미지원** → 과거 데이터는 별도로 pykrx 사용
- 일부 KIS 시세분석 API(`종목별 외인기관 추정가집계` 등)는 **모의투자 미지원**으로 사용 불가 확인됨
- 종목 수집 범위는 시가총액 상위 300개로 제한 (전체 종목 미지원)

## 확장 가능성
- 전체 종목(KOSPI+KOSDAQ 약 2,700개)으로 수집 범위 확장
- 실전투자 계좌 전환으로 호출 제한 개선
- 알림 기능(텔레그램/이메일) 추가
- 데이터 검증(이상치 탐지) 스크립트 추가