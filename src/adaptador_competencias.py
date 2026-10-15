
"""
Alumni Profile Finder
Adaptador de registros para o extrator de competências.

Não acessa o LinkedIn, não utiliza Selenium
e não modifica arquivos ou planilhas.
"""

from urllib.parse import urlsplit


def adaptar_perfis_competencias(registros):
    """
    Recebe registros preparados do Google Sheets
    e devolve a estrutura esperada pelo extrator
    de competências.
    """

    perfis = []

    for registro in registros:
        nome = str(registro.get("nome", "") or "").strip()
        link = str(registro.get("link", "") or "").strip()

        if not link:
            continue

        partes = urlsplit(link)

        dominio = (partes.hostname or "").lower()
        caminho = partes.path.strip("/").split("/")

        if (
            partes.scheme != "https"
            or dominio not in ("linkedin.com", "www.linkedin.com")
            or len(caminho) != 2
            or caminho[0].lower() != "in"
            or not caminho[1]
        ):
            continue

        perfil = (
            "https://www.linkedin.com/in/"
            + caminho[1]
            + "/"
        )

        perfis.append({
            "nome_planilha": nome,
            "link": perfil + "details/skills/",
            "perfil": perfil,
        })

    return perfis


def main():
    # Dados totalmente fictícios
    exemplos = [
        {
            "nome": "Pessoa Teste A",
            "link": "https://www.linkedin.com/in/exemplo-a/",
        },
        {
            "nome": "Pessoa Teste B",
            "link": "https://www.linkedin.com/in/exemplo-b/",
        },
    ]

    perfis = adaptar_perfis_competencias(exemplos)

    print("=== TESTE DO ADAPTADOR ===")
    print("Registros de entrada:", len(exemplos))
    print("Perfis adaptados:", len(perfis))

    assert len(perfis) == 2
    assert perfis[0]["nome_planilha"] == "Pessoa Teste A"
    assert perfis[0]["perfil"].endswith("/exemplo-a/")
    assert perfis[0]["link"].endswith(
        "/exemplo-a/details/skills/"
    )

    print("Estrutura de competências: OK")


if __name__ == "__main__":
    main()
