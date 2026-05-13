import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="校園收據核銷系統", page_icon="🛡️")
st.title("🛡️ 校園收據核銷輔助系統")

with st.sidebar:
    budget_date = st.date_input("預算通過日期", datetime(2024, 1, 1))

st.subheader("📝 憑證資訊輸入")
col1, col2 = st.columns(2)

with col1:
    ubn = st.text_input("統一編號 (8碼)", max_chars=8)
    receipt_date = st.date_input("憑證日期", datetime.now())

with col2:
    voucher_type = st.selectbox(
        "憑證形式",
        ["電子發票證明聯", "傳統發票 (長條型)", "二/三聯式發票", "免用統一發票收據"]
    )

if ubn and len(ubn) == 8:
    with st.spinner("查詢中..."):
        api_url = f"https://eip.fia.gov.tw/OAI/api/businessRegistration/{ubn}"
        try:
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                biz_data = resp.json()
                biz_name = biz_data.get("businessNm", "未知店家")
                is_use_inv = biz_data.get("isUseInvoice", "")
                
                st.divider()
                st.success(f"🏪 店家名稱：{biz_name}")
                
                is_pass = True
                errors = []
                warnings = []

                if receipt_date < budget_date:
                    is_pass = False
                    errors.append(f"❌ 日期錯誤：憑證日期 ({receipt_date}) 早於預算通過日。")

                if "使用" in is_use_inv and "免用" not in is_use_inv:
                    if voucher_type == "免用統一發票收據":
                        is_pass = False
                        errors.append("❌ 形式錯誤：店家應開發票，不得使用收據。")
                else:
                    if voucher_type != "免用統一發票收據":
                        warnings.append("⚠️ 提醒：店家稅籍為免用發票，請確認憑證格式。")
                    
                    st.warning("📋 免用發票收據檢查項")
                    c1 = st.checkbox("已蓋店家大章")
                    c2 = st.checkbox("已蓋負責人小章")
                    if not (c1 and c2):
                        is_pass = False
                        errors.append("❌ 印章缺失：收據需蓋齊大小章。")

                st.divider()
                if is_pass:
                    st.balloons()
                    st.info("💡 判定結果：【符合核銷規定】")
                else:
                    st.error("💡 判定結果：【不符合規定】")
                    for err in errors:
                        st.write(err)
                
                for warn in warnings:
                    st.warning(warn)
            else:
                st.error("查無此統編。")
        except Exception as e:
            st.error("連線失敗。")
elif ubn:
    st.warning("請輸入 8 碼統編。")

st.divider()
st.caption("本系統僅供參考，最終以會計室審核為準。")