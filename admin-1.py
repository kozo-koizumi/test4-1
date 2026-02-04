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
# --- 4. 商品仕様 (更新版) ---
# ===============================
# DBのカラム名に合わせたキー構成です。labelを追加しています。
product_specs = {
    "blazer":       {"label": "ブレザー", "type": "qty_size_memo", "size_options": ["S","M","L","XL"], "types": ["Aタイプ", "Bタイプ"]},
    "shirt":        {"label": "シャツ", "type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pants":        {"label": "スラックス", "type": "pants", "waist_range": (61, 111, 3), "length_placeholder": "72"},
    "vest":         {"label": "ベスト", "type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "sweater":      {"label": "セーター", "type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "sandals":      {"label": "サンダル", "type": "qty_size_memo", "size_options": {"range": (22, 31, 0.5)}},
    "pe_shirt":     {"label": "体操服（上）", "type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pe_halfpants": {"label": "ハーフパンツ", "type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pe_jacket":    {"label": "ジャージ（上）", "type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pe_pants":     {"label": "ジャージ（下）", "type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
}

# ===============================
# --- 5. 採寸入力モード ---
# ===============================
if mode == "採寸入力":
    st.title("採寸入力")
    order_id_input = st.number_input("受付番号を入力", min_value=1, step=1, key="search_input_field")

    if st.button("検索"):
        res = supabase.table("orders").select("*").eq("id", order_id_input).execute()
        if res.data and len(res.data) > 0:
            st.session_state.edit_order = res.data[0] 
            st.rerun()
        else:
            st.error(f"受付番号 {order_id_input} は登録されていません。")
            st.session_state.edit_order = None

    # --- 修正ポイント：ここを if st.button の外に出しました ---
    if st.session_state.edit_order:
        order = st.session_state.edit_order
        st.subheader(f"注文者: {order.get('name')} 様")

        # 各商品ごとの入力と保存
        items = order.get("items") or {}
        for key, spec in product_specs.items():
            try:
                qty = int(items.get(key, 0))
            except ValueError:
                qty = 0
            
            if qty <= 0:
                continue 

            display_name = spec.get("label", key)
        
            with st.container(border=True):
                st.markdown(f"### 👕 {display_name}（数量：{qty}）")
                item_data = {}
    
                if "types" in spec:
                    type_options = spec["types"]
                    current_type = order.get(f"{key}_type")
                    t_idx = type_options.index(current_type) if current_type in type_options else 0
                    item_data[f"{key}_type"] = st.selectbox("タイプ", type_options, index=t_idx, key=f"t_{key}")

                if spec["type"] == "pants":
                    w_start, w_end, w_step = spec["waist_range"]
                    waist_options = list(range(w_start, w_end, w_step))
                    db_waist = order.get(f"{key}_waist")
                    try: db_waist_val = int(float(db_waist))
                    except: db_waist_val = waist_options[0]
                
                    w_idx = waist_options.index(db_waist_val) if db_waist_val in waist_options else 0
                    item_data[f"{key}_waist"] = st.selectbox("ウエスト(cm)", waist_options, index=w_idx, key=f"w_{key}")
                    item_data[f"{key}_length"] = st.text_input("丈(cm)", value=order.get(f"{key}_length") or "", key=f"l_{key}")
                    item_data[f"{key}_memo"] = st.text_input("備考", value=order.get(f"{key}_memo") or "", key=f"m_p_{key}")
    
                elif spec["type"] == "qty_size_memo":
                    s_opt = spec.get("size_options")
                    if isinstance(s_opt, dict) and "range" in s_opt:
                        start, end, step = s_opt["range"]
                        size_choices = []
                        curr = float(start)
                        while curr <= end:
                            size_choices.append(curr if step % 1 != 0 else int(curr))
                            curr += step
                    else:
                        size_choices = s_opt
                    
                    current_size = order.get(f"{key}_size")
                    try: s_idx = size_choices.index(current_size)
                    except: s_idx = 0
                    item_data[f"{key}_size"] = st.selectbox("サイズ", size_choices, index=s_idx, key=f"s_{key}")
                    item_data[f"{key}_memo"] = st.text_input("備考", value=order.get(f"{key}_memo") or "", key=f"m_s_{key}")
    
                # 一時保存
                if st.button(f"{display_name} を一時保存", key=f"btn_{key}"):
                    try:
                        supabase.table("orders").update(item_data).eq("id", order["id"]).execute()
                        st.success(f"{display_name} の採寸データが更新されました ✅")
                    except Exception as e:
                        st.error(f"{display_name} の保存に失敗しました: {e}")

   
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
