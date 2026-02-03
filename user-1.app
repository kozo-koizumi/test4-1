import streamlit as st
from supabase import create_client, Client
import time

# --- 初期設定 ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if "user_order_id" not in st.session_state:
    st.session_state.user_order_id = None

# ===============================
# STEP 1: 入力画面
# ===============================
if st.session_state.user_order_id is None:
    st.title("ご注文入力")
    with st.form("input_form"):
        name = st.text_input("お名前")
        # 数量入力（省略）
        if st.form_submit_button("次へ"):
            res = supabase.table("orders").insert({
                "name": name, 
                "status": "waiting"  # 最初は待機状態
            }).execute()
            st.session_state.user_order_id = res.data[0]["id"]
            st.rerun()

# --- STEP 2: 待機または最終確認 ---
else:
    # DBから最新の注文情報とステータスを取得
    res = supabase.table("orders").select("*").eq("id", st.session_state.user_order_id).single().execute()
    order = res.data

    if order:
        # ステータスがスタッフによって 'measured' (採寸済み) に変更されたかチェック
        if order.get("status") == "waiting":
            st.title(f"受付番号: {order['id']}")
            st.warning("現在、スタッフが採寸データを入力中です。しばらくお待ちください...")
            
            # 5秒おきに「ボタンを出していいか」チェックするためにリロード
            time.sleep(5)
            st.rerun()

        elif order.get("status") == "measured":
            st.title("最終確認")
            st.success("採寸が完了しました。内容を確認してください。")

            # スタッフが入力した採寸データも表示
            st.write(f"お名前: {order['name']} 様")
            col1, col2 = st.columns(2)
            col1.metric("ウエスト", f"{order.get('pants_waist')} cm")
            col2.metric("パンツ丈", f"{order.get('pants_length')} cm")
            
            st.write("【最終注文数】")
            st.write(f"シャツ: {order.get('shirt')} / パンツ: {order.get('pants')} / 靴下: {order.get('socks')}")

            if st.button("この内容で注文を確定する"):
                # 最後にステータスを 'completed' にして完全に終了
                supabase.table("orders").update({"status": "completed"}).eq("id", order["id"]).execute()
                st.session_state.final_done = True
                st.rerun()

# 最終完了画面
if st.session_state.get("final_done"):
    st.title("ありがとうございました")
    st.write("注文が確定しました。")
    if st.button("トップに戻る"):
        st.session_state.clear()
        st.rerun()


