import streamlit as st
import requests
import pandas as pd

st.title("競馬分析アプリ（スマホ対応）")

# -----------------------------
# 入力 UI
# -----------------------------
race_id = st.text_input("レースIDを入力してください")

win_rate_threshold = st.selectbox(
    "勝率閾値（％以上）",
    [0, 5, 10, 15, 20],
    index=1  # 初期値10%
)

ev_threshold = st.selectbox(
    "単勝期待値閾値（以上）",
    [0, 1.0, 1.5, 2.0],
    index=1  # 初期値1.0
)

# -----------------------------
# データ取得
# -----------------------------
if race_id:
    url = f"https://frontrunner-race.com/api/entries?id={race_id}"
    res = requests.get(url)

    if res.status_code == 200:
        data = res.json()

        # 馬データ抽出
        horses = []
        for h in data["entries"]:
            name = h["name"]
            odds = h["odds"]
            win_rate = h["predictWinRate"] * 100  # ％表示に変換
            ev = h["odds"] * h["predictWinRate"]  # 単勝期待値

            horses.append({
                "馬名": name,
                "オッズ": odds,
                "勝率（％）": win_rate,
                "単勝期待値": ev
            })

        df = pd.DataFrame(horses)

        # -----------------------------
        # 閾値フィルタ
        # -----------------------------
        df = df[df["勝率（％）"] >= win_rate_threshold]
        df = df[df["単勝期待値"] >= ev_threshold]

        # -----------------------------
        # 表示（小数点フォーマット）
        # -----------------------------
        df["オッズ"] = df["オッズ"].round(1)
        df["勝率（％）"] = df["勝率（％）"].round(1)
        df["単勝期待値"] = df["単勝期待値"].round(2)

        st.subheader("分析結果")
        st.dataframe(df)

        # -----------------------------
        # 単勝期待値ランキング（上位5）
        # -----------------------------
        st.subheader("単勝期待値ランキング（上位5）")
        df_rank = df.sort_values("単勝期待値", ascending=False).head(5)
        st.dataframe(df_rank)

    else:
        st.error("データ取得に失敗しました。レースIDを確認してください。")
