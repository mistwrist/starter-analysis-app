
import streamlit as st
import pandas as pd
import numpy as np
import unicodedata

st.set_page_config(page_title="선발투수 분석기", layout="centered")
st.title("⚾️ 선발투수 분석기 (CSV 기반)")

def normalize_name(name: str) -> str:
    return unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def calculate_starter_score_v4_1(row, pitch_usage, num_pitches_over_15, quantiles, pitch_data):
    score, logs = 0, []
    q = quantiles

    def pct_score(val, col, label, weight):
        nonlocal score
        boundaries = q[col].values
        cuts = [weight * x for x in [1.0, 5/6, 4/6, 3/6, 2/6, 1/6, 0]]
        score_add = float(np.interp(val, boundaries, cuts[::-1]))
        score += score_add
        logs.append(f"{label} → +{round(score_add, 1)}")

    def inv_score(val, col, label, weight):
        nonlocal score
        boundaries = q[col].values
        cuts = [weight * x for x in [1.0, 5/6, 4/6, 3/6, 2/6, 1/6, 0]]
        score_add = float(np.interp(val, boundaries, cuts))
        score += score_add
        logs.append(f"{label} → +{round(score_add, 1)}")

    inv_score(row['xwoba'], 'xwoba', 'xwOBA', 25)
    inv_score(row['barrels_per_bbe_percent'], 'barrels_per_bbe_percent', 'Barrel%', 20)
    inv_score(row['xslg'], 'xslg', 'xSLG', 15)
    pct_score(row['swing_miss_percent'], 'swing_miss_percent', 'Whiff%', 20)

    if row['bb_percent'] <= 5: score += 15; logs.append("BB% ≤5 → +15")
    elif row['bb_percent'] <= 7: score += 12; logs.append("BB% ≤7 → +12")
    elif row['bb_percent'] <= 9: score += 9; logs.append("BB% ≤9 → +9")
    elif row['bb_percent'] <= 11: score += 6; logs.append("BB% ≤11 → +6")
    elif row['bb_percent'] <= 13: score += 3; logs.append("BB% ≤13 → +3")
    else: logs.append("BB% >13 → +0")

    top_2_usage = sum(sorted(pitch_data.values(), reverse=True)[:2])
    if top_2_usage >= 75: score -= 5; logs.append("상위 2개 구종 ≥75% → -5")
    elif top_2_usage >= 70: score -= 4; logs.append("상위 2개 구종 ≥70% → -4")
    elif top_2_usage >= 65: score -= 3; logs.append("상위 2개 구종 ≥65% → -3")
    elif top_2_usage >= 60: score -= 2; logs.append("상위 2개 구종 ≥60% → -2")
    elif top_2_usage >= 55: score -= 1; logs.append("상위 2개 구종 ≥55% → -1")

    if num_pitches_over_15 >= 3: score += 5; logs.append("다양성 ≥3개 → +5")
    elif num_pitches_over_15 == 2: score += 3; logs.append("다양성 2개 → +3")
    elif num_pitches_over_15 == 1: score += 1; logs.append("다양성 1개 → +1")

    tp = row['total_pitches']
    if tp >= 2500: score += 5; logs.append("투구 수 ≥2500 → +5")
    elif tp >= 1500: score += 3; logs.append("투구 수 ≥1500 → +3")
    elif tp >= 800: score += 1; logs.append("투구 수 ≥800 → +1")

    return max(score, 0), logs

csv = st.file_uploader("📂 CSV 파일 업로드 (pitchers vs all.csv)", type="csv")

if csv:
    df = pd.read_csv(csv)
    df['normalized_player'] = df['player'].apply(normalize_name)
    quantiles = df[df['total_pitches'] >= 100].quantile([0.05,0.10,0.25,0.50,0.75,0.90,0.95])

    pitcher_name = st.text_input("투수 이름 입력 (예: Spencer Strider)")
    pitch_input = st.text_area("구종 사용률 입력 (예: 4-Seam:51.1, Slider:32.6)")

    if st.button("🔍 분석 실행") and pitcher_name and pitch_input:
        try:
            pitch_usage = {k.strip(): float(v.strip()) for k,v in (item.split(":") for item in pitch_input.split(","))}
            num_15 = sum(1 for v in pitch_usage.values() if v >= 15)
            row = df[df['normalized_player'] == normalize_name(pitcher_name)]
            if row.empty:
                st.error("투수를 찾을 수 없습니다.")
            else:
                row = row.iloc[0]
                pitch_cols = ['4-Seam', 'Sinker', 'Cutter', 'Slider', 'Changeup', 'Curve', 'Splitter']
                pitch_data = {col: row[col] for col in pitch_cols if col in row and pd.notna(row[col]) and row[col] > 0}
                score, logs = calculate_starter_score_v4_1(row, pitch_usage, num_15, quantiles, pitch_data)
                st.success(f"총점: {round(score, 1)}점")
                st.subheader("📋 점수 세부 로그")
                for log in logs:
                    st.write("-", log)
        except Exception as e:
            st.error(f"입력 오류: {e}")
