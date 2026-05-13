import streamlit as st
import requests
import re
from datetime import datetime
from PIL import Image
import pytesseract
import platform

# 設定頁面資訊
st.set_page_config(page_title="校務收據自動核銷系統", layout="wide", page_icon="🧾")

# 針對 Windows 用戶指定 Tesseract 路徑 (請根據您的安裝路徑修改)
if platform.system() == "Windows":
    # 若您安裝在預設路徑，請取消下行註解並確認路徑正確
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    pass

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stAlert { border-radius: 10px; }
    .report-card { 
        padding: 20px; 
        border-radius: 10px; 
        background-color: white; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

class ReceiptSystem:
    @staticmethod
    def query_mof(ubn):
        """呼叫財政部 API 查詢稅籍"""
        url = f"https://eip.fia.gov.tw/OAI/api/businessRegistration/{ubn}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            return None
        return None

    @staticmethod
    def extract_data(image):
        """從圖片提取統編與日期"""
        # 進行 OCR 辨識 (支援繁體中文與英文)
        text = pytesseract.image_to_string(image, lang='chi_tra+eng')
        
        # 1. 提取統編 (8碼數字)
        ubn_match = re.search(r"\b\d{8}\b", text)
        ubn = ubn_match.group() if ubn_match else None
        
        # 2. 提取日期 (支援 民國 113.05.20 或 西元 2024-05-20)
        date_obj = None
        date_pattern = r"(\d{2,3})[-/.\s年](\d{1,2})[-/.\s月](\d{1,2})"
        date_match = re.search(date_pattern, text)
        if date_match:
            yy, mm, dd = date_match.groups()
            year = int(yy) + 1911 if int(yy) < 1000 else int(yy)
            try:
                date_obj = datetime(year, int(mm), int(dd))
            except:
                pass
        
        return ubn, date_obj, text

def main():
    st.title("🧾 校務收據自動核銷輔助系統")
    st.info("請上傳收據或發票照片，系統將自動根據財政部資料與校規進行審核。")

    with st.sidebar:
        st.header("⚙️ 核銷規則設定")
        budget_approval_date = st.date_input("預算審核通過日期", datetime(2024, 1, 1))
        st.divider()
        st.markdown("""
        **校規提醒：**
        1. **日期限制**：憑證日期需在預算通過日之後。
        2. **店家身分**：店家身分需與憑證形式相符。
        3. **印章檢查**：收據必須蓋有大章與負責人小章。
        """)

    uploaded_file = st.file_uploader("選擇收據圖片 (JPG/PNG)", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        img = Image.open(uploaded_file)
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.image(img, caption="上傳的憑證畫面", use_container_width=True)

        with col2:
            with st.status("正在進行 OCR 辨識與稅籍查詢...", expanded=True) as status:
                ubn, inv_date, raw_text = ReceiptSystem.extract_data(img)
                
                if not ubn:
                    st.error("❌ 無法辨識 8 碼統一編號。請確保照片清晰且統編未被遮擋。")
                    status.update(label="辨識失敗", state="error")
                else:
                    biz_data = ReceiptSystem.query_mof(ubn)
                    status.update(label="辨識與查詢完成", state="complete")
                    
                    if not biz_data:
                        st.warning(f"⚠️ 統編 {ubn} 查無財政部稅籍登記資料。")
                    else:
                        render_report(biz_data, inv_date, budget_approval_date, raw_text)

def render_report(biz_data, inv_date, budget_date, raw_text):
    biz_name = biz_data.get("businessNm", "未知店家")
    is_use_invoice = biz_data.get("isUseInvoice", "未知")
    ubn = biz_data.get("ban")

    st.subheader(f"🏢 店家資訊：{biz_name}")
    
    # 建立三項規定的查核點
    pass_all = True
    
    # 1. 日期查核 (校規 2)
    st.markdown("### 🔍 核銷查核清單")
    
    # 日期檢查
    if inv_date:
        is_date_ok = inv_date.date() >= budget_date
        if is_date_ok:
            st.success(f"✅ **日期合格**：憑證日期 ({inv_date.date()}) 符合預算通過日要求。")
        else:
            st.error(f"❌ **日期不符**：憑證日期 ({inv_date.date()}) 早於預算通過日 ({budget_date})。")
            pass_all = False
    else:
        st.warning("⚠️ **日期警示**：無法自動辨識日期，請手動確認。")

    # 2. 憑證形式查核 (校規 3)
    # 判斷 OCR 文字中是否包含發票或收據關鍵字
    is_invoice_text = any(k in raw_text for k in ["發票", "證明聯", "INVOICE"])
    is_receipt_text = any(k in raw_text for k in ["收據", "免用"])

    if "使用統一發票" in is_use_invoice:
        if is_invoice_text:
            st.success(f"✅ **形式合格**：店家應開立發票，辨識結果為發票。")
        else:
            st.error("❌ **形式錯誤**：該店家為發票商，但此憑證疑似為「收據」。")
            pass_all = False
    else:
        st.warning(f"ℹ️ **店家身分**：此店家為「免用統一發票」商號。")
        # 3. 印章檢查 (校規 1) - 這部分需要人工提醒
        st.error("❗ **重要(校規 1)**：收據必須蓋有「店家大章(非發票章)」及「負責人小章」。")

    # 總結
    if pass_all:
        st.balloons()
        st.success("🎉 系統初步判定：符合校規核銷基本條件！")
    else:
        st.error("🚫 系統判定：此憑證可能無法核銷，請修正後重新上傳。")

    with st.expander("查看原始辨識文字"):
        st.text(raw_text)

if __name__ == "__main__":
    main()