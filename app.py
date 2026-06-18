import base64
import html
import io
import re
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image


APP_TITLE = "Tesouraria Grupo Botuverá"
SUBTITLE = "Gestão Profissional do Caixa Empresarial"
PARTNER = "Grupo Botuverá"
GESTOR = "M Wealth"

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_POSITIONS_DIR = BASE_DIR / "data" / "positions"
CLIENT_CONFIG = BASE_DIR / "data" / "config" / "clientes.csv"
BOTUVERA_LOGO = BASE_DIR / "data" / "assets" / "botuvera_logo.png"
MWEALTH_LOGO = BASE_DIR / "mwealth-light.png"

MIN_POS_FIXADO = 0.80
VALIDACAO_CFO_VALOR = 5_000_000
IOF_ALERT_DAYS = 22
IOF_WARN_DAYS = 18
IOF_OK_DAYS = 14

LIQUIDITY_ORDER = ["D+0", "D+1", "D+31", "N/A"]


# ============================================================
# FORMATAÇÃO
# ============================================================

def brl(v: float) -> str:
    try:
        v = float(v or 0)
    except Exception:
        v = 0.0

    txt = f"R$ {v:,.2f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float) -> str:
    try:
        v = float(v or 0)
    except Exception:
        v = 0.0

    txt = f"{100 * v:,.2f}%"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def safe_div(a, b):
    try:
        return 0.0 if not b else float(a) / float(b)
    except Exception:
        return 0.0


def parse_money(x) -> float:
    if x is None:
        return 0.0

    if isinstance(x, (int, float, np.number)):
        try:
            if pd.isna(x):
                return 0.0
        except Exception:
            pass
        return float(x)

    try:
        if pd.isna(x):
            return 0.0
    except Exception:
        pass

    s = str(x).strip()
    if s in ["", "-", "—", "nan", "None", "NaT"]:
        return 0.0

    s = s.replace("R$", "").replace("%", "").strip()
    s = s.replace(".", "").replace(",", ".")

    try:
        return float(s)
    except Exception:
        return 0.0


def parse_date_br(x):
    if x is None:
        return pd.NaT

    try:
        if pd.isna(x):
            return pd.NaT
    except Exception:
        pass

    if isinstance(x, (datetime, pd.Timestamp)):
        ts = pd.to_datetime(x, errors="coerce")
        return pd.NaT if pd.isna(ts) else ts.date()

    if isinstance(x, date):
        return x

    s = str(x).strip()
    if s in ["", "-", "—", "nan", "NaT", "None"]:
        return pd.NaT

    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass

    ts = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return pd.NaT if pd.isna(ts) else ts.date()


def fmt_date_br(x) -> str:
    if x is None:
        return "—"

    try:
        if pd.isna(x):
            return "—"
    except Exception:
        pass

    try:
        return pd.to_datetime(x).strftime("%d/%m/%Y")
    except Exception:
        return "—"


def is_empty(x) -> bool:
    try:
        return pd.isna(x) or str(x).strip() == ""
    except Exception:
        return False


def logo_base64(path: Path) -> str:
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def short_money(v: float) -> str:
    try:
        v = float(v or 0)
    except Exception:
        v = 0

    if abs(v) >= 1_000_000:
        return f"R$ {v / 1_000_000:,.2f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    return brl(v)


# ============================================================
# CSS / LAYOUT
# ============================================================

