




if st.form_submit_button("採寸完了（お客様の確認へ進める）"):
    supabase.table("orders").update({
        "pants_waist": waist,
        "pants_length": length,
        "pants_memo": memo,
        "status": "measured"  # これで客側に「確認ボタン」が出る
    }).eq("id", order["id"]).execute()
    st.success("お客様の画面に確認ボタンを表示しました。")
