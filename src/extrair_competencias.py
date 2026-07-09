from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import csv
import os
import re
import time
import unicodedata


ARQUIVO_LINKS = "data/raw/linkscompetencias.csv"
ARQUIVO_SAIDA = "data/processed/competencias_linkedin.csv"

os.makedirs("data/processed", exist_ok=True)


options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Chrome(options=options)


def normalizar(texto):
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )

    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def limpar_linhas(texto):
    return [
        linha.strip()
        for linha in str(texto).split("\n")
        if linha.strip()
    ]


def montar_link_competencias(link):
    link = link.strip()

    if "/details/skills" in link:
        return link

    if "/details/experience" in link:
        return link.replace("/details/experience/", "/details/skills/")

    if link.endswith("/"):
        return link + "details/skills/"

    return link + "/details/skills/"


def nome_pelo_link(link):
    try:
        parte = link.split("/in/")[1].split("/")[0]
        parte = parte.split("-")
        nomes = []

        for item in parte:
            if item and not item.isdigit() and not re.search(r"\d", item):
                nomes.append(item.capitalize())

        return " ".join(nomes)
    except Exception:
        return ""


def pegar_nome(link):
    """
    Tenta pegar o nome pelo título da aba.
    Se não conseguir, usa o nome montado pelo link.
    """

    try:
        titulo = driver.title.strip()

        if titulo and "linkedin" in titulo.lower():
            titulo = titulo.replace("| LinkedIn", "").replace("LinkedIn", "")
            titulo = titulo.strip(" |")

            if titulo:
                return titulo
    except Exception:
        pass

    return nome_pelo_link(link)


def pegar_linhas_main():
    try:
        texto = driver.find_element(By.TAG_NAME, "main").text
    except Exception:
        texto = driver.find_element(By.TAG_NAME, "body").text

    return limpar_linhas(texto)


def eh_ruido(linha):
    linha_n = normalizar(linha)

    ruidos_exatos = {
        "competencias",
        "todos",
        "conhecimento do setor",
        "ferramentas e tecnologias",
        "competencias interpessoais",
        "outras competencias",
        "idiomas",
        "sobre",
        "acessibilidade",
        "solucoes de talentos",
        "diretrizes da comunidade",
        "carreiras",
        "solucoes de marketing",
        "termos e privacidade",
        "preferencias de anuncios",
        "publicidade",
        "solucoes de vendas",
        "dispositivo movel",
        "pequenas empresas",
        "central de seguranca",
        "duvidas?",
        "acesse a nossa central de ajuda.",
        "gerencie sua conta e privacidade",
        "acesse suas configuracoes.",
        "visibilidade da recomendacao",
        "saiba mais sobre os conteudos recomendados.",
        "selecionar idioma",
        "editar",
        "adicionar",
        "salvar",
        "cancelar",
        "recomendar competencia",
        "mostrar mais",
        "mostrar menos",
        "exibir mais",
        "exibir menos",
        "ver mais",
        "ver menos",
    }

    if linha_n in ruidos_exatos:
        return True

    ruidos_parciais = [
        "linkedin corporation",
        "central de ajuda",
        "politica de privacidade",
        "contrato do usuario",
        "opcoes de anuncios",
        "por que estou vendo este anuncio",
        "gerencie suas preferencias",
        "ocultar ou denunciar",
        "recomendacao de competencia",
        "recomendacoes de competencia",
        "endossado por",
        "endossos",
        "exibir todos os",
        "©",
        "http",
        "www",
    ]

    for ruido in ruidos_parciais:
        if ruido in linha_n:
            return True

    if linha_n.isdigit():
        return True

    if len(linha_n) <= 1:
        return True

    if len(linha_n) > 160:
        return True

    return False


def extrair_area_de_competencias(linhas):
    filtros = {
        "todos",
        "conhecimento do setor",
        "ferramentas e tecnologias",
        "competencias interpessoais",
        "outras competencias",
        "idiomas",
    }

    ultimo_filtro = None

    for i, linha in enumerate(linhas):
        if normalizar(linha) in filtros:
            ultimo_filtro = i

    if ultimo_filtro is None:
        inicio = 0
    else:
        inicio = ultimo_filtro + 1

    fim = len(linhas)

    for i in range(inicio, len(linhas)):
        if normalizar(linhas[i]) == "sobre":
            fim = i
            break

    return linhas[inicio:fim]


