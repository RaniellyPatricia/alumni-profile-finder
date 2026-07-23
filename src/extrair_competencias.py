from pathlib import Path
import csv
import re
import time
import unicodedata

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
ARQUIVO_LINKS = RAIZ_PROJETO / "data" / "raw" / "linkscompetencias.csv"
ARQUIVO_SAIDA = RAIZ_PROJETO / "data" / "processed" / "competencias_linkedin.csv"
PASTA_DEBUG = RAIZ_PROJETO / "data" / "processed" / "debug"

LIMITE_PERFIS = 50
REPROCESSAR_TODOS = True
MAX_ROLAGENS = 30
PAUSA_ENTRE_PERFIS = 3

ARQUIVO_SAIDA.parent.mkdir(parents=True, exist_ok=True)
PASTA_DEBUG.mkdir(parents=True, exist_ok=True)

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=options)
espera = WebDriverWait(driver, 25)


def normalizar(texto):
    texto = str(texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    return re.sub(r"\s+", " ", texto).strip()


def montar_link_competencias(link):
    link = str(link or "").strip().split("?")[0].split("#")[0]

    if "/details/skills" in link:
        return link.rstrip("/") + "/"

    if "/details/experience" in link:
        return (
            link.replace("/details/experience/", "/details/skills/")
            .replace("/details/experience", "/details/skills/")
        )

    if "/in/" in link:
        return link.rstrip("/") + "/details/skills/"

    return link


def validar_pagina():
    url = driver.current_url.lower()

    if any(
        trecho in url
        for trecho in ["/login", "/checkpoint", "/authwall", "/uas/login"]
    ):
        raise RuntimeError(
            "O LinkedIn abriu login ou verificação. "
            "Entre manualmente no Chrome conectado à porta 9222."
        )


def clicar_em_todos():
    localizado = driver.execute_script(r"""
        function normalizar(texto) {
            return (texto || "")
                .normalize("NFD")
                .replace(/[\u0300-\u036f]/g, "")
                .trim()
                .toLowerCase();
        }

        const botoes = Array.from(document.querySelectorAll("nav button, button"));

        const todos = botoes.find(botao => {
            const retangulo = botao.getBoundingClientRect();

            return (
                normalizar(botao.innerText) === "todos" &&
                retangulo.width > 0 &&
                retangulo.height > 0
            );
        });

        if (!todos) {
            return false;
        }

        if (todos.getAttribute("aria-current") !== "true") {
            todos.click();
        }

        return true;
    """)

    print(f"    Aba 'Todos' localizada: {localizado}")
    time.sleep(2)


def voltar_ao_topo():
    for _ in range(3):
        driver.execute_script(r"""
            window.scrollTo(0, 0);

            if (document.scrollingElement) {
                document.scrollingElement.scrollTop = 0;
            }

            const main = document.querySelector("main#workspace");

            if (main) {
                main.scrollTop = 0;
            }
        """)
        time.sleep(1)


def coletar_cards_carregados():
    """
    O HTML real do LinkedIn mostra que cada competência usa um contêiner
    cujo ID começa com "com.linkedin.sdui.profile.skill(".
    Os divisores terminam em "-divider" e são ignorados.
    O primeiro p span de cada card contém o nome da competência.
    """
    return driver.execute_script(r"""
        const cards = Array.from(
            document.querySelectorAll(
                '[id^="com.linkedin.sdui.profile.skill("]'
            )
        ).filter(card => !card.id.endsWith("-divider"));

        const resultado = [];

        for (const card of cards) {
            const titulo = card.querySelector("p span");

            if (!titulo) {
                continue;
            }

            const texto = (
                titulo.innerText ||
                titulo.textContent ||
                ""
            ).replace(/\s+/g, " ").trim();

            if (texto) {
                resultado.push({
                    id: card.id,
                    competencia: texto
                });
            }
        }

        return resultado;
    """)


def rolar():
    return driver.execute_script(r"""
        const pagina =
            document.scrollingElement ||
            document.documentElement;

        const main = document.querySelector("main#workspace");
        const deslocamento = Math.max(500, window.innerHeight * 0.7);

        const paginaAntes = pagina.scrollTop;
        const mainAntes = main ? main.scrollTop : 0;

        pagina.scrollTop += deslocamento;

        if (main && main.scrollHeight > main.clientHeight + 50) {
            main.scrollTop += deslocamento;
        }

        return {
            pagina_antes: paginaAntes,
            pagina_depois: pagina.scrollTop,
            main_antes: mainAntes,
            main_depois: main ? main.scrollTop : 0
        };
    """)


def coletar_competencias_rolando():
    voltar_ao_topo()
    clicar_em_todos()

    competencias = []
    vistos = set()
    sem_movimento = 0

    for passo in range(1, MAX_ROLAGENS + 1):
        cards = coletar_cards_carregados()
        novas = 0

        for card in cards:
            competencia = str(card.get("competencia", "")).strip()
            chave = normalizar(competencia)

            if chave and chave not in vistos:
                vistos.add(chave)
                competencias.append(competencia)
                novas += 1
                print(f"      Competência: {competencia}")

        print(
            f"    Passo {passo}: "
            f"cards no DOM={len(cards)} | "
            f"novas={novas} | "
            f"total={len(competencias)}"
        )

        estado = rolar()

        houve_movimento = (
            estado["pagina_depois"] != estado["pagina_antes"]
            or estado["main_depois"] != estado["main_antes"]
        )

        if houve_movimento:
            sem_movimento = 0
        else:
            sem_movimento += 1

        time.sleep(1.5)

        if sem_movimento >= 2:
            break

    return competencias


def salvar_debug(nome):
    nome_base = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        normalizar(nome),
    ).strip("_") or "perfil"

    (PASTA_DEBUG / f"{nome_base}.html").write_text(
        driver.page_source,
        encoding="utf-8",
    )

    driver.save_screenshot(
        str(PASTA_DEBUG / f"{nome_base}.png")
    )


