"""
외국인 보유율 과거 2년치 백필 스크립트 (시가총액 상위 300개 종목)
pykrx를 사용하여 날짜 범위를 지정해 과거 데이터를 가져온 뒤 DB에 UPSERT한다.
"""
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import FinanceDataReader as fdr

with open("secret.json", "r", encoding="utf-8") as f:
    secret = json.load(f)

os.environ["KRX_ID"] = secret["KRX_ID"]
os.environ["KRX_PW"] = secret["KRX_PW"]

from pykrx import stock

load_dotenv()

dbHost = os.getenv("DB_HOST", "localhost")
dbPort = int(os.getenv("DB_PORT", 3306))
dbUser = os.getenv("DB_USER", "")
dbPass = os.getenv("DB_PASS", "")
dbName = os.getenv("DB_NAME", "")

UPSERT_SQL = """
INSERT INTO foreign_ratio (date, ticker, ticker_name, foreign_holding_ratio, foreign_holding_qty, close_price)
VALUES (:date, :ticker, :ticker_name, :foreign_holding_ratio, :foreign_holding_qty, :close_price)
ON DUPLICATE KEY UPDATE
    ticker_name = VALUES(ticker_name),
    foreign_holding_ratio = VALUES(foreign_holding_ratio),
    foreign_holding_qty = VALUES(foreign_holding_qty),
    close_price = VALUES(close_price)
"""


def getAllTickers(topN=300):
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


def backfillTicker(engine, ticker, tickerName, fromDate, toDate):
    """
    한 종목의 외국인 보유율 과거 데이터를 가져와 DB에 UPSERT한다.
    """
    df = stock.get_exhaustion_rates_of_foreign_investment(fromDate, toDate, ticker)

    if df.empty:
        print(f"  {ticker}({tickerName}): 데이터 없음")
        return 0

    savedCount = 0
    with engine.connect() as conn:
        for idx in range(0, len(df)):
            row = df.iloc[idx]
            dateStr = df.index[idx].strftime('%Y-%m-%d')
            conn.execute(text(UPSERT_SQL), {
                "date": dateStr,
                "ticker": ticker,
                "ticker_name": tickerName,
                "foreign_holding_ratio": float(row["지분율"]),
                "foreign_holding_qty": int(row["보유수량"]),
                "close_price": None
            })
            savedCount = savedCount + 1
        conn.commit()

    print(f"  {ticker}({tickerName}): {savedCount}건 저장 완료")
    return savedCount


if __name__ == "__main__":
    connStr = f"mysql+pymysql://{dbUser}:{dbPass}@{dbHost}:{dbPort}/{dbName}?charset=utf8mb4"
    engine = create_engine(connStr)

    toDate = datetime.now().strftime('%Y%m%d')
    fromDate = (datetime.now() - timedelta(days=730)).strftime('%Y%m%d')

    TEST_TICKERS = getAllTickers()

    print(f"백필 기간: {fromDate} ~ {toDate}")
    print(f"대상 종목: {len(TEST_TICKERS)}개\n")

    totalSaved = 0
    tickerList = list(TEST_TICKERS.items())
    for idx in range(0, len(tickerList)):
        ticker, tickerName = tickerList[idx]
        try:
            count = backfillTicker(engine, ticker, tickerName, fromDate, toDate)
            totalSaved = totalSaved + count
        except Exception as e:
            print(f"  {ticker}({tickerName}): 오류 발생 - {e}")

    print(f"\n전체 완료! 총 {totalSaved}건 저장됨")