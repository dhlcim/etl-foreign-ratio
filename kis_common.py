"""
KIS API 공통 유틸리티
- loadSecret : secret.json 로드
- getKisToken : 토큰 발급 (캐시 우선, 만료 30분 전 자동 갱신)
- isMarketHolidayKis : True=휴장, False=개장
- retryGet : 네트워크 오류 시 재시도
"""
import os
import json
import time
import requests
from datetime import datetime, timedelta

tokenCachePath = ".kis_token_cache.json"


def loadSecret(filePath):
    """secret.json 파일을 읽어서 딕셔너리로 반환한다."""
    with open(filePath, 'r', encoding='utf-8') as f:
        return json.load(f)


def retryGet(url, headers, params, maxRetry=3, sleepSec=2):
    """
    GET 요청 실패 시 최대 maxRetry회 재시도한다.
    네트워크 오류(ConnectionError, Timeout) 발생 시에만 재시도하며,
    그 외 오류는 즉시 raise한다.
    """
    lastErr = None
    for attempt in range(0, maxRetry):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            lastErr = e
            if attempt < maxRetry - 1:
                waitSec = sleepSec * (attempt + 1)
                print(f"  [재시도 {attempt + 1}/{maxRetry}] 네트워크 오류, {waitSec}초 대기")
                time.sleep(waitSec)
        except requests.exceptions.HTTPError:
            raise
    raise lastErr or RuntimeError("retryGet 최대 재시도 초과")


def getKisToken(appKey, appSecret, urlBase, cachePath=tokenCachePath):
    """
    KIS API 접속 토큰을 발급한다.
    캐시 파일이 있고 만료 30분 전이면 캐시를 재사용하고,
    그렇지 않으면 새로 발급받아 캐시 파일에 저장한다.
    """
    if os.path.exists(cachePath):
        try:
            with open(cachePath, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            expiresAt = datetime.fromisoformat(cache['expires_at'])
            if expiresAt > datetime.now() + timedelta(minutes=30):
                print(f"캐시 토큰 사용 (만료: {expiresAt.strftime('%Y-%m-%d %H:%M:%S')})")
                return cache['access_token']
        except Exception:
            pass

    url = f"{urlBase}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": appKey,
        "appsecret": appSecret
    }

    try:
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        resp.raise_for_status()
        accessToken = resp.json()['access_token']
        expiresAt = datetime.now() + timedelta(hours=23)
        with open(cachePath, 'w', encoding='utf-8') as f:
            json.dump({"access_token": accessToken, "expires_at": expiresAt.isoformat()}, f)
        print(f"신규 KIS 토큰 발급 완료 (만료: {expiresAt.strftime('%Y-%m-%d %H:%M:%S')})")
        return accessToken
    except Exception as e:
        print(f"토큰 발급 실패: {e}")
        return None


def isMarketHolidayKis(urlBase, accessToken, appKey, appSecret, targetDate=None):
    """
    오늘이 휴장일인지 확인한다. True=휴장, False=개장.
    주말은 API 호출 없이 즉시 True를 반환한다.
    """
    if targetDate is None:
        targetDate = datetime.now().strftime('%Y%m%d')

    dt = datetime.strptime(targetDate, '%Y%m%d')
    if dt.weekday() >= 5:
        print("주말: 휴장")
        return True

    url = f"{urlBase}/uapi/domestic-stock/v1/quotations/chk-holiday"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {accessToken}",
        "appkey": appKey,
        "appsecret": appSecret,
        "tr_id": "CTCA0903R",
        "custtype": "P"
    }
    params = {"BASS_DT": targetDate, "CTX_AREA_NK": "", "CTX_AREA_FK": ""}

    try:
        resp = retryGet(url, headers, params)
        data = resp.json()
        if "output" in data and len(data["output"]) > 0:
            isOpen = data["output"][0].get("opnd_yn")
            return False if isOpen == "Y" else True
    except Exception as e:
        print(f"휴장일 확인 오류: {e}")
        return True

    return True