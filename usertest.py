import streamlit as st
import requests
from supabase import create_client, Client
from streamlit_autorefresh import st_autorefresh


# ===============================
# --- Supabase設定 ---
# ===============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===============================
# --- 固定ユーザー認証 ---
# ===============================
FIXED_USER_ID = st.secrets["USER_ID"]
FIXED_PASSWORD = st.secrets["PASSWORD"]

# ===============================
# --- 商品マスタ ---
# ===============================
# ※価格は仮（必要に応じて調整してください）
products = {
    "blazer":       {"label": "ブレザー",                "price": 12000},
    "shirt":        {"label": "シャツ",                  "price": 2000},
    "pants":        {"label": "ズボン",                  "price": 3000},
    "vest":         {"label": "ベスト",                  "price": 4000},
    "sweater":      {"label": "セーター",                "price": 4500},
    "necktie":      {"label": "ネクタイ",                "price": 1500},
    "sandals":      {"label": "サンダル",                "price": 1800},
    "pe_shirt":     {"label": "体操服（半袖）",          "price": 2200},
    "pe_halfpants": {"label": "体操服（ハーフパンツ）",  "price": 2000},
    "pe_jacket":    {"label": "体操服（ジャージ上着）",  "price": 5000},
    "pe_pants":     {"label": "体操服（パンツ）",        "price": 3800},
}

