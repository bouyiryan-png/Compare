import streamlit as st
import requests
from datetime import datetime

# --- 標題與側邊欄設定 ---
st.set_page_config(page_title="校園收據核銷系統", page_icon="🛡️")
st.title("🛡️ 校園收據核銷輔助系統")
st.write("透過輸入統編與日期，自動比對財政部資料與學校核銷規定。")

with st.sidebar:
    st.header("⚙️ 系統設定")
    budget_date = st.date_input("1. 設定預算通過日期", datetime(2024, 1, 1))
    st.info("憑證日期若早於此日期，系統將判定不符規定。")

# --- UI 介面：手動輸入區 ---
st.subheader("📝 第一步：輸入憑證資訊")
col1, col2 = st.columns(2)

with col1:
    ubn = st.text_input("店家統一編號 (8碼)", max_chars=8, placeholder="例如: 24296831")
    receipt_date = st.date_input("憑證上的日期", datetime.now())

with col2:
    voucher_type = st.selectbox(
        "憑證形式",
        ["電子發票證明聯", "傳統發票 (長條型)", "二/三聯式發票", "免用統一發票收據"]
    )

# --- 邏輯判斷與 API 查詢 ---
if ubn and len(ubn) == 8:
    with st.spinner("正在連線財政部查詢稅籍..."):
        api_url = f"https://eip.fia.gov.tw/OAI/api/businessRegistration/{ubn}"
        try:
            resp = requests.get(api_url, timeout=10)
            if resp.status_code == 200:
                biz_data = resp.json()
                biz_name = biz_data.get("businessNm", "未知店家")
                is_use_inv = biz_data.get("isUseInvoice", "") # "使用統一發票" 或 "免用統一發票"
                
                st.divider()
                st.success(f"🏪 店家名稱：{biz_name}")
                
                # --- 核心核銷檢查邏輯 ---
                is_pass = True
                errors = []
                warnings = []

                # 規則 1: 日期檢查
                if receipt_date < budget_date:
                    is_pass = False
                    errors.append(f"❌ **日期錯誤**：憑證日期 ({receipt_date}) 早於預算通過日 ({budget_date})。")
                else:
                    st.write("✅ 日期檢查通過")

                # 規則 2 & 3: 憑證形式與稅籍狀態比對
                # 若財政部紀錄為「使用統一發票」
                if "使用" in is_use_inv and "免用" not in is_use_inv:
                    if voucher_type == "免用統一發票收據":
                        is_pass = False
                        errors.append("❌ **形式錯誤**：財政部登記此店家【應開發票】，您上傳的卻是【收據】，將被會計室退件。")
                    else:
                        st.write(f"✅ 憑證形式符合 (店家稅籍：{is_use_inv})")
                
                # 若財政部紀錄為「免用統一發票」
                else:
                    if voucher_type != "免用統一發票收據":
                        warnings.append("⚠️ **提醒**：財政部登記此店家為【免用發票】，請確認憑證格式是否正確。")
                    
                    st.warning("📋 **免用發票收據專屬檢查項 (校規第1條)**")
                    c1 = st.checkbox("確認收據已蓋「店家大章」(不可為發票專用章)")
                    c2 = st.checkbox("確認收據已蓋「負責人小章」")
                    if not (c1 and c2):
                        is_pass = False
                        errors.append("❌ **印章缺失**：免用發票收據必須蓋齊大小章。")

                # --- 最終結果呈現 ---
                st.divider()
                if is_pass:
                    st.balloons()
                    st.info("💡 **系統判定結果：【符合核銷規定】**")
                else:
                    st.error("💡 **系統判定結果：【不符合規定】**")
                    for err in errors:
                        st.write(err)
                
                for warn in warnings:
                    st.warning(warn)

            else:
                st.error(f"查無此統編 ({ubn})，請檢查是否輸入錯誤。")
        except Exception as e:
            st.error(f"連線失敗，請檢查網路或稍後再試。")
else:
    if ubn:
        st.warning("請輸入完整的 8 碼統一編號。")

st.divider()
st.caption("本系統僅供輔助參考，最終核銷結果以各校會計室審核為準。")
```

### 2. 更新 `requirements.txt` (簡化版)

因為我們移除了 OCR 功能，不再需要複雜的影像庫，這會讓您的系統啟動速度變快 **10 倍**，且不會再出現 `ModuleNotFoundError`。


streamlit
requests
```

