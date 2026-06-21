"""
kis_common.py 동작 테스트
- 토큰 발급(캐싱) 확인
- 휴장일 체크 확인
"""
import json
from kis_common import loadSecret, getKisToken, isMarketHolidayKis

secret = loadSecret("secret.json")

print("=== 1) 토큰 발급 테스트 ===")
token = getKisToken(secret["KIS_APPKEY"], secret["KIS_APPSECRET"], secret["URL_BASE"])
if token:
    print("토큰 발급 성공!")
else:
    print("토큰 발급 실패!")

print("\n=== 2) 캐시 재사용 테스트 (다시 호출) ===")
token2 = getKisToken(secret["KIS_APPKEY"], secret["KIS_APPSECRET"], secret["URL_BASE"])

print("\n=== 3) 휴장일 체크 테스트 ===")
isHoliday = isMarketHolidayKis(secret["URL_BASE"], token, secret["KIS_APPKEY"], secret["KIS_APPSECRET"])
print(f"오늘 휴장 여부: {isHoliday}")