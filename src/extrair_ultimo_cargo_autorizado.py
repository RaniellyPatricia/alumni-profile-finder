from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import csv
import os
import re
import time
import unicodedata


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ARQUIVO_ENTRADA = "data/raw/links.csv"
ARQUIVO_SAIDA = "data/processed/ultimo_cargo_linkedin.csv"
PASTA_DEBUG = "data/processed/debug"

TEMPO_MAXIMO_CARREGAMENTO = 40
TEMPO_ENTRE_PERFIS = 3

os.makedirs("data/processed", exist_ok=True)
os.makedirs(PASTA_DEBUG, exist_ok=True)


COLUNAS_SAIDA = [
    "nome",
    "link",
    "nome_linkedin",
    "headline",
    "empresa_atual",
    "tipo_contrato",
    "tempo_empresa",
    "local_empresa",
    "cargo_atual",
    "data_inicio",
    "data_fim",
    "duracao_cargo",
    "local_cargo",
    "descricao_cargo",
]


# ============================================================
# CONEXÃO COM O CHROME ABERTO NA PORTA 9222
# ============================================================

options = Options()

options.add_experimental_option(
    "debuggerAddress",
    "127.0.0.1:9222",
)

driver = webdriver.Chrome(options=options)


# ============================================================
# TERMOS DE REFERÊNCIA
# ============================================================

TITULOS_EXPERIENCIA = {
    "experiencia",
    "experience",
}

MARCADORES_FIM_EXPERIENCIA = {
    "sobre",
    "about",
    "formacao academica",
    "education",
    "competencias",
    "skills",
    "recomendacoes",
    "recommendations",
    "interesses",
    "interests",
    "idiomas",
    "languages",
    "idioma do perfil",
    "profile language",
    "licencas e certificados",
    "licenses & certifications",
    "licenses and certifications",
}

TIPOS_CONTRATO = {
    "tempo integral",
    "full-time",
    "full time",
    "meio periodo",
    "meio período",
    "part-time",
    "part time",
    "estagio",
    "estágio",
    "internship",
    "autonomo",
    "autônomo",
    "self-employed",
    "self employed",
    "freelance",
    "temporario",
    "temporário",
    "temporary",
    "aprendiz",
    "apprenticeship",
    "contrato",
    "contract",
    "terceirizado",
    "terceirizada",
    "seasonal",
    "voluntario",
    "voluntário",
    "volunteer",
}

MODALIDADES_TRABALHO = {
    "remoto",
    "remote",
    "hibrido",
    "híbrido",
    "hybrid",
    "no local",
    "presencial",
    "on-site",
    "onsite",
}

LINHAS_IGNORADAS = {
    "aprimorar com ia",
    "enhance with ai",
    "enviar mensagem",
    "send message",
    "exibir todas as experiencias",
    "exibir todas as experiências",
    "show all experiences",
    "ver mais",
    "see more",
    "mostrar mais",
    "show more",
    "seguir",
    "follow",
    "conectar",
    "connect",
}

HEADLINES_INVALIDAS = {
    "pendente",
    "seguindo",
    "follow",
    "following",
    "conectar",
    "connect",
    "enviar mensagem",
    "send message",
}

PALAVRAS_QUE_INDICAM_CARGO = [
    "analista",
    "assistente",
    "auxiliar",
    "auditor",
    "atendente",
    "consultor",
    "consultora",
    "coordenador",
    "coordenadora",
    "desenvolvedor",
    "desenvolvedora",
    "developer",
    "diretor",
    "diretora",
    "engenheiro",
    "engenheira",
    "engineer",
    "especialista",
    "estagiario",
    "estagiaria",
    "gerente",
    "gestor",
    "gestora",
    "programador",
    "programadora",
    "professor",
    "professora",
    "senior",
    "socio",
    "socia",
    "supervisor",
    "supervisora",
    "tecnico",
    "tecnica",
    "ceo",
    "founder",
    "co-founder",
    "presidente",
    "coordenacao",
    "lider",
    "líder",
    "head",
    "arquiteto",
    "arquiteta",
    "administrador",
    "administradora",
]


# ============================================================
# FUNÇÕES DE LIMPEZA E NORMALIZAÇÃO
# ============================================================

def remover_acentos(texto):
    """
    Remove acentos para facilitar comparações.

    Exemplo:
    Experiência -> Experiencia
    """

    texto_normalizado = unicodedata.normalize(
        "NFKD",
        texto or "",
    )

    return "".join(
        caractere
        for caractere in texto_normalizado
        if not unicodedata.combining(caractere)
    )


def normalizar_comparacao(texto):
    """
    Padroniza um texto para comparações internas.
    """

    texto = texto or ""

    texto = texto.replace("–", "-")
    texto = texto.replace("—", "-")
    texto = remover_acentos(texto)
    texto = texto.lower().strip()

    texto = re.sub(r"\s+", " ", texto)

    return texto


