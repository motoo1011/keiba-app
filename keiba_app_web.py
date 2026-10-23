import streamlit as st
import requests
import pandas as pd
import re
import datetime

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
        return ["color: #007bff; font-weight: bold;" if col == "レース名" else "" for col in row.index]
    if "GⅡ" in val or "J・GⅡ" in val:
        return ["color: #dc3545; font-weight: bold;" if col == "レース名" else "" for col in row.index]
    if "GⅢ" in val or "J・GⅢ" in val:
        return ["color: #28a745; font-weight: bold;" if col == "レース名" else "" for col in row.index]
    if "L" in val:
        return ["color: #6f42c1; font-weight: bold;" if col == "レース名" else "" for col in row.index]
    if "OP" in val:
        return ["color: #fd7e14; font-weight: bold;" if col == "レース名" else "" for col in row.index]
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
# レース選択
# =========================

selected_race = st.selectbox("レースを選択", [""] + [r[0] for r in st.session_state.get("races", [])])

# =========================
# 単一レース分析
# =========================

if st.button("このレースだけ分析"):
    if not selected_race:
        st.warning("レースを選択してください")
    else:
        for label, rid, race_disp, race_name_display in st.session_state["races"]:
            if label == selected_race:
                race_id = rid
                break

        data = get_entries(race_id)
        entries = data["entries"]

        results = calc_ev(entries, winrate_threshold, ev_threshold)

        st.subheader(f"📌 {selected_race} 単勝期待値分析")
        if len(results) == 0:
            st.info("条件を満たす馬がいません")
        else:
            df = pd.DataFrame(results)
            st.dataframe(df.style.apply(highlight_rows, axis=1))

# =========================
# WIN5 対象レース分析
# =========================

if st.button("WINS対象レース分析"):
    st.subheader("WIN5 対象レース分析")

    # WIN5対象は通常 10R〜11R（開催場によって変動）
    win5_labels = [
        r for r in st.session_state["races"]
        if ("10R" in r[0]) or ("11R" in r[0])
    ]

    for label, rid, race_disp, race_name_display in win5_labels:
        data = get_entries(rid)
        entries = data["entries"]
        results = calc_ev(entries, winrate_threshold, ev_threshold)

        st.write(f"### {label}")
        if len(results) == 0:
            st.info("条件を満たす馬がいません")
        else:
            df = pd.DataFrame(results)
            st.dataframe(df.style.apply(highlight_rows, axis=1))

# =========================
# 全レース分析（全件）
# =========================

if st.button("全レース分析（全件）"):
    st.subheader("📌 全レース 単勝期待値分析")

    for label, rid, race_disp, race_name_display in st.session_state["races"]:
        data = get_entries(rid)
        entries = data["entries"]
        results = calc_ev(entries, winrate_threshold, ev_threshold)

        st.write(f"### {label}")
        if len(results) == 0:
            st.info("条件を満たす馬がいません")
        else:
            df = pd.DataFrame(results)
            st.dataframe(df.style.apply(highlight_rows, axis=1))

# =========================
# 全レース 単勝期待値上位1～5位
# =========================

if st.button("全レース 単勝期待値上位1～5位"):
    st.subheader("📌 全レース 単勝期待値 上位1～5位")

    rows = []

    for label, rid, race_disp, race_name_display in st.session_state["races"]:
        data = get_entries(rid)
        entries = data["entries"]
        results = calc_ev(entries, 0, 0)  # 全馬対象

        if len(results) > 0:
            top5 = results[:5]
            for r in top5:
                rows.append({
                    "レース": label,
                    "馬番": r["馬番"],
                    "馬名": r["馬名"],
                    "騎手": r["騎手"],
                    "オッズ": r["オッズ"],
                    "人気": r["人気"],
                    "勝率(%)": r["勝率(%)"],
                    "単勝期待値": r["単勝期待値"]
                })

    if len(rows) == 0:
        st.info("単勝期待値データがありません")
    else:
        df_top5 = pd.DataFrame(rows)
        st.dataframe(df_top5.style.apply(highlight_rows, axis=1))

# =========================
# 馬場傾向（トラックバイアス）完全版
# =========================

def normalize_surface(s):
    """APIの表記揺れを統一する"""
    if s is None:
        return "不明"
    s = str(s).lower()
    if s in ["芝", "turf", "grass"]:
        return "芝"
    if s in ["ダート", "dirt", "sand"]:
        return "ダート"
    return "不明"


