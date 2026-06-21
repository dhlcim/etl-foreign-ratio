"""
pykrx로 외국인 보유율(소진율) 과거 데이터 조회 테스트
삼성전자(005930) 최근 1개월 기준
"""
import os
import json

with open("secret.json", "r", encoding="utf-8") as f:
    secret = json.load(f)

os.environ["KRX_ID"] = secret["KRX_ID"]
os.environ["KRX_PW"] = secret["KRX_PW"]

from pykrx import stock

ticker = "005930"
fromDate = "20260501"
toDate = "20260620"

df = stock.get_exhaustion_rates_of_foreign_investment(fromDate, toDate, ticker)
print(df)
print(f"\n총 {len(df)}건 조회됨")