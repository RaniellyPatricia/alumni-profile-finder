
"""
Alumni Profile Finder
Adaptador dos resultados de cargos para Google Sheets.

Converte os nomes internos dos campos do extrator
para as 11 colunas originais de resultados.

Não executa Selenium.
Não acessa o Google Sheets.
Não modifica arquivos ou planilhas.
"""

from src.salvar_resultados_sheets import (
    COLUNAS_CARGOS,
    preparar_linhas,
)


def adaptar_resultado_cargo(resultado):
    """
    Converte um resultado interno do extrator para
    o formato de saída do Google Sheets.

    Preserva os valores originais.
    """

    if not isinstance(resultado, dict):
        raise TypeError(
            "O resultado de cargos deve ser um dicionário."
        )

    convertido = {
        "nome": resultado.get("nome", ""),
        "nome_linkedin": resultado.get("nome_linkedin", ""),
        "link": resultado.get("link", ""),
        "empresa": resultado.get("empresa_atual", ""),
        "tipo_contrato": resultado.get("tipo_contrato", ""),
        "tempo_empresa": resultado.get("tempo_empresa", ""),
        "cargo": resultado.get("cargo_atual", ""),
        "data_inicio": resultado.get("data_inicio", ""),
        "data_fim": resultado.get("data_fim", ""),
        "local_cargo": resultado.get("local_cargo", ""),
        "descricao_cargo": resultado.get("descricao_cargo", ""),
    }

    return convertido


def adaptar_resultados_cargos(resultados):
    """
    Adapta uma lista de resultados mantendo
    uma linha por pessoa.
    """

    return [
        adaptar_resultado_cargo(resultado)
        for resultado in resultados
    ]


def main():
    # Dados inteiramente fictícios.
    resultado_exemplo = {
        "nome": "Pessoa Teste A",
        "nome_linkedin": "Pessoa Exemplo",
        "link": "https://www.linkedin.com/in/exemplo-a/",
        "empresa_atual": "Empresa Fictícia",
        "tipo_contrato": "Tempo integral",
        "tempo_empresa": "2 anos",
        "cargo_atual": "Analista de Dados",
        "data_inicio": "01/2024",
        "data_fim": "Atual",
        "duracao_cargo": "2 anos",
        "local_cargo": "Remoto",
        "descricao_cargo": "Atividades fictícias",
    }

    convertido = adaptar_resultado_cargo(
        resultado_exemplo
    )

    linhas = preparar_linhas(
        "cargos",
        [convertido]
    )

    assert len(linhas) == 1
    assert len(linhas[0]) == len(COLUNAS_CARGOS) == 11

    indice_empresa = COLUNAS_CARGOS.index("empresa")
    indice_cargo = COLUNAS_CARGOS.index("cargo")

    assert linhas[0][indice_empresa] == "Empresa Fictícia"
    assert linhas[0][indice_cargo] == "Analista de Dados"

    assert convertido["empresa"] == resultado_exemplo["empresa_atual"]
    assert convertido["cargo"] == resultado_exemplo["cargo_atual"]

    # Verifica que o dicionário de origem não foi alterado.
    assert "empresa_atual" in resultado_exemplo
    assert "cargo_atual" in resultado_exemplo

    print("=== TESTE DO MAPEAMENTO DE CARGOS ===")
    print("Registros fictícios:", len(linhas))
    print("Colunas:", len(linhas[0]))
    print("Empresa na coluna correta: OK")
    print("Cargo na coluna correta: OK")
    print("Campos internos preservados: OK")
    print("Nenhum arquivo ou planilha foi alterado.")


if __name__ == "__main__":
    main()
