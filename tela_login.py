# ══════════════════════════════════════════════════════════════
#  TELA DE LOGIN — Painel da Padaria
#  Projeto de Extensão · Panificação Artesanal
# ══════════════════════════════════════════════════════════════
"""
Arquivo ÚNICO e autocontido da tela de login.

────────────────────────────────────────────────────────────────
COMO RODAR (só precisa do streamlit)
────────────────────────────────────────────────────────────────

    pip install streamlit
    python -m streamlit run tela_login.py

Usuário: francinete
Senha:   padaria2026

────────────────────────────────────────────────────────────────
COMO USAR NO PAINEL DE VERDADE
────────────────────────────────────────────────────────────────

No topo do seu arquivo principal:

    from tela_login import exigir_login, barra_usuario

Depois do st.set_page_config(), ANTES de qualquer consulta ao banco:

    usuario = exigir_login()      # trava aqui se não estiver logado
    barra_usuario(usuario)        # saudação + botão "Sair"

Tudo que vier depois do exigir_login() só roda para quem entrou.

────────────────────────────────────────────────────────────────
COMO TROCAR A SENHA (importante)
────────────────────────────────────────────────────────────────

A senha NUNCA é guardada em texto puro, só o hash PBKDF2-SHA256.
Para gerar o hash de uma senha nova, rode no terminal:

    python -c "import tela_login,getpass; print(tela_login.gerar_hash(getpass.getpass()))"

Cole o resultado em USUARIOS_DEMO abaixo, ou — melhor — em
.streamlit/secrets.toml, que este arquivo lê automaticamente:

    [auth]
    modo = "local"
    timeout_minutos = 30

    [auth.usuarios.francinete]
    nome = "Francinete Vieira"
    senha_hash = "pbkdf2_sha256$260000$....$...."

Havendo secrets.toml, ele tem prioridade e o USUARIOS_DEMO é ignorado.
"""

import hashlib
import hmac
import secrets as _rnd            # biblioteca padrão — não é o st.secrets
from datetime import datetime, timedelta

import streamlit as st

# ══════════════════════════════════════════════════════════════
# 1. CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════

ITERACOES          = 260_000   # custo do PBKDF2 (quanto maior, mais lento de quebrar)
MAX_TENTATIVAS     = 5         # erros antes de travar
BLOQUEIO_MINUTOS   = 5         # quanto tempo fica travado
TIMEOUT_PADRAO_MIN = 30        # minutos parado até a sessão cair

# Usuário embutido, para o arquivo rodar sem nenhuma configuração.
# ⚠️  TROQUE ANTES DE USAR DE VERDADE — este hash é público, está no Git.
USUARIOS_DEMO = {
    "francinete": {
        "nome": "Francinete Vieira",
        # senha: padaria2026
        "senha_hash": (
            "pbkdf2_sha256$260000$e1ae9b0388d1732ceb258fffe0eb4106"
            "$e9a0492daa9452acf9f26005f72a5b6abce4c9685f163af9a005e2085ecfefd9"
        ),
    }
}

# Chaves internas do st.session_state
_LOGADO, _USUARIO, _ACESSO   = "auth_logado", "auth_usuario", "auth_acesso"
_FALHAS, _BLOQUEIO           = "auth_falhas", "auth_bloqueio"
_ERRO, _EXPIROU              = "auth_erro", "auth_expirou"


# ══════════════════════════════════════════════════════════════
# 2. SENHA — hash e verificação
# ══════════════════════════════════════════════════════════════

def gerar_hash(senha: str, iteracoes: int = ITERACOES) -> str:
    """Transforma a senha em 'pbkdf2_sha256$<iteracoes>$<salt>$<hash>'.

    O salt é sorteado a cada chamada, então a mesma senha gera hashes
    diferentes — impede descobrir senhas iguais comparando os hashes.
    """
    salt = _rnd.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iteracoes)
    return f"pbkdf2_sha256${iteracoes}${salt.hex()}${dk.hex()}"


