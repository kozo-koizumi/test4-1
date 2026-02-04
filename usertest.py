import streamlit as st
import requests
from supabase import create_client, Client
#from streamlit_autorefresh import st_autorefresh

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
# --- 商品入力コンポーネント ---
# ===============================
def product_row(label: str, key: str):
    st.markdown(f"### {label}")
    qty = st.selectbox("数量を選択してください", options=list(range(11)), key=f"cust_qty_{key}")
    return {"qty": qty}
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
    zipcode = st.text_input("郵便番号(必須)  ハイフンなしで入力", value=st.session_state.order_data.get("zipcode",""), max_chars=7, placeholder="例: 6068275")

    if st.button("住所検索"):
        clean_zip = zipcode.replace("-", "").replace(" ", "")
        try:
            res = requests.get(f"https://zipcloud.ibsnet.co.jp/api/search?zipcode={clean_zip}", timeout=6).json()
            if res.get("results"):
                r = res["results"][0]
                st.session_state.address_input = r["address1"] + r["address2"] + r["address3"]
            else:
                st.warning("該当する住所が見つかりませんでした。")
        except:
            st.error("住所検索に失敗しました。時間をおいて再度お試しください。")

    address = st.text_input("住所（必須）", value=st.session_state.get("address_input", st.session_state.order_data.get("address","")))
    phone = st.text_input("電話番号（任意）", value=st.session_state.order_data.get("phone",""))
    email = st.text_input("メールアドレス（任意）", value=st.session_state.order_data.get("email",""))

    st.divider()
    st.write("### 2. 商品選択")

    # --- 商品ごとにフォーム生成 ---
    order_data = {}
    for key, info in products.items():
        order_data[key] = product_row(info["label"], key)

    # --- 合計金額計算 ---
    total_price = sum(order_data[k]["qty"] * products[k]["price"] for k in products)

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
                "items": {k: order_data[k]["qty"] for k in products},
                "total_price": total_price
            }
            st.session_state.phase = "confirm"
            st.rerun()

    # ===============================
    # --- 確認画面 --- (ここをインデントして if の中に含めました)
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

    with col_order:
        st.write("【注文商品】")
        for key, qty in data["items"].items():
            if qty > 0:
                st.write(f"{products[key]['label']}: {qty}点")
        st.write(f"合計金額: {data['total_price']:,}円")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("修正する", use_container_width=True):
            st.session_state.phase = "input"
            st.rerun()
    with c2:
        if st.button("採寸する", type="primary", use_container_width=True):
            insert_data = {
                "name": data["name"],
                "zipcode": data["zipcode"],
                "address": data["address"],
                "phone": data.get("phone"),
                "email": data.get("email"),
                "total_price": data["total_price"],
                "status": "waiting",
                "items": data["items"]  # JSONB保存
            }
            res = supabase.table("orders").insert(insert_data).execute()
            if res.data:
                st.session_state.order_id = res.data[0]["id"]
                st.session_state.phase = "complete"
                st.rerun()

# ===============================
# --- 採寸待ち画面（数量変更可能） ---
# ===============================
#from streamlit_autorefresh import st_autorefresh
elif st.session_state.phase == "complete":
    order = supabase.table("orders").select("*").eq("id", st.session_state.order_id).single().execute().data

    st.title("採寸待ち（数量変更可）")
    st.write(f"受付番号：{order['id']}")

    # 数量変更用のエクスパンダー
    with st.expander("数量を変更する"):
        updated_items = {}
        total_price = 0

        for key, info in products.items():
            current_qty = order["items"].get(key, 0)
            qty = st.selectbox(
                info["label"],
                options=list(range(11)),
                index=current_qty,
                key=f"wait_qty_{key}",
            )
            updated_items[key] = qty
            total_price += qty * info["price"]

        st.write(f"合計金額：¥{total_price:,}")

        if st.button("この内容で数量を更新"):
            supabase.table("orders").update({
                "items": updated_items,
                "total_price": total_price
            }).eq("id", order["id"]).execute()
            st.success("数量を更新しました")
            st.rerun()

    # 最新状態チェック用ボタン
    if st.button("最新の状態を確認"):
        order = supabase.table("orders").select("*").eq("id", st.session_state.order_id).single().execute().data
        if order["status"] == "measured":
            st.session_state.phase = "final_confirm"
            st.rerun()
        else:
            st.info("まだ採寸は完了していません。")

    # =========================
    # 採寸完了
    # =========================
    elif order["status"] == "measured":
        st.info("採寸が完了しました。内容をご確認ください。")
        st.session_state.phase = "final_confirm"

        # measured になったら一度だけ items を展開
        items = order.get("items", {})
        update_data = {k: items.get(k, 0) for k in products.keys()}

        supabase.table("orders").update(update_data).eq("id", order["id"]).execute()

        st.rerun()

# ===============================
# --- 最終確認 ---
# ===============================
elif st.session_state.phase == "final_confirm":
    order = supabase.table("orders").select("*").eq("id", st.session_state.order_id).single().execute().data
    st.title("最終確認")
    st.success("採寸が完了しました")
    st.write(f"ウエスト：{order.get('pants_waist','')} cm")
    st.write(f"丈：{order.get('pants_length','')} cm")

    if st.button("この内容で確定"):
        supabase.table("orders").update({"status": "completed"}).eq("id", order["id"]).execute()
        st.session_state.phase = "done"
        st.rerun()

# ===============================
# --- 完了画面 ---
# ===============================
elif st.session_state.phase == "done":
    st.title("ありがとうございました")
    st.success("注文が確定しました")
    st.write(f"受付番号：{st.session_state.order_id}")
    st.write("受付番号をお控えください。")

    if st.button("ログアウト"):
        st.session_state.clear()
        st.rerun()
