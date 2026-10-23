import streamlit as st
import requests
import pandas as pd
import re
import datetime
import jpholiday

# =========================
# 2026年中央競馬 全開催日
# =========================

JRA_2026 = [
    "2026-01-04","2026-01-05","2026-01-10","2026-01-11","2026-01-12","2026-01-17","2026-01-18","2026-01-24","2026-01-25",
    "2026-02-01","2026-02-07","2026-02-08","2026-02-10","2026-02-14","2026-02-15","2026-02-21","2026-02-22","2026-02-28",
    "2026-03-01","2026-03-07","2026-03-08","2026-03-14","2026-03-15","2026-03-21","2026-03-22","2026-03-28","2026-03-29",
    "2026-04-04","2026-04-05","2026-04-11","2026-04-12","2026-04-18","2026-04-19","2026-04-25","2026-04-26",
    "2026-05-02","2026-05-03","2026-05-09","2026-05-10","2026-05-16","2026-05-17","2026-05-23","2026-05-24","2026-05-30","2026-05-31",
    "2026-06-07","2026-06-13","2026-06-14","2026-06-21","2026-06-27","2026-06-28",
    "2026-07-04","2026-07-05","2026-07-11","2026-07-12","2026-07-18","2026-07-19","2026-07-25","2026-07-26",
    "2026-08-01","2026-08-02","2026-08-08","2026-08-09","2026-08-15","2026-08-16","2026-08-22","2026-08-23","2026-08-29","2026-08-30",
    "2026-09-05","2026-09-06","2026-09-12","2026-09-13","2026-09-19","2026-09-20","2026-09-21","2026-09-26","2026-09-27",
    "2026-10-03","2026-10-04","2026-10-10","2026-10-11","2026-10-12","2026-10-17","2026-10-18","2026-10-24","2026-10-25","2026-10-31",
    "2026-11-01","2026-11-07","2026-11-08","2026-11-14","2026-11-15","2026-11-21","2026-11-22","2026-11-23","2026-11-28","2026-11-29",
    "2026-12-05","2026-12-06","2026-12-12","2026-12-13","2026-12-19","2026-12-20","2026-12-26","2026-12-27"
]

# =========================
# 開催日（未来日除外＋直近順）
# =========================

def get_jra_days_sorted():
    today = datetime.date.today()
    valid_dates = [
        d for d in JRA_2026
        if datetime.datetime.strptime(d, "%Y-%m-%d").date() <= today
    ]
    sorted_dates = sorted(
        valid_dates,
        key=lambda x: abs((datetime.datetime.strptime(x, "%Y-%m-%d").date() - today).days)
    )
    return sorted_dates

# =========================
# API
# =========================

def get_race_list(date):
    url = f"https://frontrunner-race.com/api/races?date={date}"
    return requests.get(url).json()

def get_entries(race_id):
    url = f"https://frontrunner-race.com/api/race/{race_id}/entries"
    return requests.get(url).json()

# =========================
# グレード判定
# =========================

def extract_class(class_name, grade, is_jump):
    if is_jump:
        if grade == "G1": return "J・GⅠ"
        if grade == "G2": return "J・GⅡ"
        if grade == "G3": return "J・GⅢ"
    if grade == "G1": return "GⅠ"
    if grade == "G2": return "GⅡ"
    if grade == "G3": return "GⅢ"
    if grade == "L": return "L"
    if class_name and ("オープン" in class_name) and (not grade):
        return "OP"
    return ""

# =========================
# グレード色付け
# =========================

def grade_color(row):
    val = row["レース名"]
    if "GⅠ" in val or "J・GⅠ" in val:
        return ["color: #007bff; font-weight: bold;" if col=="レース名" else "" for col in row.index]
    if "GⅡ" in val or "J・GⅡ" in val:
        return ["color: #dc3545; font-weight: bold;" if col=="レース名" else "" for col in row.index]
    if "GⅢ" in val or "J・GⅢ" in val:
        return ["color: #28a745; font-weight: bold;" if col=="レース名" else "" for col in row.index]
    if "L" in val:
        return ["color: #6f42c1; font-weight: bold;" if col=="レース名" else "" for col in row.index]
    if "OP" in val:
        return ["color: #fd7e14; font-weight: bold;" if col=="レース名" else "" for col in row.index]
    return [""] * len(row)