def detectar_delimitador(caminho):
    with caminho.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as arquivo:
        amostra = arquivo.read(4096)

    try:
        return csv.Sniffer().sniff(
            amostra,
            delimiters=";,",
        ).delimiter
    except csv.Error:
        return ";"


def ler_perfis():
    delimitador = detectar_delimitador(ARQUIVO_LINKS)
    perfis = []

    with ARQUIVO_LINKS.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as arquivo:
        leitor = csv.DictReader(
            arquivo,
            delimiter=delimitador,
        )

        print(f"Delimitador detectado: {delimitador!r}")
        print(f"Colunas encontradas: {leitor.fieldnames}")

        for linha in leitor:
            nome = (linha.get("nome") or linha.get("Nome") or "").strip()
            link = (linha.get("link") or linha.get("Link") or "").strip()

            if link:
                perfis.append(
                    {
                        "nome": nome,
                        "link": montar_link_competencias(link),
                    }
                )

    return perfis


def carregar_resultados_existentes():
    if REPROCESSAR_TODOS or not ARQUIVO_SAIDA.exists():
        return []

    resultados = []

    with ARQUIVO_SAIDA.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")

        for linha in leitor:
            competencias = [
                item.strip()
                for item in linha.get("lista_competencias", "").split(" | ")
                if item.strip()
            ]

            resultados.append(
                {
                    "nome": linha.get("nome", ""),
                    "link": linha.get("link", ""),
                    "lista_competencias": competencias,
                    "quantidade_competencias": int(
                        linha.get("quantidade_competencias", 0) or 0
                    ),
                    "status": linha.get("status", ""),
                }
            )

    return resultados


def salvar_resultados(resultados):
    colunas = [
        "nome",
        "link",
        "lista_competencias",
        "quantidade_competencias",
        "status",
    ]

    with ARQUIVO_SAIDA.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=colunas,
            delimiter=";",
        )
        escritor.writeheader()

        for resultado in resultados:
            linha = resultado.copy()
            linha["lista_competencias"] = " | ".join(
                resultado["lista_competencias"]
            )
            escritor.writerow(linha)


def extrair_competencias_do_perfil(nome, link):
    driver.get(link)

    try:
        espera.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "main#workspace")
            )
        )
    except TimeoutException:
        raise RuntimeError("A área principal do perfil não carregou.")

    validar_pagina()

    try:
        espera.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="lazy-column"]')
            )
        )
    except TimeoutException:
        pass

    time.sleep(2)

    print(f"    URL aberta: {driver.current_url}")
    print(f"    Título: {driver.title}")

    competencias = coletar_competencias_rolando()

    if competencias:
        status = "competências candidatas extraídas"
    else:
        status = "nenhuma competência encontrada"
        salvar_debug(nome)

    return {
        "nome": nome,
        "link": link,
        "lista_competencias": competencias,
        "quantidade_competencias": len(competencias),
        "status": status,
    }


def main():
    print("=" * 72)
    print("EXTRAÇÃO DE COMPETÊNCIAS DO LINKEDIN - CARDS REAIS")
    print("=" * 72)

    perfis = ler_perfis()

    if LIMITE_PERFIS is not None:
        perfis = perfis[:LIMITE_PERFIS]

    resultados = carregar_resultados_existentes()
    links_processados = {item["link"] for item in resultados}

    pendentes = [
        perfil
        for perfil in perfis
        if perfil["link"] not in links_processados
    ]

    print(f"Total no arquivo: {len(perfis)}")
    print(f"Resultados reaproveitados: {len(resultados)}")
    print(f"Pendentes: {len(pendentes)}")

    for indice, perfil in enumerate(pendentes, start=1):
        nome = perfil["nome"]
        link = perfil["link"]

        print("\n" + "=" * 72)
        print(f"Perfil {indice} de {len(pendentes)}")
        print(f"Nome: {nome}")
        print(f"Link: {link}")
        print("=" * 72)

        try:
            resultado = extrair_competencias_do_perfil(nome, link)
        except Exception as erro:
            print(f"Erro ao processar o perfil: {erro}")

            resultado = {
                "nome": nome,
                "link": link,
                "lista_competencias": [],
                "quantidade_competencias": 0,
                "status": f"erro: {erro}",
            }

            salvar_debug(nome)

        resultados = [
            item
            for item in resultados
            if item["link"] != link
        ]

        resultados.append(resultado)
        salvar_resultados(resultados)

        print(
            f"Quantidade encontrada: "
            f"{resultado['quantidade_competencias']}"
        )
        print(f"Status: {resultado['status']}")

        for competencia in resultado["lista_competencias"]:
            print(f"  - {competencia}")

        time.sleep(PAUSA_ENTRE_PERFIS)

    print("\n" + "=" * 72)
    print("PROCESSAMENTO FINALIZADO")
    print("=" * 72)
    print(f"Arquivo salvo em: {ARQUIVO_SAIDA}")

    input("\nPressione ENTER para finalizar...")


if __name__ == "__main__":
    main()