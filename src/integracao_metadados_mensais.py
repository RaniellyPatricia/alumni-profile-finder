
"""
Alumni Profile Finder
Integração dos metadados com o planejamento mensal.

Reutiliza:
- processamento_mensal.py
- metadados_coleta.py

Este teste:
- Usa exclusivamente dados fictícios.
- Não acessa o Google Sheets.
- Não executa Selenium.
- Não altera CSVs.
- Não modifica os módulos existentes.
"""

from datetime import date

from src.processamento_mensal import preparar_processamento

from src.metadados_coleta import (
    criar_identificacao_execucao,
    preparar_metadados,
)


def preparar_pesquisa_com_metadados(
    resultados_por_tipo,
    abas_existentes,
    natureza="TESTE",
    aba_origem="",
    data_coleta=None,
):
    """
    Prepara as abas mensais e os metadados
    de uma mesma execução.

    Não realiza gravações no Google Sheets.
    """

    planejamento = preparar_processamento(
        resultados_por_tipo,
        abas_existentes,
        data_coleta=data_coleta,
    )

    identificacao = criar_identificacao_execucao(
        natureza=natureza,
        aba_origem=aba_origem,
    )

    planejamento_completo = []

    for item in planejamento:
        metadados = preparar_metadados(
            item["tipo"],
            identificacao,
        )

        # A execução começa como EM_ANDAMENTO.
        # A conclusão será registrada somente depois
        # da futura confirmação dos dados pela API.
        metadados["status_execucao"] = "EM_ANDAMENTO"

        planejamento_completo.append(
            {
                **item,
                "metadados": metadados,
            }
        )

    return planejamento_completo


def main():
    print("=" * 60)
    print("ALUMNI PROFILE FINDER")
    print("TESTE DE INTEGRAÇÃO DOS METADADOS")
    print("=" * 60)

    abas_ficticias = [
        "Cargos 10-2026",
        "Competencias 10-2026",
        "Cargos 10-2026 (1)",
        "Competencias 10-2026 (1)",
        "Cargos 10-2026 (2)",
        "Competencias 10-2026 (2)",
    ]

    resultados_ficticios = {
        "cargos": [
            {
                "nome": "Pessoa Fictícia A",
                "nome_linkedin": "Pessoa Exemplo A",
                "link": (
                    "https://www.linkedin.com/"
                    "in/exemplo-metadados-a/"
                ),
                "empresa": "Empresa Fictícia",
                "tipo_contrato": "Tempo integral",
                "tempo_empresa": "2 anos",
                "cargo": "Analista de Dados",
                "data_inicio": "01/2024",
                "data_fim": "Atual",
                "local_cargo": "Remoto",
                "descricao_cargo": "Descrição fictícia.",
            }
        ],
        "competencias": [
            {
                "nome_planilha": "Pessoa Fictícia A",
                "nome_linkedin": "Pessoa Exemplo A",
                "link": (
                    "https://www.linkedin.com/"
                    "in/exemplo-metadados-a/"
                ),
                "lista_competencias": [
                    "Python",
                    "SQL",
                    "Power BI",
                ],
                "quantidade_competencias": 3,
                "status": "TESTE_FICTICIO",
            }
        ],
    }

    planejamento = preparar_pesquisa_com_metadados(
        resultados_por_tipo=resultados_ficticios,
        abas_existentes=abas_ficticias,
        natureza="TESTE",
        aba_origem="Base Ficticia",
        data_coleta=date(2026, 10, 15),
    )

    assert len(planejamento) == 2

    cargos, competencias = planejamento

    assert cargos["nome_aba"] == "Cargos 10-2026 (3)"
    assert (
        competencias["nome_aba"]
        == "Competencias 10-2026 (3)"
    )

    assert (
        cargos["metadados"]["id_execucao"]
        == competencias["metadados"]["id_execucao"]
    )

    assert (
        cargos["metadados"]["data_hora_coleta"]
        == competencias["metadados"]["data_hora_coleta"]
    )

    assert all(
        item["metadados"]["natureza"] == "TESTE"
        for item in planejamento
    )

    assert all(
        item["metadados"]["aba_origem"] == "Base Ficticia"
        for item in planejamento
    )

    assert all(
        item["metadados"]["status_execucao"]
        == "EM_ANDAMENTO"
        for item in planejamento
    )

    print("\nABAS MENSAIS SIMULADAS:")

    for item in planejamento:
        print(
            f"- {item['nome_aba']}: "
            f"{item['quantidade']} registro(s)"
        )

    print("\nVALIDAÇÕES:")
    print("Mesmo identificador da execução: OK")
    print("Mesma data e hora: OK")
    print("Origem da pesquisa: OK")
    print("Natureza TESTE: OK")
    print("Status inicial EM_ANDAMENTO: OK")
    print("Numeração mensal: OK")

    print("\nNenhum Google Sheets foi acessado.")
    print("Nenhum arquivo CSV foi alterado.")
    print("Nenhum Selenium foi executado.")
    print("\nTeste local concluído com sucesso!")


if __name__ == "__main__":
    main()