def verificar_hash(senha: str, armazenado: str) -> bool:
    """Confere a senha digitada contra o hash guardado.

    Usa compare_digest (tempo constante): a comparação demora o mesmo
    tanto acertando ou errando, então ninguém descobre a senha
    caractere por caractere medindo o tempo de resposta.
    """
    try:
        algo, iteracoes, salt_hex, hash_hex = str(armazenado).split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), bytes.fromhex(salt_hex), int(iteracoes)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError, TypeError):
        return False


# Hash descartável, calculado uma vez ao carregar o arquivo.
# Serve para o login inexistente gastar o mesmo tempo de um login real,
# senão dá para descobrir quais usuários existem cronometrando a resposta.
_HASH_ISCA = gerar_hash(_rnd.token_hex(16))


# ══════════════════════════════════════════════════════════════
# 3. DE ONDE VÊM OS USUÁRIOS
# ══════════════════════════════════════════════════════════════

def _config() -> dict:
    """Seção [auth] do secrets.toml. Nunca quebra se o arquivo não existir."""
    try:
        return dict(st.secrets.get("auth", {}))
    except Exception:
        return {}


def _usuarios() -> dict:
    """secrets.toml tem prioridade; sem ele, cai no usuário de demonstração."""
    try:
        do_secrets = dict(_config().get("usuarios", {}))
        if do_secrets:
            return do_secrets
    except Exception:
        pass
    return USUARIOS_DEMO


def _usando_demo() -> bool:
    return _usuarios() is USUARIOS_DEMO


def _timeout() -> timedelta:
    try:
        return timedelta(minutes=int(_config().get("timeout_minutos", TIMEOUT_PADRAO_MIN)))
    except (TypeError, ValueError):
        return timedelta(minutes=TIMEOUT_PADRAO_MIN)


def autenticar(login: str, senha: str):
    """Devolve (deu_certo, dados_do_usuario)."""
    procurado = login.strip().lower()
    achado = None
    for chave, dados in _usuarios().items():
        if chave.strip().lower() == procurado:
            achado = (chave, dict(dados))

    if achado is None:
        verificar_hash(senha, _HASH_ISCA)      # gasta o mesmo tempo
        return False, None

    chave, dados = achado
    if verificar_hash(senha, dados.get("senha_hash", "")):
        return True, {"login": chave, "nome": dados.get("nome", chave)}
    return False, None


# ══════════════════════════════════════════════════════════════
# 4. BLOQUEIO POR TENTATIVAS
# ══════════════════════════════════════════════════════════════

def _segundos_bloqueado() -> int:
    ate = st.session_state.get(_BLOQUEIO)
    if not ate:
        return 0
    falta = (ate - datetime.now()).total_seconds()
    if falta <= 0:
        st.session_state.pop(_BLOQUEIO, None)
        st.session_state[_FALHAS] = 0
        return 0
    return int(falta)


def _registrar_falha():
    falhas = st.session_state.get(_FALHAS, 0) + 1
    st.session_state[_FALHAS] = falhas
    if falhas >= MAX_TENTATIVAS:
        st.session_state[_BLOQUEIO] = datetime.now() + timedelta(minutes=BLOQUEIO_MINUTOS)


# ══════════════════════════════════════════════════════════════
# 5. VISUAL
# ══════════════════════════════════════════════════════════════

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #FFFBF0;
    color: #1C1008;
}
.block-container { padding-top: 2.5rem !important; max-width: 900px; }
header[data-testid="stHeader"] { background: transparent; }

