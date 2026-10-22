import streamlit as st
import requests
import pandas as pd
import re

# API
def get_race_list(date):
    url = f"https://frontrunner-race.com/api/races?date={date}"
    return requests.get(url).json()

def get_entries(race_id):
    url = f"https://frontrunner-race.com/api/race/{race_id}/entries"
    return requests.get(url).json()

# ★レースクラスをAPI表記そのままで抽出
def extract_class(class_str):
    if class_str is None:
        return ""

    # 重賞
    if "GⅠ" in class_str:
        return "GⅠ"
    if "GⅡ" in class_str:
        return "GⅡ"
    if "GⅢ" in class_str:
        return "GⅢ"

    # オープン・リステッド
    if "OP" in class_str:
        return "OP"
    if "L" in class_str:
        return "L"

    # 条件戦
    if "3勝" in class_str:
        return "3勝"
    if "2勝" in class_str:
        return "2勝"
    if "1勝" in class_str:
        return "1勝"

    # 未勝利・新馬
    if "未勝利" in class_str:
        return "未勝利"
    if "新馬" in class_str:
        return "新馬"

    return ""

# 単勝期待値計算（勝率フィルター修正済み）
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

        # 勝率フィルター（％で比較）
        if win * 100 >= winrate_threshold and ev >= ev_threshold:
            results.append({
                "馬番": e["number"],
                "馬名": e["name"],
                "騎手": jockey,
                "オッズ": odds,
                "人気": e["popularity"],
                "勝率(%)": win * 100,
                "単勝期待値": ev,
                "逃げ馬指数": e.get("predictFirstPhaseIndex", 0)
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

# 開催場 → レース番号で並び替える関数（動的開催場順）
def sort_race_label(label, venue_order):
    venue = label.split()[0]
    race_num = int(re.findall(r"(\d+)R", label)[0])
    venue_index = venue_order.index(venue) if venue in venue_order else 999
    return (venue_index, race_num)

# UI
st.set_page_config(page_title="🐎競馬分析アプリ", layout="wide")
st.title("🐎競馬分析アプリ")

date = st.text_input("開催日 (YYYY-MM-DD)", "2026-10-18")
winrate_threshold = st.selectbox("勝率閾値（％以上）", [0, 5, 10, 15, 20, 25, 30])
ev_threshold = float(st.selectbox("単勝期待値閾値（以上）", ["0"] + [f"{x/10:.1f}" for x in range(10, 31)]))

# レース一覧取得
if st.button("レース一覧取得"):
    race_list = get_race_list(date)

    if "venues" not in race_list or len(race_list["venues"]) == 0:
        st.error("開催日ではありません")
    else:
        st.success("レース一覧を取得しました")

        # ★開催場順を動的に保存
        venue_order = [v["name"] for v in race_list["venues"]]
        st.session_state["venue_order"] = venue_order

        races = []
        for venue in race_list["venues"]:
            for idx, race in enumerate(venue["races"], start=1):
                race_number = race.get("number", idx)

                race_name = race.get("name") or race.get("raceNameShort", "レース名不明")

                # ★レースクラス抽出
                race_class = extract_class(race.get("class"))

                # ★レース名にクラスを追加
                label = f"{venue['name']} {race_number}R（{race_name}・{race_class}）"

                races.append((label, race["id"], f"{venue['name']} {race_number}R", f"{race_name}（{race_class}）"))

        # ★開催場 → レース番号で並び替え
        races.sort(key=lambda x: sort_race_label(x[0], st.session_state["venue_order"]))

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

# 全レース分析（開催場 → レース番号で並び替え）
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

        df["venue"] = df["レース"].str.split().str[0]
        df["race_num"] = df["レース"].str.extract(r"(\d+)R").astype(int)

        df["venue_order"] = df["venue"].apply(
            lambda v: st.session_state["venue_order"].index(v)
            if v in st.session_state["venue_order"] else 999
        )

        df = df.sort_values(["venue_order", "race_num"])

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

# 上位1〜5位（開催場 → レース番号で並び替え）
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

        df["venue"] = df["レース"].str.split().str[0]
        df["race_num"] = df["レース"].str.extract(r"(\d+)R").astype(int)

        df["venue_order"] = df["venue"].apply(
            lambda v: st.session_state["venue_order"].index(v)
            if v in st.session_state["venue_order"] else 999
        )

        df = df.sort_values(["venue_order", "race_num"])

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
