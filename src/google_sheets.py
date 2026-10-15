
"""
Alumni Profile Finder
Integração reutilizável com Google Sheets privado.

Etapa 2:
- OAuth 2.0 individual
- Armazenamento local de token
- Listagem de abas
- Leitura de até 200 perfis
- Validação de nome e link

Não executa Selenium nem altera planilhas.
"""

import os
import re
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# ============================================================
# CONFIGURAÇÕES
# ============================================================

NOME_APLICATIVO = "AlumniProfileFinder"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

LIMITE_PERFIS = 200


# ============================================================
# CAMINHOS DO APLICATIVO
# ============================================================

def obter_pasta_recursos():
    """
    Localiza os recursos do projeto no desenvolvimento
    e, futuramente, no executável PyInstaller.
    """

    if getattr(sys, "frozen", False):
        return Path(
            getattr(
                sys,
                "_MEIPASS",
                Path(sys.executable).resolve().parent
            )
        )

    return Path(__file__).resolve().parents[1]


def obter_caminho_credenciais():
    """
    Localiza a configuração OAuth do aplicativo.
    """

    return (
        obter_pasta_recursos()
        / "config"
        / "credentials.json"
    )


def obter_pasta_usuario():
    """
    Usa a pasta individual do usuário no Windows.

    Não grava tokens na pasta do projeto
    nem ao lado do executável.
    """

    local_appdata = os.environ.get("LOCALAPPDATA")

    if local_appdata:
        pasta_base = Path(local_appdata)
    else:
        pasta_base = (
            Path.home() / "AppData" / "Local"
        )

    return pasta_base / NOME_APLICATIVO


def obter_caminho_token():
    return obter_pasta_usuario() / "token.json"


# ============================================================
# AUTENTICAÇÃO GOOGLE
# ============================================================

def autenticar():
    """
    Autentica o usuário usando OAuth 2.0.

    Reaproveita um token válido ou abre o navegador
    para obter autorização.

    Retorna o serviço Google Sheets.
    """

    caminho_credenciais = obter_caminho_credenciais()
    caminho_token = obter_caminho_token()

    credenciais = None

    if caminho_token.exists():
        credenciais = (
            Credentials.from_authorized_user_file(
                str(caminho_token),
                SCOPES
            )
        )

    if not credenciais or not credenciais.valid:

        if (
            credenciais
            and credenciais.expired
            and credenciais.refresh_token
        ):
            credenciais.refresh(Request())

        else:
            if not caminho_credenciais.exists():
                raise FileNotFoundError(
                    "Configuração OAuth não encontrada em: "
                    f"{caminho_credenciais}"
                )

            fluxo = (
                InstalledAppFlow.from_client_secrets_file(
                    str(caminho_credenciais),
                    SCOPES
                )
            )

            credenciais = fluxo.run_local_server(
                port=0
            )

        pasta_usuario = obter_pasta_usuario()

        pasta_usuario.mkdir(
            parents=True,
            exist_ok=True
        )

        caminho_token.write_text(
            credenciais.to_json(),
            encoding="utf-8"
        )

        # Restringe permissões no Windows quando
        # o sistema suportar o comando icacls.
        if os.name == "nt":
            import subprocess

            usuario = os.environ.get("USERNAME")

            if usuario:
                try:
                    subprocess.run(
                        [
                            "icacls",
                            str(caminho_token),
                            "/inheritance:r",
                            "/grant:r",
                            f"{usuario}:(F)"
                        ],
                        capture_output=True,
                        check=True
                    )
                except (
                    OSError,
                    subprocess.CalledProcessError
                ):
                    # A falha não é ocultada como garantia
                    # de proteção. A implantação final
                    # precisará validar as ACLs.
                    raise RuntimeError(
                        "Não foi possível confirmar as "
                        "permissões do arquivo de token."
                    )

    return build(
        "sheets",
        "v4",
        credentials=credenciais,
        cache_discovery=False
    )


def desconectar():
    """
    Remove o token OAuth local deste usuário.

    Não revoga o acesso na conta Google.
    A revogação deverá ser tratada separadamente.
    """

    caminho_token = obter_caminho_token()

    if caminho_token.exists():
        caminho_token.unlink()
        return True

    return False


# ============================================================
# IDENTIFICAÇÃO DA PLANILHA
# ============================================================

def extrair_id(url):
    """
    Extrai o ID de uma URL Google Sheets.
    """

    url = str(url or "").strip()

    resultado = re.search(
        r"^https://docs\.google\.com/spreadsheets/d/"
        r"([a-zA-Z0-9_-]+)",
        url
    )

    if not resultado:
        raise ValueError(
            "Informe uma URL válida do Google Sheets."
        )

    return resultado.group(1)


# ============================================================
# CONSULTAR ABAS
# ============================================================