# =========================
# 単勝期待値計算
# =========================

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

# =========================
# 色付け（期待値）
# =========================

def highlight_rows(row):
    if row["単勝期待値"] >= 2.0:
        return ["background-color: #d0ffd0"] * len(row)
    elif row["単勝期待値"] < 1.0:
        return ["background-color: #ffd0d0"] * len(row)
    else:
        return [""] * len(row)

# =========================
# 開催場 → レース番号で並び替え
# =========================

def sort_race_label(label, venue_order):
    venue = label.split()[0]
    race_num = int(re.findall(r"(\d+)R", label)[0])
    venue_index = venue_order.index(venue) if venue in venue_order else 999
    return (venue_index, race_num)

# =========================
# UI
# =========================

st.set_page_config(page_title="🐎競馬分析アプリ", layout="wide")
st.title("🐎競馬分析アプリ")

# 開催日プルダウン
jra_days = [""] + get_jra_days_sorted()
date = st.selectbox("開催日を選択してください", jra_days)

winrate_threshold = st.selectbox("勝率閾値（％以上）", [0, 5, 10, 15, 20, 25, 30])
ev_threshold = float(st.selectbox("単勝期待値閾値（以上）", ["0"] + [f"{x/10:.1f}" for x in range(10, 31)]))

# =========================
# レース一覧取得
# =========================

if st.button("レース一覧取得"):
    race_list = get_race_list(date)

    if "venues" not in race_list or len(race_list["venues"]) == 0:
        st.error("開催日ではありません")
    else:
        st.success("レース一覧を取得しました")

        venue_order = [v["name"] for v in race_list["venues"]]
        st.session_state["venue_order"] = venue_order

        races = []
        for venue in race_list["venues"]:
            for idx, race in enumerate(venue["races"], start=1):
                race_number = race.get("raceNumber", idx)
                race_name = race.get("name") or race.get("nameShort", "レース名不明")

                race_class = extract_class(
                    race.get("className"),
                    race.get("grade"),
                    race.get("isJump")
                )

                race_name_display = f"{race_name}（{race_class}）" if race_class else race_name
                label = f"{venue['name']} {race_number}R（{race_name_display}）"

                races.append((label, race["id"], f"{venue['name']} {race_number}R", race_name_display))

        races.sort(key=lambda x: sort_race_label(x[0], st.session_state["venue_order"]))
        st.session_state["races"] = races

# =========================
# レース一覧取得後の処理
# =========================

