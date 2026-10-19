import streamlit as st
import requests
import pandas as pd

# API
def get_race_list(date):
    url = f"https://frontrunner-race.com/api/races?date={date}"
    return requests.get(url).json()

def get_entries(race_id):
    url = f"https://frontrunner-race.com/api/race/{race_id}/entries"
    return requests.get(url).json()

# EV計算（None対策入り）
def calc_ev(entries, winrate_threshold, ev_threshold):
    results = []
    for e in entries:

        if e["predictWinRate"] is None:
            continue

        win = float(e["predictWinRate"])

        if e["odds"] is None:
            continue

        odds = float(e["odds"])
        ev = win * odds

        if win >= winrate_threshold and ev >= ev_threshold:
            results.append({
                "馬番": e["number"],
                "馬名": e["name"],
                "オッズ": odds,
                "人気": e["popularity"],
                "勝率(%)": win * 100,
                "期待値": ev
            })

    return sorted(results, key=lambda x: x["期待値"], reverse=True)

# 色付け関数
def highlight_rows(row):
    if row["期待値"] >= 2.0:
        return ["background-color: #d0ffd0"] * len(row)
    elif row["期待値"] < 1.0:
        return ["background-color: #ffd0d0"] * len(row)
    else:
        return [""] * len(row)

# Streamlit UI
st.set_page_config(page_title="競馬分析アプリ（スマホ対応）", layout="wide")

st.title("🐎 競馬分析アプリ（スマホ対応 Web版）")

# 入力
date = st.text_input("開催日 (YYYY-MM-DD)", "2026-10-18")

winrate_threshold = st.selectbox("勝率閾値（％）", [5,10,15,20,25,30]) / 100
ev_threshold = float(st.selectbox("EV閾値", [f"{x/10:.1f}" for x in range(10,31)]))

# レース一覧取得
if st.button("レース一覧取得"):
    race_list = get_race_list(date)

    if "venues" not in race_list or len(race_list["venues"]) == 0:
        st.error("開催日ではありません")
    else:
        st.success("レース一覧を取得しました")

        races = []
        for venue in race_list["venues"]:
            for race in venue["races"]:
                race_number = race.get("number", "?")
                label = f"{venue['name']} {race_number}R"
                races.append((label, race["id"]))

        st.session_state["races"] = races

# レース選択
if "races" in st.session_state:
    race_labels = [r[0] for r in st.session_state["races"]]
    selected_race = st.selectbox("レースを選択", race_labels)

    # 単レース分析
    if st.button("このレースだけ分析"):
        race_id = [rid for label, rid in st.session_state["races"] if label == selected_race][0]
        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)

        if ranking:
            df = pd.DataFrame(ranking)
            df["レース"] = selected_race

            # ★ 列順変更（レース → 馬番の左）
            df = df[["レース", "馬番", "馬名", "オッズ", "人気", "勝率(%)", "期待値"]]

            styler = df.style.apply(highlight_rows, axis=1)\
                             .format({
                                 "オッズ": "{:.1f}",
                                 "勝率(%)": "{:.1f}",
                                 "期待値": "{:.2f}"
                             })

            st.dataframe(styler, use_container_width=True)
        else:
            st.warning("条件に合う馬がいません")

# 全レース分析（全件）
if "races" in st.session_state and st.button("全レース分析（全件）"):
    all_rows = []

    for label, race_id in st.session_state["races"]:
        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)

        for r in ranking:
            r["レース"] = label
            all_rows.append(r)

    if all_rows:
        df = pd.DataFrame(all_rows)

        # ★ 列順変更
        df = df[["レース", "馬番", "馬名", "オッズ", "人気", "勝率(%)", "期待値"]]

        styler = df.style.apply(highlight_rows, axis=1)\
                         .format({
                             "オッズ": "{:.1f}",
                             "勝率(%)": "{:.1f}",
                             "期待値": "{:.2f}"
                         })

        st.dataframe(styler, use_container_width=True)
    else:
        st.warning("条件に合う馬がいません")

# EV上位1〜5位
if "races" in st.session_state and st.button("全レース EV上位1〜5位"):
    top_rows = []

    for label, race_id in st.session_state["races"]:
        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)
        top5 = ranking[:5]

        for r in top5:
            r["レース"] = label
            top_rows.append(r)

    if top_rows:
        df = pd.DataFrame(top_rows)

        # ★ 列順変更
        df = df[["レース", "馬番", "馬名", "オッズ", "人気", "勝率(%)", "期待値"]]

        styler = df.style.apply(highlight_rows, axis=1)\
                         .format({
                             "オッズ": "{:.1f}",
                             "勝率(%)": "{:.1f}",
                             "期待値": "{:.2f}"
                         })

        st.dataframe(styler, use_container_width=True)
    else:
        st.warning("条件に合う馬がいません")