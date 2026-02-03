import streamlit as st
from supabase import create_client, Client

# ===============================
# --- 1. 初期設定 ---
# ===============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

ADMIN_ID = st.secrets["ADMIN_ID"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "edit_order" not in st.session_state:
    st.session_state.edit_order = None

# ===============================
# --- 2. ログイン画面 ---
# ===============================
if not st.session_state.logged_in:
    st.title("管理者ログイン")
    user_input = st.text_input("ユーザーID")
    pass_input = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if user_input == ADMIN_ID and pass_input == ADMIN_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("ログイン失敗")
    st.stop()

# ===============================
# --- 3. メインメニュー ---
# ===============================
mode = st.sidebar.radio("機能を選択", ["パンツ採寸入力", "注文一覧"])
if st.sidebar.button("ログアウト"):
    st.session_state.logged_in = False
    st.rerun()

# ===============================
# --- 4. 画面表示の分岐 ---
# ===============================

# --- A. パンツ採寸入力 ---
if mode == "パンツ採寸入力":
    st.title("パンツ採寸入力")
    
    order_id_input = st.number_input("受付番号を入力してください", min_value=1, step=1, key="search_input_field")

    if st.button("検索"):
        res = supabase.table("orders").select("*").eq("id", order_id_input).single().execute()
        if res.data:
            st.session_state.edit_order = res.data
        else:
            st.error("該当する受付番号が見つかりません。")
            st.session_state.edit_order = None

    if st.session_state.edit_order:
        order = st.session_state.edit_order
        st.subheader(f"注文者: {order.get('name')} 様")
        st.write(f"シャツ: {order.get('shirt', 0)} / パンツ: {order.get('pants', 0)} / 靴下: {order.get('socks', 0)}")

        with st.form("pants_measure_form"):
            waist_options = [i for i in range(61, 111, 3)]
            try:
                db_waist = int(float(order.get("pants_waist") or 61))
            except:
                db_waist = 61

            waist = st.selectbox(
                "パンツ ウエスト(cm)", 
                options=waist_options, 
                index=waist_options.index(db_waist) if db_waist in waist_options else 0
            )
            
            length = st.text_input("パンツ 丈(cm)", value=order.get("pants_length") or "")
            memo = st.text_input("備考", value=order.get("pants_memo") or "")

            if st.form_submit_button("採寸完了（お客様の確認へ進める）"):
                # DBを更新
                supabase.table("orders").update({
                    "pants_waist": waist,
                    "pants_length": length,
                    "pants_memo": memo,  # ←修正点：カンマを追加
                    "status": "measured"
                }).eq("id", order["id"]).execute()
                
                st.session_state.edit_order = None
                st.toast(f"ID:{order['id']} を保存しました")
                st.rerun()

# --- B. 注文一覧 ---
elif mode == "注文一覧":
    st.title("注文一覧")
    res = supabase.table("orders").select("id", "name").order("id", desc=False).execute()
    orders = res.data or []

    if not orders:
        st.info("注文データがありません。")
    else:
        # 修正点：括弧を閉じ、末尾の日本語を削除
        st.dataframe(orders, hide_index=True, use_container_width=True)