if "races" in st.session_state:
    race_labels = [r[0] for r in st.session_state["races"]]
    selected_race = st.selectbox("レースを選択", race_labels)

    # ★ 単一レース分析
    if st.button("このレースだけ分析"):
        for label, rid, race_disp, race_name_display in st.session_state["races"]:
            if label == selected_race:
                race_id = rid
                race_display = race_disp
                race_name_display = race_name_display
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

            df = df.sort_values(by=["単勝期待値"], ascending=[False])

            styler = (
                df.style
                .apply(highlight_rows, axis=1)
                .apply(grade_color, axis=1)
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

# =========================
# ★★★ WIN5対象レース分析（2場・3場開催対応）
# =========================

if "races" in st.session_state and st.button("WIN5対象レース分析"):
    win5_rows = []

    venue_order = st.session_state["venue_order"]
    venues = venue_order

    if len(venues) < 2:
        st.warning("WIN5対象レースは2場以上開催時のみ対応しています")
    else:
        venue_A = venues[0]
        venue_B = venues[1]
        venue_C = venues[2] if len(venues) >= 3 else None

        race_map = {}
        for label, race_id, race_disp, race_name_display in st.session_state["races"]:
            venue = race_disp.split()[0]
            race_num = int(re.findall(r"(\d+)R", race_disp)[0])
            race_map.setdefault((venue, race_num), []).append(
                (venue, race_id, race_disp, race_name_display)
            )

        if venue_C is not None:
            # 3場開催
            win5_targets = [
                (venue_A, 10),
                (venue_B, 10),
                (venue_C, 11),
                (venue_A, 11),
                (venue_B, 11),
            ]
        else:
            # 2場開催
            win5_targets = [
                (venue_A, 9),
                (venue_B, 10),
                (venue_A, 10),
                (venue_B, 11),
                (venue_A, 11),
            ]

        selected_win5 = []
        for venue, num in win5_targets:
            key = (venue, num)
            if key in race_map:
                selected_win5.extend(race_map[key])

        for venue, race_id, race_disp, race_name_display in selected_win5:
            data = get_entries(race_id)
            ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)

            for r in ranking:
                r["レース"] = race_disp
                r["レース名"] = race_name_display
                win5_rows.append(r)

        if win5_rows:
            df = pd.DataFrame(win5_rows)

            df["venue"] = df["レース"].str.split().str[0]
            df["race_num"] = df["レース"].str.extract(r"(\d+)R").astype(int)

            df["venue_order"] = df["venue"].apply(
                lambda v: venue_order.index(v)
                if v in venue_order else 999
            )

            df = df.sort_values(by=["venue_order", "race_num"], ascending=[True, True])
            df = df.sort_values(by=["venue_order", "race_num", "単勝期待値"], ascending=[True, True, False])

            df = df[[
                "レース", "レース名",
                "馬番", "馬名", "騎手",
                "オッズ", "人気", "勝率(%)", "単勝期待値",
                "逃げ馬指数"
            ]]

            styler = (
                df.style
                .apply(highlight_rows, axis=1)
                .apply(grade_color, axis=1)
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
            st.warning("WIN5対象レースが見つかりません")

# =========================
# ★★★ 全レース分析（各レースごとに単勝期待値順）
# =========================

if "races" in st.session_state and st.button("全レース分析（全件）"):
    all_rows = []

    for label, race_id, race_disp, race_name_display in st.session_state["races"]:
        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)

        for r in ranking:
            r["レース"] = race_disp
            r["レース名"] = race_name_display
            all_rows.append(r)

    if all_rows:
        df = pd.DataFrame(all_rows)

        df["venue"] = df["レース"].str.split().str[0]
        df["race_num"] = df["レース"].str.extract(r"(\d+)R").astype(int)

        df["venue_order"] = df["venue"].apply(
            lambda v: st.session_state["venue_order"].index(v)
            if v in st.session_state["venue_order"] else 999
        )

        df = df.sort_values(by=["venue_order", "race_num"], ascending=[True, True])
        df = df.sort_values(by=["venue_order", "race_num", "単勝期待値"], ascending=[True, True, False])

        df = df[[
            "レース", "レース名",
            "馬番", "馬名", "騎手",
            "オッズ", "人気", "勝率(%)", "単勝期待値",
            "逃げ馬指数"
        ]]

        styler = (
            df.style
            .apply(highlight_rows, axis=1)
            .apply(grade_color, axis=1)
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

# =========================
# ★★★ 全レース 上位1〜5位（各レースごとに単勝期待値順）
# =========================

if "races" in st.session_state and st.button("全レース 単勝期待値 上位1〜5位"):
    top_rows = []

    for label, race_id, race_disp, race_name_display in st.session_state["races"]:
        data = get_entries(race_id)
        ranking = calc_ev(data["entries"], winrate_threshold, ev_threshold)
        top5 = ranking[:5]

        for r in top5:
            r["レース"] = race_disp
            r["レース名"] = race_name_display
            top_rows.append(r)

    if top_rows:
        df = pd.DataFrame(top_rows)

        df["venue"] = df["レース"].str.split().str[0]
        df["race_num"] = df["レース"].str.extract(r"(\d+)R").astype(int)

        df["venue_order"] = df["venue"].apply(
            lambda v: st.session_state["venue_order"].index(v)
            if v in st.session_state["venue_order"] else 999
        )

        df = df.sort_values(by=["venue_order", "race_num"], ascending=[True, True])
        df = df.sort_values(by=["venue_order", "race_num", "単勝期待値"], ascending=[True, True, False])

        df = df[[
            "レース", "レース名",
            "馬番", "馬名", "騎手",
            "オッズ", "人気", "勝率(%)", "単勝期待値",
            "逃げ馬指数"
        ]]

        styler = (
            df.style
            .apply(highlight_rows, axis=1)
            .apply(grade_color, axis=1)
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
