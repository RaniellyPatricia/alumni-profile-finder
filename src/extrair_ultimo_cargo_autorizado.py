from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import csv
import time
import os

ARQUIVO_LINKS = "data/raw/links.csv"
ARQUIVO_SAIDA = "data/processed/ultimo_cargo_linkedin.csv"

os.makedirs("data/processed", exist_ok=True)

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Chrome(options=options)


def limpar_linhas(texto):
    return [linha.strip() for linha in texto.split("\n") if linha.strip()]


def pegar_nome_headline(linhas):
    for i, linha in enumerate(linhas):
        if linha == "Reative Premium: 50% de desconto" and i + 2 < len(linhas):
            return linhas[i + 1], linhas[i + 2]

    for i, linha in enumerate(linhas):
        if linha == "Experiência" and i >= 2:
            return linhas[i - 2], linhas[i - 1]

    return "", ""


def parece_periodo(linha):
    linha_lower = linha.lower()

    return " - " in linha and (
        " de " in linha_lower
        or "o momento" in linha_lower
        or "atual" in linha_lower
        or "present" in linha_lower
    )


def dividir_periodo(linha_periodo):
    data_inicio = ""
    data_fim = ""
    duracao = ""

    if "·" in linha_periodo:
        periodo, duracao = linha_periodo.split("·", 1)
        duracao = duracao.strip()
    else:
        periodo = linha_periodo

    if " - " in periodo:
        data_inicio, data_fim = periodo.split(" - ", 1)
        data_inicio = data_inicio.strip()
        data_fim = data_fim.strip()

    return data_inicio, data_fim, duracao


def eh_linha_de_duracao(linha):
    linha_lower = linha.lower()

    palavras_duracao = [
        "ano",
        "anos",
        "mês",
        "meses",
        "month",
        "months",
        "year",
        "years",
    ]

    return any(palavra in linha_lower for palavra in palavras_duracao)


def eh_linha_local(linha):
    tipos_local = [
        "Remoto",
        "No local",
        "Híbrido",
        "Remote",
        "On-site",
        "Hybrid",
    ]

    tem_tipo_local = any(tipo in linha for tipo in tipos_local)
    parece_localizacao = "," in linha

    return tem_tipo_local or parece_localizacao


def extrair_ultimo_cargo(texto, link):
    linhas = limpar_linhas(texto)

    nome, headline = pegar_nome_headline(linhas)

    dados = {
        "link": link,
        "nome": nome,
        "headline": headline,
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

    if "Experiência" not in linhas:
        return dados

    inicio = linhas.index("Experiência") + 1

    fim = len(linhas)
    for marcador in ["Idioma do perfil", "Sobre", "Formação acadêmica", "Competências"]:
        if marcador in linhas[inicio:]:
            pos = linhas.index(marcador)
            fim = min(fim, pos)

    exp = linhas[inicio:fim]

    if not exp:
        return dados

    dados["empresa_atual"] = exp[0]

    idx = 1

    # Exemplo: "Estágio · 2 a 1 m" ou "Tempo integral · 3 a 7 m"
    if idx < len(exp) and "·" in exp[idx] and not parece_periodo(exp[idx]):
        partes = [p.strip() for p in exp[idx].split("·")]

        if len(partes) >= 1:
            dados["tipo_contrato"] = partes[0]

        if len(partes) >= 2:
            dados["tempo_empresa"] = partes[1]

        idx += 1

    # Caso apareça só duração da empresa, tipo: "2 anos 1 mês"
    if idx < len(exp) and eh_linha_de_duracao(exp[idx]):
        dados["tempo_empresa"] = exp[idx]
        idx += 1

    # Local/modelo da empresa
    if idx < len(exp) and eh_linha_local(exp[idx]):
        dados["local_empresa"] = exp[idx]
        idx += 1

    # Pula linhas que não são cargo
    while idx < len(exp):
        linha = exp[idx]

        if linha in ["Aprimorar com IA", "Enviar mensagem"]:
            idx += 1
            continue

        if eh_linha_de_duracao(linha):
            idx += 1
            continue

        if eh_linha_local(linha):
            idx += 1
            continue

        break

    # Primeiro cargo real
    if idx < len(exp):
        dados["cargo_atual"] = exp[idx]
        idx += 1

    # Período do cargo
    if idx < len(exp) and parece_periodo(exp[idx]):
        data_inicio, data_fim, duracao = dividir_periodo(exp[idx])

        dados["data_inicio"] = data_inicio
        dados["data_fim"] = data_fim
        dados["duracao_cargo"] = duracao

        idx += 1

    # Local do cargo
    if idx < len(exp) and eh_linha_local(exp[idx]):
        dados["local_cargo"] = exp[idx]
        idx += 1

    descricao = []

    while idx < len(exp):
        linha = exp[idx]

        if linha.startswith("Competências:"):
            break

        if linha in ["Aprimorar com IA", "Enviar mensagem"]:
            idx += 1
            continue

        # Para antes do próximo cargo
        if idx + 1 < len(exp) and parece_periodo(exp[idx + 1]):
            break

        descricao.append(linha)
        idx += 1

    dados["descricao_cargo"] = " ".join(descricao).strip()

    return dados


resultados = []

with open(ARQUIVO_LINKS, "r", encoding="utf-8-sig") as arquivo:
    leitor = csv.DictReader(arquivo)

    for i, linha in enumerate(leitor, start=1):
        link = linha["link"].strip()

        print(f"Acessando perfil {i}: {link}")

        driver.get(link)
        time.sleep(5)

        texto = driver.find_element(By.TAG_NAME, "body").text

        dados = extrair_ultimo_cargo(texto, link)
        resultados.append(dados)

        print(
            f"Extraído: {dados['nome']} | "
            f"{dados['cargo_atual']} | "
            f"{dados['empresa_atual']}"
        )


colunas = [
    "link",
    "nome",
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

with open(ARQUIVO_SAIDA, "w", encoding="utf-8-sig", newline="") as arquivo:
    escritor = csv.DictWriter(arquivo, fieldnames=colunas)
    escritor.writeheader()
    escritor.writerows(resultados)

print(f"Arquivo salvo em: {ARQUIVO_SAIDA}")

input("Pressione ENTER para finalizar...")