def normalizar_tracos(texto):
    """
    Substitui diferentes tipos de traço por hífen comum.
    """

    return (
        (texto or "")
        .replace("–", "-")
        .replace("—", "-")
    )


def limpar_linhas(texto):
    """
    Divide o texto da página em linhas e remove linhas vazias.
    """

    linhas = []

    for linha in (texto or "").split("\n"):
        linha = linha.strip()

        if linha:
            linhas.append(linha)

    return linhas


def eh_linha_ignorada(linha):
    """
    Identifica botões e textos auxiliares do LinkedIn.
    """

    return normalizar_comparacao(linha) in {
        normalizar_comparacao(item)
        for item in LINHAS_IGNORADAS
    }


def eh_headline_invalida(texto):
    """
    Evita salvar Pendente, Seguindo e outros botões
    como headline profissional.
    """

    texto_normalizado = normalizar_comparacao(texto)

    if not texto_normalizado:
        return True

    return texto_normalizado in {
        normalizar_comparacao(item)
        for item in HEADLINES_INVALIDAS
    }


# ============================================================
# FUNÇÕES PARA O CSV
# ============================================================

def identificar_delimitador(caminho):
    """
    Identifica se o CSV usa vírgula ou ponto e vírgula.
    """

    with open(
        caminho,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as arquivo:
        amostra = arquivo.read(4096)

    try:
        formato = csv.Sniffer().sniff(
            amostra,
            delimiters=",;",
        )

        return formato.delimiter

    except csv.Error:
        return ";"


def localizar_colunas(fieldnames):
    """
    Localiza as colunas nome e link no arquivo de entrada.
    """

    mapa_colunas = {}

    for coluna in fieldnames:
        if coluna:
            mapa_colunas[
                normalizar_comparacao(coluna)
            ] = coluna

    nomes_aceitos = [
        "nome",
        "nome completo",
    ]

    coluna_nome = None

    for nome_aceito in nomes_aceitos:
        if nome_aceito in mapa_colunas:
            coluna_nome = mapa_colunas[nome_aceito]
            break

    if coluna_nome is None:
        raise ValueError(
            "A planilha precisa ter uma coluna chamada "
            "'nome' ou 'Nome Completo'."
        )

    if "link" not in mapa_colunas:
        raise ValueError(
            "A planilha precisa ter uma coluna chamada 'link'."
        )

    return coluna_nome, mapa_colunas["link"]


def salvar_resultados(resultados):
    """
    Salva os resultados depois de cada perfil.
    """

    with open(
        ARQUIVO_SAIDA,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as arquivo:

        escritor = csv.DictWriter(
            arquivo,
            fieldnames=COLUNAS_SAIDA,
            delimiter=";",
            extrasaction="ignore",
        )

        escritor.writeheader()
        escritor.writerows(resultados)


# ============================================================
# VALIDAÇÃO E NORMALIZAÇÃO DOS LINKS
# ============================================================

def preparar_link(link):
    """
    Completa links sem https e direciona para a seção
    de experiências do LinkedIn.
    """

    link = (link or "").strip()

    if not link:
        return ""

    if link.startswith("linkedin.com/"):
        link = f"https://www.{link}"

    elif link.startswith("www.linkedin.com/"):
        link = f"https://{link}"

    elif not link.startswith(("http://", "https://")):
        link = f"https://{link}"

    link = link.split("?")[0].rstrip("/")

    if "linkedin.com/in/" in link:
        if "/details/experience" not in link:
            link = f"{link}/details/experience/"

        elif not link.endswith("/"):
            link = f"{link}/"

    return link


def eh_link_linkedin(link):
    """
    Verifica se o endereço pertence ao LinkedIn.
    """

    return "linkedin.com/in/" in normalizar_comparacao(link)


# ============================================================
# LOCALIZAÇÃO DA SEÇÃO DE EXPERIÊNCIA
# ============================================================

def localizar_experiencia(linhas):
    """
    Localiza o título Experiência ou Experience.
    """

    for indice, linha in enumerate(linhas):
        if (
            normalizar_comparacao(linha)
            in TITULOS_EXPERIENCIA
        ):
            return indice

    return None


def localizar_fim_experiencia(linhas, inicio):
    """
    Procura a próxima seção do perfil depois de Experiência.
    """

    for indice in range(inicio, len(linhas)):
        linha_normalizada = normalizar_comparacao(
            linhas[indice]
        )

        if linha_normalizada in MARCADORES_FIM_EXPERIENCIA:
            return indice

    return len(linhas)


# ============================================================
# CARREGAMENTO DA PÁGINA
# ============================================================

def carregar_texto_perfil(link, timeout=40):
    """
    Abre o perfil e aguarda a seção de experiência aparecer.

    Depois de encontrar a seção, aguarda alguns segundos
    adicionais para os cargos terminarem de carregar.
    """

    driver.get(link)

    WebDriverWait(driver, timeout).until(
        lambda navegador: navegador.execute_script(
            "return document.readyState"
        ) == "complete"
    )

    limite = time.time() + timeout
    momento_experiencia_encontrada = None
    ultimo_texto = ""

    while time.time() < limite:
        try:
            corpo = driver.find_element(
                By.TAG_NAME,
                "body",
            )

            ultimo_texto = corpo.text
            linhas = limpar_linhas(ultimo_texto)

            encontrou_experiencia = (
                localizar_experiencia(linhas)
                is not None
            )

            if encontrou_experiencia:
                if momento_experiencia_encontrada is None:
                    momento_experiencia_encontrada = time.time()

                # Aguarda mais 4 segundos depois que a seção aparece.
                if (
                    time.time()
                    - momento_experiencia_encontrada
                    >= 4
                ):
                    return ultimo_texto

        except Exception:
            pass

        time.sleep(1)

    return ultimo_texto


# ============================================================
# ARQUIVOS DE DIAGNÓSTICO
# ============================================================

def nome_arquivo_seguro(texto):
    """
    Cria um nome de arquivo seguro para Windows.
    """

    texto = remover_acentos(texto or "perfil")
    texto = re.sub(r"[^a-zA-Z0-9_-]+", "_", texto)
    texto = texto.strip("_")

    return texto[:60] or "perfil"


def salvar_debug(indice, nome, texto):
    """
    Salva texto e captura de tela para diagnóstico.
    """

    nome_seguro = nome_arquivo_seguro(nome)

    prefixo = os.path.join(
        PASTA_DEBUG,
        f"{indice:03d}_{nome_seguro}",
    )

    caminho_texto = f"{prefixo}.txt"
    caminho_imagem = f"{prefixo}.png"

    with open(
        caminho_texto,
        "w",
        encoding="utf-8",
    ) as arquivo:
        arquivo.write(
            f"URL ATUAL: {driver.current_url}\n"
        )
        arquivo.write(
            f"TÍTULO: {driver.title}\n"
        )
        arquivo.write("=" * 80)
        arquivo.write("\n\n")
        arquivo.write(texto or "")

    try:
        driver.save_screenshot(caminho_imagem)
    except Exception:
        pass

    return caminho_texto


# ============================================================
# EXTRAÇÃO DO NOME E DA HEADLINE
# ============================================================

def limpar_titulo_pagina(titulo):
    """
    Tenta obter o nome pelo título da aba.
    """

    titulo = (titulo or "").strip()

    titulo = re.sub(
        r"\s*\|\s*LinkedIn\s*$",
        "",
        titulo,
        flags=re.IGNORECASE,
    )

    titulo = re.sub(
        r"\s*-\s*LinkedIn\s*$",
        "",
        titulo,
        flags=re.IGNORECASE,
    )

    titulo = re.sub(
        r"^Experi[eê]ncia\s+de\s+",
        "",
        titulo,
        flags=re.IGNORECASE,
    )

    titulo = re.sub(
        r"^Experience\s+of\s+",
        "",
        titulo,
        flags=re.IGNORECASE,
    )

    titulo = titulo.strip(" |-")

    if normalizar_comparacao(titulo) in TITULOS_EXPERIENCIA:
        return ""

    return titulo


def extrair_nome_dom():
    """
    Tenta encontrar o nome por elementos HTML.
    """

    seletores = [
        "h1.text-heading-xlarge",
        "h1",
        ".pv-text-details__left-panel h1",
    ]

    for seletor in seletores:
        try:
            elementos = driver.find_elements(
                By.CSS_SELECTOR,
                seletor,
            )

            for elemento in elementos:
                texto = elemento.text.strip()

                if (
                    texto
                    and normalizar_comparacao(texto)
                    not in TITULOS_EXPERIENCIA
                ):
                    return texto

        except Exception:
            continue

    return ""


def extrair_headline_dom():
    """
    Tenta encontrar a headline por elementos HTML.
    """

    seletores = [
        ".text-body-medium.break-words",
        ".pv-text-details__left-panel .text-body-medium",
        ".pv-top-card--list-bullet + div",
    ]

    for seletor in seletores:
        try:
            elementos = driver.find_elements(
                By.CSS_SELECTOR,
                seletor,
            )

            for elemento in elementos:
                texto = elemento.text.strip()

                if texto and not eh_headline_invalida(texto):
                    return texto

        except Exception:
            continue

    return ""


def pegar_nome_headline(linhas):
    """
    Tenta identificar nome e headline utilizando DOM,
    título da página e texto anterior à seção Experiência.
    """

    nome = extrair_nome_dom()
    headline = extrair_headline_dom()

    if not nome:
        nome = limpar_titulo_pagina(driver.title)

    indice_experiencia = localizar_experiencia(linhas)

    if indice_experiencia is not None:
        linhas_anteriores = linhas[
            max(0, indice_experiencia - 12):
            indice_experiencia
        ]

        candidatas = []

        termos_descartados = {
            "inicio",
            "home",
            "minha rede",
            "my network",
            "vagas",
            "jobs",
            "mensagens",
            "messaging",
            "notificacoes",
            "notifications",
            "eu",
            "me",
            "para negocios",
            "for business",
            "pendente",
            "seguindo",
            "follow",
            "following",
            "conectar",
            "connect",
        }

        for linha in linhas_anteriores:
            if eh_linha_ignorada(linha):
                continue

            linha_normalizada = normalizar_comparacao(
                linha
            )

            if linha_normalizada in termos_descartados:
                continue

            candidatas.append(linha)

        if not nome and len(candidatas) >= 2:
            nome = candidatas[-2]

        if not headline and candidatas:
            candidata_headline = candidatas[-1]

            if not eh_headline_invalida(
                candidata_headline
            ):
                headline = candidata_headline

    if eh_headline_invalida(headline):
        headline = ""

    return nome, headline


# ============================================================
# IDENTIFICAÇÃO DE PERÍODO, DURAÇÃO E LOCAL
# ============================================================

def parece_periodo(linha):
    """
    Identifica períodos profissionais com diferentes traços.

    Exemplos:
    jan de 2022 - o momento · 3 anos
    jan de 2022–o momento · 3 anos
    Jan 2022 - Present · 3 yrs
    """

    texto = normalizar_comparacao(
        normalizar_tracos(linha)
    )

    periodo = texto.split("·", 1)[0].strip()

    partes = re.split(
        r"\s*-\s*",
        periodo,
        maxsplit=1,
    )

    if len(partes) != 2:
        return False

    inicio, fim = partes

    inicio_tem_ano = bool(
        re.search(
            r"\b(?:19|20)\d{2}\b",
            inicio,
        )
    )

    fim_tem_ano = bool(
        re.search(
            r"\b(?:19|20)\d{2}\b",
            fim,
        )
    )

    fim_atual = any(
        termo in fim
        for termo in [
            "o momento",
            "atual",
            "presente",
            "present",
            "current",
        ]
    )

    return inicio_tem_ano and (
        fim_tem_ano or fim_atual
    )


def dividir_periodo(linha_periodo):
    """
    Divide período e duração.

    Exemplo:
    jan de 2023 - o momento · 2 anos 4 meses
    """

    linha_periodo = normalizar_tracos(
        linha_periodo
    )

    data_inicio = ""
    data_fim = ""
    duracao = ""

    if "·" in linha_periodo:
        periodo, duracao = linha_periodo.split(
            "·",
            1,
        )

        duracao = duracao.strip()

    else:
        periodo = linha_periodo

    partes = re.split(
        r"\s*-\s*",
        periodo,
        maxsplit=1,
    )

    if len(partes) == 2:
        data_inicio = partes[0].strip()
        data_fim = partes[1].strip()

    return data_inicio, data_fim, duracao


def eh_linha_de_duracao(linha):
    """
    Identifica durações completas e abreviadas.

    Exemplos:
    3 anos 2 meses
    11 meses
    6 a 7 m
    10 a 3 m
    4 yrs 2 mos
    """

    texto = normalizar_comparacao(linha)

    # Formato abreviado do LinkedIn:
    # 6 a 7 m = 6 anos e 7 meses
    if re.fullmatch(
        r"\d+\s*a(?:\s+\d+\s*m)?",
        texto,
    ):
        return True

    # Exemplo: 9 m
    if re.fullmatch(
        r"\d+\s*m",
        texto,
    ):
        return True

    padroes = [
        r"\b\d+\s+ano(?:s)?\b",
        r"\b\d+\s+mes(?:es)?\b",
        r"\b\d+\s+year(?:s)?\b",
        r"\b\d+\s+month(?:s)?\b",
        r"\b\d+\s+yr(?:s)?\b",
        r"\b\d+\s+mo(?:s)?\b",
    ]

    return any(
        re.search(padrao, texto)
        for padrao in padroes
    )


def eh_tipo_contrato(texto):
    """
    Verifica se o texto corresponde a um tipo de contrato.
    """

    texto_normalizado = normalizar_comparacao(texto)

    tipos_normalizados = {
        normalizar_comparacao(tipo)
        for tipo in TIPOS_CONTRATO
    }

    return texto_normalizado in tipos_normalizados


def eh_linha_local(linha):
    """
    Identifica localização ou modalidade de trabalho.
    """

    linha_normalizada = normalizar_comparacao(linha)

    tem_modalidade = any(
        normalizar_comparacao(modalidade)
        in linha_normalizada
        for modalidade in MODALIDADES_TRABALHO
    )

    if tem_modalidade:
        return True

    if (
        "," in linha
        and len(linha) <= 120
        and not parece_periodo(linha)
        and not linha.endswith(".")
    ):
        return True

    return False


def eh_mensagem_sem_experiencia(linha):
    """
    Identifica mensagens exibidas quando a pessoa
    não cadastrou experiências.
    """

    texto = normalizar_comparacao(linha)

    return (
        texto == "nada para ver por enquanto"
        or texto.startswith("a experiencia que ")
        or texto.startswith("the experience ")
        or "adicionar sera exibida aqui" in texto
        or "will be displayed here" in texto
    )


def parece_nome_de_cargo(texto):
    """
    Verifica se o texto possui palavras comuns de cargos.
    """

    texto_normalizado = normalizar_comparacao(texto)

    return any(
        normalizar_comparacao(palavra)
        in texto_normalizado
        for palavra in PALAVRAS_QUE_INDICAM_CARGO
    )


# ============================================================
# CRIAÇÃO DO REGISTRO
# ============================================================

def criar_registro_vazio(nome, link):
    """
    Cria uma linha vazia preservando nome e link.
    """

    return {
        "nome": nome,
        "link": link,
        "nome_linkedin": "",
        "headline": "",
        "empresa_atual": "",
        "tipo_contrato": "",
        "tempo_empresa": "",
        "local_empresa": "",
        "cargo_atual": "",
        "data_inicio": "",
        "data_fim": "",
        "duracao_cargo": "",
        "local_cargo": "",
        "descricao_cargo": "",
    }


# ============================================================
# LIMPEZA DO BLOCO DE EXPERIÊNCIA
# ============================================================

def limpar_bloco_experiencia(linhas):
    """
    Remove botões, títulos repetidos e linhas duplicadas.
    """

    resultado = []

    for linha in linhas:
        if eh_linha_ignorada(linha):
            continue

        linha_normalizada = normalizar_comparacao(
            linha
        )

        if linha_normalizada in TITULOS_EXPERIENCIA:
            continue

        if resultado and linha == resultado[-1]:
            continue

        resultado.append(linha)

    return resultado


# ============================================================
# EXTRAÇÃO DO ÚLTIMO CARGO
# ============================================================

def extrair_ultimo_cargo(
    texto,
    nome_planilha,
    link,
):
    """
    Extrai o primeiro registro da seção Experiência.

    Formatos principais reconhecidos:

    Cargo
    Empresa · Tipo de contrato
    Período

    Empresa
    Tipo de contrato · duração
    Local
    Cargo
    Período
    """

    linhas = limpar_linhas(texto)

    dados = criar_registro_vazio(
        nome=nome_planilha,
        link=link,
    )

    nome_linkedin, headline = pegar_nome_headline(
        linhas
    )

    dados["nome_linkedin"] = nome_linkedin
    dados["headline"] = headline

    indice_experiencia = localizar_experiencia(
        linhas
    )

    if indice_experiencia is None:
        return dados

    inicio = indice_experiencia + 1

    fim = localizar_fim_experiencia(
        linhas,
        inicio,
    )

    exp = limpar_bloco_experiencia(
        linhas[inicio:fim]
    )

    if not exp:
        return dados

    # Quando o perfil não possui experiência.
    if any(
        eh_mensagem_sem_experiencia(linha)
        for linha in exp[:5]
    ):
        return dados

    idx = 0

    primeira_linha = exp[0]

    segunda_linha = (
        exp[1]
        if len(exp) > 1
        else ""
    )

    # --------------------------------------------------------
    # FORMATO 1
    #
    # Cargo
    # Empresa · Tipo de contrato
    # Período
    # --------------------------------------------------------

    if (
        "·" in segunda_linha
        and not parece_periodo(segunda_linha)
    ):
        partes = [
            parte.strip()
            for parte in segunda_linha.split("·")
            if parte.strip()
        ]

        # Cargo / Empresa · Tempo integral
        if (
            len(partes) >= 2
            and eh_tipo_contrato(partes[1])
        ):
            dados["cargo_atual"] = primeira_linha
            dados["empresa_atual"] = partes[0]
            dados["tipo_contrato"] = partes[1]

            if (
                len(partes) >= 3
                and eh_linha_de_duracao(partes[2])
            ):
                dados["tempo_empresa"] = partes[2]

            idx = 2

        # ----------------------------------------------------
        # FORMATO 2
        #
        # Empresa
        # Tempo integral · 6 a 7 m
        # Local opcional
        # Cargo
        # Período
        # ----------------------------------------------------

        elif (
            len(partes) >= 2
            and eh_tipo_contrato(partes[0])
            and eh_linha_de_duracao(partes[1])
        ):
            dados["empresa_atual"] = primeira_linha
            dados["tipo_contrato"] = partes[0]
            dados["tempo_empresa"] = partes[1]

            idx = 2

        # Empresa / outro contrato · duração
        elif (
            len(partes) >= 2
            and eh_linha_de_duracao(partes[1])
        ):
            dados["empresa_atual"] = primeira_linha

            if eh_tipo_contrato(partes[0]):
                dados["tipo_contrato"] = partes[0]

            dados["tempo_empresa"] = partes[1]

            idx = 2

        else:
            dados["cargo_atual"] = primeira_linha
            dados["empresa_atual"] = partes[0]

            if (
                len(partes) >= 2
                and eh_tipo_contrato(partes[1])
            ):
                dados["tipo_contrato"] = partes[1]

            idx = 2

    # --------------------------------------------------------
    # FORMATO 3
    #
    # Cargo
    # Empresa
    # Período
    # --------------------------------------------------------

    elif (
        len(exp) > 2
        and parece_periodo(exp[2])
    ):
        dados["cargo_atual"] = primeira_linha
        dados["empresa_atual"] = segunda_linha

        idx = 2

    # --------------------------------------------------------
    # FORMATO 4
    #
    # Cargo
    # Período
    # --------------------------------------------------------

    elif parece_periodo(segunda_linha):
        dados["cargo_atual"] = primeira_linha
        idx = 1

    # --------------------------------------------------------
    # FORMATO ALTERNATIVO DE EMPRESA AGRUPADA
    # --------------------------------------------------------

    else:
        dados["empresa_atual"] = primeira_linha
        idx = 1

    # Caso a linha seguinte seja somente duração.
    if (
        idx < len(exp)
        and eh_linha_de_duracao(exp[idx])
        and not parece_periodo(exp[idx])
    ):
        dados["tempo_empresa"] = exp[idx]
        idx += 1

    # Local da empresa antes do cargo.
    if (
        idx < len(exp)
        and eh_linha_local(exp[idx])
        and not parece_periodo(exp[idx])
    ):
        dados["local_empresa"] = exp[idx]
        idx += 1

    # Procura o cargo verdadeiro.
    while (
        idx < len(exp)
        and not dados["cargo_atual"]
    ):
        linha = exp[idx]

        if eh_linha_ignorada(linha):
            idx += 1
            continue

        if eh_mensagem_sem_experiencia(linha):
            return dados

        if parece_periodo(linha):
            break

        if (
            eh_linha_de_duracao(linha)
            and not parece_periodo(linha)
        ):
            idx += 1
            continue

        if eh_linha_local(linha):
            idx += 1
            continue

        if eh_tipo_contrato(linha):
            if not dados["tipo_contrato"]:
                dados["tipo_contrato"] = linha

            idx += 1
            continue

        dados["cargo_atual"] = linha
        idx += 1
        break

    # Período do cargo.
    if idx < len(exp) and parece_periodo(exp[idx]):
        (
            data_inicio,
            data_fim,
            duracao,
        ) = dividir_periodo(exp[idx])

        dados["data_inicio"] = data_inicio
        dados["data_fim"] = data_fim
        dados["duracao_cargo"] = duracao

        idx += 1

    # Local do cargo.
    if (
        idx < len(exp)
        and eh_linha_local(exp[idx])
    ):
        dados["local_cargo"] = exp[idx]
        idx += 1

    # Descrição do cargo.
    descricao = []

    while idx < len(exp):
        linha = exp[idx]
        linha_normalizada = normalizar_comparacao(
            linha
        )

        if linha_normalizada.startswith(
            "competencias:"
        ):
            break

        if linha_normalizada.startswith(
            "skills:"
        ):
            break

        if eh_linha_ignorada(linha):
            idx += 1
            continue

        # Próximo cargo seguido de período.
        if (
            idx + 1 < len(exp)
            and parece_periodo(exp[idx + 1])
        ):
            break

        # Próximo cargo, empresa e período.
        if (
            idx + 2 < len(exp)
            and parece_periodo(exp[idx + 2])
        ):
            break

        descricao.append(linha)
        idx += 1

    dados["descricao_cargo"] = " ".join(
        descricao
    ).strip()

    return dados


# ============================================================
# CORREÇÕES PÓS-EXTRAÇÃO
# ============================================================

def separar_contrato_embutido_empresa(dados):
    """
    Corrige empresas salvas assim:

    GOVERNANÇABRASIL - GOVBR · Tempo integral

    Resultado:
    empresa = GOVERNANÇABRASIL - GOVBR
    tipo_contrato = Tempo integral
    """

    empresa = (
        dados.get("empresa_atual", "") or ""
    ).strip()

    if "·" not in empresa:
        return dados

    partes = [
        parte.strip()
        for parte in empresa.split("·")
        if parte.strip()
    ]

    if not partes:
        return dados

    empresa_limpa = partes[0]

    for parte in partes[1:]:
        if (
            eh_tipo_contrato(parte)
            and not dados["tipo_contrato"]
        ):
            dados["tipo_contrato"] = parte

        elif (
            eh_linha_de_duracao(parte)
            and not dados["tempo_empresa"]
        ):
            dados["tempo_empresa"] = parte

    dados["empresa_atual"] = empresa_limpa

    return dados


def corrigir_campos_deslocados(dados):
    """
    Corrige contrato e duração salvos em colunas erradas.
    """

    empresa = (
        dados.get("empresa_atual", "") or ""
    ).strip()

    tipo = (
        dados.get("tipo_contrato", "") or ""
    ).strip()

    cargo = (
        dados.get("cargo_atual", "") or ""
    ).strip()

    # Caso a duração tenha sido salva como tipo de contrato.
    if (
        tipo
        and eh_linha_de_duracao(tipo)
        and not dados["tempo_empresa"]
    ):
        dados["tempo_empresa"] = tipo
        dados["tipo_contrato"] = ""
        tipo = ""

    # Caso "Tempo integral" tenha sido salvo como empresa.
    if empresa and eh_tipo_contrato(empresa):
        if not dados["tipo_contrato"]:
            dados["tipo_contrato"] = empresa

        # Se o cargo atual parece uma empresa, move para empresa.
        if cargo and not parece_nome_de_cargo(cargo):
            dados["empresa_atual"] = cargo
            dados["cargo_atual"] = ""
        else:
            dados["empresa_atual"] = ""

    return dados


def corrigir_inversao_empresa_cargo(dados):
    """
    Corrige casos como:

    empresa = Gerente PJ
    cargo = Sicredi Ibiraiaras RS/MG
    """

    empresa = (
        dados.get("empresa_atual", "") or ""
    ).strip()

    cargo = (
        dados.get("cargo_atual", "") or ""
    ).strip()

    if not empresa or not cargo:
        return dados

    empresa_parece_cargo = parece_nome_de_cargo(
        empresa
    )

    cargo_parece_cargo = parece_nome_de_cargo(
        cargo
    )

    if (
        empresa_parece_cargo
        and not cargo_parece_cargo
    ):
        print(
            "Correção automática: "
            "empresa e cargo estavam invertidos."
        )

        dados["empresa_atual"] = cargo
        dados["cargo_atual"] = empresa

    return dados


def limpar_mensagem_sem_experiencia(dados):
    """
    Remove mensagens do LinkedIn salvas como empresa ou cargo.
    """

    empresa = dados.get("empresa_atual", "") or ""
    cargo = dados.get("cargo_atual", "") or ""

    if (
        eh_mensagem_sem_experiencia(empresa)
        or eh_mensagem_sem_experiencia(cargo)
    ):
        dados["empresa_atual"] = ""
        dados["tipo_contrato"] = ""
        dados["tempo_empresa"] = ""
        dados["local_empresa"] = ""
        dados["cargo_atual"] = ""
        dados["data_inicio"] = ""
        dados["data_fim"] = ""
        dados["duracao_cargo"] = ""
        dados["local_cargo"] = ""
        dados["descricao_cargo"] = ""

    return dados


def aplicar_correcoes(dados):
    """
    Executa todas as correções depois da extração.
    """

    dados = separar_contrato_embutido_empresa(
        dados
    )

    dados = corrigir_campos_deslocados(
        dados
    )

    dados = corrigir_inversao_empresa_cargo(
        dados
    )

    dados = limpar_mensagem_sem_experiencia(
        dados
    )

    if eh_headline_invalida(
        dados.get("headline", "")
    ):
        dados["headline"] = ""

    return dados


# ============================================================
# VERIFICAÇÕES DA PÁGINA
# ============================================================

def pagina_parece_login_ou_bloqueio(texto):
    """
    Verifica se o LinkedIn mostrou login ou bloqueio.
    """

    texto_normalizado = normalizar_comparacao(
        texto
    )

    termos = [
        "entre para continuar",
        "entrar no linkedin",
        "sign in",
        "join linkedin",
        "faca login",
        "verificacao de seguranca",
        "security verification",
        "checkpoint",
        "challenge",
        "captcha",
        "acesso negado",
        "access denied",
    ]

    return any(
        normalizar_comparacao(termo)
        in texto_normalizado
        for termo in termos
    )


# ============================================================
# EXECUÇÃO
# ============================================================

resultados = []

delimitador = identificar_delimitador(
    ARQUIVO_ENTRADA
)

with open(
    ARQUIVO_ENTRADA,
    "r",
    encoding="utf-8-sig",
    newline="",
) as arquivo:

    leitor = csv.DictReader(
        arquivo,
        delimiter=delimitador,
    )

    if not leitor.fieldnames:
        raise ValueError(
            "O arquivo de entrada está vazio "
            "ou não possui cabeçalho."
        )

    coluna_nome, coluna_link = localizar_colunas(
        leitor.fieldnames
    )

    for indice, linha in enumerate(
        leitor,
        start=1,
    ):

        nome_planilha = (
            linha.get(coluna_nome, "") or ""
        ).strip()

        link_original = (
            linha.get(coluna_link, "") or ""
        ).strip()

        link = preparar_link(link_original)

        print()
        print("=" * 80)
        print(f"PERFIL {indice}")
        print(f"Nome da planilha: {nome_planilha}")
        print(f"Link: {link}")
        print("=" * 80)

        if not link:
            print("Registro sem link.")

            dados = criar_registro_vazio(
                nome=nome_planilha,
                link="",
            )

            resultados.append(dados)
            salvar_resultados(resultados)
            continue

        if not eh_link_linkedin(link):
            print(
                "O endereço não é um perfil do LinkedIn."
            )

            dados = criar_registro_vazio(
                nome=nome_planilha,
                link=link,
            )

            resultados.append(dados)
            salvar_resultados(resultados)
            continue

        try:
            texto = carregar_texto_perfil(
                link=link,
                timeout=TEMPO_MAXIMO_CARREGAMENTO,
            )

            print(f"URL aberta: {driver.current_url}")
            print(f"Título: {driver.title}")

            linhas_pagina = limpar_linhas(texto)

            indice_experiencia = localizar_experiencia(
                linhas_pagina
            )

            if indice == 1:
                caminho_debug = salvar_debug(
                    indice=indice,
                    nome=nome_planilha,
                    texto=texto,
                )

                print(
                    f"Diagnóstico salvo em: "
                    f"{caminho_debug}"
                )

            if pagina_parece_login_ou_bloqueio(
                texto
            ):
                print(
                    "AVISO: a página parece ser de login, "
                    "verificação ou bloqueio."
                )

                caminho_debug = salvar_debug(
                    indice=indice,
                    nome=nome_planilha,
                    texto=texto,
                )

                print(
                    f"Confira o diagnóstico: "
                    f"{caminho_debug}"
                )

            elif indice_experiencia is None:
                print(
                    "A seção Experiência não foi encontrada."
                )

                print(
                    "Primeiros 500 caracteres visualizados:"
                )

                print(texto[:500])

                caminho_debug = salvar_debug(
                    indice=indice,
                    nome=nome_planilha,
                    texto=texto,
                )

                print(
                    f"Confira o diagnóstico: "
                    f"{caminho_debug}"
                )

            dados = extrair_ultimo_cargo(
                texto=texto,
                nome_planilha=nome_planilha,
                link=link,
            )

            dados = aplicar_correcoes(dados)

            # Salva diagnóstico quando existe experiência,
            # mas o cargo continua não identificado.
            if (
                indice_experiencia is not None
                and not dados["cargo_atual"]
                and not pagina_parece_login_ou_bloqueio(
                    texto
                )
            ):
                print(
                    "AVISO: cargo não identificado. "
                    "Foi salvo um arquivo de diagnóstico."
                )

                caminho_debug = salvar_debug(
                    indice=indice,
                    nome=nome_planilha,
                    texto=texto,
                )

                print(
                    f"Diagnóstico: {caminho_debug}"
                )

            resultados.append(dados)

            salvar_resultados(resultados)

            print("-" * 80)
            print(
                f"Nome LinkedIn: "
                f"{dados['nome_linkedin'] or 'Não identificado'}"
            )
            print(
                f"Headline: "
                f"{dados['headline'] or 'Não identificada'}"
            )
            print(
                f"Empresa: "
                f"{dados['empresa_atual'] or 'Não identificada'}"
            )
            print(
                f"Tipo de contrato: "
                f"{dados['tipo_contrato'] or 'Não identificado'}"
            )
            print(
                f"Tempo na empresa: "
                f"{dados['tempo_empresa'] or 'Não identificado'}"
            )
            print(
                f"Cargo: "
                f"{dados['cargo_atual'] or 'Não identificado'}"
            )
            print("Resultado salvo.")

        except Exception as erro:
            print(
                f"Erro ao processar o perfil: "
                f"{type(erro).__name__}: {erro}"
            )

            try:
                texto_erro = driver.find_element(
                    By.TAG_NAME,
                    "body",
                ).text
            except Exception:
                texto_erro = ""

            caminho_debug = salvar_debug(
                indice=indice,
                nome=nome_planilha,
                texto=texto_erro,
            )

            print(
                f"Diagnóstico do erro salvo em: "
                f"{caminho_debug}"
            )

            dados = criar_registro_vazio(
                nome=nome_planilha,
                link=link,
            )

            resultados.append(dados)
            salvar_resultados(resultados)

        time.sleep(TEMPO_ENTRE_PERFIS)


print()
print("=" * 80)
print("COLETA CONCLUÍDA")
print(f"Arquivo salvo em: {ARQUIVO_SAIDA}")
print(f"Quantidade de registros: {len(resultados)}")
print("=" * 80)

input("Pressione ENTER para finalizar...")