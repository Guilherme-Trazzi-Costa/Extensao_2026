# ══════════════════════════════════════════════════════════════
#  TELA DE LOGIN — Painel da Padaria
#  Projeto de Extensão · Panificação Artesanal
# ══════════════════════════════════════════════════════════════
"""
Arquivo ÚNICO e autocontido da tela de login, com login persistente
via cookie (sobrevive a quedas de conexão do túnel/proxy).

────────────────────────────────────────────────────────────────
DEPENDÊNCIA NOVA
────────────────────────────────────────────────────────────────

    pip install extra-streamlit-components

(adicione "extra-streamlit-components" no requirements.txt)

────────────────────────────────────────────────────────────────
COMO RODAR (autocontido)
────────────────────────────────────────────────────────────────

    pip install streamlit extra-streamlit-components
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
LOGIN PERSISTENTE (COOKIE) — por que existe
────────────────────────────────────────────────────────────────

O Streamlit guarda "estou logado" no st.session_state, que vive na
memória do servidor amarrado à conexão WebSocket do navegador. Atrás
de túneis instáveis (ex: Cloudflare Quick Tunnel), essa conexão pode
cair e reconectar como uma sessão nova — derrubando o login a cada
atualização de página.

Para resolver isso, ao logar com sucesso este arquivo grava um cookie
no navegador com um token assinado (HMAC-SHA256, com validade). Numa
sessão nova sem session_state, o app confere esse cookie antes de
pedir login de novo.

────────────────────────────────────────────────────────────────
CONFIGURAR A CHAVE DO COOKIE (recomendado)
────────────────────────────────────────────────────────────────

Sem configuração, a chave de assinatura do cookie é gerada uma vez
quando o container sobe — funciona bem para sobreviver a quedas do
túnel, mas muda se o container reiniciar (todo mundo precisa logar
de novo nesse caso). Para persistir mesmo entre reinícios, defina uma
chave fixa no .streamlit/secrets.toml:

    [auth]
    modo = "local"
    timeout_minutos = 30
    cookie_dias = 7
    cookie_secret = "troque-por-uma-string-aleatoria-bem-longa"

────────────────────────────────────────────────────────────────
COMO TROCAR A SENHA (importante)
────────────────────────────────────────────────────────────────

A senha NUNCA é guardada em texto puro, só o hash PBKDF2-SHA256.
Para gerar o hash de uma senha nova, rode no terminal:

    python -c "import tela_login,getpass; print(tela_login.gerar_hash(getpass.getpass()))"

Cole o resultado em USUARIOS_DEMO abaixo, ou — melhor — em
.streamlit/secrets.toml, que este arquivo lê automaticamente:

    [auth.usuarios.francinete]
    nome = "Francinete Vieira"
    senha_hash = "pbkdf2_sha256$260000$....$...."

Havendo secrets.toml, ele tem prioridade e o USUARIOS_DEMO é ignorado.
"""

import hashlib
import hmac
import secrets as _rnd            # biblioteca padrão — não é o st.secrets
import time
from datetime import datetime, timedelta
from urllib.parse import unquote

import streamlit as st
import extra_streamlit_components as stx

# ══════════════════════════════════════════════════════════════
# 1. CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════

ITERACOES          = 260_000   # custo do PBKDF2 (quanto maior, mais lento de quebrar)
MAX_TENTATIVAS     = 5         # erros antes de travar
BLOQUEIO_MINUTOS   = 5         # quanto tempo fica travado
TIMEOUT_PADRAO_MIN = 30        # minutos parado até a sessão cair (dentro da mesma conexão)

_COOKIE_NOME        = "padaria_auth_token"
_DIAS_COOKIE_PADRAO = 7         # validade do login persistente

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
_COOKIE_MGR                  = "auth_cookie_manager"
_SAIU                        = "auth_saiu"


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


def _dias_cookie() -> int:
    try:
        return int(_config().get("cookie_dias", _DIAS_COOKIE_PADRAO))
    except (TypeError, ValueError):
        return _DIAS_COOKIE_PADRAO


@st.cache_resource
def _secret_fallback() -> str:
    """Chave sorteada UMA vez por processo.

    Não pode ser variável de módulo: o Streamlit re-executa o script
    inteiro a cada rerun, então uma variável de módulo receberia uma
    chave nova toda vez — e o cookie assinado há dois segundos já não
    validaria mais. Era esta a causa da queda no refresh.
    """
    return _rnd.token_hex(32)


def _secret_key() -> str:
    """Chave de assinatura do cookie: secrets.toml tem prioridade;
    sem ela, usa a chave do processo (some ao reiniciar o servidor)."""
    secreto = _config().get("cookie_secret")
    return str(secreto) if secreto else _secret_fallback()


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
# 5. LOGIN PERSISTENTE (COOKIE)
# ══════════════════════════════════════════════════════════════

def _cookie_manager() -> stx.CookieManager:
    """Uma única instância por sessão de navegador (guardada no
    session_state para não recriar o componente a cada rerun)."""
    if _COOKIE_MGR not in st.session_state:
        st.session_state[_COOKIE_MGR] = stx.CookieManager(key="tela_login_cookie_manager")
    return st.session_state[_COOKIE_MGR]


