
"""
Alumni Profile Finder
Adaptador de registros para o extrator de cargos.

Converte perfis preparados do Google Sheets
para a estrutura de entrada do extrator de cargos.

Não acessa o LinkedIn.
Não executa Selenium.
Não altera planilhas ou arquivos CSV.
"""

from urllib.parse import urlsplit


# ============================================================
# ADAPTAR PERFIS PARA CARGOS
# ============================================================

def adaptar_perfis_cargos(registros):
    """
    Recebe registros preparados do Google Sheets.

    Retorna uma lista com os campos:
        nome
        link

    Preserva os nomes e normaliza URLs de perfil.
    """

    perfis = []

    for registro in registros:
        nome = str(
            registro.get("nome", "") or ""
        ).strip()

        link = str(
            registro.get("link", "") or ""
        ).strip()

        if not link:
            continue

        try:
            partes = urlsplit(link)
        except ValueError:
            continue

        dominio = (partes.hostname or "").lower()
        caminho = partes.path.strip("/").split("/")

        if (
            partes.scheme != "https"
            or dominio not in (
                "linkedin.com",
                "www.linkedin.com"
            )
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
            "nome": nome,
            "link": perfil
        })

    return perfis


# ============================================================
# TESTE COM DADOS FICTÍCIOS
# ============================================================

def main():

    exemplos = [
        {
            "nome": "Pessoa Teste A",
            "link": "https://www.linkedin.com/in/exemplo-a/",
        },
        {
            "nome": "Pessoa Teste B",
            "link": "https://linkedin.com/in/exemplo-b/",
        },
        {
            "nome": "Pessoa Teste C",
            "link": "",
        },
    ]

    perfis = adaptar_perfis_cargos(exemplos)

    print("=== TESTE DO ADAPTADOR DE CARGOS ===")
    print("Registros de entrada:", len(exemplos))
    print("Perfis adaptados:", len(perfis))

    assert len(perfis) == 2

    assert perfis[0] == {
        "nome": "Pessoa Teste A",
        "link": "https://www.linkedin.com/in/exemplo-a/"
    }

    assert perfis[1] == {
        "nome": "Pessoa Teste B",
        "link": "https://www.linkedin.com/in/exemplo-b/"
    }

    print("Estrutura de cargos: OK")
    print("Nenhum perfil foi acessado.")
    print("Nenhum arquivo foi alterado.")


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()
