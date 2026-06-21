"""
외국인 보유율 일별 수집 스크립트 (크론탭용)
KIS API로 시가총액 상위 300종목의 오늘자 외국인 보유율을 조회하여 DB에 UPSERT한다.
"""
import os
import time
import argparse
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import FinanceDataReader as fdr

from kis_common import loadSecret, getKisToken, isMarketHolidayKis, retryGet

parser = argparse.ArgumentParser()
parser.add_argument('--test', action='store_true', help='휴장일 체크를 건너뛰고 테스트 실행')
cliArgs = parser.parse_args()

load_dotenv()

dbHost = os.getenv("DB_HOST", "localhost")
dbPort = int(os.getenv("DB_PORT", 3306))
dbUser = os.getenv("DB_USER", "")
dbPass = os.getenv("DB_PASS", "")
dbName = os.getenv("DB_NAME", "")

KIS_SLEEP = 1.5
COMMIT_INTERVAL = 20

UPSERT_SQL = """
INSERT INTO foreign_ratio (date, ticker, ticker_name, foreign_holding_ratio, foreign_holding_qty, close_price)
VALUES (:date, :ticker, :ticker_name, :foreign_holding_ratio, :foreign_holding_qty, :close_price)
ON DUPLICATE KEY UPDATE
    ticker_name = VALUES(ticker_name),
    foreign_holding_ratio = VALUES(foreign_holding_ratio),
    foreign_holding_qty = VALUES(foreign_holding_qty),
    close_price = VALUES(close_price)
"""


def getTopTickers(topN=300):
    """
    KOSPI + KOSDAQ 종목을 시가총액 기준으로 정렬하여,
    상위 topN개를 딕셔너리(종목코드: 종목명)로 반환한다.
    """
    kospiDf = fdr.StockListing('KOSPI')
    kosdaqDf = fdr.StockListing('KOSDAQ')

    combinedDf = kospiDf._append(kosdaqDf, ignore_index=True)
    combinedDf = combinedDf.sort_values(by='Marcap', ascending=False)
    topDf = combinedDf.head(topN)

    tickerDict = {}
    for idx in range(0, len(topDf)):
        code = topDf.iloc[idx]['Code']
        name = topDf.iloc[idx]['Name']
        tickerDict[code] = name

    return tickerDict


def fetchForeignRatio(urlBase, token, appKey, appSecret, ticker):
    """
    KIS API로 한 종목의 현재가 시세(외국인 보유율 포함)를 조회한다.
    """
    url = f"{urlBase}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": appKey,
        "appsecret": appSecret,
        "tr_id": "FHKST01010100"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": ticker
    }

    resp = retryGet(url, headers, params)
    data = resp.json()
    output = data.get("output", {})
    return output


if __name__ == "__main__":
    secret = loadSecret("secret.json")

    modeLabel = "[TEST]" if cliArgs.test else ""
    print(f"{modeLabel}[일별 수집] 실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    token = getKisToken(secret["KIS_APPKEY"], secret["KIS_APPSECRET"], secret["URL_BASE"])
    if not token:
        print("토큰 발급 실패. 종료.")
        exit(1)

    if cliArgs.test:
        print("테스트 모드: 휴장일 체크 건너뜀")
    else:
        isHoliday = isMarketHolidayKis(secret["URL_BASE"], token, secret["KIS_APPKEY"], secret["KIS_APPSECRET"])
        if isHoliday:
            print("오늘은 휴장일입니다. 종료.")
            exit(0)
        print("오늘은 개장일입니다. 계속 진행합니다.")

    tickerDict = getTopTickers()
    today = datetime.now().strftime('%Y-%m-%d')

    connStr = f"mysql+pymysql://{dbUser}:{dbPass}@{dbHost}:{dbPort}/{dbName}?charset=utf8mb4"
    engine = create_engine(connStr)

    tickerList = list(tickerDict.items())
    savedCount = 0
    failCount = 0

    conn = engine.connect()
    for idx in range(0, len(tickerList)):
        ticker, tickerName = tickerList[idx]
        try:
            output = fetchForeignRatio(secret["URL_BASE"], token, secret["KIS_APPKEY"], secret["KIS_APPSECRET"], ticker)
            ratio = output.get("hts_frgn_ehrt")
            qty = output.get("frgn_hldn_qty")
            price = output.get("stck_prpr")

            conn.execute(text(UPSERT_SQL), {
                "date": today,
                "ticker": ticker,
                "ticker_name": tickerName,
                "foreign_holding_ratio": float(ratio) if ratio else None,
                "foreign_holding_qty": int(qty) if qty else None,
                "close_price": float(price) if price else None
            })
            savedCount = savedCount + 1
            print(f"  [{idx + 1}/{len(tickerList)}] {ticker}({tickerName}): 저장 완료")
        except Exception as e:
            failCount = failCount + 1
            print(f"  [{idx + 1}/{len(tickerList)}] {ticker}({tickerName}): 오류 발생 - {e}")

        if (idx + 1) % COMMIT_INTERVAL == 0:
            conn.commit()
            print(f"  --- 중간 커밋 완료 ({idx + 1}건째) ---")

        time.sleep(KIS_SLEEP)

    conn.commit()
    conn.close()

    print(f"\n완료! 성공 {savedCount}건 / 실패 {failCount}건 / 전체 {len(tickerList)}건")