import requests
import pandas as pd
import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="종가베팅 포착기", layout="wide")

st.title("🎯 오늘 오후 종가베팅 추천 종목")
st.caption("오후 3시~3시 20분 진입 전용 스코어링 대시보드")

# 보안을 위해 설정값에서 API 키 불러오기
APP_KEY = st.secrets.get("PSfphBgQS16mRManwLEL8dSfKHvN78i2quCa", "")
APP_SECRET = st.secrets.get("3O0zlnTf8PNpoZUOcjsESN3L+p8GbFSrIEKSnCEzkd+rJpqf7cYHEXARcZmD8BCKrLDA3ZwL0ggr8+4BC8IFsaw0r0OpROSewXaVX6ujOHhbZS+qlEskBgbymBBfdlXuzuQsY2tr+Pdkgzf5wY8620L/9fVtEDrSKX1UWoEqmgDYiqe4ce0=", "")
URL_BASE = "https://openapi.koreainvestment.com:9443"

@st.cache_data(ttl=3600)
def get_access_token():
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers=headers, json=body)
    return res.json().get("access_token")

def fetch_top_trading_volume(token):
    path = "/uapi/domestic-stock/v1/ranking/trade-value"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHPST01710000"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_DIV_CODE": "20171",
        "FID_INPUT_ISCD": "0000", "FID_DIV_CLS_CODE": "0",
        "FID_BLNG_CLS_CODE": "0", "FID_TRGT_CLS_CODE": "0",
        "FID_TRGT_EXLS_CLS_CODE": "0", "FID_INPUT_PRICE_1": "",
        "FID_INPUT_PRICE_2": "", "FID_VOL_CONT": ""
    }
    res = requests.get(f"{URL_BASE}/{path}", headers=headers, params=params)
    return pd.DataFrame(res.json().get('output', []))

def calculate_score(row):
    score = 0
    reasons = []
    
    # 증권사에서 받아온 데이터(문자)를 계산하기 위해 숫자(float)로 변환
    price = float(row.get('stck_prpr', 0))       # 현재가
    open_p = float(row.get('stck_oprc', 0))      # 시가
    high = float(row.get('stck_hgpr', 0))        # 당일 최고가
    low = float(row.get('stck_lwpr', 1))         # 당일 최저가
    rate = float(row.get('prdy_ctrt', 0))        # 등락률(%)
    
    # 거래대금: 누적거래량 * 현재가 / 1억 (간이 계산)
    vol = float(row.get('acml_vol', 0))
    trade_val = (price * vol) / 100000000
    
    # 1. 기본 거래대금 (20점)
    if trade_val >= 1000:
        score += 20
        reasons.append("1.거래대금 1천억통과")

    # 2. 당일 상승률 (15점)
    if 5.0 <= rate <= 20.0:
        score += 15
        reasons.append(f"2.상승률적절({rate}%)")

    # 3. 양봉 유지 (10점)
    if price > open_p:
        score += 10
        reasons.append("3.양봉유지")

    # 4. 윗꼬리 길이 (15점)
    if high > open_p:
        # (고가-현재가) / (고가-시가) 비중 계산
        tail_ratio = ((high - price) / (high - open_p)) * 100
        if tail_ratio < 20:
            score += 15
            reasons.append("4.윗꼬리짧음")

    # 5. 막판 고가 방어력 (15점)
    # 현재가가 당일 최고가에서 3% 이상 빠지지 않았는지 확인
    if price >= (high * 0.97):
        score += 15
        reasons.append("5.최고가부근마감")

    # 6. 장중 변동성 (10점)
    # 하루 종일 10% 이상 위아래로 움직였는지 확인
    volatility = ((high - low) / low) * 100
    if volatility >= 10:
        score += 10
        reasons.append("6.활발한움직임")

    # 7. 대규모 자금 보너스 (15점)
    if trade_val >= 2000:
        score += 15
        reasons.append("7.대규모자금(2천억↑)")

    return score, ", ".join(reasons)

    
    if high > open_p:
        tail_ratio = ((high - close) / (high - open_p)) * 100
        if tail_ratio < 20:
            score += 40
            reasons.append("종가 고가 관리 잘됨")
            
    return score, ", ".join(reasons)

# 메인 실행 화면
if st.button("🔥 실시간 종가베팅 후보 분석 실행"):
    if not APP_KEY or not APP_SECRET:
        st.error("API 키 설정이 필요합니다.")
    else:
        token = get_access_token()
        df = fetch_top_trading_volume(token)
        
        results = []
        for idx, row in df.iterrows():
            score, reason = calculate_score(row)
            if score >= 50:  # 50점 이상 종목만
                results.append({
                    "종목명": row.get('hts_kor_isnm'),
                    "현재가": f"{int(row.get('stck_prpr', 0)):,}원",
                    "등락률": f"{float(row.get('prdy_ctrt', 0))}%",
                    "종베점수": score,
                    "포착이유": reason
                })
        