# ===============================
# --- 入力仕様（商品別フォーム定義） ---
# ===============================
# type:
#  - "qty_size_memo": 数量 + サイズ + 備考
#  - "pants":         数量 + ウエスト + 丈 + 備考
#  - "qty_memo":      数量 + 備考（サイズ不要）
# size_options:
#  - リストの場合: セレクトボックス
#  - "free_text":     自由入力
#  - 数値レンジ:      {"range": (min, max, step)} でセレクトボックス
product_specs = {
    "blazer":       {"type": "qty_size_memo", 
                     "size_options": ["S","M","L","XL"],
                     "types": ["Aタイプ", "Bタイプ"]},
    "shirt":        {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pants":        {"type": "pants",         "waist_range": (61, 111, 3), "length_placeholder": "72"},
    "vest":         {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "sweater":      {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "necktie":      {"type": "qty_memo"},
    "sandals":      {"type": "qty_size_memo", "size_options": {"range": (22, 31, 1)}},  # 例: 22〜30cm
    "pe_shirt":     {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pe_halfpants": {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pe_jacket":    {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
    "pe_pants":     {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]},
}

st.set_page_config(page_title="注文登録", layout="wide")

# ===============================
# --- CSS ---
# ===============================
st.markdown("""
<style>
.stTextInput input,
.stSelectbox div[data-baseweb="select"] { height: 32px; font-size: 13px; }
.w-xs input, .w-xs div[data-baseweb="select"] { width: 60px !important; }
.w-s  input, .w-s  div[data-baseweb="select"] { width: 90px !important; }
.w-m  input, .w-m  div[data-baseweb="select"] { width: 160px !important; }
.w-l  input, .w-l  div[data-baseweb="select"] { width: 260px !important; }
.w-xl input { width: 100% !important; }
.header { font-weight: 600; font-size: 14px; color: #555; }
.total-box { background: #f5f7fa; padding: 10px; border-radius: 8px; text-align: right; font-size: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ===============================
# --- セッションステート初期化 ---
# ===============================
if "phase" not in st.session_state:
    st.session_state.phase = "login"
if "order_data" not in st.session_state:
    st.session_state.order_data = {}
if "order_id" not in st.session_state:
    st.session_state.order_id = None
if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False

# ===============================
# --- ログイン画面 ---
# ===============================
if not st.session_state.user_logged_in:
    st.title("ログイン")
    user_id_input = st.text_input("ユーザーID")
    password_input = st.text_input("パスワード", type="password")
    if st.button("ログイン"):
        if user_id_input == FIXED_USER_ID and password_input == FIXED_PASSWORD:
            st.session_state.user_logged_in = True
            st.session_state.phase = "input"
            st.success("ログイン成功")
            st.rerun()
        else:
            st.error("ログイン失敗")
    st.stop()

# ===============================
# --- 入力コンポーネント ---
# ===============================
def product_row(label: str, key: str):
    """商品別の入力行を定義に基づき生成"""
    st.write(f"### {label}")
    spec = product_specs.get(key, {"type": "qty_size_memo", "size_options": ["S","M","L","XL"]})

    # 数量（共通）
    qty = st.selectbox("数量", range(11), key=f"{key}_qty")
    item_type = None
    if "types" in spec:
        item_type = st.selectbox(
            "タイプ", 
            spec["types"], 
            index=0,  # 0番目（Aタイプ）を初期選択にする
            key=f"{key}_type"
        )
    # 種別ごとに追加フィールド
    if spec["type"] == "pants":
        waist_min, waist_max, waist_step = spec.get("waist_range", (61,111,3))
        waist_choices = list(range(waist_min, waist_max, waist_step))
        waist = st.selectbox("ウエスト", waist_choices, index=None, key=f"{key}_waist", format_func=lambda x: "" if x is None else str(x))
        length = st.text_input("丈", key=f"{key}_length", placeholder=spec.get("length_placeholder", "丈を入力"))
        memo = st.text_input("備考", key=f"{key}_memo", placeholder="備考を入力")
        return {"qty": qty, "waist": waist, "length": length, "memo": memo}

    elif spec["type"] == "qty_memo":
        memo = st.text_input("備考", key=f"{key}_memo", placeholder="備考を入力")
        return {"qty": qty, "memo": memo}

    else:  # "qty_size_memo"
        size_opt = spec.get("size_options", ["S","M","L","XL"])
        if isinstance(size_opt, dict) and "range" in size_opt:
            mn, mx, step = size_opt["range"]
            size_choices = list(range(mn, mx, step))
            size = st.selectbox("サイズ", size_choices, index=None, key=f"{key}_size", format_func=lambda x: "" if x is None else str(x))
        elif size_opt == "free_text":
            size = st.text_input("サイズ", key=f"{key}_size", placeholder="サイズを入力")
        else:
            size = st.selectbox("サイズ", size_opt, index=None, key=f"{key}_size", format_func=lambda x: "" if x is None else str(x))
        memo = st.text_input("備考", key=f"{key}_memo", placeholder="備考を入力")
        return {"qty": qty, "size": size, "memo": memo}

# ===============================
# --- 入力画面 ---
# ===============================
if st.session_state.phase == "input":
    st.title("ご注文入力")

    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

    # --- お客様情報 ---
    st.write("### 1. お客様情報")
    name = st.text_input("お名前（必須）", value=st.session_state.order_data.get("name", ""))
    zipcode = st.text_input("郵便番号(必須)  ハイフンなしで入力", value=st.session_state.order_data.get("zipcode",""), max_chars=7,placeholder="例: 6068275")

    if st.button("住所検索"):
        clean_zip = zipcode.replace("-", "").replace(" ", "")
        try:
            res = requests.get(f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={clean_zip}", timeout=6).json()
            if res.get("results"):
                r = res["results"][0]
                st.session_state.address_input = r["address1"] + r["address2"] + r["address3"]
            else:
                st.warning("該当する住所が見つかりませんでした。")
        except Exception as e:
            st.error("住所検索に失敗しました。時間をおいて再度お試しください。")

    address = st.text_input(
        "住所（必須）",
        value=st.session_state.get("address_input", st.session_state.order_data.get("address",""))
    )
    phone = st.text_input("電話番号（任意）", value=st.session_state.order_data.get("phone",""), placeholder="例: 0750010001")
    email = st.text_input("メールアドレス（任意）", value=st.session_state.order_data.get("email",""),placeholder="例: taro@outlook.jp")

    st.divider()
    st.write("### 2. 商品選択")

    # --- 商品ごとにフォーム生成 ---
    order_data = {}
    for key, info in products.items():
        order_data[key] = product_row(info["label"], key)

    # --- 合計金額計算 ---
    total_price = 0
    for key, info in products.items():
        qty = order_data[key].get("qty", 0) or 0
        total_price += qty * info["price"]

    st.markdown(f"<div class='total-box'>合計金額：{total_price:,} 円</div>", unsafe_allow_html=True)

    if st.button("確認画面へ進む", type="primary", use_container_width=True):
        if not name or not address or total_price == 0:
            st.error("必須項目を入力してください")
        else:
            st.session_state.order_data = {
                "name": name,
                "zipcode": zipcode,
                "address": address,
                "phone": phone,
                "email": email,
                **order_data,
                "total_price": total_price
            }
            st.session_state.phase = "confirm"
            st.rerun()

# ===============================
# --- 確認画面 ---
# ===============================
elif st.session_state.phase == "confirm":
    data = st.session_state.order_data
    st.title("注文内容の確認")

    col_info, col_order = st.columns(2)
    with col_info:
        st.write("【お客様情報】")
        st.write(f"お名前: {data['name']}")
        st.write(f"郵便番号: {data['zipcode']}")
        st.write(f"住所: {data['address']}")
        st.write(f"電話番号: {data.get('phone','未入力')}")
        st.write(f"メール: {data.get('email','未入力')}")

    def format_item_line(pkey: str, item: dict) -> str:
        spec = product_specs.get(pkey, {"type": "qty_size_memo"})
        memo = f" / 備考: {item['memo']}" if item.get("memo") else ""
        if spec["type"] == "pants":
            # パンツ用表示
            waist = item.get("waist", "")
            length = item.get("length", "")
            return f"{products[pkey]['label']}: {item['qty']}点 (ウエスト: {waist}, 丈: {length}){memo}"
        elif spec["type"] == "qty_memo":
            return f"{products[pkey]['label']}: {item['qty']}点{memo}"
        else:
            size = item.get("size", "")
            return f"{products[pkey]['label']}: {item['qty']}点 ({size}){memo}"

    with col_order:
        st.write("【注文商品】")
        for key in products:
            item = data.get(key, {})
            if item and (item.get("qty") or 0) > 0:
                st.write(format_item_line(key, item))
        st.write(f"合計金額: {data['total_price']:,}円")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("修正する", use_container_width=True):
            data = st.session_state.order_data
            # --- 商品入力値を session_state に戻す ---
            for key in products:
                item = data.get(key, {})
                st.session_state[f"{key}_qty"] = item.get("qty", 0)
                spec = product_specs.get(key, {"type": "qty_size_memo"})
                if spec["type"] == "pants":
                    st.session_state[f"{key}_waist"] = item.get("waist", None)
                    st.session_state[f"{key}_length"] = item.get("length", "")
                elif spec["type"] == "qty_memo":
                    st.session_state[f"{key}_memo"] = item.get("memo", "")
                else:
                    st.session_state[f"{key}_size"] = item.get("size", None)
                    st.session_state[f"{key}_memo"] = item.get("memo", "")

            # --- 顧客情報 ---
            st.session_state["address_input"] = data["address"]

            st.session_state.phase = "input"
            st.rerun()

    with c2:
        if st.button("確定する", type="primary", use_container_width=True):

            insert_data = {
                "name": data["name"],
                "zipcode": data["zipcode"],
                "address": data["address"],
                "phone": data.get("phone"),
                "email": data.get("email"),
                "total_price": data["total_price"],
                "status": "waiting",
            }    

            for key in products:
                item = data.get(key, {})
                spec = product_specs.get(key, {"type": "qty_size_memo"})

                insert_data[key] = item.get("qty", 0)
    
                if spec["type"] == "pants":
                    insert_data[f"{key}_waist"] = item.get("waist")
                    insert_data[f"{key}_length"] = item.get("length")
                    insert_data[f"{key}_memo"] = item.get("memo", "")
                elif spec["type"] == "qty_memo":
                    insert_data[f"{key}_memo"] = item.get("memo", "")
                else:
                    insert_data[f"{key}_size"] = item.get("size")
                    insert_data[f"{key}_memo"] = item.get("memo", "")

            res = supabase.table("orders").insert(insert_data).execute()

            if res.data:
                st.session_state.order_id = res.data[0]["id"]
                st.session_state.phase = "complete"
                st.rerun()

# ===============================
# 採寸待ち画面
# ===============================
elif st.session_state.phase == "complete":
    order = supabase.table("orders") \
        .select("*") \
        .eq("id", st.session_state.order_id) \
        .single() \
        .execute().data

    if order["status"] == "waiting":
        st.title("採寸待ち")
        st.write(f"受付番号：{order['id']}")
        st.info("スタッフが採寸中です。しばらくお待ちください。")

        st_autorefresh(interval=5000, key="wait")

    elif order["status"] == "measured":
        st.session_state.phase = "final_confirm"
        st.rerun()

# ===============================
# 最終確認
# ===============================
elif st.session_state.phase == "final_confirm":
    order = supabase.table("orders") \
        .select("*") \
        .eq("id", st.session_state.order_id) \
        .single() \
        .execute().data

    st.title("最終確認")
    st.success("採寸が完了しました")

    st.write(f"ウエスト：{order.get('pants_waist')} cm")
    st.write(f"丈：{order.get('pants_length')} cm")

    if st.button("この内容で確定"):
        supabase.table("orders").update({
            "status": "completed"
        }).eq("id", order["id"]).execute()

        st.session_state.phase = "done"
        st.rerun()

# ===============================
# 完了
# ===============================
elif st.session_state.phase == "done":
    st.title("ありがとうございました")
    st.success("注文が確定しました")
    st.write(f"受付番号：{st.session_state.order_id}")
    st.write("受付番号をお控えください。")
    st.session_state.pop("address_input", None)
  
    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()