.login-brand { text-align: center; margin-bottom: 1.1rem; }
.login-brand .icone {
    font-size: 2.6rem;
    line-height: 1;
    display: inline-block;
    padding: 0.55rem 0.8rem;
    background: linear-gradient(135deg, #78350F 0%, #D97706 100%);
    border-radius: 16px;
    margin-bottom: 0.6rem;
}
.login-brand h1 {
    font-family: 'Playfair Display', serif;
    font-size: 1.7rem;
    color: #78350F;
    margin: 0;
    line-height: 1.2;
}
.login-brand p { color: #92400E; font-size: 0.82rem; margin: 0.25rem 0 0; }

div[data-testid="stForm"] {
    background: #FFFFFF;
    border: 1.5px solid #F3E8CC;
    border-radius: 16px;
    padding: 1.4rem 1.3rem 1rem;
    box-shadow: 0 6px 22px rgba(120,53,15,0.10);
}
div[data-testid="stForm"] label p {
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    color: #78350F !important;
}
div[data-testid="stForm"] input {
    border-radius: 9px !important;
    border: 1.5px solid #F3E8CC !important;
    background: #FFFBF0 !important;
}
div[data-testid="stForm"] input:focus {
    border-color: #D97706 !important;
    box-shadow: 0 0 0 2px rgba(217,119,6,0.18) !important;
}
div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #78350F 0%, #D97706 100%) !important;
    border: none !important;
    color: #FEF3C7 !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    padding: 0.45rem 0 !important;
    margin-top: 0.3rem;
}
div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover { opacity: 0.92; }
/* Durante o bloqueio o botão precisa PARECER travado: o gradiente acima
   usa !important e sobrepõe o estilo padrão de desabilitado do Streamlit. */
div[data-testid="stForm"] button[kind="primaryFormSubmit"]:disabled,
div[data-testid="stForm"] button[kind="primaryFormSubmit"][disabled] {
    background: #EFE3CA !important;
    color: #A98B5E !important;
    cursor: not-allowed !important;
    opacity: 1 !important;
}
.login-rodape {
    text-align: center;
    color: #92400E;
    font-size: 0.72rem;
    margin-top: 1rem;
    opacity: 0.85;
}
</style>
"""


# ══════════════════════════════════════════════════════════════
# 6. A TELA
# ══════════════════════════════════════════════════════════════

def _tela_login():
    st.markdown(_CSS, unsafe_allow_html=True)

    _, centro, _ = st.columns([1, 2.1, 1])
    with centro:
        st.markdown(
            """
            <div class="login-brand">
              <div class="icone">🥐</div>
              <h1>Minha Padaria</h1>
              <p>Painel financeiro · acesso restrito</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.pop(_EXPIROU, False):
            st.info("Sua sessão expirou por inatividade. Entre novamente.")

        bloqueio = _segundos_bloqueado()

        with st.form("form_login"):
            login = st.text_input(
                "Usuário", placeholder="digite seu acesso", disabled=bool(bloqueio)
            )
            senha = st.text_input(
                "Senha", type="password", placeholder="••••••••", disabled=bool(bloqueio)
            )
            enviar = st.form_submit_button(
                "Entrar", use_container_width=True, type="primary", disabled=bool(bloqueio)
            )

        if bloqueio:
            st.warning(
                f"Muitas tentativas incorretas. Aguarde {bloqueio // 60}min "
                f"{bloqueio % 60}s para tentar novamente."
            )
        elif enviar:
            if not login or not senha:
                st.session_state[_ERRO] = "Preencha usuário e senha."
            else:
                ok, usuario = autenticar(login, senha)
                if ok:
                    st.session_state[_LOGADO]  = True
                    st.session_state[_USUARIO] = usuario
                    st.session_state[_ACESSO]  = datetime.now()
                    st.session_state[_FALHAS]  = 0
                    st.session_state.pop(_ERRO, None)
                    st.rerun()
                else:
                    _registrar_falha()
                    if _segundos_bloqueado():
                        # O bloqueio acabou de entrar em vigor. `bloqueio` foi
                        # calculado antes do envio, então precisa redesenhar
                        # para o aviso aparecer e os campos travarem agora.
                        st.rerun()
                    restam = max(MAX_TENTATIVAS - st.session_state.get(_FALHAS, 0), 0)
                    # Mensagem genérica de propósito: não conta se o usuário existe.
                    st.session_state[_ERRO] = (
                        f"Usuário ou senha inválidos. Restam {restam} tentativa(s)."
                    )

        erro = st.session_state.pop(_ERRO, None)
        if erro:
            st.error(erro)

        st.markdown(
            '<p class="login-rodape">🔒 Área exclusiva da administração da padaria</p>',
            unsafe_allow_html=True,
        )

        if _usando_demo():
            st.caption(
              
            )


# ══════════════════════════════════════════════════════════════
# 7. O QUE VOCÊ CHAMA DE FORA
# ══════════════════════════════════════════════════════════════

def exigir_login() -> dict:
    """Porteiro do painel.

    Se já existe sessão válida, devolve os dados do usuário e o script
    segue. Se não, desenha a tela de login e chama st.stop() — nada
    escrito depois desta chamada chega a ser executado.
    """
    if st.session_state.get(_LOGADO):
        ultimo = st.session_state.get(_ACESSO)
        if ultimo and datetime.now() - ultimo > _timeout():
            _limpar()
            st.session_state[_EXPIROU] = True
        else:
            st.session_state[_ACESSO] = datetime.now()   # renova a sessão
            return st.session_state[_USUARIO]

    _tela_login()
    st.stop()


def _limpar():
    for chave in (_LOGADO, _USUARIO, _ACESSO):
        st.session_state.pop(chave, None)


def sair():
    """Encerra a sessão e volta para a tela de login."""
    _limpar()
    st.cache_data.clear()      # não deixa dados do painel no cache
    st.rerun()


def barra_usuario(usuario: dict):
    """Linha com a saudação e o botão de sair."""
    col_nome, col_sair = st.columns([3, 1])
    with col_nome:
        st.markdown(
            '<div style="font-size:.82rem;color:#92400E;padding-top:.45rem">'
            f'👤 Olá, <b style="color:#78350F">{usuario.get("nome", "")}</b></div>',
            unsafe_allow_html=True,
        )
    with col_sair:
        if st.button("Sair", use_container_width=True):
            sair()


# ══════════════════════════════════════════════════════════════
# 8. DEMONSTRAÇÃO
# Só roda quando o arquivo é executado direto:
#     python -m streamlit run tela_login.py
# Ao importar de outro arquivo, este bloco é ignorado.
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    st.set_page_config(
        page_title="Padaria · Login",
        page_icon="🥐",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    usuario = exigir_login()      # ← daqui para baixo, só quem entrou

    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#78350F 0%,#D97706 100%);
                    border-radius:14px;padding:1rem 1.2rem;margin-bottom:1rem;
                    display:flex;align-items:center;gap:.75rem;">
          <div style="font-size:2rem;line-height:1">🥐</div>
          <div>
            <h1 style="font-family:'Playfair Display',serif;color:#FDE68A;
                       font-size:1.5rem;margin:0;line-height:1.2">Minha Padaria</h1>
            <p style="color:#FEF3C7;margin:.15rem 0 0;font-size:.78rem">
              Painel financeiro · acesso restrito</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    barra_usuario(usuario)

    st.success(f"Login funcionando. Bem-vinda, {usuario['nome']}!")
    st.markdown(
        # ──────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Padaria · Dashboard",
    page_icon="🥐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# ESTILO — otimizado para mobile
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
# FILTROS TEMPORAIS  (calculados uma vez)
# ──────────────────────────────────────────────
hoje        = date.today()
ano_atual   = hoje.year
mes_atual   = hoje.month

# Últimos 3 meses (mes_ord como int YYYYMM)
def ultimos_3_meses_ords():
    ords = []
    for i in range(2, -1, -1):           # i = 2, 1, 0  →  2 meses atrás … mês atual
        m = mes_atual - i
        y = ano_atual
        if m <= 0:
            m += 12
            y -= 1
        ords.append(y * 100 + m)
    return ords

# Últimos 3 trimestres: mês atual e os 2 anteriores (mesmo que acima, só renomeado para clareza)
ultimos_3_ords = ultimos_3_meses_ords()

# Início do trimestre corrente para a tabela (mês atual − 2)
inicio_trimestre_ord = ultimos_3_ords[0]

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

tab_fin, tab_metas = st.tabs(["📊  Financeiro", "🎯  Metas"])

# ═══════════════════════════════════════════════
# ABA 1 — FINANCEIRO
# ═══════════════════════════════════════════════
with tab_fin:
    df = load_financeiro()

    if df.empty:
        st.info("Nenhum dado financeiro encontrado ainda.")
    else:
        # Cards de resumo usam TODOS os dados (histórico completo)
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

        # ── Últimos 3 meses (barras + lucro líquido) ──────────────────────
        df_3m = df[df["mes_ord"].isin(ultimos_3_ords)].copy()

        mes_ordem_3m = (
            df_3m[["mes_ord","mes"]].drop_duplicates()
            .sort_values("mes_ord")["mes"].tolist()
        )

        # — Rendimento Mensal (últimos 3 meses) ————
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
            height=310,
            uniformtext_minsize=11, uniformtext_mode="hide",
            dragmode=False,
        )
        fig_bar.update_traces(
            marker_line_width=0, opacity=0.9,
            textposition="outside",
            textfont=dict(size=13, family="DM Sans"),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config=CHART_CFG)

        # — Lucro Líquido por Mês (últimos 3 meses) ————
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
            uniformtext_minsize=11, uniformtext_mode="hide",
            dragmode=False,
        )
        st.plotly_chart(fig_liq, use_container_width=True, config=CHART_CFG)

        # ── Lucro Acumulado (reseta a cada ano) ───────────────────────────
        # ── Receita vs Despesa (apenas mês atual) ─────────────────────────
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
            fig_acum.update_traces(
                fill="tozeroy", fillcolor="rgba(217,119,6,0.15)",
                line_color="#D97706", line_width=2.5
            )
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

            # Apenas mês atual
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
                    hole=0.55,
                    title=nome_mes_atual,
                )
                fig_pie.update_layout(
                    font_family="DM Sans", font_size=13,
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=60, r=60, t=40, b=30),
                    height=290, dragmode=False,
                    title_font=dict(size=13, family="DM Sans", color="#92400E"),
                    title_x=0.5,
                )
                fig_pie.update_traces(
                    textposition="outside", textinfo="percent+label",
                    textfont_size=13, pull=[0.05, 0.05],
                )
                st.plotly_chart(fig_pie, use_container_width=True, config=CHART_CFG)

        # — Tabela (últimos 3 meses) ————
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
        # Investimento realizado: SEMPRE usa histórico completo, independente da data
        total_concluido_historico = dm[dm["concluida"]]["preco"].sum()

        # Para exibição na lista: oculta metas concluídas há mais de 1 ano
        # Usa concluida_em (preenchida pelo n8n quando obs vira "CONCLUÍDO")
        um_ano_atras = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=1)

        if "concluida_em" in dm.columns:
            dm["concluida_em"] = pd.to_datetime(dm["concluida_em"], errors="coerce", utc=True)
            # Pendentes: sempre visíveis
            # Concluídas: visíveis se concluida_em for nulo (segurança) ou dentro de 1 ano
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

        # Métricas usando dm_visivel para contagens, mas total_concluido_historico para valor
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

        # Gráfico de rosca
        st.markdown('<p class="section-title">Distribuição</p>', unsafe_allow_html=True)
        fig_donut = go.Figure(go.Pie(
            labels=["Concluídas","Pendentes"],
            values=[max(concluidas_vis, 0), max(pendentes_vis, 0)],
            hole=0.6,
            marker_colors=["#059669","#D97706"],
            textinfo="percent",
            textfont_size=12,
        ))
        fig_donut.update_layout(
            font_family="DM Sans", font_size=11,
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=30),
            height=220, showlegend=True,
            legend=dict(orientation="h", y=-0.1),
            annotations=[dict(
                text=f"<b>{pct}%</b>", x=0.5, y=0.5,
                font_size=20, font_color="#78350F", showarrow=False,
            )],
            dragmode=False,
        )
        st.plotly_chart(fig_donut, use_container_width=True, config=CHART_CFG)

        # Lista de metas
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
    st.code(
        "from tela_login import exigir_login, barra_usuario\n\n"
        "usuario = exigir_login()\n"
        "barra_usuario(usuario)",
        language="python",
    )
