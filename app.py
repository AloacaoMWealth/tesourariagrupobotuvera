
import re
from datetime import datetime, date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


APP_TITLE = "Tesouraria As a Service"
SUBTITLE = "Gestão Profissional do Caixa Empresarial"
PARTNER = "Grupo Botuverá"
GESTOR = "M Wealth"
DEFAULT_POSITIONS_DIR = Path("data/positions")
CLIENT_CONFIG = Path("data/config/clientes.csv")

# Política de Investimentos — parâmetros editáveis
MIN_POS_FIXADO = 0.80
LIMITE_CONGLOMERADO_PCT = 0.50
LIMITE_CONGLOMERADO_VALOR = 10_000_000
VALIDACAO_CFO_VALOR = 5_000_000

# Regras visuais de eficiência para compromissadas
IOF_ALERT_DAYS = 22
IOF_WARN_DAYS = 18
IOF_OK_DAYS = 14


# -------------------- Formatação --------------------

def brl(v: float) -> str:
    try:
        v = float(v or 0)
    except Exception:
        v = 0
    txt = f"R$ {v:,.2f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float) -> str:
    try:
        v = float(v or 0)
    except Exception:
        v = 0
    return f"{v*100:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_money(x) -> float:
    if pd.isna(x):
        return 0.0
    if isinstance(x, (int, float, np.number)):
        return float(x)
    s = str(x).strip()
    if not s:
        return 0.0
    s = s.replace("R$", "").replace("%", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def parse_date_br(x):
    if pd.isna(x) or x is None or str(x).strip() in ["", "-", "—"]:
        return pd.NaT
    if isinstance(x, (datetime, pd.Timestamp)):
        return pd.to_datetime(x).date()
    s = str(x).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return pd.NaT


def safe_div(a, b):
    return 0 if not b else a / b


# -------------------- Layout / CSS --------------------

def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 18% 0%, rgba(96, 165, 250, .16), transparent 30%),
                linear-gradient(180deg, #071226 0%, #080f20 52%, #07101f 100%);
            color: #F8FAFC;
        }

        .block-container {
            max-width: 1240px;
            padding-top: 2.0rem;
            padding-bottom: 3rem;
        }

        section[data-testid="stSidebar"] {
            background: #0B1426;
            border-right: 1px solid rgba(148,163,184,.16);
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(31, 41, 59, .96), rgba(15, 23, 42, .96));
            border: 1px solid rgba(148, 163, 184, .16);
            border-radius: 22px;
            padding: 18px 20px;
            box-shadow: 0 24px 70px rgba(0, 0, 0, .24);
        }

        div[data-testid="stMetric"] label {
            color: #A9C7FF !important;
            text-transform: uppercase;
            letter-spacing: .13em;
            font-size: .72rem !important;
            font-weight: 800;
        }

        div[data-testid="stMetricValue"] {
            color: #F8FAFC;
            font-weight: 800;
        }

        .hero {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:2rem;
            padding: 18px 0 26px 0;
            border-bottom: 1px solid rgba(148,163,184,.13);
            margin-bottom: 20px;
        }

        .brand {
            display:flex;
            align-items:center;
            gap:18px;
        }

        .logo-box {
            width:44px;height:44px;border:3px solid #7FB0FF;display:flex;align-items:center;justify-content:center;
            font-weight:900;font-size:24px;color:#F8FAFC;
        }

        .hero h1 {
            font-size: 48px;
            line-height: 1;
            margin:0;
            letter-spacing:-.04em;
            font-weight:900;
        }

        .hero h1 span {
            color:#9EC5FF;
            font-style:italic;
        }

        .hero p {margin:8px 0 0 0;color:#9EC5FF;font-weight:700;}

        .hero-meta {
            display:grid;
            grid-template-columns:auto auto;
            gap:8px 22px;
            font-size:.86rem;
            align-items:center;
        }

        .hero-meta .k {
            color:#9EC5FF;
            text-transform:uppercase;
            letter-spacing:.16em;
            font-weight:800;
            font-size:.72rem;
        }

        .hero-meta .v {
            color:#fff;
            font-weight:800;
        }

        .section-title {
            color:#9EC5FF;
            letter-spacing:.24em;
            text-transform:uppercase;
            font-weight:900;
            font-size:.86rem;
            margin: 18px 0 14px;
            border-left: 5px solid #7FB0FF;
            padding-left: 12px;
        }

        .panel {
            background: rgba(30, 41, 59, .78);
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 24px;
            padding: 22px;
            box-shadow: 0 24px 70px rgba(0,0,0,.24);
        }

        .account-card {
            background: linear-gradient(135deg, rgba(30,41,59,.95), rgba(15,23,42,.95));
            border: 1px solid rgba(148,163,184,.18);
            border-radius: 22px;
            padding: 20px 22px;
            margin-bottom: 14px;
        }

        .account-head {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:20px;
        }

        .avatar {
            width:48px;height:48px;border-radius:18px;
            background:linear-gradient(135deg,#7FB0FF,#C4B5FD);
            display:flex;align-items:center;justify-content:center;
            font-weight:900;color:white;font-size:18px;
            flex:0 0 auto;
        }

        .muted { color:#94A3B8; font-size:.84rem; }
        .big-money { font-size:1.55rem; font-weight:900;color:#fff;text-align:right; }
        .small-blue { color:#9EC5FF; font-size:.8rem; font-weight:800; }

        .bar-bg {
            height:8px;background:#263246;border-radius:999px;overflow:hidden;margin-top:14px;
        }
        .bar-fill {
            height:100%;background:linear-gradient(90deg,#7FB0FF,#C4B5FD,#61D7A8,#FFC65A);border-radius:999px;
        }

        .badge {
            display:inline-block;
            padding:4px 9px;
            border-radius:999px;
            font-weight:900;
            font-size:.72rem;
            border:1px solid rgba(255,255,255,.18);
            margin-left:6px;
        }
        .ok { background:rgba(16,185,129,.16); color:#6EE7B7; }
        .warn { background:rgba(245,158,11,.16); color:#FCD34D; }
        .danger { background:rgba(239,68,68,.18); color:#FCA5A5; }
        .info { background:rgba(96,165,250,.18); color:#BFDBFE; }

        .footer {text-align:center;color:#64748B;font-size:.78rem;margin-top:36px;}

        [data-testid="stDataFrame"] {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid rgba(148,163,184,.18);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 22px;
            border-bottom: 1px solid rgba(148,163,184,.16);
        }

        .stTabs [data-baseweb="tab"] {
            color: #A5B4FC;
            font-weight: 800;
        }

        .stTabs [aria-selected="true"] {
            color: #FFFFFF !important;
            border-bottom: 3px solid #9EC5FF;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def header(reference_date: str):
    st.markdown(
        f"""
        <div class="hero">
            <div class="brand">
                <div class="logo-box">M</div>
                <div>
                    <h1>Tesouraria <span>As a Service</span></h1>
                    <p>{SUBTITLE}</p>
                </div>
            </div>
            <div class="hero-meta">
                <div class="k">Data</div><div class="v">{reference_date}</div>
                <div class="k">Parceiro</div><div class="v">{PARTNER}</div>
                <div class="k">Gestor</div><div class="v">{GESTOR}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


# -------------------- Parser XP --------------------

def load_clients():
    default = pd.DataFrame(
        [
            {"conta": "7983962", "titular": "Irineu Afonso", "tipo": "principal"},
            {"conta": "5166121", "titular": "Adriano Bissoni", "tipo": "principal"},
            {"conta": "4163084", "titular": "Vicente Bissoni", "tipo": "residual"},
            {"conta": "11370136", "titular": "Deise Cristina", "tipo": "residual"},
            {"conta": "9445242", "titular": "Transportes Botuvera", "tipo": "residual"},
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


def classify_product(section_name: str, asset_name: str) -> tuple[str, str, str]:
    s = f"{section_name or ''} {asset_name or ''}".lower()

    if "compromiss" in s:
        return "Op. Compromissadas", "D+0", "pos_fixado"
    if "fundo" in s or "fic" in s or "firf" in s:
        return "Fundos D+0", "D+0", "pos_fixado"
    if any(x in s for x in ["lca", "lci"]):
        return "Renda Fixa Isenta", "ISENTA", "isento"
    if "saldo" in s:
        return "Saldo em Conta", "D+0", "caixa"
    if "tesouro" in s or "cdb" in s:
        return "Renda Fixa Pós-Fixada", "D+0", "pos_fixado"
    return "Outros", "N/A", "outros"


def row_to_position(row, section_name, account, titular, ref_date):
    asset = row.iloc[0]
    if pd.isna(asset) or str(asset).strip() in ["", "nan"]:
        asset = section_name if "compromiss" in str(section_name).lower() else ""

    product, liquidity, factor = classify_product(section_name, asset)
    appl = parse_date_br(row.iloc[1]) if len(row) > 1 else pd.NaT
    venc = parse_date_br(row.iloc[3]) if len(row) > 3 else pd.NaT

    # XP export usa Valor líquido em J para RF/compromissadas e G para fundos.
    val_candidates = []
    for idx in [9, 6, 8, 7]:
        if len(row) > idx:
            val_candidates.append(parse_money(row.iloc[idx]))
    value = max(val_candidates) if val_candidates else 0.0

    days = None
    if isinstance(appl, date) and isinstance(ref_date, date):
        days = max((ref_date - appl).days, 0)

    return {
        "conta": str(account),
        "titular": titular,
        "ativo": str(asset).strip() if str(asset).strip() else product.upper(),
        "produto": product,
        "liquidez": liquidity,
        "fator": factor,
        "aplicacao": appl,
        "vencimento": venc,
        "dias_desde_aplicacao": days,
        "valor": value,
        "secao_origem": section_name,
    }


def parse_xp_file(file_obj, filename: str, clients: pd.DataFrame):
    df = pd.read_excel(file_obj, sheet_name=0, header=None, dtype=object, engine="openpyxl")

    header_text = " ".join([str(x) for x in df.iloc[0].dropna().tolist()])
    m = re.search(r"Conta:\s*(\d+)", header_text)
    account = m.group(1) if m else re.sub(r"\D+", "", filename)

    dm = re.search(r"(\d{2}/\d{2}/\d{4})", header_text)
    ref_date = datetime.strptime(dm.group(1), "%d/%m/%Y").date() if dm else date.today()

    match = clients[clients["conta"].astype(str) == str(account)]
    titular = match.iloc[0]["titular"] if not match.empty else f"Conta {account}"

    patrimonio = parse_money(df.iloc[3, 0]) if df.shape[0] > 3 else 0
    saldo_disp = parse_money(df.iloc[3, 2]) if df.shape[0] > 3 and df.shape[1] > 2 else 0

    positions = []
    current_section = None
    header_mode = False

    for i in range(len(df)):
        first = df.iloc[i, 0]
        row_vals = df.iloc[i].tolist()

        if isinstance(first, str) and "|" in first:
            label = first.split("|", 1)[1].strip()
            current_section = label
            header_mode = False
            continue

        # Cabeçalhos de seções com linhas de ativos abaixo
        if any(str(x).strip().lower() == "aplicação" for x in row_vals) or any(str(x).strip().lower() == "data cota" for x in row_vals):
            header_mode = True
            continue

        if header_mode:
            if all(pd.isna(x) or str(x).strip() == "" for x in row_vals):
                header_mode = False
                continue

            pos = row_to_position(df.iloc[i], current_section, account, titular, ref_date)
            if pos["valor"] > 0:
                positions.append(pos)

    if saldo_disp > 0:
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
                "valor": saldo_disp,
                "secao_origem": "Saldo projetado",
            }
        )

    summary = {
        "conta": str(account),
        "titular": titular,
        "patrimonio": patrimonio if patrimonio > 0 else sum(p["valor"] for p in positions),
        "saldo_disponivel": saldo_disp,
        "data_referencia": ref_date,
        "arquivo": filename,
    }

    return pd.DataFrame(positions), summary


@st.cache_data(show_spinner=False)
def load_data_from_disk(mtime_token: float):
    clients = load_clients()

    files = sorted(DEFAULT_POSITIONS_DIR.glob("*.xlsx"))
    all_pos = []
    summaries = []

    for p in files:
        try:
            pos, summ = parse_xp_file(p, p.name, clients)
            all_pos.append(pos)
            summaries.append(summ)
        except Exception as e:
            st.warning(f"Não consegui ler {p.name}: {e}")

    positions = pd.concat(all_pos, ignore_index=True) if all_pos else pd.DataFrame()
    summary = pd.DataFrame(summaries)
    return positions, summary


def load_data_from_uploads(uploaded_files):
    clients = load_clients()
    all_pos = []
    summaries = []
    for f in uploaded_files:
        try:
            pos, summ = parse_xp_file(f, f.name, clients)
            all_pos.append(pos)
            summaries.append(summ)
        except Exception as e:
            st.warning(f"Não consegui ler {f.name}: {e}")
    positions = pd.concat(all_pos, ignore_index=True) if all_pos else pd.DataFrame()
    summary = pd.DataFrame(summaries)
    return positions, summary


def get_mtime_token():
    if not DEFAULT_POSITIONS_DIR.exists():
        return 0
    files = list(DEFAULT_POSITIONS_DIR.glob("*.xlsx"))
    if not files:
        return 0
    return max(p.stat().st_mtime for p in files)


# -------------------- Cálculos --------------------

def enrich(positions: pd.DataFrame, summary: pd.DataFrame):
    if positions.empty:
        return positions, summary

    total = positions["valor"].sum()
    positions["participacao"] = positions["valor"] / total if total else 0
    positions["aplicacao_fmt"] = positions["aplicacao"].apply(lambda x: x.strftime("%d/%m/%Y") if isinstance(x, date) else "—")
    positions["vencimento_fmt"] = positions["vencimento"].apply(lambda x: x.strftime("%d/%m/%Y") if isinstance(x, date) else "—")
    positions["valor_fmt"] = positions["valor"].apply(brl)
    positions["participacao_fmt"] = positions["participacao"].apply(pct)

    summary_total = summary["patrimonio"].sum() if not summary.empty else total
    summary["participacao"] = summary["patrimonio"] / summary_total if summary_total else 0
    summary["patrimonio_fmt"] = summary["patrimonio"].apply(brl)
    summary["participacao_fmt"] = summary["participacao"].apply(pct)

    return positions, summary


def calc_kpis(positions, summary):
    total = summary["patrimonio"].sum() if not summary.empty else positions["valor"].sum()
    liquidez_d0 = positions.loc[positions["liquidez"].isin(["D+0", "D+1"]), "valor"].sum()
    isenta = positions.loc[positions["liquidez"].eq("ISENTA"), "valor"].sum()
    d31 = positions.loc[positions["liquidez"].eq("D+31"), "valor"].sum()
    principais = summary[summary["patrimonio"] > 100_000]["conta"].nunique() if not summary.empty else 0
    residuais = summary[summary["patrimonio"] <= 100_000]["conta"].nunique() if not summary.empty else 0

    titular_group = summary.groupby("titular", as_index=False)["patrimonio"].sum() if not summary.empty else pd.DataFrame()
    maior_nome, maior_pct = "—", 0
    if not titular_group.empty and total:
        row = titular_group.sort_values("patrimonio", ascending=False).iloc[0]
        maior_nome = row["titular"]
        maior_pct = row["patrimonio"] / total

    return {
        "total": total,
        "liquidez_d0": liquidez_d0,
        "liquidez_d0_pct": safe_div(liquidez_d0, total),
        "isenta": isenta,
        "isenta_pct": safe_div(isenta, total),
        "d31": d31,
        "d31_pct": safe_div(d31, total),
        "contas": summary["conta"].nunique() if not summary.empty else 0,
        "principais": principais,
        "residuais": residuais,
        "maior_nome": maior_nome,
        "maior_pct": maior_pct,
    }


# -------------------- Componentes visuais --------------------

def donut(df, labels_col, values_col, title="", height=360):
    fig = go.Figure(
        data=[
            go.Pie(
                labels=df[labels_col],
                values=df[values_col],
                hole=.58,
                textinfo="none",
                marker=dict(line=dict(color="#111827", width=2)),
            )
        ]
    )
    fig.update_layout(
        title=title,
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        legend=dict(orientation="v", y=.5),
        margin=dict(l=10, r=10, t=35, b=10),
    )
    return fig


def hbar(df, y, x, title="", height=360):
    fig = go.Figure(go.Bar(y=df[y], x=df[x], orientation="h", text=df[x].apply(pct), textposition="auto"))
    fig.update_layout(
        title=title,
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        xaxis=dict(tickformat=".0%", gridcolor="rgba(148,163,184,.12)", range=[0, max(1, df[x].max() * 1.15 if len(df) else 1)]),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=35, b=10),
    )
    return fig


def account_card(row, total):
    initials = "".join([x[0] for x in str(row["titular"]).split()[:2]]).upper()
    progress = min(100, safe_div(row["patrimonio"], total) * 100)
    st.markdown(
        f"""
        <div class="account-card">
            <div class="account-head">
                <div style="display:flex;align-items:center;gap:16px;">
                    <div class="avatar">{initials}</div>
                    <div>
                        <div style="font-size:1.08rem;font-weight:900;color:white;">{row['titular']}</div>
                        <div class="muted">Conta {row['conta']}</div>
                    </div>
                </div>
                <div>
                    <div class="big-money">{brl(row['patrimonio'])}</div>
                    <div class="small-blue">{pct(row['participacao'])}</div>
                </div>
            </div>
            <div class="bar-bg"><div class="bar-fill" style="width:{progress:.2f}%"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def efficiency_badge(days):
    if days is None or pd.isna(days):
        return '<span class="badge info">—</span>'
    days = int(days)
    if days >= IOF_ALERT_DAYS:
        return f'<span class="badge danger">{days}d</span>'
    if days >= IOF_WARN_DAYS:
        return f'<span class="badge warn">{days}d</span>'
    return f'<span class="badge ok">{days}d</span>'


# -------------------- Tabs --------------------

def tab_visao_geral(positions, summary, kpis):
    section("Visão Geral")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Patrimônio Total", brl(kpis["total"]))
    c2.metric("Liquidez D+0/D+1", pct(kpis["liquidez_d0_pct"]), brl(kpis["liquidez_d0"]))
    c3.metric("Contas sob Gestão", f'{kpis["contas"]}', f'{kpis["principais"]} principais • {kpis["residuais"]} residuais')
    c4.metric("Maior Titular", pct(kpis["maior_pct"]), kpis["maior_nome"])

    st.write("")
    col1, col2 = st.columns([1, 1])
    produto = positions.groupby("produto", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
    produto["participacao"] = produto["valor"] / produto["valor"].sum()
    with col1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section("Distribuição por Produto")
        st.plotly_chart(donut(produto, "produto", "valor"), use_container_width=True)
        st.dataframe(
            produto.assign(valor=produto["valor"].apply(brl), participacao=produto["participacao"].apply(pct))[["produto", "participacao", "valor"]],
            hide_index=True,
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    titular = summary.groupby("titular", as_index=False)["patrimonio"].sum().sort_values("patrimonio", ascending=False)
    titular["participacao"] = titular["patrimonio"] / titular["patrimonio"].sum()
    with col2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        section("Concentração por Titular")
        st.plotly_chart(hbar(titular, "titular", "participacao"), use_container_width=True)
        st.dataframe(
            titular.assign(patrimonio=titular["patrimonio"].apply(brl), participacao=titular["participacao"].apply(pct))[["titular", "participacao", "patrimonio"]],
            hide_index=True,
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    section("Detalhamento por Produto")
    table = produto.copy()
    table.loc[len(table)] = ["TOTAL GERAL", table["valor"].sum(), 1.0]
    table["valor"] = table["valor"].apply(brl)
    table["participacao"] = table["participacao"].apply(pct)
    st.dataframe(table[["produto", "participacao", "valor"]], hide_index=True, use_container_width=True)


def tab_por_titular(positions, summary, kpis):
    section("Posição por Titular")
    st.markdown(f"<div style='text-align:right;font-size:1.5rem;font-weight:900'>{brl(kpis['total'])}</div>", unsafe_allow_html=True)

    s = summary.sort_values("patrimonio", ascending=False)
    for _, row in s.iterrows():
        account_card(row, kpis["total"])

        detail = positions[positions["conta"].astype(str) == str(row["conta"])]
        if not detail.empty and row["patrimonio"] > 100_000:
            produto = detail.groupby("produto", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
            produto["participacao"] = produto["valor"] / produto["valor"].sum()
            st.dataframe(
                produto.assign(valor=produto["valor"].apply(brl), participacao=produto["participacao"].apply(pct))[["produto", "participacao", "valor"]],
                hide_index=True,
                use_container_width=True,
            )


def tab_detalhamento(positions, summary):
    section("Detalhamento das Contas")
    titulares = ["Todos"] + sorted(summary["titular"].unique().tolist())
    selected = st.segmented_control("Titular", titulares, default="Todos", label_visibility="collapsed")

    df = positions.copy()
    if selected != "Todos":
        df = df[df["titular"] == selected]

    if df.empty:
        st.info("Sem posições para exibir.")
        return

    total = df["valor"].sum()
    title = selected if selected != "Todos" else "Grupo Botuverá"

    st.markdown(
        f"""
        <div class="panel">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div class="section-title" style="margin:0;">{title}</div>
                    <div class="muted">{df['conta'].nunique()} conta(s) • {len(df)} posição(ões)</div>
                </div>
                <div class="big-money">{brl(total)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    view = df.sort_values(["titular", "produto", "valor"], ascending=[True, True, False]).copy()
    view["dias"] = view["dias_desde_aplicacao"].apply(lambda x: "—" if pd.isna(x) else f"{int(x)}d")
    view = view[["titular", "conta", "ativo", "produto", "liquidez", "aplicacao_fmt", "vencimento_fmt", "dias", "participacao_fmt", "valor_fmt"]]
    view.columns = ["Titular", "Conta", "Ativo", "Produto", "Liquidez", "Aplicação", "Vencimento", "Dias desde aplic.", "% Carteira", "Valor"]
    st.dataframe(view, hide_index=True, use_container_width=True)

    section("Eficiência das Compromissadas")
    comp = df[df["produto"].eq("Op. Compromissadas")].copy()
    if comp.empty:
        st.info("Não há operações compromissadas no filtro selecionado.")
    else:
        for _, r in comp.sort_values("dias_desde_aplicacao", ascending=False).iterrows():
            st.markdown(
                f"""
                <div class="account-card">
                    <div class="account-head">
                        <div>
                            <div style="font-weight:900;color:white;">{r['titular']} • Conta {r['conta']}</div>
                            <div class="muted">Aplicação: {r['aplicacao_fmt']} • Vencimento: {r['vencimento_fmt']} {efficiency_badge(r['dias_desde_aplicacao'])}</div>
                        </div>
                        <div class="big-money">{brl(r['valor'])}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.caption(f"Regra visual: verde até {IOF_OK_DAYS}d, amarelo até {IOF_WARN_DAYS}d, vermelho a partir de {IOF_ALERT_DAYS}d.")


def tab_liquidez(positions, kpis):
    section("Perfil de Liquidez")
    c1, c2, c3 = st.columns(3)
    c1.metric("Liquidez D+0/D+1", pct(kpis["liquidez_d0_pct"]), brl(kpis["liquidez_d0"]))
    c2.metric("Renda Fixa Isenta", pct(kpis["isenta_pct"]), brl(kpis["isenta"]))
    c3.metric("Liquidez D+31+", pct(kpis["d31_pct"]), brl(kpis["d31"]))

    liq = positions.groupby("liquidez", as_index=False)["valor"].sum()
    liq["participacao"] = liq["valor"] / liq["valor"].sum()

    order = pd.Categorical(liq["liquidez"], categories=["D+0", "D+1", "ISENTA", "D+31", "N/A"], ordered=True)
    liq = liq.assign(_ord=order).sort_values("_ord")

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    section("Distribuição de Liquidez")
    fig = go.Figure(go.Bar(x=liq["participacao"], y=liq["liquidez"], orientation="h", text=liq["participacao"].apply(pct), textposition="auto"))
    fig.update_layout(
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        xaxis=dict(tickformat=".0%", gridcolor="rgba(148,163,184,.12)", range=[0, 1]),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        section("Composição D+0/D+1")
        d0 = positions[positions["liquidez"].isin(["D+0", "D+1"])].groupby("produto", as_index=False)["valor"].sum()
        d0["participacao"] = d0["valor"] / d0["valor"].sum() if not d0.empty else 0
        st.dataframe(
            d0.assign(valor=d0["valor"].apply(brl), participacao=d0["participacao"].apply(pct))[["produto", "participacao", "valor"]],
            hide_index=True,
            use_container_width=True,
        )
    with col2:
        section("D+31 e Renda Fixa Isenta")
        travado = positions[~positions["liquidez"].isin(["D+0", "D+1"])].groupby("produto", as_index=False)["valor"].sum()
        travado["participacao"] = travado["valor"] / positions["valor"].sum()
        st.dataframe(
            travado.assign(valor=travado["valor"].apply(brl), participacao=travado["participacao"].apply(pct))[["produto", "participacao", "valor"]],
            hide_index=True,
            use_container_width=True,
        )


def tab_politica(positions, kpis):
    section("Política de Investimentos")
    pos_fixado = positions[positions["fator"].isin(["pos_fixado", "caixa"])]["valor"].sum()
    pos_fixado_pct = safe_div(pos_fixado, kpis["total"])
    status_pos = "Dentro da política" if pos_fixado_pct >= MIN_POS_FIXADO else "Ponto de atenção"

    c1, c2, c3 = st.columns(3)
    c1.metric("Pós-fixado / Caixa", pct(pos_fixado_pct), f"Mín. {pct(MIN_POS_FIXADO)}")
    c2.metric("Liquidez operacional", pct(kpis["liquidez_d0_pct"]), "D+0/D+1")
    c3.metric("Validação CFO", brl(VALIDACAO_CFO_VALOR), "exceto compromissadas")

    st.markdown(
        f"""
        <div class="panel">
            <div class="section-title">Comparativo Automatizado</div>
            <p style="font-size:1.05rem;color:#CBD5E1;line-height:1.7;">
                A política prioriza <b>segurança</b>, depois <b>liquidez</b> e, por fim, <b>rentabilidade</b>.
                O controle de risco de mercado exige mínimo de <b>{pct(MIN_POS_FIXADO)}</b> do PL em ativos pós-fixados/CDI.
                Status atual: <b>{status_pos}</b>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    section("Roadmap de Controles")
    roadmap = pd.DataFrame(
        [
            ["Cadastro dos limites por produto (mín./máx.)", "Pronto para parametrizar"],
            ["Liquidez mínima por horizonte (D+0, D+30, D+90, +)", "Parcialmente automatizado"],
            ["Comparativo Política vs. Realidade", "Ativo"],
            ["Simulador de distribuição de novos recursos", "Próxima versão"],
            ["Alertas de desenquadramento por e-mail/WhatsApp", "Próxima versão"],
        ],
        columns=["Controle", "Status"],
    )
    st.dataframe(roadmap, hide_index=True, use_container_width=True)


# -------------------- Main --------------------

def main():
    st.set_page_config(
        page_title=f"{APP_TITLE} | {PARTNER}",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    with st.sidebar:
        st.markdown("### Atualização de dados")
        st.caption("Use os arquivos do GitHub em `data/positions` ou suba uma posição manualmente para conferência.")
        uploaded = st.file_uploader("Upload manual de posições XP", type=["xlsx"], accept_multiple_files=True)
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
        header("—")
        st.error("Nenhuma posição encontrada. Inclua os arquivos `.xlsx` em `data/positions/` ou use o upload manual na lateral.")
        return

    positions, summary = enrich(positions, summary)
    kpis = calc_kpis(positions, summary)

    ref_dates = summary["data_referencia"].dropna().unique()
    ref_date = pd.to_datetime(ref_dates[0]).strftime("%d/%m/%Y") if len(ref_dates) else date.today().strftime("%d/%m/%Y")

    header(ref_date)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Visão Geral", "Por Titular", "Detalhamento das Contas", "Liquidez", "Política de Investimentos"]
    )

    with tab1:
        tab_visao_geral(positions, summary, kpis)
    with tab2:
        tab_por_titular(positions, summary, kpis)
    with tab3:
        tab_detalhamento(positions, summary)
    with tab4:
        tab_liquidez(positions, kpis)
    with tab5:
        tab_politica(positions, kpis)

    st.markdown(f'<div class="footer">{GESTOR} • Tesouraria As a Service • Informações confidenciais</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
