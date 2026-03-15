"""
chart_practice.py - テクニカルチャート予想練習アプリ
"""
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
import random

st.set_page_config(
    page_title="チャート予想練習",
    page_icon="📈",
    layout="wide",
)

st.title("📈 チャート予想練習")
st.caption("過去チャートを見て、この後3ヶ月でどう動くかを予想しよう")

# ── 銘柄リスト ────────────────────────────────────────────────────────────────
STOCKS = {
    "自動車": [
        ("7203", "トヨタ自動車"),
        ("7267", "ホンダ"),
        ("7201", "日産自動車"),
        ("7269", "スズキ"),
        ("7270", "SUBARU"),
        ("7261", "マツダ"),
    ],
    "電機・家電": [
        ("6758", "ソニーグループ"),
        ("6752", "パナソニック"),
        ("6501", "日立製作所"),
        ("6971", "京セラ"),
        ("6594", "日本電産（ニデック）"),
    ],
    "半導体・精密": [
        ("6861", "キーエンス"),
        ("6723", "ルネサスエレクトロニクス"),
        ("8035", "東京エレクトロン"),
        ("6857", "アドバンテスト"),
        ("4063", "信越化学工業"),
    ],
    "IT・通信": [
        ("9984", "ソフトバンクグループ"),
        ("9432", "NTT"),
        ("9433", "KDDI"),
        ("9434", "ソフトバンク"),
        ("4755", "楽天グループ"),
        ("4385", "メルカリ"),
    ],
    "金融・銀行": [
        ("8306", "三菱UFJフィナンシャル"),
        ("8316", "三井住友フィナンシャル"),
        ("8411", "みずほフィナンシャル"),
        ("8604", "野村ホールディングス"),
        ("8591", "オリックス"),
    ],
    "小売・流通": [
        ("9983", "ファーストリテイリング（ユニクロ）"),
        ("3382", "セブン＆アイ・ホールディングス"),
        ("8267", "イオン"),
        ("2413", "エムスリー"),
        ("3659", "ネクソン"),
    ],
    "食品・飲料": [
        ("2802", "味の素"),
        ("2503", "キリンホールディングス"),
        ("2502", "アサヒグループ"),
        ("2801", "キッコーマン"),
        ("2282", "日本ハム"),
    ],
    "医薬品": [
        ("4502", "武田薬品工業"),
        ("4503", "アステラス製薬"),
        ("4519", "中外製薬"),
        ("4568", "第一三共"),
    ],
    "ゲーム・エンタメ": [
        ("7974", "任天堂"),
        ("9697", "カプコン"),
        ("9684", "スクウェア・エニックス"),
        ("3765", "ガンホー"),
        ("2121", "ミクシィ"),
    ],
    "不動産・建設": [
        ("8801", "三井不動産"),
        ("8802", "三菱地所"),
        ("1925", "大和ハウス工業"),
        ("1928", "積水ハウス"),
    ],
    "サービス・その他": [
        ("6098", "リクルートホールディングス"),
        ("9020", "東日本旅客鉄道（JR東日本）"),
        ("9022", "東海旅客鉄道（JR東海）"),
        ("9501", "東京電力ホールディングス"),
        ("5401", "日本製鉄"),
    ],
}

# フラットなリスト（表示用）
ALL_STOCKS = []
for sector, stocks in STOCKS.items():
    for code, name in stocks:
        ALL_STOCKS.append((sector, code, name))

# ── 予想の選択肢 ──────────────────────────────────────────────────────────────
PREDICTIONS = {
    "↑↑ 大きく上昇（+10%以上）": (10, 999),
    "↑  やや上昇（+5〜10%）":     (5, 10),
    "→↑ 小幅上昇（0〜+5%）":     (0, 5),
    "→↓ 小幅下落（0〜-5%）":     (-5, 0),
    "↓  やや下落（-5〜-10%）":    (-10, -5),
    "↓↓ 大きく下落（-10%以下）":  (-999, -10),
}

# ── セッション初期化 ──────────────────────────────────────────────────────────
if "phase" not in st.session_state:
    st.session_state.phase = "input"      # input → predict → result
if "df" not in st.session_state:
    st.session_state.df = None
if "cut_date" not in st.session_state:
    st.session_state.cut_date = None
if "ticker" not in st.session_state:
    st.session_state.ticker = ""
if "stock_name" not in st.session_state:
    st.session_state.stock_name = ""
if "stock_info" not in st.session_state:
    st.session_state.stock_info = {}
if "score" not in st.session_state:
    st.session_state.score = {"total": 0, "correct": 0}


def fetch_data(ticker_code: str):
    """yfinanceで株価データを取得"""
    ticker = yf.Ticker(ticker_code)
    # 3年分取得（カット余裕のため）
    df = ticker.history(period="3y")
    if df.empty:
        return None, None, {}
    info = ticker.info
    name = info.get("longName") or info.get("shortName") or ticker_code
    stock_info = {
        "name": name,
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "summary": info.get("longBusinessSummary", ""),
        "market_cap": info.get("marketCap"),
    }
    return df, name, stock_info