def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        :root {
            color-scheme: dark !important;
            --bg-main: #03122b;
            --bg-panel: #0f1b31;
            --bg-panel-2: #162238;
            --border-soft: rgba(148,163,184,.16);
            --text-main: #F8FAFC;
            --text-soft: #CBD5E1;
            --text-muted: #94A3B8;
            --accent: #8DB7FF;
            --accent-2: #9EC5FF;
            --green: #22C55E;
            --red: #F87171;
            --yellow: #FBBF24;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
            color: var(--text-main) !important;
            background: var(--bg-main) !important;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 0%, rgba(59,130,246,.16), transparent 28%),
                radial-gradient(circle at 100% 0%, rgba(15,118,110,.10), transparent 22%),
                linear-gradient(180deg, #03122b 0%, #04152e 46%, #031126 100%) !important;
            color: var(--text-main) !important;
        }

        .stApp,
        .main,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] {
            background-color: transparent !important;
            color: var(--text-main) !important;
        }

        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
            background: transparent !important;
        }

        .block-container {
            max-width: 1320px !important;
            margin: 0 auto;
            padding-top: 1.15rem;
            padding-left: 1.1rem;
            padding-right: 1.1rem;
            padding-bottom: 3rem;
        }

        section[data-testid="stSidebar"] {
            background: #09162F !important;
            border-right: 1px solid rgba(148, 163, 184, .15);
        }

        .hero-shell {
            background: linear-gradient(135deg, rgba(8,21,44,.88), rgba(5,16,35,.88));
            border: 1px solid rgba(148,163,184,.10);
            border-radius: 26px;
            padding: 24px 26px 24px;
            box-shadow: 0 18px 55px rgba(0,0,0,.20);
            margin-bottom: 18px;
        }

        .hero {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap: 28px;
        }

        .hero-left {
            display:flex;
            align-items:center;
            gap: 26px;
            min-width:0;
        }

        .mw-mark {
            display:flex;
            align-items:center;
            border-right: 1px solid rgba(148,163,184,.16);
            padding-right: 30px;
            min-width: 0;
        }

        .mw-logo {
            width: 178px;
            max-width: 178px;
            height: auto;
            display:block;
            object-fit: contain;
        }

        .mw-logo-fallback {
            color:#F8FAFC;
            font-size: 1.35rem;
            font-weight: 900;
            letter-spacing: -.03em;
            white-space: nowrap;
        }

        .hero-title h1 {
            margin: 0;
            line-height: .95;
            font-weight: 900;
            color:#F8FAFC;
        }

        .title-line {
            display:flex;
            align-items:baseline;
            gap: 26px;
            flex-wrap: wrap;
        }

        .title-main {
            font-size: 46px;
            letter-spacing: -.045em;
            color:#F8FAFC;
        }

        .title-service {
            font-size: 46px;
            letter-spacing: -.035em;
            color:#9EC5FF;
            font-style: italic;
        }

        .hero-title p {
            margin: 12px 0 0;
            color: #A9C7FF;
            font-weight: 700;
            font-size: 1rem;
        }

        .hero-right {
            display:flex;
            align-items:center;
            gap: 22px;
        }

        .hero-meta {
            display:grid;
            grid-template-columns:auto auto;
            gap: 8px 20px;
            align-items:center;
        }

        .hero-meta .k {
            color:#9EC5FF;
            text-transform:uppercase;
            letter-spacing:.17em;
            font-size: .72rem;
            font-weight: 800;
        }

        .hero-meta .v {
            color:#FFF;
            font-weight: 800;
            font-size: .90rem;
        }

        .hero-logo {
            width: 92px;
            height: 92px;
            object-fit: contain;
            background: rgba(255,255,255,.025);
            border-radius: 16px;
            padding: 7px;
        }

        .section-title {
            color: #A9C7FF;
            letter-spacing: .22em;
            text-transform: uppercase;
            font-weight: 900;
            font-size: .76rem;
            margin: 18px 0 12px;
            padding-left: 10px;
            border-left: 3px solid rgba(141,183,255,.72);
            opacity: .96;
        }

        .soft-rule {
            height: 1px;
            width: 100%;
            margin: 4px 0 18px;
            background: linear-gradient(90deg, rgba(141,183,255,.22), rgba(148,163,184,.08), transparent);
        }

        .kpi-grid {
            display:grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 14px;
            margin: 10px 0 18px;
        }

        .kpi-card {
            min-height: 108px;
            background: linear-gradient(135deg, rgba(30,41,59,.96), rgba(15,23,42,.96));
            border: 1px solid rgba(148,163,184,.14);
            border-radius: 20px;
            padding: 16px 18px;
            box-shadow: 0 12px 34px rgba(0,0,0,.14);
            display:flex;
            flex-direction:column;
            justify-content:center;
        }

        .kpi-label {
            color:#A9C7FF;
            text-transform:uppercase;
            letter-spacing:.15em;
            font-size:.66rem;
            font-weight:900;
            margin-bottom:10px;
        }

        .kpi-value {
            color:#FFF;
            font-size:1.55rem;
            line-height:1.05;
            font-weight:900;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .kpi-sub {
            color:#94A3B8;
            font-size:.78rem;
            font-weight:700;
            margin-top:8px;
            min-height:18px;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .kpi-sub.good {
            color:#22C55E;
        }

        .panel {
            background: linear-gradient(135deg, rgba(30,41,59,.86), rgba(15,23,42,.88));
            border: 1px solid rgba(148,163,184,.12);
            border-radius: 24px;
            padding: 20px;
            box-shadow: 0 14px 42px rgba(0,0,0,.16);
        }

        div[data-testid="stPlotlyChart"] {
            background: linear-gradient(135deg, rgba(30,41,59,.74), rgba(15,23,42,.76));
            border: 1px solid rgba(148,163,184,.11);
            border-radius: 24px;
            padding: 14px 14px 10px;
            box-shadow: 0 14px 42px rgba(0,0,0,.14);
        }

        .account-card {
            background: linear-gradient(135deg, rgba(30,41,59,.92), rgba(15,23,42,.92));
            border: 1px solid rgba(148,163,184,.13);
            border-radius: 22px;
            padding: 20px;
            box-shadow: 0 14px 44px rgba(0,0,0,.14);
            margin-bottom: 16px;
        }

        .account-head {
            display:flex;
            justify-content:space-between;
            gap: 18px;
            align-items:flex-start;
        }

        .account-left {
            display:flex;
            gap: 14px;
            align-items:flex-start;
        }

        .avatar {
            width: 50px;
            height: 50px;
            border-radius: 16px;
            display:flex;
            align-items:center;
            justify-content:center;
            background: linear-gradient(135deg,#8DB7FF,#CABFFD);
            color: #FFF;
            font-weight: 900;
            font-size: 1.08rem;
            flex: 0 0 auto;
        }

        .name {
            color:#FFF;
            font-size: 1.18rem;
            font-weight: 800;
            margin-bottom: 2px;
        }

        .muted {
            color:#94A3B8;
            font-size: .86rem;
        }

        .money {
            color:#FFF;
            font-size: 1.45rem;
            font-weight: 900;
            text-align:right;
        }

        .submoney {
            color:#9EC5FF;
            font-size: .82rem;
            font-weight: 800;
            text-align:right;
            margin-top: 4px;
        }

        .bar-bg {
            margin-top: 14px;
            width:100%;
            height: 9px;
            border-radius: 999px;
            background: rgba(148,163,184,.16);
            overflow: hidden;
        }

        .bar-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #8DB7FF, #CABFFD, #6EE7B7, #F7C561);
        }

        .badge {
            display:inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            font-size: .72rem;
            font-weight: 900;
            border: 1px solid rgba(255,255,255,.16);
            margin-left: 8px;
            white-space: nowrap;
        }

        .ok {
            background: rgba(16,185,129,.16);
            color:#6EE7B7;
        }

        .warn {
            background: rgba(245,158,11,.16);
            color:#FCD34D;
        }

        .danger {
            background: rgba(239,68,68,.16);
            color:#FCA5A5;
        }

        .info {
            background: rgba(96,165,250,.16);
            color:#BFDBFE;
        }

        .table-shell {
            background: linear-gradient(135deg, rgba(30,41,59,.92), rgba(15,23,42,.92));
            border: 1px solid rgba(148,163,184,.16);
            border-radius: 20px;
            overflow-x: auto;
            overflow-y: hidden;
            width: 100%;
            max-width: 100%;
            box-shadow: 0 14px 42px rgba(0,0,0,.14);
        }

        .table-shell::-webkit-scrollbar {
            height: 9px;
        }

        .table-shell::-webkit-scrollbar-track {
            background: rgba(15,23,42,.50);
            border-radius: 999px;
        }

        .table-shell::-webkit-scrollbar-thumb {
            background: rgba(141,183,255,.45);
            border-radius: 999px;
        }

        table.pretty {
            width: 100%;
            min-width: 100%;
            border-collapse: collapse;
            table-layout: auto;
        }
        
        .table-shell.wide table.pretty {
            min-width: 1380px;
        }

        table.pretty thead {
            background: rgba(255,255,255,.04);
        }

        table.pretty th {
            color: #9EC5FF;
            font-size: .70rem;
            letter-spacing: .09em;
            text-transform: uppercase;
            padding: 13px 14px;
            text-align: left;
            border-bottom: 1px solid rgba(148,163,184,.16);
            white-space: nowrap;
        }

        table.pretty td {
            color: #F8FAFC;
            padding: 13px 14px;
            border-bottom: 1px solid rgba(148,163,184,.10);
            vertical-align: middle;
            font-weight: 650;
            line-height: 1.55;
        }

        table.pretty tbody tr:last-child td {
            border-bottom: none;
        }

        table.pretty td.num,
        table.pretty th.num {
            text-align: right;
            white-space: nowrap;
        }

        table.pretty td.center,
        table.pretty th.center {
            text-align: center;
            white-space: nowrap;
        }

        table.pretty td.wrap {
            white-space: normal;
            min-width: 190px;
        }

        .empty-state {
            color:#94A3B8;
            padding: 22px;
        }

        .ir-pill {
            display:inline-block;
            padding: 7px 10px;
            border-radius: 999px;
            background: rgba(239,68,68,.14);
            color:#FCA5A5;
            border:1px solid rgba(239,68,68,.24);
            font-weight:900;
            font-size:.78rem;
            white-space:nowrap;
        }

        .footer {
            text-align: center;
            color: #64748B;
            font-size: .78rem;
            margin-top: 34px;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
            border-bottom: 1px solid rgba(148,163,184,.14);
        }

        .stTabs [data-baseweb="tab"] {
            color: #A5B4FC !important;
            font-weight: 800;
            padding-left: 0;
            padding-right: 0;
            background: transparent !important;
        }

        .stTabs [aria-selected="true"] {
            color: #FFF !important;
            border-bottom: 3px solid #8DB7FF;
        }

        div[data-testid="stExpander"] {
            background: rgba(15,23,42,.58) !important;
            border: 1px solid rgba(148,163,184,.12) !important;
            border-radius: 16px !important;
            margin: -4px 0 14px;
        }

        div[data-testid="stExpander"] summary {
            color:#BFDBFE !important;
            font-weight:800;
        }

        .stDownloadButton > button,
        .stButton > button {
            border-radius: 999px !important;
            border: 1px solid rgba(148,163,184,.22) !important;
            background: #111D33 !important;
            color: #BFDBFE !important;
            font-weight: 800 !important;
            padding: 0.35rem 0.8rem !important;
            min-height: 2.1rem !important;
            box-shadow: none !important;
        }

        .stDownloadButton > button:hover,
        .stButton > button:hover {
            background: #17243D !important;
            border-color: rgba(141,183,255,.45) !important;
            color: #FFFFFF !important;
        }

        input,
        textarea,
        [data-baseweb="input"] input,
        [data-baseweb="select"] {
            color: #F8FAFC !important;
            background-color: #111D33 !important;
            border-color: rgba(148,163,184,.22) !important;
        }

        label,
        p,
        span,
        div,
        button {
            color-scheme: dark !important;
        }

        @media (max-width: 1180px) {
            .kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 1100px) {
            .hero {
                flex-direction: column;
                align-items: flex-start;
            }

            .hero-right {
                width: 100%;
                justify-content: space-between;
            }

            .title-main,
            .title-service {
                font-size: 38px;
            }

            .mw-logo {
                width: 150px;
            }
        }
        
        div[role="radiogroup"] {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 14px;
        }
        
        div[role="radiogroup"] label {
            background: rgba(15,23,42,.78) !important;
            border: 1px solid rgba(148,163,184,.18) !important;
            border-radius: 999px !important;
            padding: 7px 14px !important;
            color: #F8FAFC !important;
            font-weight: 800 !important;
        }
        
        div[role="radiogroup"] label:hover {
            border-color: rgba(141,183,255,.55) !important;
            background: rgba(30,41,59,.92) !important;
        }
        
        div[role="radiogroup"] input {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# HEADER / COMPONENTES
# ============================================================

def render_header(reference_date: str):
    botuvera_logo = logo_base64(BOTUVERA_LOGO)
    mwealth_logo = logo_base64(MWEALTH_LOGO)

    botuvera_logo_html = (
        f'<img class="hero-logo" src="data:image/png;base64,{botuvera_logo}" />'
        if botuvera_logo else ""
    )

    mwealth_logo_html = (
        f'<img class="mw-logo" src="data:image/png;base64,{mwealth_logo}" alt="M Wealth" />'
        if mwealth_logo else '<div class="mw-logo-fallback">M Wealth</div>'
    )

    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="hero">
                <div class="hero-left">
                    <div class="mw-mark">
                        {mwealth_logo_html}
                    </div>
                    <div class="hero-title">
                        <h1 class="title-line">
                            <span class="title-main">Tesouraria</span>
                            <span class="title-service">As a Service</span>
                        </h1>
                        <p>{SUBTITLE}</p>
                    </div>
                </div>
                <div class="hero-right">
                    <div class="hero-meta">
                        <div class="k">Data</div><div class="v">{reference_date}</div>
                        <div class="k">Parceiro</div><div class="v">{PARTNER}</div>
                        <div class="k">Gestor</div><div class="v">{GESTOR}</div>
                    </div>
                    {botuvera_logo_html}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str):
    st.markdown(
        f'<div class="section-title">{html.escape(title)}</div><div class="soft-rule"></div>',
        unsafe_allow_html=True,
    )


def html_table(df: pd.DataFrame, col_labels=None, col_classes=None, allow_html_cols=None):
    if df is None or df.empty:
        return '<div class="table-shell"><div class="empty-state">Sem dados para exibir.</div></div>'

    work = df.copy()
    columns = list(work.columns)
    labels = col_labels or {c: c for c in columns}
    classes = col_classes or {}
    allow_html_cols = set(allow_html_cols or [])

    # Só usa tabela larga quando realmente precisa.
    # Isso evita que tabelas pequenas fiquem com colunas gigantes/vazias.
    shell_class = "table-shell wide" if len(columns) >= 7 else "table-shell"

    head = "".join(
        f'<th class="{classes.get(c, "")}">{html.escape(str(labels.get(c, c)))}</th>'
        for c in columns
    )

    rows = []
    for _, row in work.iterrows():
        tds = []
        for c in columns:
            val = row[c]

            if val is None or (isinstance(val, float) and pd.isna(val)):
                txt = "—"
            else:
                txt = str(val)

            txt = txt if c in allow_html_cols else html.escape(txt)
            tds.append(f'<td class="{classes.get(c, "")}">{txt}</td>')

        rows.append("<tr>" + "".join(tds) + "</tr>")

    return (
        f'<div class="{shell_class}">'
        '<table class="pretty">'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
        '</div>'
    )


def efficiency_badge(days) -> str:
    if days is None or pd.isna(days):
        return '<span class="badge info">sem data</span>'

    try:
        d = int(days)
    except Exception:
        return '<span class="badge info">sem data</span>'

    if d >= IOF_ALERT_DAYS:
        return f'<span class="badge danger">{d}d</span>'
    if d >= IOF_WARN_DAYS:
        return f'<span class="badge warn">{d}d</span>'
    if d >= IOF_OK_DAYS:
        return f'<span class="badge info">{d}d</span>'

    return f'<span class="badge ok">{d}d</span>'


def status_badge(ok: bool, text_ok="OK", text_bad="Atenção"):
    cls = "ok" if ok else "danger"
    text = text_ok if ok else text_bad
    return f'<span class="badge {cls}">{text}</span>'


# ============================================================
# PARSER XP
# ============================================================

def load_clients():
    default = pd.DataFrame(
        [
            {"conta": "7983962", "titular": "Irineu Afonso", "tipo": "principal"},
            {"conta": "5166121", "titular": "Adriano Bissoni", "tipo": "principal"},
            {"conta": "4163084", "titular": "Vicente Bissoni", "tipo": "residual"},
            {"conta": "11370136", "titular": "Deise Cristina", "tipo": "residual"},
            {"conta": "9445242", "titular": "Transportes Botuverá", "tipo": "residual"},
        ]
    )

    if CLIENT_CONFIG.exists():
        try:
            cfg = pd.read_csv(CLIENT_CONFIG, dtype={"conta": str})
            if {"conta", "titular"}.issubset(cfg.columns):
                return cfg
        except Exception:
            pass

    return default


def classify_product(group_name: str, subgroup_name: str, asset_name: str):
    s = f"{group_name or ''} {subgroup_name or ''} {asset_name or ''}".lower()

    if "compromiss" in s:
        return "Op. Compromissadas", "D+0", "pos_fixado"

    if any(x in s for x in ["lca", "lci"]):
        return "Renda Fixa Isenta", "D+0", "isento"

    if "fundo" in s or "fic" in s or "firf" in s:
        if "d+31" in s or "d31" in s:
            return "Fundos D+31", "D+31", "pos_fixado"
        return "Fundos D+0", "D+0", "pos_fixado"

    if any(x in s for x in ["cdb", "tesouro", "letra financeira"]):
        return "Renda Fixa Pós-Fixada", "D+31", "pos_fixado"

    if "saldo" in s:
        return "Saldo em Conta", "D+0", "caixa"

    return "Outros", "N/A", "outros"


def build_position_from_row(
    row,
    group_name: str,
    subgroup_name: str,
    account: str,
    titular: str,
    ref_date: date,
):
    group_text = f"{group_name or ''} {subgroup_name or ''}".lower()

    asset = ""
    appl = pd.NaT
    venc = pd.NaT
    valor_bruto = 0.0
    valor_liquido = 0.0

    if "fundo" in group_text:
        asset = str(row.iloc[0]).strip() if not is_empty(row.iloc[0]) else str(group_name).strip().upper()
        valor_bruto = parse_money(row.iloc[5]) if len(row) > 5 else 0.0
        valor_liquido = parse_money(row.iloc[6]) if len(row) > 6 else valor_bruto

    elif "compromiss" in group_text:
        asset = "OPERAÇÕES COMPROMISSADAS"
        appl = parse_date_br(row.iloc[1]) if len(row) > 1 else pd.NaT
        venc = parse_date_br(row.iloc[3]) if len(row) > 3 else pd.NaT
        valor_bruto = parse_money(row.iloc[8]) if len(row) > 8 else 0.0
        valor_liquido = parse_money(row.iloc[9]) if len(row) > 9 else valor_bruto

    else:
        asset = str(row.iloc[0]).strip() if not is_empty(row.iloc[0]) else str(group_name).strip().upper()
        appl = parse_date_br(row.iloc[1]) if len(row) > 1 else pd.NaT
        venc = parse_date_br(row.iloc[3]) if len(row) > 3 else pd.NaT
        valor_bruto = parse_money(row.iloc[8]) if len(row) > 8 else 0.0
        valor_liquido = parse_money(row.iloc[9]) if len(row) > 9 else valor_bruto

    if valor_bruto <= 0:
        return None

    if valor_liquido <= 0:
        valor_liquido = valor_bruto

    produto, liquidez, fator = classify_product(group_name, subgroup_name, asset)

    days = None
    if isinstance(appl, date) and not pd.isna(appl) and isinstance(ref_date, date):
        try:
            days = max((ref_date - appl).days, 0)
        except Exception:
            days = None

    return {
        "conta": str(account),
        "titular": titular,
        "ativo": asset.upper(),
        "produto": produto,
        "liquidez": liquidez,
        "fator": fator,
        "aplicacao": appl,
        "vencimento": venc,
        "dias_desde_aplicacao": days,
        "valor_bruto": valor_bruto,
        "valor_liquido": valor_liquido,
        "valor": valor_bruto,
        "ir": max(valor_bruto - valor_liquido, 0.0),
        "grupo_origem": group_name,
        "subgrupo_origem": subgroup_name,
    }


def parse_xp_file(file_obj, filename: str, clients: pd.DataFrame):
    df = pd.read_excel(
        file_obj,
        sheet_name=0,
        header=None,
        dtype=object,
        engine="openpyxl",
    )

    header_text = " ".join([str(x) for x in df.iloc[0].dropna().tolist()])

    account_match = re.search(r"Conta:\s*(\d+)", header_text)
    account = account_match.group(1) if account_match else re.sub(r"\D+", "", filename)

    date_match = re.search(r"(\d{2}/\d{2}/\d{4})", header_text)
    ref_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date() if date_match else date.today()

    client_match = clients[clients["conta"].astype(str) == str(account)]
    titular = client_match.iloc[0]["titular"] if not client_match.empty else f"Conta {account}"
    tipo = client_match.iloc[0]["tipo"] if (not client_match.empty and "tipo" in client_match.columns) else ""

    patrimonio_arquivo = parse_money(df.iloc[3, 0]) if df.shape[0] > 3 else 0.0
    saldo_disponivel = parse_money(df.iloc[3, 2]) if df.shape[0] > 3 and df.shape[1] > 2 else 0.0

    positions = []
    current_group = None
    current_subgroup = None
    capture_rows = False

    for _, row in df.iterrows():
        first = "" if is_empty(row.iloc[0]) else str(row.iloc[0]).strip()
        values_lower = [str(x).strip().lower() for x in row.tolist() if not is_empty(x)]

        if first.startswith("Saldo Disponível"):
            capture_rows = False
            current_subgroup = None
            continue

        if first and "|" in first and re.match(r"^\s*\d+[\d,.]*%\|", first):
            label = first.split("|", 1)[1].strip()
            is_header_row = any(v in ["aplicação", "data cota"] for v in values_lower)

            if is_header_row:
                current_subgroup = label
                capture_rows = True
            else:
                current_group = label
                current_subgroup = None
                capture_rows = False

            continue

        if capture_rows:
            if all(is_empty(x) for x in row.tolist()):
                capture_rows = False
                continue

            pos = build_position_from_row(
                row=row,
                group_name=current_group,
                subgroup_name=current_subgroup,
                account=account,
                titular=titular,
                ref_date=ref_date,
            )

            if pos is not None:
                positions.append(pos)

    if saldo_disponivel > 0:
        positions.append(
            {
                "conta": str(account),
                "titular": titular,
                "ativo": "SALDO EM CONTA",
                "produto": "Saldo em Conta",
                "liquidez": "D+0",
                "fator": "caixa",
                "aplicacao": pd.NaT,
                "vencimento": pd.NaT,
                "dias_desde_aplicacao": None,
                "valor_bruto": saldo_disponivel,
                "valor_liquido": saldo_disponivel,
                "valor": saldo_disponivel,
                "ir": 0.0,
                "grupo_origem": "Saldo em Conta",
                "subgrupo_origem": "Saldo em Conta",
            }
        )

    summary = {
        "conta": str(account),
        "titular": titular,
        "tipo": tipo,
        "patrimonio_arquivo": patrimonio_arquivo,
        "saldo_disponivel": saldo_disponivel,
        "data_referencia": ref_date,
        "arquivo": filename,
    }

    return pd.DataFrame(positions), summary


def get_mtime_token():
    files = list(DEFAULT_POSITIONS_DIR.glob("*.xlsx"))
    return sum(f.stat().st_mtime for f in files) if files else 0.0


@st.cache_data(show_spinner=False)
def load_data_from_disk(_mtime_token: float):
    clients = load_clients()
    files = sorted(DEFAULT_POSITIONS_DIR.glob("*.xlsx"))

    all_positions = []
    summaries = []

    for file in files:
        pos, summ = parse_xp_file(file, file.name, clients)
        if not pos.empty:
            all_positions.append(pos)
        summaries.append(summ)

    positions = pd.concat(all_positions, ignore_index=True) if all_positions else pd.DataFrame()
    summary = pd.DataFrame(summaries)

    return positions, summary


def load_data_from_uploads(uploaded_files):
    clients = load_clients()

    all_positions = []
    summaries = []

    for up in uploaded_files:
        pos, summ = parse_xp_file(up, up.name, clients)
        if not pos.empty:
            all_positions.append(pos)
        summaries.append(summ)

    positions = pd.concat(all_positions, ignore_index=True) if all_positions else pd.DataFrame()
    summary = pd.DataFrame(summaries)

    return positions, summary


# ============================================================
# ENRIQUECIMENTO / KPIS
# ============================================================

def enrich(positions: pd.DataFrame, summary: pd.DataFrame):
    if positions.empty:
        return positions, summary

    positions = positions.copy()

    for col in ["valor", "valor_bruto", "valor_liquido", "ir"]:
        positions[col] = pd.to_numeric(positions[col], errors="coerce").fillna(0.0)

    positions["ir"] = (positions["valor_bruto"] - positions["valor_liquido"]).clip(lower=0)

    positions["aplicacao_fmt"] = positions["aplicacao"].apply(fmt_date_br)
    positions["vencimento_fmt"] = positions["vencimento"].apply(fmt_date_br)

    totals_by_account = positions.groupby("conta")["valor"].sum().rename("patrimonio")
    liquid_by_account = positions.groupby("conta")["valor_liquido"].sum().rename("patrimonio_liquido")
    ir_by_account = positions.groupby("conta")["ir"].sum().rename("ir_total_conta")

    positions = positions.merge(totals_by_account, on="conta", how="left", suffixes=("", "_conta"))

    positions["participacao_conta"] = positions["valor"] / positions["patrimonio"]
    positions["participacao_total"] = positions["valor"] / positions["valor"].sum()

    positions["participacao_fmt"] = positions["participacao_conta"].apply(pct)
    positions["valor_fmt"] = positions["valor"].apply(brl)
    positions["valor_bruto_fmt"] = positions["valor_bruto"].apply(brl)
    positions["valor_liquido_fmt"] = positions["valor_liquido"].apply(brl)
    positions["ir_fmt"] = positions["ir"].apply(brl)
    positions["ir_pill"] = positions["ir"].apply(
        lambda x: f'<span class="ir-pill">{brl(x)}</span>' if x > 0 else brl(0)
    )

    summary = summary.copy()
    if summary.empty:
        return positions, summary

    summary["patrimonio"] = summary["conta"].astype(str).map(totals_by_account.to_dict()).fillna(
        summary.get("patrimonio_arquivo", 0)
    )
    summary["patrimonio_liquido"] = summary["conta"].astype(str).map(liquid_by_account.to_dict()).fillna(summary["patrimonio"])
    summary["ir_total"] = summary["conta"].astype(str).map(ir_by_account.to_dict()).fillna(0.0)

    summary["participacao_total"] = summary["patrimonio"] / summary["patrimonio"].sum()
    summary["participacao_fmt"] = summary["participacao_total"].apply(pct)
    summary["patrimonio_fmt"] = summary["patrimonio"].apply(brl)

    summary["iniciais"] = summary["titular"].apply(
        lambda s: "".join([p[0] for p in str(s).split()[:2]]).upper()
    )
    summary["posicoes"] = summary["conta"].astype(str).map(
        positions.groupby("conta").size().to_dict()
    ).fillna(0).astype(int)

    return positions, summary


def calc_kpis(positions: pd.DataFrame, summary: pd.DataFrame):
    total = float(positions["valor"].sum()) if not positions.empty else 0.0
    total_liquido = float(positions["valor_liquido"].sum()) if not positions.empty else 0.0
    ir_total = float(positions["ir"].sum()) if not positions.empty else 0.0

    liq_d0 = float(positions[positions["liquidez"].isin(["D+0", "D+1"])]["valor"].sum())
    isenta = float(positions[positions["produto"].eq("Renda Fixa Isenta")]["valor"].sum())
    travado = float(positions[positions["liquidez"].eq("D+31")]["valor"].sum())

    maior = summary.sort_values("patrimonio", ascending=False).iloc[0] if not summary.empty else None

    return {
        "total": total,
        "total_liquido": total_liquido,
        "ir_total": ir_total,
        "liquidez_d0": liq_d0,
        "liquidez_d0_pct": safe_div(liq_d0, total),
        "isenta": isenta,
        "isenta_pct": safe_div(isenta, total),
        "travado": travado,
        "travado_pct": safe_div(travado, total),
        "contas": int(summary["conta"].nunique()) if not summary.empty else 0,
        "maior_titular_nome": str(maior["titular"]) if maior is not None else "—",
        "maior_titular_pct": float(maior["participacao_total"]) if maior is not None else 0.0,
    }


# ============================================================
# EXPORTAÇÃO
# ============================================================

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Detalhamento")

    return output.getvalue()


# ============================================================
# RENDERIZAÇÕES
# ============================================================

def kpi_card(label, value, sub=""):
    sub_class = "kpi-sub good" if str(sub).startswith("↑") else "kpi-sub"
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{html.escape(str(label))}</div>
        <div class="kpi-value" title="{html.escape(str(value))}">{html.escape(str(value))}</div>
        <div class="{sub_class}">{html.escape(str(sub))}</div>
    </div>
    """


def render_account_card(row, total_geral: float):
    st.markdown(
        f"""
        <div class="account-card">
            <div class="account-head">
                <div class="account-left">
                    <div class="avatar">{html.escape(str(row['iniciais']))}</div>
                    <div>
                        <div class="name">{html.escape(str(row['titular']))}</div>
                        <div class="muted">Conta {html.escape(str(row['conta']))} • {int(row['posicoes'])} posição(ões)</div>
                    </div>
                </div>
                <div>
                    <div class="money">{brl(row['patrimonio'])}</div>
                    <div class="submoney">{pct(safe_div(row['patrimonio'], total_geral))}</div>
                </div>
            </div>
            <div class="bar-bg">
                <div class="bar-fill" style="width:{max(min(100 * safe_div(row['patrimonio'], total_geral), 100), 0):.2f}%"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_visao_geral(positions, summary, kpis):
    st.markdown(
        """
        <div class="kpi-grid">
        """
        + kpi_card("Patrimônio bruto", short_money(kpis["total"]), "")
        + kpi_card("Valor líquido", short_money(kpis["total_liquido"]), "")
        + kpi_card("IR estimado", brl(kpis["ir_total"]), "")
        + kpi_card("Liquidez D+0/D+1", pct(kpis["liquidez_d0_pct"]), f"↑ {brl(kpis['liquidez_d0'])}")
        + kpi_card("Maior titular", pct(kpis["maior_titular_pct"]), f"↑ {kpis['maior_titular_nome']}")
        + """
        </div>
        """,
        unsafe_allow_html=True,
    )

    section("Distribuição por produto")
    left, right = st.columns([1.05, 1])

    prod = positions.groupby("produto", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
    prod["participacao"] = prod["valor"] / prod["valor"].sum()

    with left:
        fig = go.Figure(
            go.Pie(
                labels=prod["produto"],
                values=prod["valor"],
                hole=0.62,
                textinfo="none",
                marker=dict(colors=["#8DB7FF", "#6EE7B7", "#CABFFD", "#F7C561", "#94A3B8"]),
            )
        )

        fig.update_layout(
            height=330,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E2E8F0"),
            showlegend=False,
            annotations=[
                dict(
                    text=short_money(kpis["total"]),
                    showarrow=False,
                    font=dict(size=17, color="#FFF", family="Inter"),
                )
            ],
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        disp = prod.copy()
        disp["participação"] = disp["participacao"].apply(pct)
        disp["valor (R$)"] = disp["valor"].apply(brl)
        disp = disp[["produto", "participação", "valor (R$)"]]

        st.markdown(
            html_table(
                disp,
                col_classes={
                    "participação": "num",
                    "valor (R$)": "num",
                },
            ),
            unsafe_allow_html=True,
        )

    section("Concentração por titular")
    titular = summary.sort_values("patrimonio", ascending=True).copy()

    fig = go.Figure(
        go.Bar(
            x=titular["participacao_total"],
            y=titular["titular"],
            orientation="h",
            marker=dict(color="#8DB7FF"),
            text=titular["participacao_total"].apply(pct),
            textposition="outside",
        )
    )

    fig.update_layout(
        height=max(310, 90 + 48 * len(titular)),
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0"),
        xaxis=dict(
            tickformat=".0%",
            range=[0, max(1, titular["participacao_total"].max() * 1.1)],
            gridcolor="rgba(148,163,184,.10)",
        ),
        yaxis=dict(gridcolor="rgba(148,163,184,.0)"),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    section("Detalhamento por produto")
    prod_table = prod.copy()
    prod_table["liquidez"] = prod_table["produto"].map(
        positions.groupby("produto")["liquidez"].agg(
            lambda s: ", ".join(
                sorted(
                    s.unique(),
                    key=lambda x: LIQUIDITY_ORDER.index(x) if x in LIQUIDITY_ORDER else 99,
                )
            )
        ).to_dict()
    )
    prod_table["participação"] = prod_table["participacao"].apply(pct)
    prod_table["valor (R$)"] = prod_table["valor"].apply(brl)
    prod_table = prod_table[["produto", "liquidez", "participação", "valor (R$)"]]

    st.markdown(
        html_table(
            prod_table,
            col_classes={
                "liquidez": "center",
                "participação": "num",
                "valor (R$)": "num",
            },
        ),
        unsafe_allow_html=True,
    )


def render_por_titular(positions, summary, kpis):
    section("Posição por titular")
    st.markdown(
        f"<div style='text-align:right;font-size:1.65rem;font-weight:900;margin:-12px 0 10px'>{brl(kpis['total'])}</div>",
        unsafe_allow_html=True,
    )

    for _, row in summary.sort_values("patrimonio", ascending=False).iterrows():
        render_account_card(row, kpis["total"])

        detail = positions[positions["conta"].astype(str) == str(row["conta"])].copy()
        if detail.empty:
            continue

        with st.expander(f"Ver posições de {row['titular']}", expanded=False):
            produto = detail.groupby("produto", as_index=False).agg(
                valor=("valor", "sum"),
                valor_liquido=("valor_liquido", "sum"),
                ir=("ir", "sum"),
            ).sort_values("valor", ascending=False)

            produto["participação"] = produto["valor"] / produto["valor"].sum()
            produto["participação"] = produto["participação"].apply(pct)
            produto["bruto (R$)"] = produto["valor"].apply(brl)
            produto["IR (R$)"] = produto["ir"].apply(brl)
            produto["líquido (R$)"] = produto["valor_liquido"].apply(brl)
            produto = produto[["produto", "participação", "bruto (R$)", "IR (R$)", "líquido (R$)"]]

            st.markdown(
                html_table(
                    produto,
                    col_classes={
                        "participação": "num",
                        "bruto (R$)": "num",
                        "IR (R$)": "num",
                        "líquido (R$)": "num",
                    },
                ),
                unsafe_allow_html=True,
            )


def render_detalhamento(positions, summary):
    section("Detalhamento das contas")

    titulares = ["Todos"] + summary.sort_values("titular")["titular"].tolist()
    selected = st.radio("Titular", titulares, horizontal=True, label_visibility="collapsed")

    df = positions.copy()
    if selected != "Todos":
        df = df[df["titular"] == selected]

    if df.empty:
        st.info("Sem posições para exibir.")
        return

    total = float(df["valor"].sum())
    contas = int(df["conta"].nunique())
    posicoes = int(len(df))
    titulo = selected if selected != "Todos" else "Grupo Botuverá"

    st.markdown(
        f"""
        <div class="panel" style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;gap:18px;align-items:flex-start;">
                <div>
                    <div class="section-title" style="margin:0 0 6px 0;">{html.escape(titulo)}</div>
                    <div class="muted">{contas} conta(s) • {posicoes} posição(ões)</div>
                </div>
                <div class="money">{brl(total)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    export = df.copy()
    export["Aplicação"] = export["aplicacao"].apply(fmt_date_br)
    export["Vencimento"] = export["vencimento"].apply(fmt_date_br)
    export["Dias desde aplicação"] = export["dias_desde_aplicacao"].apply(
        lambda x: "" if x is None or pd.isna(x) else int(x)
    )

    export = export[
        [
            "titular",
            "conta",
            "ativo",
            "produto",
            "liquidez",
            "Aplicação",
            "Vencimento",
            "Dias desde aplicação",
            "valor_bruto",
            "ir",
            "valor_liquido",
        ]
    ].copy()

    export.columns = [
        "Titular",
        "Conta",
        "Ativo",
        "Produto",
        "Liquidez",
        "Aplicação",
        "Vencimento",
        "Dias desde aplicação",
        "Valor bruto",
        "IR",
        "Valor líquido",
    ]

    st.download_button(
        label="baixar arquivo",
        data=to_excel_bytes(export),
        file_name=f"tesouraria_botuvera_{selected.lower().replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    view = df.sort_values(
        ["titular", "conta", "produto", "valor"],
        ascending=[True, True, True, False],
    ).copy()

    view["dias desde aplic."] = view["dias_desde_aplicacao"].apply(
        lambda x: "—" if x is None or pd.isna(x) else f"{int(x)}d"
    )
    view["% carteira"] = view["participacao_conta"].apply(pct)
    view["valor bruto"] = view["valor_bruto"].apply(brl)
    view["IR"] = view["ir"].apply(
        lambda x: f'<span class="ir-pill">{brl(x)}</span>' if x > 0 else brl(0)
    )
    view["valor líquido"] = view["valor_liquido"].apply(brl)

    view = view[
        [
            "titular",
            "conta",
            "ativo",
            "produto",
            "liquidez",
            "aplicacao_fmt",
            "vencimento_fmt",
            "dias desde aplic.",
            "% carteira",
            "valor bruto",
            "IR",
            "valor líquido",
        ]
    ]

    view.columns = [
        "Titular",
        "Conta",
        "Ativo",
        "Produto",
        "Liquidez",
        "Aplicação",
        "Vencimento",
        "Dias desde aplic.",
        "% carteira",
        "Valor bruto",
        "IR",
        "Valor líquido",
    ]

    st.markdown(
        html_table(
            view,
            col_classes={
                "Conta": "center",
                "Ativo": "wrap",
                "Produto": "wrap",
                "Liquidez": "center",
                "Dias desde aplic.": "center",
                "% carteira": "num",
                "Valor bruto": "num",
                "IR": "num",
                "Valor líquido": "num",
            },
            allow_html_cols=["IR"],
        ),
        unsafe_allow_html=True,
    )

    section("Eficiência das compromissadas")

    comp = df[df["produto"].eq("Op. Compromissadas")].sort_values(
        "dias_desde_aplicacao",
        ascending=False,
    )

    if comp.empty:
        st.markdown(
            '<div class="panel"><div class="muted">Não há operações compromissadas no filtro selecionado.</div></div>',
            unsafe_allow_html=True,
        )
    else:
        for _, r in comp.iterrows():
            st.markdown(
                f"""
                <div class="account-card">
                    <div class="account-head">
                        <div>
                            <div class="name">{html.escape(str(r['titular']))} • Conta {html.escape(str(r['conta']))}</div>
                            <div class="muted">Aplicação: {r['aplicacao_fmt']} • Vencimento: {r['vencimento_fmt']} {efficiency_badge(r['dias_desde_aplicacao'])}</div>
                        </div>
                        <div>
                            <div class="money">{brl(r['valor_bruto'])}</div>
                            <div class="submoney">Líquido {brl(r['valor_liquido'])} • IR {brl(r['ir'])}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.caption(
            f"Sinalização visual: verde até {IOF_OK_DAYS} dias, azul até {IOF_WARN_DAYS - 1} dias, amarelo até {IOF_ALERT_DAYS - 1} dias e vermelho a partir de {IOF_ALERT_DAYS} dias."
        )


def render_liquidez(positions, kpis):
    section("Perfil de liquidez")

    c1, c2, c3 = st.columns(3)
    c1.metric("Liquidez D+0/D+1", pct(kpis["liquidez_d0_pct"]), brl(kpis["liquidez_d0"]))
    c2.metric("Renda fixa isenta", pct(kpis["isenta_pct"]), brl(kpis["isenta"]))
    c3.metric("Liquidez D+31+", pct(kpis["travado_pct"]), brl(kpis["travado"]))

    liq = positions.groupby("liquidez", as_index=False)["valor"].sum()
    liq["ord"] = liq["liquidez"].apply(lambda x: LIQUIDITY_ORDER.index(x) if x in LIQUIDITY_ORDER else 99)
    liq = liq.sort_values("ord")
    liq["participacao"] = liq["valor"] / liq["valor"].sum()

    section("Distribuição de liquidez")

    fig = go.Figure(
        go.Bar(
            x=liq["participacao"],
            y=liq["liquidez"],
            orientation="h",
            marker=dict(color=["#6EE7B7", "#8DB7FF", "#CABFFD", "#F7C561", "#94A3B8"][: len(liq)]),
            text=liq["participacao"].apply(pct),
            textposition="inside",
            insidetextanchor="middle",
        )
    )

    fig.update_layout(
        height=max(260, 80 + 50 * len(liq)),
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0"),
        xaxis=dict(tickformat=".0%", range=[0, 1], gridcolor="rgba(148,163,184,.10)"),
        yaxis=dict(gridcolor="rgba(148,163,184,.0)"),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    col1, col2 = st.columns(2)

    with col1:
        section("Composição D+0/D+1")
        d0 = positions[positions["liquidez"].isin(["D+0", "D+1"])].groupby(
            "produto",
            as_index=False,
        )["valor"].sum().sort_values("valor", ascending=False)

        d0["participação"] = d0["valor"] / d0["valor"].sum() if not d0.empty else 0
        d0["participação"] = d0["participação"].apply(pct)
        d0["valor (R$)"] = d0["valor"].apply(brl)
        d0 = d0[["produto", "participação", "valor (R$)"]]

        st.markdown(
            html_table(
                d0,
                col_classes={
                    "participação": "num",
                    "valor (R$)": "num",
                },
            ),
            unsafe_allow_html=True,
        )

    with col2:
        section("D+31 e renda fixa isenta")
        travado = positions[
            (~positions["liquidez"].isin(["D+0", "D+1"])) |
            (positions["produto"].eq("Renda Fixa Isenta"))
        ].groupby(
            ["produto", "liquidez"],
            as_index=False,
        )["valor"].sum().sort_values("valor", ascending=False)

        travado["participação"] = travado["valor"] / positions["valor"].sum() if not travado.empty else 0
        travado["participação"] = travado["participação"].apply(pct)
        travado["valor (R$)"] = travado["valor"].apply(brl)
        travado = travado[["produto", "liquidez", "participação", "valor (R$)"]]

        st.markdown(
            html_table(
                travado,
                col_classes={
                    "liquidez": "center",
                    "participação": "num",
                    "valor (R$)": "num",
                },
            ),
            unsafe_allow_html=True,
        )


def infer_emissor(row):
    asset = str(row.get("ativo", "")).upper()
    produto = str(row.get("produto", ""))

    if "BRADESCO" in asset:
        return "Bradesco"

    if "SAFRA" in asset:
        return "Safra"

    if "BNDES" in asset:
        return "BNDES"

    if "COMPROMISS" in produto.upper() or "COMPROMISS" in asset:
        return "XP / Compromissadas"

    if "SALDO" in asset:
        return "Caixa"

    return produto or "Não identificado"


def render_politica(positions, kpis):
    section("Política de investimentos")

    pos_fixado = positions[positions["fator"].isin(["pos_fixado", "caixa", "isento"])]["valor"].sum()
    pos_fixado_pct = safe_div(pos_fixado, kpis["total"])
    pos_ok = pos_fixado_pct >= MIN_POS_FIXADO

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pós-fixado / Caixa", pct(pos_fixado_pct), f"mín. {pct(MIN_POS_FIXADO)}")
    c2.metric("Liquidez operacional", pct(kpis["liquidez_d0_pct"]), "D+0 / D+1")
    c3.metric("Valor líquido", brl(kpis["total_liquido"]), f"IR {brl(kpis['ir_total'])}")
    c4.metric("Validação CFO", brl(VALIDACAO_CFO_VALOR), "exceto compromissadas")

    section("Enquadramento automático")

    non_comp_cfo = positions[
        (positions["produto"] != "Op. Compromissadas") &
        (positions["valor"] >= VALIDACAO_CFO_VALOR)
    ].copy()

    checks = pd.DataFrame(
        [
            [
                "Risco de mercado",
                "Mínimo de 80% em caixa/pós-fixado/isentos",
                status_badge(pos_ok),
                pct(pos_fixado_pct),
            ],
            [
                "Liquidez operacional",
                "Disponibilidade em D+0 ou D+1",
                status_badge(kpis["liquidez_d0_pct"] >= 0.80),
                pct(kpis["liquidez_d0_pct"]),
            ],
            [
                "Validação CFO",
                "Aplicações acima de R$ 5 mi, exceto compromissadas",
                status_badge(non_comp_cfo.empty),
                f"{len(non_comp_cfo)} alerta(s)",
            ],
            [
                "IR consolidado",
                "Diferença entre posição bruta e valor líquido",
                status_badge(True),
                brl(kpis["ir_total"]),
            ],
        ],
        columns=["controle", "regra", "status", "leitura atual"],
    )

    st.markdown(
        html_table(
            checks,
            col_labels={
                "controle": "Controle",
                "regra": "Regra",
                "status": "Status",
                "leitura atual": "Leitura atual",
            },
            col_classes={
                "status": "center",
                "leitura atual": "num",
            },
            allow_html_cols=["status"],
        ),
        unsafe_allow_html=True,
    )

    section("Limite por produto / emissor")

    limite_emissor = min(kpis["total"] * 0.50, 10_000_000)

    emissor_df = positions.copy()
    emissor_df["emissor"] = emissor_df.apply(infer_emissor, axis=1)

    emissores = emissor_df.groupby("emissor", as_index=False).agg(
        valor=("valor", "sum"),
        valor_liquido=("valor_liquido", "sum"),
        ir=("ir", "sum"),
    ).sort_values("valor", ascending=False)

    emissores["% carteira"] = emissores["valor"] / kpis["total"]
    emissores["limite"] = limite_emissor
    emissores["status"] = emissores["valor"].apply(lambda v: status_badge(v <= limite_emissor))
    emissores["% carteira"] = emissores["% carteira"].apply(pct)
    emissores["limite"] = emissores["limite"].apply(brl)
    emissores["valor bruto"] = emissores["valor"].apply(brl)
    emissores["IR"] = emissores["ir"].apply(brl)
    emissores["valor líquido"] = emissores["valor_liquido"].apply(brl)

    emissores = emissores[
        [
            "emissor",
            "valor bruto",
            "% carteira",
            "limite",
            "IR",
            "valor líquido",
            "status",
        ]
    ]

    st.markdown(
        html_table(
            emissores,
            col_labels={
                "emissor": "Produto / Emissor",
                "status": "Status",
            },
            col_classes={
                "valor bruto": "num",
                "% carteira": "num",
                "limite": "num",
                "IR": "num",
                "valor líquido": "num",
                "status": "center",
            },
            allow_html_cols=["status"],
        ),
        unsafe_allow_html=True,
    )

    if not non_comp_cfo.empty:
        section("Alertas CFO")
        alert = non_comp_cfo[["titular", "conta", "ativo", "produto", "valor_fmt"]].copy()
        alert.columns = ["Titular", "Conta", "Ativo", "Produto", "Valor bruto"]

        st.markdown(
            html_table(
                alert,
                col_classes={
                    "Valor bruto": "num",
                    "Conta": "center",
                },
            ),
            unsafe_allow_html=True,
        )


# ============================================================
# MAIN
# ============================================================

def main():
    page_icon = Image.open(BOTUVERA_LOGO) if BOTUVERA_LOGO.exists() else "📊"

    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    inject_css()

    with st.sidebar:
        st.markdown("### Atualização de dados")
        st.caption("Use os arquivos em `data/positions/` ou faça upload manual para conferência.")
        uploaded = st.file_uploader(
            "Upload manual de posições XP",
            type=["xlsx"],
            accept_multiple_files=True,
        )

        st.divider()
        st.markdown("### Regras atuais")
        st.write(f"• Mínimo pós-fixado: **{pct(MIN_POS_FIXADO)}**")
        st.write(f"• Validação CFO acima de: **{brl(VALIDACAO_CFO_VALOR)}**")
        st.write(f"• Alerta compromissada: **{IOF_ALERT_DAYS} dias**")

    if uploaded:
        positions, summary = load_data_from_uploads(uploaded)
    else:
        positions, summary = load_data_from_disk(get_mtime_token())

    if positions.empty or summary.empty:
        render_header("—")
        st.error(
            "Nenhuma posição encontrada. Inclua arquivos `.xlsx` em `data/positions/` ou use o upload manual na lateral."
        )
        return

    positions, summary = enrich(positions, summary)
    kpis = calc_kpis(positions, summary)

    ref_dates = summary["data_referencia"].dropna().tolist()
    ref_date = fmt_date_br(ref_dates[0]) if ref_dates else fmt_date_br(date.today())

    render_header(ref_date)

    tabs = st.tabs(
        [
            "Visão Geral",
            "Por Titular",
            "Detalhamento das Contas",
            "Liquidez",
            "Política de Investimentos",
        ]
    )

    with tabs[0]:
        render_visao_geral(positions, summary, kpis)

    with tabs[1]:
        render_por_titular(positions, summary, kpis)

    with tabs[2]:
        render_detalhamento(positions, summary)

    with tabs[3]:
        render_liquidez(positions, kpis)

    with tabs[4]:
        render_politica(positions, kpis)

    st.markdown(
        f'<div class="footer">{GESTOR} • Tesouraria Grupo Botuverá • Informações confidenciais</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
