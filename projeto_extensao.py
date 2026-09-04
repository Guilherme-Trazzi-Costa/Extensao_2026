import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import requests
from supabase import create_client, Client

from tela_login import exigir_login, barra_usuario

# ──────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Padaria · Dashboard",
    page_icon="🥐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

usuario = exigir_login()

# ──────────────────────────────────────────────
# ESTILO
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500;600&display=swap');

:root {
    --amber:   #D97706;
    --cream:   #FFFBF0;
    --brown:   #78350F;
    --green:   #059669;
    --red:     #DC2626;
    --card-bg: #FFFFFF;
    --border:  #F3E8CC;
    --text:    #1C1008;
    --muted:   #92400E;
}
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--cream);
    color: var(--text);
}
.hero {
    background: linear-gradient(135deg, #78350F 0%, #D97706 100%);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.hero h1 {
    font-family: 'Playfair Display', serif;
    color: #FDE68A;
    font-size: 1.5rem;
    margin: 0;
    line-height: 1.2;
}
.hero p { color: #FEF3C7; margin: 0.15rem 0 0; font-size: 0.78rem; }
.hero-icon { font-size: 2rem; line-height: 1; }

.metrics-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.6rem;
    margin-bottom: 1rem;
}
.metric-card {
    background: var(--card-bg);
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 0.65rem 0.8rem;
    text-align: center;
    box-shadow: 0 1px 4px rgba(120,53,15,0.07);
}
.metric-card .label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .05em;
    color: var(--muted);
    margin-bottom: .25rem;
}
.metric-card .value {
    font-family: 'Playfair Display', serif;
    font-size: 1.25rem;
    font-weight: 700;
    line-height: 1.1;
}
.metric-card .value.positive { color: var(--green); }
.metric-card .value.negative { color: var(--red); }
.metric-card .value.neutral  { color: var(--amber); }

.section-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    color: var(--brown);
    margin: 0.5rem 0 0.6rem;
    border-left: 4px solid var(--amber);
    padding-left: 0.6rem;
}

/* ── Chat ── */
.chat-wrap {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    max-height: 480px;
    overflow-y: auto;
    padding: 0.5rem 0.2rem;
    margin-bottom: 0.8rem;
}
.bubble {
    max-width: 80%;
    padding: 0.65rem 0.9rem;
    border-radius: 16px;
    font-size: 0.92rem;
    line-height: 1.5;
    word-break: break-word;
}
.bubble.usuario {
    align-self: flex-end;
    background: #D97706;
    color: #fff;
    border-bottom-right-radius: 4px;
}
.bubble.bot {
    align-self: flex-start;
    background: #FFFFFF;
    border: 1.5px solid #F3E8CC;
    color: #1C1008;
    border-bottom-left-radius: 4px;
}
.bubble.erro {
    align-self: flex-start;
    background: #FEF2F2;
    border: 1.5px solid #FCA5A5;
    color: #991B1B;
    border-bottom-left-radius: 4px;
}

