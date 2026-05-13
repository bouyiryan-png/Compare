import streamlit as st
import requests
import re
import cv2
import numpy as np
from datetime import datetime
from PIL import Image
import pytesseract

# --- 設定區 ---
BUDGET_DATE = st.sidebar.date_input("1. 設定預算通過日期", datetime(2024, 1, 1))
VALID_INVOICE_KEYWORDS = ["電子發票", "統一發票", "收銀機發票", "證明聯"]
VALID_RECEIPT_KEYWORDS = ["免用統一發票", "收據"]

def validate_ubn(ubn):
    """ 台灣統一編號校驗邏輯 (Modulo 10) """
    if not ubn or len(ubn) != 8 or not ubn.isdigit():
        return False
    weights = [1, 2, 1, 2, 1, 2, 4, 1]
    s = 0
    for i in range(8):
        tmp = int(ubn[i]) * weights[i]
        s += (tmp // 10) + (tmp % 10)
    
    if s % 10 == 0:
        return True
    if ubn[6] == '7' and (s + 1) % 10 == 0:
        return True
    return False

def preprocess_image(image):
    """ 影像預處理：轉灰階、增強對比，幫助辨識模糊收據 """
    img = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # 增加對比度
    alpha = 1.5 # 對比度 (1.0-3.0)
    beta = 0    # 亮度 (0-100)
    adjusted = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
    # 二值化處理
    _, thresh = cv2.threshold(adjusted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)

def extract_data(text):
    data = {"ubn": None, "date": None, "type": "未知"}
    
    # A. 搜尋所有 8 碼數字，並透過校驗碼篩選真正的統編
    potential_ubns = re.findall(r"\d{8}", text)
    valid_ubns = [u for u in potential_ubns if validate_ubn(u)]
    if valid_ubns:
        # 通常收據上會有店家的統編跟學校的統編，這裡先取第一個，或篩選非學校的
        data["ubn"] = valid_ubns[0]

    # B. 日期搜尋
    date_pattern = r"(\d{2,3})[-/.\s年](\d{1,2})[-/.\s月](\d{1,2})"
    date_match = re.search(date_pattern, text)
    if date_match:
        yy, mm, dd = date_match.groups()
        year = int(yy) + 1911 if int(yy) < 1000 else int(yy)
        try: data["date"] = datetime(year, int(mm), int(dd))
        except: pass

    # C. 憑證類型
    if any(k in text for k in VALID_INVOICE_KEYWORDS): data["type"] = "發票"
    elif any(k in text for k in VALID_RECEIPT_KEYWORDS): data["type"] = "免用統一發票收據"

    return data

# --- UI 介面 ---
st.title("🛡️ 校園收據自動核銷系統 (進階辨識版)")
st.write("修正了電子發票誤判與收據辨識率問題。")

uploaded_file = st.file_uploader("上傳憑證照片 (發票或收據)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="原始圖片", use_container_width=True)
    
    with st.spinner("辨識中..."):
        # 進行預處理提升辨識率
        processed_img = preprocess_image(img)
        raw_text = pytesseract.image_to_string(processed_img, lang='chi_tra+eng')
        res = extract_data(raw_text)
        
    st.divider()
    
    if res["ubn"]:
        # 呼叫財政部 API
        api_url = f"https://eip.fia.gov.tw/OAI/api/businessRegistration/{res['ubn']}"
        try:
            resp = requests.get(api_url, timeout=10).json()
            biz_name = resp.get("businessNm", "未知店家")
            is_use_inv = resp.get("isUseInvoice", "")
            
            st.success(f"✅ 辨識成功：{biz_name} ({res['ubn']})")
            
            # --- 校規比對邏輯 ---
            is_pass = True
            errors = []
            
            # 1. 日期檢查
            if res["date"]:
                if res["date"].date() < BUDGET_DATE:
                    is_pass = False
                    errors.append(f"❌ 日期錯誤：憑證日期({res['date'].date()})早於預算通過日")
            else:
                errors.append("⚠️ 無法辨識日期，請人工確認")

            # 2. 憑證形式檢查
            if "使用統一發票" in is_use_inv:
                if res["type"] != "發票":
                    is_pass = False
                    errors.append("❌ 店家應開立發票，但現場為收據格式")
            else:
                st.warning("ℹ️ 此為【免用發票】店家，請檢查是否有蓋「店家大章」與「負責人小章」。")

            if is_pass:
                st.balloons()
                st.info("💡 系統初步判定：【符合核銷規定】")
            else:
                st.error("💡 系統判定：【不符合規定】")
                for err in errors: st.write(err)

        except:
            st.error("API 連線失敗，請稍後再試。")
    else:
        st.error("無法辨識有效的統一編號。請確保照片清晰且包含 8 碼統編。")
        with st.expander("查看 OCR 辨識結果文本"):
            st.text(raw_text)
eof