def listar_abas(servico, planilha_id):
    """
    Retorna o título da planilha e os nomes das abas.

    A API verifica o acesso da conta conectada.
    """

    resposta = servico.spreadsheets().get(
        spreadsheetId=planilha_id,
        fields=(
            "properties(title),"
            "sheets(properties(title))"
        )
    ).execute()

    titulo = resposta["properties"]["title"]

    abas = [
        item["properties"]["title"]
        for item in resposta.get("sheets", [])
    ]

    return titulo, abas


# ============================================================
# LEITURA DOS REGISTROS
# ============================================================

def ler_aba(
    servico,
    planilha_id,
    nome_aba,
    limite=LIMITE_PERFIS
):
    """
    Lê o cabeçalho e até 'limite' registros.

    Não imprime dados pessoais.
    """

    if (
        not isinstance(limite, int)
        or isinstance(limite, bool)
        or not 1 <= limite <= LIMITE_PERFIS
    ):
        raise ValueError(
            "O limite deve estar entre 1 e 200."
        )

    nome_seguro = str(nome_aba).replace(
        "'",
        "''"
    )

    ultima_linha = limite + 1

    intervalo = (
        f"'{nome_seguro}'!A1:ZZ{ultima_linha}"
    )

    resposta = servico.spreadsheets().values().get(
        spreadsheetId=planilha_id,
        range=intervalo
    ).execute()

    return resposta.get("values", [])


# ============================================================
# VALIDAR NOME E LINK
# ============================================================

def validar_colunas(dados):
    """
    Localiza as colunas obrigatórias no cabeçalho.

    Retorna os índices de 'nome' e 'link'.
    """

    if not dados:
        raise ValueError(
            "A aba selecionada está vazia."
        )

    cabecalho = [
        str(valor).strip().lower()
        for valor in dados[0]
    ]

    if "nome" not in cabecalho:
        raise ValueError(
            "A aba precisa conter a coluna 'nome'."
        )

    if "link" not in cabecalho:
        raise ValueError(
            "A aba precisa conter a coluna 'link'."
        )

    return (
        cabecalho.index("nome"),
        cabecalho.index("link")
    )


def preparar_registros(dados):
    """
    Converte linhas em registros com nome e link.

    Não elimina duplicatas nesta etapa.
    Isso será definido na integração de resultados.
    """

    indice_nome, indice_link = validar_colunas(
        dados
    )

    registros = []

    for linha in dados[1:]:

        nome = (
            str(linha[indice_nome]).strip()
            if indice_nome < len(linha)
            else ""
        )

        link = (
            str(linha[indice_link]).strip()
            if indice_link < len(linha)
            else ""
        )

        if not nome and not link:
            continue

        registros.append({
            "nome": nome,
            "link": link
        })

    return registros


# ============================================================
# PREPARAÇÃO DE PERFIS PARA PROCESSAMENTO
# ============================================================

def preparar_perfis_processamento(
    registros,
    limite=LIMITE_PERFIS
):
    """
    Prepara os perfis recebidos do Google Sheets.

    - Preserva o nome original da planilha.
    - Valida o formato dos links do LinkedIn.
    - Remove duplicatas somente da lista de processamento.
    - Respeita o limite máximo de 200 registros.
    - Não altera os registros originais.
    - Não acessa o LinkedIn.

    Retorna:
        perfis: lista de dicionários com nome e link
        resumo: estatísticas da preparação
    """

    from urllib.parse import urlsplit

    if (
        not isinstance(limite, int)
        or isinstance(limite, bool)
        or not 1 <= limite <= LIMITE_PERFIS
    ):
        raise ValueError(
            "O limite deve estar entre 1 e 200."
        )

    perfis = []
    vistos = set()

    resumo = {
        "analisados": 0,
        "sem_nome": 0,
        "sem_link": 0,
        "links_invalidos": 0,
        "duplicados": 0,
        "selecionados": 0,
    }

    for registro in registros[:limite]:

        resumo["analisados"] += 1

        nome = str(
            registro.get("nome", "") or ""
        ).strip()

        link = str(
            registro.get("link", "") or ""
        ).strip()

        if not nome:
            resumo["sem_nome"] += 1

        if not link:
            resumo["sem_link"] += 1
            continue

        candidato = link

        if "://" not in candidato:
            candidato = "https://" + candidato

        try:
            partes = urlsplit(candidato)

            dominio = (
                partes.hostname or ""
            ).lower()

            caminho = partes.path.strip("/").split("/")

        except ValueError:
            resumo["links_invalidos"] += 1
            continue

        if (
            partes.scheme.lower() not in ("http", "https")
            or dominio not in (
                "linkedin.com",
                "www.linkedin.com"
            )
            or len(caminho) < 2
            or caminho[0].lower() != "in"
            or not caminho[1]
        ):
            resumo["links_invalidos"] += 1
            continue

        identificador = caminho[1].lower()

        chave = f"linkedin.com/in/{identificador}"

        if chave in vistos:
            resumo["duplicados"] += 1
            continue

        vistos.add(chave)

        perfis.append({
            "nome": nome,
            "link": (
                "https://www.linkedin.com/in/"
                f"{identificador}/"
            )
        })

    resumo["selecionados"] = len(perfis)

    return perfis, resumo
