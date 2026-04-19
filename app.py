#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""山竹比比的随身账本 — Streamlit Web 版。"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
WALLETS_DIR = BASE_DIR / "wallets"
FIELDNAMES = ["date", "category", "amount", "note", "recorded_at"]

CATEGORIES = [
    "餐饮 🍔",
    "购物 🛍️",
    "交通 🚗",
    "娱乐 🎮",
]


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
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #fff8e7 0%, #ffe4f3 55%, #e8f4ff 100%);
        padding: 1.25rem 1.5rem;
        border-radius: 20px;
        border: 3px solid #ffb347;
        box-shadow: 4px 4px 0 #ff9aa2;
    }
    div[data-testid="stMetric"] label {
        font-size: 1.1rem !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 2.4rem !important;
        font-weight: 800;
        color: #e85d04 !important;
    }
    .wallet-title {
        font-size: 2.1rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
        color: #d9480f;
    }
    .wallet-sub {
        color: #868e96;
        font-size: 1rem;
        margin-bottom: 1rem;
    }
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="wallet-title">🍊 山竹比比的随身账本</p>'
        '<p class="wallet-sub">记一笔，开心花～</p>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("### 👤 你是谁？")
    user_name = st.sidebar.text_input(
        "输入你的名字",
        placeholder="例如：山竹比比",
        help="每个名字对应一个独立的 CSV 文件，只显示你自己的账目。",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ✏️ 记一笔")

    with st.sidebar.form("add_expense", clear_on_submit=True):
        d = st.date_input("日期", value=date.today())
        cat = st.selectbox("类别", CATEGORIES, index=0)
        amount = st.number_input("金额（元）", min_value=0.01, value=10.0, step=1.0, format="%.2f")
        note = st.text_input("备注", placeholder="可选")
        submitted = st.form_submit_button("保存到账本 💾")

    name_ok = bool((user_name or "").strip())

    if submitted:
        if not name_ok:
            st.warning("请先在侧边栏输入你的名字，再记账哦。")
        else:
            path = user_csv_path(user_name)
            df = load_wallet_df(path)
            row = {
                "date": d.isoformat(),
                "category": cat,
                "amount": float(amount),
                "note": (note or "").strip(),
                "recorded_at": recorded_time_to_minute(),
            }
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            save_wallet_df(path, df)
            st.success(f"「{safe_user_file_stem(user_name)}」已保存：{cat} ¥{amount:.2f} 🎉")
            st.balloons()

    if not name_ok:
        st.info("👈 请在左侧边栏输入你的名字，即可查看专属账单与图表。")
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

    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        st.metric("本月总支出", f"¥ {total_month:,.2f}")
    with c2:
        st.metric("本月笔数", len(df_month))
    with c3:
        st.caption("数据文件")
        st.code(path.name, language=None)

    left, right = st.columns([1.1, 1])

    with left:
        st.subheader("📒 全部明细")
        if df.empty:
            st.caption("还没有记录，在左侧记一笔吧～")
        else:
            show = df.copy()
            show["amount"] = pd.to_numeric(show["amount"], errors="coerce").round(2)
            st.dataframe(show, use_container_width=True, hide_index=True)

    with right:
        st.subheader("🎨 本月消费结构")
        if df_month.empty or df_month["amount"].sum() == 0:
            st.caption("本月暂无支出数据，无法绘制饼图。")
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
                hole=0.35,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
