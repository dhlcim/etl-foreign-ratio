"""
KIS API 외국인 보유비율 조회 테스트
삼성전자(005930) 기준
"""
import json
import requests

with open("secret.json", "r", encoding="utf-8") as f:
    secret = json.load(f)

# 1) 토큰 발급
tokenUrl = f"{secret['URL_BASE']}/oauth2/tokenP"
tokenBody = {
    "grant_type": "client_credentials",
    "appkey": secret["KIS_APPKEY"],
    "appsecret": secret["KIS_APPSECRET"]
}
tokenRes = requests.post(tokenUrl, headers={"content-type": "application/json"}, data=json.dumps(tokenBody))
accessToken = tokenRes.json()["access_token"]

# 2) 주식현재가 시세 조회 (외국인 보유비율 포함)
priceUrl = f"{secret['URL_BASE']}/uapi/domestic-stock/v1/quotations/inquire-price"
headers = {
    "content-type": "application/json",
    "authorization": f"Bearer {accessToken}",
    "appkey": secret["KIS_APPKEY"],
    "appsecret": secret["KIS_APPSECRET"],
    "tr_id": "FHKST01010100"
}
params = {
    "FID_COND_MRKT_DIV_CODE": "J",
    "FID_INPUT_ISCD": "005930"
}

priceRes = requests.get(priceUrl, headers=headers, params=params)
data = priceRes.json()

print("응답 코드:", priceRes.status_code)
print("외국인 현보유율(%):", data.get("output", {}).get("hts_frgn_ehrt"))
print("전체 응답:", data)