/* Metas */
.meta-card {
    background: var(--card-bg);
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 4px rgba(120,53,15,0.06);
}
.meta-card.done { border-left: 5px solid var(--green); }
.meta-card.todo { border-left: 5px solid var(--amber); }
.meta-name  { font-weight: 600; font-size: 0.9rem; color: var(--text); }
.meta-price { font-size: 0.78rem; color: var(--muted); margin-top: 2px; }
.badge {
    font-size: 0.7rem; font-weight: 700;
    padding: 3px 9px; border-radius: 20px;
    white-space: nowrap; margin-left: 0.5rem;
}
.badge-done { background: #D1FAE5; color: #065F46; }
.badge-todo { background: #FEF3C7; color: #92400E; }

div[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-weight: 600; font-size: 0.95rem; color: var(--muted);
}
div[data-testid="stTabs"] [aria-selected="true"] {
    color: var(--amber) !important;
    border-bottom-color: var(--amber) !important;
}
.block-container {
    padding-top: 1rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# SUPABASE
# ──────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

MESES_PT = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
            7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

@st.cache_data(ttl=60)
def load_financeiro():
    res = get_supabase().table("financeiro").select("*").order("data").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df["data"]    = pd.to_datetime(df["data"])
        df["valor"]   = df["valor"].astype(float)
        df["tipo"]    = df["valor"].apply(lambda x: "Receita" if x >= 0 else "Despesa")
        df["mes_ord"] = df["data"].dt.year * 100 + df["data"].dt.month
        df["mes"]     = df["data"].apply(lambda d: f"{MESES_PT[d.month]}/{str(d.year)[2:]}")
    return df

@st.cache_data(ttl=60)
def load_metas():
    res = get_supabase().table("metas").select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df["concluida"] = df["obs"].notna() & (df["obs"].str.upper().str.strip() == "CONCLUÍDO")
        df["preco"]     = df["preco"].astype(float)
    return df

def fmt_brl(v):
    return f"R$ {abs(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")

CHART_CFG = {"displayModeBar": False, "scrollZoom": False}

# ──────────────────────────────────────────────
# FILTROS TEMPORAIS
# ──────────────────────────────────────────────
hoje      = date.today()
ano_atual = hoje.year
mes_atual = hoje.month

def ultimos_3_meses_ords():
    ords = []
    for i in range(2, -1, -1):
        m = mes_atual - i
        y = ano_atual
        if m <= 0:
            m += 12
            y -= 1
        ords.append(y * 100 + m)
    return ords

ultimos_3_ords = ultimos_3_meses_ords()

# ──────────────────────────────────────────────
# CHATBOT — função de envio ao n8n
# ──────────────────────────────────────────────
def enviar_para_n8n(mensagem: str) -> str:
    webhook_url = st.secrets.get("N8N_WEBHOOK_URL", "")
    if not webhook_url:
        return "⚠️ Webhook do n8n não configurado no secrets.toml."
    try:
        resp = requests.post(
            webhook_url,
            json={"chatInput": mensagem, "sessionId": "streamlit"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        # Tenta extrair a resposta em diferentes formatos que o n8n pode retornar
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        return (
            data.get("output")
            or data.get("text")
            or data.get("resposta")
            or data.get("message")
            or str(data)
        )
    except requests.exceptions.Timeout:
        return "⏱️ O servidor demorou demais para responder. Tente novamente."
    except Exception as e:
        return f"❌ Erro ao conectar com o assistente: {e}"

# ──────────────────────────────────────────────
# CABEÇALHO
# ──────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-icon">🥐</div>
  <div>
    <h1>Minha Padaria</h1>
    <p>Painel financeiro · Atualizado em tempo real</p>
  </div>
</div>
""", unsafe_allow_html=True)

barra_usuario(usuario)

tab_chat, tab_fin, tab_metas = st.tabs(["🤖  Assistente", "📊  Financeiro", "🎯  Metas"])

# ═══════════════════════════════════════════════
# ABA 0 — CHATBOT
# ═══════════════════════════════════════════════
with tab_chat:
    st.markdown('<p class="section-title">Assistente Financeiro</p>', unsafe_allow_html=True)
    st.caption("Registre vendas, gastos, metas e faça perguntas sobre suas finanças.")

    # Inicializa histórico na sessão
    if "chat_historico" not in st.session_state:
        st.session_state.chat_historico = [
            {"papel": "bot", "texto": "Olá! 👋 Pode me dizer suas vendas, gastos ou perguntar sobre suas finanças. Como posso ajudar?"}
        ]

    # Renderiza bolhas do histórico
    bolhas_html = '<div class="chat-wrap" id="chat-wrap">'
    for msg in st.session_state.chat_historico:
        cls = "usuario" if msg["papel"] == "usuario" else ("erro" if msg["papel"] == "erro" else "bot")
        bolhas_html += f'<div class="bubble {cls}">{msg["texto"]}</div>'
    bolhas_html += "</div>"
    st.markdown(bolhas_html, unsafe_allow_html=True)

    # Input + botão enviar
    with st.form("chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_input = st.text_input(
                "Mensagem",
                placeholder='Ex: "vendi R$200 hoje" ou "quanto lucrei em maio?"',
                label_visibility="collapsed",
            )
        with col_btn:
            enviado = st.form_submit_button("Enviar", use_container_width=True)

    if enviado and user_input.strip():
        # Adiciona mensagem do usuário
        st.session_state.chat_historico.append(
            {"papel": "usuario", "texto": user_input.strip()}
        )

        # Chama o n8n e aguarda resposta
        with st.spinner("Processando..."):
            resposta = enviar_para_n8n(user_input.strip())

        papel_resposta = "erro" if resposta.startswith(("❌", "⚠️", "⏱️")) else "bot"
        st.session_state.chat_historico.append(
            {"papel": papel_resposta, "texto": resposta}
        )

        # Invalida cache para atualizar gráficos após novo registro
        load_financeiro.clear()
        load_metas.clear()
        st.rerun()

    # Botão limpar conversa
    if len(st.session_state.chat_historico) > 1:
        if st.button("🗑️ Limpar conversa", key="limpar_chat"):
            st.session_state.chat_historico = [
                {"papel": "bot", "texto": "Conversa reiniciada. Como posso ajudar?"}
            ]
            st.rerun()

# ═══════════════════════════════════════════════
# ABA 1 — FINANCEIRO
# ═══════════════════════════════════════════════
with tab_fin:
    df = load_financeiro()

    if df.empty:
        st.info("Nenhum dado financeiro encontrado ainda.")
    else:
        total_receitas = df.loc[df["valor"] > 0, "valor"].sum()
        total_despesas = df.loc[df["valor"] < 0, "valor"].sum()
        lucro_total    = df["valor"].sum()
        n_transacoes   = len(df)

        st.markdown('<p class="section-title">Resumo Geral</p>', unsafe_allow_html=True)
        cls_lucro = "positive" if lucro_total >= 0 else "negative"
        st.markdown(f"""
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="label">Lucro Total</div>
            <div class="value {cls_lucro}">{fmt_brl(lucro_total)}</div>
          </div>
          <div class="metric-card">
            <div class="label">Total Receitas</div>
            <div class="value positive">{fmt_brl(total_receitas)}</div>
          </div>
          <div class="metric-card">
            <div class="label">Total Despesas</div>
            <div class="value negative">{fmt_brl(abs(total_despesas))}</div>
          </div>
          <div class="metric-card">
            <div class="label">Transações</div>
            <div class="value neutral">{n_transacoes}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        df_3m = df[df["mes_ord"].isin(ultimos_3_ords)].copy()
        mes_ordem_3m = (
            df_3m[["mes_ord","mes"]].drop_duplicates()
            .sort_values("mes_ord")["mes"].tolist()
        )

        st.markdown('<p class="section-title">Rendimento Mensal</p>', unsafe_allow_html=True)
        mensal = (
            df_3m.groupby(["mes_ord","mes","tipo"])["valor"]
            .sum().abs().reset_index()
        )
        mensal["_ord"] = mensal["tipo"].map({"Receita":0,"Despesa":1})
        mensal = mensal.sort_values(["mes_ord","_ord"]).drop("_ord", axis=1)

        fig_bar = px.bar(
            mensal, x="mes", y="valor", color="tipo",
            barmode="group",
            category_orders={"mes": mes_ordem_3m},
            labels={"mes":"","valor":"R$","tipo":""},
            color_discrete_map={"Receita":"#059669","Despesa":"#DC2626"},
            template="plotly_white",
            text=mensal["valor"].apply(lambda v: f"R${v:,.0f}".replace(",",".")),
        )
        fig_bar.update_layout(
            font_family="DM Sans", font_size=13,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.15, font_size=13),
            xaxis=dict(showgrid=False, type="category", tickfont=dict(size=13)),
            yaxis=dict(showticklabels=False, showgrid=False),
            margin=dict(l=0, r=0, t=40, b=0),
            height=310, uniformtext_minsize=11, uniformtext_mode="hide", dragmode=False,
        )
        fig_bar.update_traces(marker_line_width=0, opacity=0.9, textposition="outside",
                              textfont=dict(size=13, family="DM Sans"))
        st.plotly_chart(fig_bar, use_container_width=True, config=CHART_CFG)

        st.markdown('<p class="section-title">Lucro Líquido por Mês</p>', unsafe_allow_html=True)
        lucro_3m = (
            df_3m.groupby(["mes_ord","mes"])["valor"].sum()
            .reset_index().sort_values("mes_ord")
            .rename(columns={"valor":"lucro"})
        )
        lucro_3m["cor"] = lucro_3m["lucro"].apply(lambda x: "#059669" if x >= 0 else "#DC2626")

        fig_liq = go.Figure(go.Bar(
            x=lucro_3m["mes"], y=lucro_3m["lucro"],
            marker_color=lucro_3m["cor"],
            text=lucro_3m["lucro"].apply(lambda v: f"R${v:,.0f}".replace(",",".")),
            textposition="outside",
            textfont=dict(size=13, family="DM Sans"),
        ))
        fig_liq.update_layout(
            font_family="DM Sans", font_size=13,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, type="category",
                       categoryorder="array", categoryarray=mes_ordem_3m,
                       tickfont=dict(size=13)),
            yaxis=dict(showticklabels=False, showgrid=False),
            margin=dict(l=0, r=0, t=40, b=0),
            showlegend=False, height=310,
            uniformtext_minsize=11, uniformtext_mode="hide", dragmode=False,
        )
        st.plotly_chart(fig_liq, use_container_width=True, config=CHART_CFG)

        col_acum, col_pie = st.columns(2)

        with col_acum:
            st.markdown('<p class="section-title">Lucro Acumulado</p>', unsafe_allow_html=True)
            df_ano = df[df["data"].dt.year == ano_atual].copy()
            mes_ordem_ano = (
                df_ano[["mes_ord","mes"]].drop_duplicates()
                .sort_values("mes_ord")["mes"].tolist()
            )
            lucro_ano = (
                df_ano.groupby(["mes_ord","mes"])["valor"].sum()
                .reset_index().sort_values("mes_ord")
                .rename(columns={"valor":"lucro"})
            )
            lucro_ano["lucro_acumulado"] = lucro_ano["lucro"].cumsum()
            fig_acum = px.area(
                lucro_ano, x="mes", y="lucro_acumulado",
                labels={"mes":"","lucro_acumulado":"R$ Acumulado"},
                template="plotly_white",
                color_discrete_sequence=["#D97706"],
                category_orders={"mes": mes_ordem_ano},
            )
            fig_acum.update_traces(fill="tozeroy", fillcolor="rgba(217,119,6,0.15)",
                                   line_color="#D97706", line_width=2.5)
            fig_acum.update_layout(
                font_family="DM Sans", font_size=13,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, type="category", tickfont=dict(size=13)),
                yaxis=dict(gridcolor="#F3E8CC", tickfont=dict(size=12)),
                margin=dict(l=0, r=0, t=10, b=0),
                height=260, dragmode=False,
            )
            st.plotly_chart(fig_acum, use_container_width=True, config=CHART_CFG)

        with col_pie:
            st.markdown('<p class="section-title">Receita vs Despesa</p>', unsafe_allow_html=True)
            df_mes = df[
                (df["data"].dt.year == ano_atual) &
                (df["data"].dt.month == mes_atual)
            ]
            rec_mes  = df_mes.loc[df_mes["valor"] > 0, "valor"].sum()
            desp_mes = df_mes.loc[df_mes["valor"] < 0, "valor"].sum()
            nome_mes_atual = f"{MESES_PT[mes_atual]}/{str(ano_atual)[2:]}"

            if rec_mes == 0 and desp_mes == 0:
                st.info(f"Sem movimentações em {nome_mes_atual}.")
            else:
                fig_pie = px.pie(
                    pd.DataFrame({"Tipo":["Receitas","Despesas"],
                                  "Valor":[rec_mes, abs(desp_mes)]}),
                    names="Tipo", values="Valor",
                    color="Tipo",
                    color_discrete_map={"Receitas":"#059669","Despesas":"#DC2626"},
                    hole=0.55, title=nome_mes_atual,
                )
                fig_pie.update_layout(
                    font_family="DM Sans", font_size=13,
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=60, r=60, t=40, b=30),
                    height=290, dragmode=False,
                    title_font=dict(size=13, family="DM Sans", color="#92400E"),
                    title_x=0.5,
                )
                fig_pie.update_traces(textposition="outside", textinfo="percent+label",
                                      textfont_size=13, pull=[0.05, 0.05])
                st.plotly_chart(fig_pie, use_container_width=True, config=CHART_CFG)

        with st.expander("📋 Ver todas as transações"):
            df_tab = df[df["mes_ord"].isin(ultimos_3_ords)].copy()
            df_tab = df_tab.sort_values("data", ascending=False)
            exibir = df_tab[["data","valor","tipo"]].copy()
            exibir["data"]  = exibir["data"].dt.strftime("%d/%m/%Y")
            exibir["valor"] = exibir["valor"].apply(fmt_brl)
            exibir.columns  = ["Data","Valor","Tipo"]
            st.dataframe(exibir, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════
# ABA 2 — METAS
# ═══════════════════════════════════════════════
with tab_metas:
    dm = load_metas()

    if dm.empty:
        st.info("Nenhuma meta cadastrada ainda.")
    else:
        total_concluido_historico = dm[dm["concluida"]]["preco"].sum()
        um_ano_atras = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=1)

        if "concluida_em" in dm.columns:
            dm["concluida_em"] = pd.to_datetime(dm["concluida_em"], errors="coerce", utc=True)
            mask_visivel = (
                (~dm["concluida"]) |
                (dm["concluida"] & (
                    dm["concluida_em"].isna() |
                    (dm["concluida_em"] >= um_ano_atras)
                ))
            )
            dm_visivel = dm[mask_visivel].copy()
        else:
            dm_visivel = dm.copy()

        concluidas_vis  = int(dm_visivel["concluida"].sum())
        pendentes_vis   = int((~dm_visivel["concluida"]).sum())
        total_m_vis     = len(dm_visivel)
        total_pendente  = dm_visivel[~dm_visivel["concluida"]]["preco"].sum()
        pct = int(concluidas_vis / total_m_vis * 100) if total_m_vis else 0

        st.markdown('<p class="section-title">Progresso das Metas</p>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="label">Total de Metas</div>
            <div class="value neutral">{total_m_vis}</div>
          </div>
          <div class="metric-card">
            <div class="label">Concluídas</div>
            <div class="value positive">{concluidas_vis}</div>
          </div>
          <div class="metric-card">
            <div class="label">Invest. Realizado</div>
            <div class="value positive">{fmt_brl(total_concluido_historico)}</div>
          </div>
          <div class="metric-card">
            <div class="label">Invest. Pendente</div>
            <div class="value negative">{fmt_brl(total_pendente)}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.progress(pct / 100, text=f"**{pct}%** das metas concluídas")
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<p class="section-title">Distribuição</p>', unsafe_allow_html=True)
        fig_donut = go.Figure(go.Pie(
            labels=["Concluídas","Pendentes"],
            values=[max(concluidas_vis, 0), max(pendentes_vis, 0)],
            hole=0.6,
            marker_colors=["#059669","#D97706"],
            textinfo="percent", textfont_size=12,
        ))
        fig_donut.update_layout(
            font_family="DM Sans", font_size=11,
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=30),
            height=220, showlegend=True,
            legend=dict(orientation="h", y=-0.1),
            annotations=[dict(text=f"<b>{pct}%</b>", x=0.5, y=0.5,
                              font_size=20, font_color="#78350F", showarrow=False)],
            dragmode=False,
        )
        st.plotly_chart(fig_donut, use_container_width=True, config=CHART_CFG)

        st.markdown('<p class="section-title">Lista de Metas</p>', unsafe_allow_html=True)
        dm_sorted = pd.concat([
            dm_visivel[dm_visivel["concluida"]],
            dm_visivel[~dm_visivel["concluida"]],
        ]).reset_index(drop=True)

        for _, row in dm_sorted.iterrows():
            status_cls = "done" if row["concluida"] else "todo"
            badge_cls  = "badge-done" if row["concluida"] else "badge-todo"
            badge_txt  = "✅ Concluída" if row["concluida"] else "⏳ Pendente"
            preco_fmt  = fmt_brl(row["preco"])
            obs_html = ""
            if row["concluida"]:
                data_str = ""
                if "concluida_em" in row and pd.notna(row["concluida_em"]):
                    try:
                        data_str = f" · {pd.to_datetime(row['concluida_em']).strftime('%d/%m/%Y')}"
                    except Exception:
                        pass
                obs_html = f'<span style="font-size:.72rem;color:#059669;font-weight:600;">✔ Concluída{data_str}</span>'

            st.markdown(f"""
            <div class="meta-card {status_cls}">
              <div>
                <div class="meta-name">{row["objetivo"]}</div>
                <div class="meta-price">Custo: {preco_fmt}</div>
                {obs_html}
              </div>
              <span class="badge {badge_cls}">{badge_txt}</span>
            </div>
            """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# RODAPÉ
# ──────────────────────────────────────────────
st.markdown(
    "<hr style='border-color:#F3E8CC;margin-top:1rem'>"
    "<p style='text-align:center;color:#92400E;font-size:.75rem;padding-bottom:.5rem'>"
    "🥐 Painel da Padaria · Dados sincronizados com Supabase</p>",
    unsafe_allow_html=True
)