def _gerar_token(login: str) -> str:
    """login|validade_unix|assinatura_hmac"""
    expira = int((datetime.now() + timedelta(days=_dias_cookie())).timestamp())
    payload = f"{login}|{expira}"
    assinatura = hmac.new(_secret_key().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}|{assinatura}"


def _validar_token(token: str):
    """Devolve os dados do usuário se o token for válido e não tiver expirado, senão None."""
    try:
        login, expira_str, assinatura = str(token).split("|")
    except (ValueError, AttributeError):
        return None

    payload = f"{login}|{expira_str}"
    esperado = hmac.new(_secret_key().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(assinatura, esperado):
        return None

    try:
        if int(expira_str) < datetime.now().timestamp():
            return None
    except ValueError:
        return None

    procurado = login.strip().lower()
    for chave, dados in _usuarios().items():
        if chave.strip().lower() == procurado:
            return {"login": chave, "nome": dados.get("nome", chave)}
    return None


def _ler_cookie() -> str | None:
    """Lê o cookie de sessão.

    Usa `st.context.cookies`, que vem do cabeçalho HTTP da própria
    conexão — é síncrono e já está disponível no primeiro rerun.

    O CookieManager NÃO serve para ler aqui: ele é um componente de
    frontend e leva 2–3 reruns para responder, então na primeira
    execução devolve vazio mesmo havendo cookie — e a sessão salva era
    descartada antes de chegar. Ele continua sendo usado só para
    gravar e apagar, que é o que `st.context.cookies` não faz.
    """
    bruto = None
    try:
        bruto = st.context.cookies.get(_COOKIE_NOME)
    except Exception:
        # Streamlit antigo, ou fora de um contexto de script.
        try:
            bruto = _cookie_manager().get(_COOKIE_NOME)
        except Exception:
            return None

    if not bruto:
        return None

    # O CookieManager grava o valor URL-encodado, e a leitura nativa
    # devolve exatamente o que está no cabeçalho — ou seja, o separador
    # "|" chega como "%7C". Sem decodificar, o split("|") não acha nada
    # e a sessão válida era jogada fora.
    return unquote(bruto)


def _tentar_login_por_cookie() -> bool:
    """Se existir um cookie de sessão válido, restaura o login sem pedir senha."""
    token = _ler_cookie()
    if not token:
        return False
    usuario = _validar_token(token)
    if usuario is None:
        return False
    st.session_state[_LOGADO]  = True
    st.session_state[_USUARIO] = usuario
    st.session_state[_ACESSO]  = datetime.now()
    return True


# ══════════════════════════════════════════════════════════════
# 6. VISUAL
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
# 7. A TELA
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
                    st.session_state.pop(_SAIU, None)
                    # Grava o cookie ANTES do rerun, para sobreviver a
                    # quedas de conexão do túnel/proxy.
                    _cookie_manager().set(
                        _COOKIE_NOME,
                        _gerar_token(usuario["login"]),
                        expires_at=datetime.now() + timedelta(days=_dias_cookie()),
                        key="set_cookie_login",
                    )
                    # set() é assíncrono: escreve o cookie via round-trip
                    # até o navegador. Sem esta pausa o st.rerun() aborta o
                    # script antes disso e o cookie nunca chega a existir.
                    time.sleep(0.6)
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
                "⚠️ Rodando com o usuário de demonstração embutido no arquivo. "
                "Configure o `.streamlit/secrets.toml` antes de usar de verdade."
            )


# ══════════════════════════════════════════════════════════════
# 8. O QUE VOCÊ CHAMA DE FORA
# ══════════════════════════════════════════════════════════════

def exigir_login() -> dict:
    """Porteiro do painel.

    Se já existe sessão válida (session_state OU cookie assinado
    válido), devolve os dados do usuário e o script segue. Se não,
    desenha a tela de login e chama st.stop() — nada escrito depois
    desta chamada chega a ser executado.
    """
    if st.session_state.get(_LOGADO):
        ultimo = st.session_state.get(_ACESSO)
        if ultimo and datetime.now() - ultimo > _timeout():
            _limpar()
            st.session_state[_EXPIROU] = True
        else:
            st.session_state[_ACESSO] = datetime.now()   # renova a sessão
            return st.session_state[_USUARIO]

    # Sem sessão em memória (refresh da página, WebSocket reconectado) —
    # tenta restaurar pelo cookie antes de exigir senha de novo.
    # Quem clicou em "Sair" não pode ser reconectado pelo cookie nesta
    # mesma conexão: st.context.cookies vem do cabeçalho de quando o
    # WebSocket abriu, então continua mostrando o cookie que o navegador
    # acabou de apagar. Sem esta trava, "Sair" não surtia efeito até a
    # página ser atualizada.
    if not st.session_state.get(_SAIU) and _tentar_login_por_cookie():
        return st.session_state[_USUARIO]

    _tela_login()
    st.stop()


def _limpar():
    for chave in (_LOGADO, _USUARIO, _ACESSO):
        st.session_state.pop(chave, None)


def sair():
    """Encerra a sessão, apaga o cookie e volta para a tela de login."""
    try:
        _cookie_manager().delete(_COOKIE_NOME, key="delete_cookie_logout")
    except KeyError:
        pass
    _limpar()
    st.session_state[_SAIU] = True
    st.cache_data.clear()      # não deixa dados do painel no cache
    time.sleep(0.6)            # dá tempo de o delete chegar ao navegador
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
# 9. DEMONSTRAÇÃO
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
