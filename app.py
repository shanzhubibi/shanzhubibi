#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""山竹比比的随身账本 — Streamlit Web 版。"""

from __future__ import annotations

import html as html_module
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
WALLETS_DIR = BASE_DIR / "wallets"
FIELDNAMES = ["date", "category", "payment_method", "amount", "note", "recorded_at"]

CATEGORIES = [
    "餐饮 🍔",
    "购物 🛍️",
    "交通 🚗",
    "娱乐 🎮",
]

PAYMENT_METHODS = [
    "微信支付",
    "支付宝",
]
DEFAULT_MONTHLY_BUDGET = 2000.0
RECENT_LIST_LIMIT = 25


def recorded_time_to_minute() -> str:
    now = datetime.now().replace(second=0, microsecond=0)
    return now.strftime("%Y-%m-%d %H:%M")


def safe_user_file_stem(name: str) -> str:
    """文件名安全片段（禁止路径穿越与非法字符）。"""
    n = (name or "").strip()
    if not n:
        return ""
    n = re.sub(r'[\\/:*?"<>|]', "_", n)
    n = n.replace("\x00", "")
    return (n[:80] if n else "") or "用户"


def user_csv_path(display_name: str) -> Path:
    stem = safe_user_file_stem(display_name)
    return WALLETS_DIR / f"{stem}.csv"


def load_wallet_df(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=FIELDNAMES)
    df = pd.read_csv(path, encoding="utf-8-sig")
    for col in FIELDNAMES:
        if col not in df.columns:
            df[col] = ""
    return df.reindex(columns=FIELDNAMES, fill_value="")


def save_wallet_df(path: Path, df: pd.DataFrame) -> None:
    WALLETS_DIR.mkdir(parents=True, exist_ok=True)
    out = df.reindex(columns=FIELDNAMES)
    out.to_csv(path, index=False, encoding="utf-8-sig")


def month_mask(df: pd.DataFrame, y: int, m: int) -> pd.Series:
    if df.empty or "date" not in df.columns:
        return pd.Series([False] * len(df), index=df.index)
    d = pd.to_datetime(df["date"], errors="coerce")
    return (d.dt.year == y) & (d.dt.month == m)


def today_spending(df: pd.DataFrame, today_d: date) -> float:
    if df.empty or "date" not in df.columns:
        return 0.0
    d = pd.to_datetime(df["date"], errors="coerce")
    m = d.dt.date == today_d
    amounts = pd.to_numeric(df.loc[m, "amount"], errors="coerce").fillna(0.0)
    return float(amounts.sum())


