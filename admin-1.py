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
            st.success("ログイン成功！")
            st.rerun()  # ← ここで強制再実行して「メインメニュー」側へ飛ばす
        else:
            st.error("ユーザーIDまたはパスワードが違います")
    
    st.stop() # ログインしていない場合は、これ以降のコードを実行させない

# ===============================
# --- 3. メインメニュー ---
# ===============================
mode = st.sidebar.radio("機能を選択", ["採寸入力", "注文一覧"])
if st.sidebar.button("ログアウト"):
    st.session_state.logged_in = False
    st.experimental_rerun()

# ===============================
# --- 4. 商品仕様 ---
# ===============================
product_specs = {
    "blazer":       {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "shirt":        {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pants":        {"type": "pants", "waist_range": (61, 111, 3), "length_placeholder": "72"},
    "vest":         {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "sweater":      {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "sandals":      {"type": "qty_size_memo", "size_options": {"range": (22, 31, 1)}},
    "pe_shirt":     {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pe_halfpants": {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pe_jacket":    {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pe_pants":     {"type": "pants", "waist_range": (61, 111, 3), "length_placeholder": "72"},
}

# ===============================
# --- 5. 採寸入力モード ---
# ===============================
if mode == "採寸入力":
    st.title("採寸入力")

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

        with st.form(f"measure_form_{order['id']}"):
            updated_data = {}
            for key, spec in product_specs.items():
                qty = order.get(key, 0)
                st.write(f"**{key}（数量: {qty}）**")

                # 数量
                qty_input = st.number_input(
                    "数量",
                    min_value=0, max_value=20,
                    value=qty,
                    key=f"{key}_qty_{order['id']}"
                )
                updated_data[key] = qty_input

                if spec["type"] == "pants":
                    waist_options = list(range(*spec["waist_range"]))
                    db_waist = int(order.get(f"{key}_waist") or waist_options[0])
                    waist_input = st.selectbox(
                        "ウエスト(cm)",
                        options=waist_options,
                        index=waist_options.index(db_waist) if db_waist in waist_options else 0,
                        key=f"{key}_waist_{order['id']}"
                    )
                    length_input = st.text_input(
                        "丈(cm)",
                        value=order.get(f"{key}_length") or "",
                        key=f"{key}_length_{order['id']}"
                    )
                    memo_input = st.text_input(
                        "備考",
                        value=order.get(f"{key}_memo") or "",
                        key=f"{key}_memo_{order['id']}"
                    )
                    updated_data[f"{key}_waist"] = waist_input
                    updated_data[f"{key}_length"] = length_input
                    updated_data[f"{key}_memo"] = memo_input

                elif spec["type"] == "qty_size_memo":
                    size_opt = spec.get("size_options", ["S","M","L","XL"])
                    if isinstance(size_opt, dict) and "range" in size_opt:
                        mn, mx, step = size_opt["range"]
                        size_choices = list(range(mn, mx, step))
                    else:
                        size_choices = size_opt
                    size_input = st.selectbox(
                        "サイズ",
                        options=size_choices,
                        index=size_choices.index(order.get(f"{key}_size")) if order.get(f"{key}_size") in size_choices else 0,
                        key=f"{key}_size_{order['id']}"
                    )
                    memo_input = st.text_input(
                        "備考",
                        value=order.get(f"{key}_memo") or "",
                        key=f"{key}_memo_{order['id']}"
                    )
                    updated_data[f"{key}_size"] = size_input
                    updated_data[f"{key}_memo"] = memo_input

            if st.form_submit_button("採寸完了（お客様の確認へ進める）"):
                updated_data["status"] = "measured"
                supabase.table("orders").update(updated_data).eq("id", order["id"]).execute()
                st.session_state.edit_order = None
                st.toast(f"ID:{order['id']} を保存しました")
                st.experimental_rerun()

# ===============================
# --- 6. 注文一覧モード ---
# ===============================
elif mode == "注文一覧":
    st.title("注文一覧")

    res = supabase.table("orders").select("id", "name", "status").order("id", desc=False).execute()
    orders = res.data or []

    if not orders:
        st.info("注文データがありません。")
    else:
        st.dataframe(orders, hide_index=True, use_container_width=True)