def calc_ma(df: pd.DataFrame):
    df = df.copy()
    df["MA25"] = df["Close"].rolling(25).mean()
    df["MA75"] = df["Close"].rolling(75).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    return df


def make_chart(df: pd.DataFrame, title: str, show_future=False):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="株価",
        increasing_line_color="#ef5350",
        decreasing_line_color="#26a69a",
    ))

    colors = {"MA25": "#ffb74d", "MA75": "#42a5f5", "MA200": "#ab47bc"}
    for ma, color in colors.items():
        if ma in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[ma],
                name=ma, line=dict(color=color, width=1.5),
                opacity=0.9,
            ))

    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        height=500,
        plot_bgcolor="#1e1e1e",
        paper_bgcolor="#1e1e1e",
        font_color="#ffffff",
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(gridcolor="#333"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


# ── サイドバー：スコアと設定 ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### スコア")
    sc = st.session_state.score
    if sc["total"] > 0:
        rate = sc["correct"] / sc["total"] * 100
        st.metric("正解率", f"{rate:.0f}%", f"{sc['correct']}/{sc['total']} 問")
    else:
        st.metric("正解率", "─", "まだ0問")

    st.divider()
    st.markdown("### 使い方")
    st.markdown("""
    1. 銘柄コードを入力
    2. チャートを読む
    3. 6択で予想する
    4. 答え合わせ
    5. 「次の問題へ」で繰り返す
    """)

# ── フェーズ1: 銘柄入力 ───────────────────────────────────────────────────────
if st.session_state.phase == "input":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("銘柄を選ぶ")

        # セクター選択 → 銘柄選択
        sector_options = list(STOCKS.keys())
        selected_sector = st.selectbox("セクター", sector_options)
        sector_stocks = STOCKS[selected_sector]
        stock_labels = [f"{name}（{code}）" for code, name in sector_stocks]
        selected_stock_label = st.selectbox("銘柄", stock_labels)
        selected_idx = stock_labels.index(selected_stock_label)
        code = sector_stocks[selected_idx][0]

        st.caption(f"銘柄コード: {code}")
        load_btn = st.button("チャートを読み込む", type="primary", use_container_width=True)

        if load_btn:
            ticker_code = code + ".T"
            with st.spinner("データ取得中..."):
                df, name, stock_info = fetch_data(ticker_code)

            if df is None or len(df) < 300:
                st.error("データを取得できませんでした。銘柄コードを確認してください。")
            else:
                df = calc_ma(df)

                # カット位置をランダムに決める（末尾から63〜126営業日前 ≒ 3〜6ヶ月）
                future_days = 63  # 約3ヶ月（営業日）
                margin = len(df) - future_days
                cut_idx = random.randint(max(250, margin - 63), margin)
                cut_date = df.index[cut_idx]

                st.session_state.df = df
                st.session_state.cut_date = cut_date
                st.session_state.ticker = code
                st.session_state.stock_name = name
                st.session_state.stock_info = stock_info
                st.session_state.phase = "predict"
                st.rerun()

    with col2:
        st.info("""
        **練習の流れ**

        銘柄コードを入力すると、過去チャートが表示されます。
        チャートはある時点でカットされています。
        移動平均線（25・75・200日）を参考にしながら、
        その後3ヶ月でどう動くかを予想してください。
        """)

# ── フェーズ2: チャート表示・予想入力 ─────────────────────────────────────────
elif st.session_state.phase == "predict":
    df = st.session_state.df
    cut_date = st.session_state.cut_date
    name = st.session_state.stock_name
    ticker = st.session_state.ticker

    # カット前データ
    df_show = df[df.index <= cut_date].copy()
    # 表示は直近約1.5年分
    df_display = df_show.tail(380)

    info = st.session_state.stock_info
    st.subheader(f"{ticker}  {name}")

    # 会社概要
    meta_parts = []
    if info.get("sector"):
        meta_parts.append(f"セクター: {info['sector']}")
    if info.get("industry"):
        meta_parts.append(f"業種: {info['industry']}")
    if info.get("market_cap"):
        cap = info["market_cap"]
        cap_str = f"{cap/1e12:.1f}兆円" if cap >= 1e12 else f"{cap/1e8:.0f}億円"
        meta_parts.append(f"時価総額: {cap_str}")
    if meta_parts:
        st.caption("  |  ".join(meta_parts))
    if info.get("summary"):
        with st.expander("会社概要"):
            st.write(info["summary"])

    st.caption(f"チャート表示期間: {df_display.index[0].date()} 〜 {cut_date.date()}　（この後3ヶ月を予想）")

    fig = make_chart(df_display, f"{ticker} {name} — ここまでのチャート")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("この後3ヶ月でどう動く？")

    col_pred, col_info = st.columns([2, 1])
    with col_pred:
        prediction = st.radio(
            "予想を選んでください",
            options=list(PREDICTIONS.keys()),
            index=2,
        )
        memo = st.text_area(
            "根拠メモ（任意）",
            height=80,
            placeholder="なぜそう思うか、チャートのどこを見たか",
        )

        if st.button("答えを見る", type="primary", use_container_width=True):
            st.session_state.prediction = prediction
            st.session_state.memo = memo
            st.session_state.phase = "result"
            st.rerun()

    with col_info:
        last_close = df_show["Close"].iloc[-1]
        st.metric("現在の終値", f"{last_close:,.0f}円")
        ma25 = df_show["MA25"].iloc[-1]
        ma75 = df_show["MA75"].iloc[-1]
        if not pd.isna(ma25):
            diff25 = (last_close - ma25) / ma25 * 100
            st.metric("25日線との乖離", f"{diff25:+.1f}%")
        if not pd.isna(ma75):
            diff75 = (last_close - ma75) / ma75 * 100
            st.metric("75日線との乖離", f"{diff75:+.1f}%")

    st.divider()
    if st.button("← 銘柄を変える"):
        st.session_state.phase = "input"
        st.rerun()

# ── フェーズ3: 答え合わせ ─────────────────────────────────────────────────────
elif st.session_state.phase == "result":
    df = st.session_state.df
    cut_date = st.session_state.cut_date
    name = st.session_state.stock_name
    ticker = st.session_state.ticker
    prediction = st.session_state.prediction
    memo = st.session_state.get("memo", "")

    # カット前後のデータ
    df_before = df[df.index <= cut_date]
    df_after = df[df.index > cut_date].head(63)  # 約3ヶ月

    if df_after.empty:
        st.warning("この銘柄の3ヶ月後データがありません。別の問題を試してください。")
    else:
        # 騰落率計算
        price_start = df_before["Close"].iloc[-1]
        price_end = df_after["Close"].iloc[-1]
        actual_pct = (price_end - price_start) / price_start * 100

        # 正解判定
        lo, hi = PREDICTIONS[prediction]
        is_correct = lo <= actual_pct < hi

        # スコア更新
        st.session_state.score["total"] += 1
        if is_correct:
            st.session_state.score["correct"] += 1

        # 正解の選択肢を探す
        correct_label = ""
        for label, (l, h) in PREDICTIONS.items():
            if l <= actual_pct < h:
                correct_label = label
                break

        # 結果表示
        if is_correct:
            st.success(f"✅ 正解！  実際の騰落率: **{actual_pct:+.1f}%**")
        else:
            st.error(
                f"❌ 外れ  |  あなたの予想: {prediction}\n\n"
                f"実際の騰落率: **{actual_pct:+.1f}%**  →  正解: **{correct_label}**"
            )

        # チャート（カット前後を合わせて表示）
        cut_pos = df.index.searchsorted(cut_date)
        start_pos = max(0, cut_pos - 380)
        end_pos = min(len(df), cut_pos + 64)
        df_full = df.iloc[start_pos:end_pos]
        fig = make_chart(df_full, f"{ticker} {name} — 答え合わせ")

        # カット位置に縦線を追加
        cut_str = str(cut_date.date())
        fig.add_shape(
            type="line",
            x0=cut_str, x1=cut_str,
            y0=0, y1=1, yref="paper",
            line=dict(color="yellow", dash="dash", width=2),
        )
        fig.add_annotation(
            x=cut_str, y=1, yref="paper",
            text="◀ 予想開始",
            showarrow=False,
            font=dict(color="yellow", size=12),
            xanchor="right",
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("予想開始時の株価", f"{price_start:,.0f}円")
        col2.metric("3ヶ月後の株価", f"{price_end:,.0f}円")
        sign = "+" if actual_pct >= 0 else ""
        col3.metric("実際の騰落率", f"{sign}{actual_pct:.1f}%")

        if memo:
            st.info(f"📝 あなたのメモ: {memo}")

        st.divider()
        col_next, col_same, col_back = st.columns(3)
        with col_next:
            if st.button("同じ銘柄で次の問題", type="primary", use_container_width=True):
                # 同じ銘柄でカット位置を変えて再挑戦
                future_days = 63
                margin = len(df) - future_days
                cut_idx = random.randint(max(250, margin - 63), margin)
                cut_date_new = df.index[cut_idx]
                st.session_state.cut_date = cut_date_new
                st.session_state.phase = "predict"
                st.rerun()
        with col_same:
            if st.button("別の銘柄に変える", use_container_width=True):
                st.session_state.phase = "input"
                st.rerun()
        with col_back:
            if st.button("スコアをリセット", use_container_width=True):
                st.session_state.score = {"total": 0, "correct": 0}
                st.session_state.phase = "input"
                st.rerun()