def coletar_competencias_rolando():
    """
    Coleta todas as linhas candidatas a competência que aparecem
    conforme a página vai sendo rolada.
    """

    todas = []
    vistos = set()
    passos_sem_novidade = 0

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

    for passo in range(15):
        print(f"    Capturando passo {passo + 1}...")

        linhas = pegar_linhas_main()
        linhas_area = extrair_area_de_competencias(linhas)

        linhas_validas = [
            linha
            for linha in linhas_area
            if not eh_ruido(linha)
        ]

        novas = 0

        for linha in linhas_validas:
            chave = normalizar(linha)

            if chave and chave not in vistos:
                vistos.add(chave)
                todas.append(linha)
                novas += 1

        print(f"    Novas linhas candidatas: {novas}")
        print(f"    Total acumulado: {len(todas)}")

        if novas == 0:
            passos_sem_novidade += 1
        else:
            passos_sem_novidade = 0

        if passos_sem_novidade >= 3:
            print("    Sem novas competências por 3 passos. Indo para o próximo perfil.")
            break

        driver.execute_script("window.scrollBy(0, 700);")
        time.sleep(1)

        driver.execute_script("""
            const main = document.querySelector('main');
            if (main) {
                main.scrollTop = main.scrollTop + 700;
            }
        """)
        time.sleep(1)

        driver.execute_script("""
            const elementos = Array.from(document.querySelectorAll('*'));
            elementos.forEach(el => {
                if (el.scrollHeight > el.clientHeight) {
                    el.scrollTop = el.scrollTop + 700;
                }
            });
        """)
        time.sleep(2)

    return todas


def extrair_competencias_do_perfil(link):
    driver.get(link)
    time.sleep(6)

    nome = pegar_nome(link)

    competencias = coletar_competencias_rolando()

    competencias = list(dict.fromkeys(competencias))

    if competencias:
        status = "competências candidatas extraídas"
    else:
        status = "nenhuma competência encontrada"

    return {
        "link": link,
        "nome": nome,
        "lista_competencias": competencias,
        "quantidade_competencias": len(competencias),
        "status": status,
    }


def ler_links():
    links = []

    with open(ARQUIVO_LINKS, "r", encoding="utf-8-sig") as arquivo:
        leitor = csv.DictReader(arquivo)

        for linha in leitor:
            link = linha["link"].strip()

            if link:
                links.append(montar_link_competencias(link))

    return links


def salvar_resultados(resultados):
    colunas = [
        "link",
        "nome",
        "lista_competencias",
        "quantidade_competencias",
        "status",
    ]

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()

        for resultado in resultados:
            linha = resultado.copy()
            linha["lista_competencias"] = "; ".join(resultado["lista_competencias"])
            escritor.writerow(linha)


def main():
    print("=" * 70)
    print("EXTRAÇÃO DE COMPETÊNCIAS - VÁRIOS PERFIS")
    print("=" * 70)

    links = ler_links()

    print(f"Total de links encontrados: {len(links)}")

    resultados = []

    for i, link in enumerate(links, start=1):
        print("\n" + "=" * 70)
        print(f"Perfil {i} de {len(links)}")
        print(f"Link: {link}")
        print("=" * 70)

        try:
            resultado = extrair_competencias_do_perfil(link)
            resultados.append(resultado)

            print(f"Nome: {resultado['nome']}")
            print(f"Quantidade: {resultado['quantidade_competencias']}")
            print(f"Status: {resultado['status']}")

            if resultado["lista_competencias"]:
                print("Competências candidatas:")
                for competencia in resultado["lista_competencias"]:
                    print(f"- {competencia}")

        except Exception as erro:
            print(f"Erro ao processar perfil: {erro}")

            resultados.append(
                {
                    "link": link,
                    "nome": "",
                    "lista_competencias": [],
                    "quantidade_competencias": 0,
                    "status": f"erro: {erro}",
                }
            )

    salvar_resultados(resultados)

    print("\n" + "=" * 70)
    print("FINALIZADO")
    print("=" * 70)
    print(f"Arquivo salvo em: {ARQUIVO_SAIDA}")

    input("\nPressione ENTER para finalizar...")


if __name__ == "__main__":
    main()