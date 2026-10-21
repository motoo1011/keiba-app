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

# 単勝期待値計算
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

        jockey = e.get("jockey", "不明")

        results.append({
            "馬番": e["number"],
            "馬名": e["name"],
            "騎手": jockey,
            "オッズ": odds,
            "人気": e["popularity"],
            "勝率(%)": win * 100,
            "単勝期待値": ev,
            "逃げ馬指数": e.get("predictFirstPhaseIndex", 0)  # ★修正ポイント
        })

    return sorted(results, key=lambda x: x["単勝期待値"], reverse=True)

# EV色付け（背景）
def highlight_rows(row):
    if row["単勝期待値"] >= 2.0:
        return ["background-color: #d0ffd0"] * len(row)
    elif row["単勝期待値"] < 1.0:
        return ["background-color: #ffd0d0"] * len(row)
    else:
        return [""] * len(row)

# UI
st.set_page_config(page_title="🐎競馬分析アプリ", layout="wide")
st.title("🐎競馬分析アプリ")

date = st.text_input("開催日 (YYYY-MM-DD)", "2026-10-18")
winrate_threshold = st.selectbox("勝率閾値（％以上）", [0, 5, 10, 15, 20, 25, 30]) / 100
ev_threshold = float(st.selectbox("単勝期待値閾値（以上）", ["0"] + [f"{x/10:.1f}" for x in range(10, 31)]))

# レース一覧取得
if st.button("レース一覧取得"):
    race_list = get_race_list(date)

    if "venues" not in race_list or len(race_list["venues"]) == 0:
        st.error("開催日ではありません")
    else:
        st.success("レース一覧を取得しました")

        races = []
        for venue in race_list["venues"]:
            for idx, race in enumerate(venue["races"], start=1):
                race_number = race.get("number", idx)

                race_name = race.get("name")
                if not race_name:
                    race_name = race.get("raceNameShort", "レース名不明")

                label = f"{venue['name']} {race_number}R（{race_name}）"

                races.append((label, race["id"], f"{venue['name']} {race_number}R", race_name))

        st.session_state["races"] = races

# レース選択
if "races" in st.session_state:
    race_labels = [r[0] for r in st.session_state["races"]]
    selected_race = st.selectbox("レースを選択", race_labels)

    if st.button("このレースだけ分析"):
        for label, rid, race_disp, race_name in st.session_state["races"]:
            if label == selected_race:
                race_id = rid
                race_display = race_disp
                race_name_display = race_name
                break

        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)

        if ranking:
            df = pd.DataFrame(ranking)
            df["レース"] = race_display
            df["レース名"] = race_name_display

            df = df[[
                "レース", "レース名",
                "馬番", "馬名", "騎手",
                "オッズ", "人気", "勝率(%)", "単勝期待値",
                "逃げ馬指数"
            ]]

            styler = (
                df.style
                .apply(highlight_rows, axis=1)
                .format({
                    "オッズ": "{:.1f}",
                    "人気": "{:.0f}",
                    "勝率(%)": "{:.1f}",
                    "単勝期待値": "{:.2f}",
                    "逃げ馬指数": "{:.1f}"
                })
            )

            st.dataframe(styler, use_container_width=True)
        else:
            st.warning("条件に合う馬がいません")

# 全レース分析
if "races" in st.session_state and st.button("全レース分析（全件）"):
    all_rows = []

    for label, race_id, race_disp, race_name in st.session_state["races"]:
        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)

        for r in ranking:
            r["レース"] = race_disp
            r["レース名"] = race_name
            all_rows.append(r)

    if all_rows:
        df = pd.DataFrame(all_rows)
        df = df[[
            "レース", "レース名",
            "馬番", "馬名", "騎手",
            "オッズ", "人気", "勝率(%)", "単勝期待値",
            "逃げ馬指数"
        ]]

        styler = (
            df.style
            .apply(highlight_rows, axis=1)
            .format({
                "オッズ": "{:.1f}",
                "人気": "{:.0f}",
                "勝率(%)": "{:.1f}",
                "単勝期待値": "{:.2f}",
                "逃げ馬指数": "{:.1f}"
            })
        )

        st.dataframe(styler, use_container_width=True)
    else:
        st.warning("条件に合う馬がいません")

# 上位1〜5位
if "races" in st.session_state and st.button("全レース 単勝期待値 上位1〜5位"):
    top_rows = []

    for label, race_id, race_disp, race_name in st.session_state["races"]:
        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)
        top5 = ranking[:5]

        for r in top5:
            r["レース"] = race_disp
            r["レース名"] = race_name
            top_rows.append(r)

    if top_rows:
        df = pd.DataFrame(top_rows)
        df = df[[
            "レース", "レース名",
            "馬番", "馬名", "騎手",
            "オッズ", "人気", "勝率(%)", "単勝期待値",
            "逃げ馬指数"
        ]]

        styler = (
            df.style
            .apply(highlight_rows, axis=1)
            .format({
                "オッズ": "{:.1f}",
                "人気": "{:.0f}",
                "勝率(%)": "{:.1f}",
                "単勝期待値": "{:.2f}",
                "逃げ馬指数": "{:.1f}"
            })
        )

        st.dataframe(styler, use_container_width=True)
    else:
        st.warning("条件に合う馬がいません")
