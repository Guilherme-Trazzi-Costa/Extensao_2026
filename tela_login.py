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

        #if _usando_demo():
            #st.caption(
               
            #)


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
    st.markdown("Exemplo de como usar no seu painel real:")
    st.code(
        "from tela_login import exigir_login, barra_usuario\n\n"
        "usuario = exigir_login()\n"
        "barra_usuario(usuario)",
        language="python",
    )
