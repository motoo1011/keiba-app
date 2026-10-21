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

        jockey = e.get("jockey", "不明")  # ★略称のまま（辞書作成のため）

        if win >= winrate_threshold and ev >= ev_threshold:
            results.append({
                "馬番": e["number"],
                "馬名": e["name"],
                "騎手": jockey,
                "オッズ": odds,
                "人気": e["popularity"],
                "勝率(%)": win * 100,
                "単勝期待値": ev
            })

    return sorted(results, key=lambda x: x["単勝期待値"], reverse=True)

# 色付け
def highlight_rows(row):
    if row["単勝期待値"] >= 2.0:
        return ["background-color: #d0ffd0"] * len(row)
    elif row["単勝期待値"] < 1.0:
        return ["background-color: #ffd0d0"] * len(row)
    else:
        return [""] * len(row)

# ★ 略称一覧抽出関数
def collect_jockey_short_names(races):
    shorts = set()
    for label, race_id, race_name in races:
        data = get_entries(race_id)
        for e in data["entries"]:
            short = e.get("jockey")
            if short:
                shorts.add(short)
    return sorted(list(shorts))


# UI
st.set_page_config(page_title="競馬分析アプリ（スマホ対応）", layout="wide")
st.title("🐎 競馬分析アプリ（スマホ対応 Web版）")

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
            for race in venue["races"]:
                race_number = race.get("number", "?")
                race_name = race.get("name", "レース名不明")

                # ★レース名をタブに戻す
                label = f"{venue['name']} {race_number}R（{race_name}）"

                races.append((label, race["id"], race_name))

        st.session_state["races"] = races

# ★★★ ここに配置すると必ずボタンが出る ★★★
if "races" in st.session_state:
    st.subheader("🔍 騎手略称一覧の抽出")
    if st.button("騎手略称一覧を抽出"):
        shorts = collect_jockey_short_names(st.session_state["races"])
        st.write("抽出された略称一覧：")
        st.write(shorts)

# レース選択
if "races" in st.session_state:
    race_labels = [r[0] for r in st.session_state["races"]]
    selected_race = st.selectbox("レースを選択", race_labels)

    # 単レース分析
    if st.button("このレースだけ分析"):
        race_id = [rid for label, rid, rname in st.session_state["races"] if label == selected_race][0]

        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)

        if ranking:
            df = pd.DataFrame(ranking)

            df["レース"] = selected_race  # ★レース名統合済み

            df = df[[
                "レース",
                "馬番", "馬名", "騎手",
                "オッズ", "人気", "勝率(%)", "単勝期待値"
            ]]

            styler = df.style.apply(highlight_rows, axis=1).format({
                "オッズ": "{:.1f}",
                "勝率(%)": "{:.1f}",
                "単勝期待値": "{:.2f}"
            })

            st.dataframe(styler, use_container_width=True)
        else:
            st.warning("条件に合う馬がいません")

# 全レース分析
if "races" in st.session_state and st.button("全レース分析（全件）"):
    all_rows = []

    for label, race_id, race_name in st.session_state["races"]:
        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)

        for r in ranking:
            r["レース"] = label
            all_rows.append(r)

    if all_rows:
        df = pd.DataFrame(all_rows)
        df = df[[
            "レース",
            "馬番", "馬名", "騎手",
            "オッズ", "人気", "勝率(%)", "単勝期待値"
        ]]

        styler = df.style.apply(highlight_rows, axis=1).format({
            "オッズ": "{:.1f}",
            "勝率(%)": "{:.1f}",
            "単勝期待値": "{:.2f}"
        })

        st.dataframe(styler, use_container_width=True)
    else:
        st.warning("条件に合う馬がいません")

# 上位1〜5位
if "races" in st.session_state and st.button("全レース 単勝期待値 上位1〜5位"):
    top_rows = []

    for label, race_id, race_name in st.session_state["races"]:
        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)
        top5 = ranking[:5]

        for r in top5:
            r["レース"] = label
            top_rows.append(r)

    if top_rows:
        df = pd.DataFrame(top_rows)
        df = df[[
            "レース",
            "馬番", "馬名", "騎手",
            "オッズ", "人気", "勝率(%)", "単勝期待値"
        ]]

        styler = df.style.apply(highlight_rows, axis=1).format({
            "オッズ": "{:.1f}",
            "勝率(%)": "{:.1f}",
            "単勝期待値": "{:.2f}"
        })

        st.dataframe(styler, use_container_width=True)
    else:
        st.warning("条件に合う馬がいません")