def main() -> None:
    st.set_page_config(
        page_title="山竹比比的随身账本",
        page_icon="🍊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
<style>
    :root {
        --bg: #F8F9FA;
        --text: #333333;
        --primary: #8FA79A;
        --primary-deep: #7A9286;
        --line: rgba(51, 51, 51, 0.08);
    }
    .stApp {
        background: var(--bg);
        color: var(--text);
    }
    .bb-card {
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 4px 22px rgba(0, 0, 0, 0.045);
        border: 1px solid var(--line);
        padding: 1.15rem 1.25rem 1.25rem 1.25rem;
        margin-bottom: 1.15rem;
    }
    .bb-kicker {
        font-size: 0.72rem;
        font-weight: 650;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #6f6f6f;
        margin: 0 0 0.85rem 0;
    }
    .bb-hero-title {
        font-size: 1.35rem;
        font-weight: 750;
        margin: 0.15rem 0 1.35rem 0;
        color: var(--text);
        letter-spacing: -0.02em;
    }
    .bb-dash-metric div[data-testid="stMetric"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    .bb-dash-metric div[data-testid="stMetric"] label {
        font-size: 0.78rem !important;
        font-weight: 650 !important;
        letter-spacing: 0.07em !important;
        text-transform: uppercase !important;
        color: #6f6f6f !important;
    }
    .bb-dash-metric div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.85rem !important;
        font-weight: 750 !important;
        color: var(--text) !important;
    }
    .bb-list-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 1rem;
        padding: 0.72rem 0;
        border-bottom: 1px solid var(--line);
        font-size: 0.94rem;
    }
    .bb-list-row:last-child {
        border-bottom: none;
    }
    .bb-list-left {
        min-width: 0;
        flex: 1;
    }
    .bb-list-date {
        color: #6f6f6f;
        font-size: 0.82rem;
        margin-right: 0.35rem;
    }
    .bb-list-cat {
        font-weight: 600;
        color: var(--text);
    }
    .bb-list-note {
        display: block;
        color: #888888;
        font-size: 0.82rem;
        margin-top: 0.2rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .bb-list-amt {
        font-weight: 700;
        color: var(--text);
        flex-shrink: 0;
    }
    section[data-testid="stSidebar"] {
        background: #f3f4f6;
        border-right: 1px solid var(--line);
    }
    section[data-testid="stSidebar"] .bb-card {
        margin-bottom: 0.85rem;
    }
    .stApp div[data-testid="stFormSubmitButton"] > button {
        width: 100%;
        border: none;
        border-radius: 10px;
        background: var(--primary);
        color: #ffffff;
        font-weight: 650;
        padding: 0.45rem 0.65rem;
        transition: background 0.15s ease, transform 0.12s ease;
    }
    .stApp div[data-testid="stFormSubmitButton"] > button:hover {
        background: var(--primary-deep);
    }
    .stApp div[data-testid="stFormSubmitButton"] > button:active {
        transform: scale(0.98);
    }
    div[data-testid="stPlotlyChart"] {
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<p class="bb-hero-title">山竹比比 · 随身账本</p>', unsafe_allow_html=True)

    st.sidebar.markdown('<div class="bb-card">', unsafe_allow_html=True)
    st.sidebar.markdown('<p class="bb-kicker">账户设置</p>', unsafe_allow_html=True)
    user_name = st.sidebar.text_input(
        "你的名字",
        placeholder="例如：山竹比比",
        help="每个名字对应一个独立的 CSV 文件。",
        label_visibility="collapsed",
    )
    if not (user_name or "").strip():
        st.sidebar.caption("请输入名字以启用记账与总览。")
    monthly_budget = st.sidebar.number_input(
        "本月预算（元）",
        min_value=0.0,
        value=DEFAULT_MONTHLY_BUDGET,
        step=100.0,
        format="%.2f",
        help="用于计算剩余预算；超支时页面会提示。",
    )
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    name_ok = bool((user_name or "").strip())
    submitted = False
    d = date.today()
    cat = CATEGORIES[0]
    amount = 10.0
    note = ""

    st.markdown('<div class="bb-card">', unsafe_allow_html=True)
    st.markdown('<p class="bb-kicker">快捷记账</p>', unsafe_allow_html=True)
    with st.form("quick_entry", clear_on_submit=True):
        fc_date, fc_cat, fc_amt, fc_note, fc_save = st.columns([1.05, 1.15, 0.95, 1.35, 0.72], gap="small")
        with fc_date:
            d = st.date_input("日期", value=date.today(), label_visibility="collapsed")
        with fc_cat:
            cat = st.selectbox("类别", CATEGORIES, index=0, label_visibility="collapsed")
        with fc_amt:
            amount = st.number_input(
                "金额",
                min_value=0.01,
                value=10.0,
                step=1.0,
                format="%.2f",
                label_visibility="collapsed",
            )
        with fc_note:
            note = st.text_input("备注", placeholder="备注（可选）", label_visibility="collapsed")
        with fc_save:
            st.markdown('<div style="height:1.55rem;"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("保存")
    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if not name_ok:
            st.warning("请先在左侧边栏填写你的名字，再保存。")
        else:
            path = user_csv_path(user_name)
            df_save = load_wallet_df(path)
            row = {
                "date": d.isoformat(),
                "category": cat,
                "payment_method": PAYMENT_METHODS[0],
                "amount": float(amount),
                "note": (note or "").strip(),
                "recorded_at": recorded_time_to_minute(),
            }
            df_save = pd.concat([df_save, pd.DataFrame([row])], ignore_index=True)
            save_wallet_df(path, df_save)
            st.success(f"已记一笔：{cat} · ¥{float(amount):,.2f}")

    if not name_ok:
        st.info("在左侧填写你的名字后，即可查看总览、列表与分类占比。")
        return

    path = user_csv_path(user_name)
    df = load_wallet_df(path)

    today = date.today()
    m = month_mask(df, today.year, today.month)
    df_month = df.loc[m].copy() if not df.empty else df.iloc[0:0]

    try:
        df_month["amount"] = pd.to_numeric(df_month["amount"], errors="coerce").fillna(0.0)
    except Exception:
        df_month = df.iloc[0:0]

    total_month = float(df_month["amount"].sum()) if not df_month.empty else 0.0
    total_today = today_spending(df, today)
    budget_left = float(monthly_budget) - total_month
    over_budget = total_month > float(monthly_budget)

    if over_budget:
        st.markdown(
            """
<style>
    .stApp {
        background: linear-gradient(180deg, #f5ebe6 0%, #F8F9FA 38%) !important;
    }
</style>
""",
            unsafe_allow_html=True,
        )
        st.error("本月已超出预算，请注意控制支出。")

    st.markdown('<div class="bb-spacer" style="height:0.25rem;"></div>', unsafe_allow_html=True)

    d1, d2, d3 = st.columns(3, gap="medium")
    with d1:
        st.markdown('<div class="bb-card bb-dash-metric">', unsafe_allow_html=True)
        st.metric("本月总支出", f"¥ {total_month:,.2f}")
        st.markdown("</div>", unsafe_allow_html=True)
    with d2:
        st.markdown('<div class="bb-card bb-dash-metric">', unsafe_allow_html=True)
        st.metric("今日支出", f"¥ {total_today:,.2f}")
        st.markdown("</div>", unsafe_allow_html=True)
    with d3:
        st.markdown('<div class="bb-card bb-dash-metric">', unsafe_allow_html=True)
        st.metric("剩余预算", f"¥ {budget_left:,.2f}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="bb-spacer" style="height:0.35rem;"></div>', unsafe_allow_html=True)

    insight_left, insight_right = st.columns([2, 1], gap="medium")

    with insight_left:
        st.markdown('<div class="bb-card">', unsafe_allow_html=True)
        st.markdown('<p class="bb-kicker">最近账目</p>', unsafe_allow_html=True)
        if df.empty:
            st.caption("还没有记录，使用上方快捷记账添加第一笔。")
        else:
            recent = df.tail(RECENT_LIST_LIMIT).iloc[::-1]
            for _, r in recent.iterrows():
                raw_date = str(r.get("date", "") or "").strip()
                cat_lbl = html_module.escape(str(r.get("category", "") or ""))
                amt_val = pd.to_numeric(r.get("amount", 0), errors="coerce")
                if pd.isna(amt_val):
                    amt_val = 0.0
                amt_str = html_module.escape(f"¥{float(amt_val):,.2f}")
                note_raw = (str(r.get("note", "") or "")).strip()
                note_esc = html_module.escape(note_raw[:48])
                note_block = (
                    f'<span class="bb-list-note">{note_esc}</span>' if note_raw else ""
                )
                st.markdown(
                    f"""
<div class="bb-list-row">
  <div class="bb-list-left">
    <span class="bb-list-date">{html_module.escape(raw_date)}</span>
    <span class="bb-list-cat">{cat_lbl}</span>
    {note_block}
  </div>
  <div class="bb-list-amt">{amt_str}</div>
</div>
""",
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

    with insight_right:
        st.markdown('<div class="bb-card">', unsafe_allow_html=True)
        st.markdown('<p class="bb-kicker">本月分类</p>', unsafe_allow_html=True)
        if df_month.empty or float(df_month["amount"].sum()) == 0:
            st.caption("本月暂无支出，无法绘制占比。")
        else:
            pie_df = (
                df_month.groupby("category", as_index=False)["amount"]
                .sum()
                .sort_values("amount", ascending=False)
            )
            fig = px.pie(
                pie_df,
                names="category",
                values="amount",
                hole=0.5,
                color_discrete_sequence=["#8FA79A", "#9eb5aa", "#b3c7be", "#c9d8d2", "#dfe9e5"],
            )
            fig.update_traces(textposition="inside", textinfo="percent", insidetextfont_size=11)
            fig.update_layout(
                height=300,
                margin=dict(t=8, b=8, l=8, r=8),
                showlegend=True,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11, color="#333333"),
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02,
                    font=dict(size=10),
                ),
            )
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
