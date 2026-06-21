"""
KIS API 토큰 발급 테스트
키가 정상적으로 작동하는지 확인
"""
import json
import requests

with open("secret.json", "r", encoding="utf-8") as f:
    secret = json.load(f)

url = f"{secret['URL_BASE']}/oauth2/tokenP"
headers = {"content-type": "application/json"}
body = {
    "grant_type": "client_credentials",
    "appkey": secret["KIS_APPKEY"],
    "appsecret": secret["KIS_APPSECRET"]
}

response = requests.post(url, headers=headers, data=json.dumps(body))

if response.status_code == 200:
    print("✅ 토큰 발급 성공!")
    print(response.json())
else:
    print("❌ 토큰 발급 실패")
    print(response.status_code, response.text)