if "races" in st.session_state and st.button("馬場傾向（トラックバイアス）"):
    bias_rows = []

    # 全レースの結果を取得
    for label, race_id, race_disp, race_name_display in st.session_state["races"]:
        data = get_entries(race_id)
        entries = data["entries"]

        # 小頭数レースは除外（9頭以下）
        if len(entries) <= 9:
            continue

        for e in entries:
            finish = e.get("finishPosition")
            if finish is None:
                continue  # 結果が入っていないレースは除外

            bias_rows.append({
                "レース": race_disp,
                "芝ダート": normalize_surface(e.get("surface")),
                "枠": e.get("frameNumber", None),
                "4角位置": e.get("cornerPositions", {}).get("4c", None),
                "上がり": e.get("last3fTime", None),
                "着順": finish
            })

    df = pd.DataFrame(bias_rows)

    if df.empty:
        st.warning("馬場傾向を判定できるレースがありません（小頭数除外 or 結果未反映）")
    else:
        # 脚質分類
        def classify_kyakushitsu(pos):
            if pos is None:
                return None
            pos = int(pos)
            if pos <= 3:
                return "前"
            elif pos <= 6:
                return "中"
            else:
                return "後"

        df["脚質"] = df["4角位置"].apply(classify_kyakushitsu)

        # 枠分類
        def classify_waku(w):
            if w is None:
                return None
            w = int(w)
            if w <= 3:
                return "内"
            elif w <= 6:
                return "中"
            else:
                return "外"

        df["枠傾向"] = df["枠"].apply(classify_waku)

        # 芝・ダート別集計
        result = {}
        reason = []  # 判定できない理由を記録

        for sd in ["芝", "ダート"]:
            sdf = df[df["芝ダート"] == sd]

            # 10頭以上のレースが3つ未満なら判定不可
            if len(sdf) < 30:
                reason.append(f"{sd}：10頭以上のレースが3つ未満")
                continue

            # 複勝馬（1〜3着）
            fuku = sdf[sdf["着順"] <= 3]

            # 枠複勝率
            waku_rate = fuku["枠傾向"].value_counts(normalize=True)

            # 脚質複勝率
            kyaku_rate = fuku["脚質"].value_counts(normalize=True)

            # 4角平均位置（全馬）
            avg_4c = sdf["4角位置"].astype(float).mean()

            # 勝ち馬の上がり平均
            win_avg_agari = sdf[sdf["着順"] == 1]["上がり"].astype(float).mean()

            # -------------------------
            # 判定ロジック
            # -------------------------

            # 枠判定
            diff_waku = waku_rate.get("内", 0) - waku_rate.get("外", 0)
            if diff_waku > 0.15:
                waku_judge = "内"
            elif diff_waku < -0.15:
                waku_judge = "外"
            else:
                waku_judge = "フラット"

            # 前後（脚質）
            if avg_4c <= 3.5:
                maeushiro = "超前"
            elif avg_4c <= 5.0:
                maeushiro = "前"
            elif avg_4c <= 6.5:
                maeushiro = "展開次第"
            elif avg_4c <= 8.0:
                maeushiro = "差し"
            else:
                maeushiro = "超差し"

            # 上がり判定
            if win_avg_agari <= 34.0:
                agari_judge = "速い"
            elif win_avg_agari <= 34.8:
                agari_judge = "やや速い"
            elif win_avg_agari <= 35.5:
                agari_judge = "標準"
            elif win_avg_agari <= 36.2:
                agari_judge = "やや遅い"
            else:
                agari_judge = "遅い"

            # 直線の伸び（複勝馬の枠で判定）
            if waku_rate.get("内", 0) > 0.45:
                nobi = "内"
            elif waku_rate.get("外", 0) > 0.45:
                nobi = "外"
            else:
                nobi = "フラット"

            # 馬場（軽い/重い） → 上がりで判定
            if win_avg_agari <= 34.0:
                baba = "軽い"
            elif win_avg_agari <= 34.8:
                baba = "やや軽い"
            elif win_avg_agari <= 35.5:
                baba = "標準"
            elif win_avg_agari <= 36.2:
                baba = "やや重い"
            else:
                baba = "重い"

            result[sd] = {
                "馬場": baba,
                "上がり": agari_judge,
                "枠": waku_judge,
                "直線": nobi,
                "前後": maeushiro
            }

        # -------------------------
        # 表示
        # -------------------------

        st.subheader("📊 馬場傾向（トラックバイアス）")

        if len(result) == 0:
            st.error("馬場傾向を判定できませんでした")
            for r in reason:
                st.write("・" + r)
        else:
            for sd, info in result.items():
                st.write(f"### {sd}")

                table = pd.DataFrame({
                    "項目": ["馬場", "上がり", "枠", "直線の伸び", "前後"],
                    "判定": [
                        info["馬場"],
                        info["上がり"],
                        info["枠"],
                        info["直線"],
                        info["前後"]
                    ]
                })

                st.table(table)

            st.success("馬場傾向の判定が完了しました")
