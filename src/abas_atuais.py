
"""
Alumni Profile Finder
Preparação das abas fixas para o Power BI.

Abas:
- Cargos_Atual
- Competencias_Atual

Este módulo:
- Reutiliza a validação de resultados mensais.
- Verifica os metadados informados.
- Prepara cabeçalhos e linhas para as abas fixas.
- Não acessa o Google Sheets.
- Não altera arquivos CSV.
- Não executa Selenium.

IMPORTANTE:
A verificação dos metadados aqui é local.
Na integração real, os metadados deverão ser
consultados novamente pela API do Google Sheets.
"""

from src.processamento_mensal import validar_resultados

from src.salvar_resultados_sheets import obter_colunas


ABAS_ATUAIS = {
    "cargos": "Cargos_Atual",
    "competencias": "Competencias_Atual",
}

NATUREZA_PERMITIDA = "PESQUISA"
STATUS_PERMITIDO = "CONCLUIDO"


def validar_metadados_para_atualizacao(tipo, metadados):
    """
    Confere as condições necessárias para
    atualizar uma aba fixa.

    Não consulta o Google Sheets.
    """

    if tipo not in ABAS_ATUAIS:
        raise ValueError(
            "Tipo inválido. Use cargos ou competencias."
        )

    if not isinstance(metadados, dict):
        raise TypeError(
            "Os metadados devem ser um dicionário."
        )

    natureza = str(
        metadados.get("natureza") or ""
    ).strip().upper()

    status = str(
        metadados.get("status_execucao") or ""
    ).strip().upper()

    tipo_metadados = str(
        metadados.get("tipo") or ""
    ).strip().lower()

    identificador = str(
        metadados.get("id_execucao") or ""
    ).strip()

    data_coleta = str(
        metadados.get("data_hora_coleta") or ""
    ).strip()

    if natureza != NATUREZA_PERMITIDA:
        raise ValueError(
            "Atualização bloqueada: somente PESQUISA "
            "pode alimentar as abas fixas."
        )

    if status != STATUS_PERMITIDO:
        raise ValueError(
            "Atualização bloqueada: a pesquisa "
            "precisa estar CONCLUIDO."
        )

    if tipo_metadados != tipo:
        raise ValueError(
            "O tipo informado não corresponde "
            "aos metadados da pesquisa."
        )

    if not identificador:
        raise ValueError(
            "Identificador da execução ausente."
        )

    if not data_coleta:
        raise ValueError(
            "Data e hora da coleta ausentes."
        )

    return True


def preparar_aba_atual(tipo, resultados, metadados):
    """
    Prepara o conteúdo completo da aba fixa.

    A primeira linha contém os cabeçalhos.
    As demais contêm os resultados da pesquisa.

    Não escreve na planilha.
    """

    validar_metadados_para_atualizacao(
        tipo,
        metadados,
    )

    linhas_resultados = validar_resultados(
        tipo,
        resultados,
    )

    cabecalho = obter_colunas(tipo)

    return {
        "tipo": tipo,
        "nome_aba": ABAS_ATUAIS[tipo],
        "id_execucao": metadados["id_execucao"],
        "data_hora_coleta": metadados["data_hora_coleta"],
        "quantidade": len(linhas_resultados),
        "valores": [
            cabecalho,
            *linhas_resultados,
        ],
    }


def preparar_abas_atuais(
    resultados_por_tipo,
    metadados_por_tipo,
):
    """
    Prepara uma ou duas abas fixas.

    Valida todos os conjuntos de dados antes
    de devolver o planejamento.
    """

    if not isinstance(resultados_por_tipo, dict):
        raise TypeError(
            "Os resultados devem ser organizados "
            "por tipo de pesquisa."
        )

    if not isinstance(metadados_por_tipo, dict):
        raise TypeError(
            "Os metadados devem ser organizados "
            "por tipo de pesquisa."
        )

    if not resultados_por_tipo:
        raise ValueError(
            "Nenhum resultado foi informado."
        )

    tipos_desconhecidos = (
        set(resultados_por_tipo) - set(ABAS_ATUAIS)
    )

    if tipos_desconhecidos:
        raise ValueError(
            "Tipos de pesquisa desconhecidos: "
            + ", ".join(sorted(tipos_desconhecidos))
        )

    planejamento = []

    for tipo in ABAS_ATUAIS:
        if tipo not in resultados_por_tipo:
            continue

        if tipo not in metadados_por_tipo:
            raise ValueError(
                f"Metadados ausentes para {tipo}."
            )

        item = preparar_aba_atual(
            tipo,
            resultados_por_tipo[tipo],
            metadados_por_tipo[tipo],
        )

        planejamento.append(item)

    if len(planejamento) == 2:
        cargos, competencias = planejamento

        if (
            cargos["id_execucao"]
            != competencias["id_execucao"]
        ):
            raise ValueError(
                "As pesquisas selecionadas não "
                "pertencem à mesma execução."
            )

        if (
            cargos["data_hora_coleta"]
            != competencias["data_hora_coleta"]
        ):
            raise ValueError(
                "As datas de coleta não correspondem."
            )

    return planejamento


def verificar_bloqueio(funcao, descricao):
    """
    Confirma que uma situação inválida
    é recusada durante o teste local.
    """

    try:
        funcao()
    except (ValueError, TypeError):
        print(f"{descricao}: OK")
    else:
        raise AssertionError(
            f"O bloqueio falhou: {descricao}"
        )


def main():
    """
    Testes locais inteiramente fictícios.

    Não acessa a API do Google Sheets.
    """

    print("=" * 60)
    print("ALUMNI PROFILE FINDER")
    print("TESTE LOCAL DAS ABAS FIXAS")
    print("=" * 60)

    identificacao = {
        "id_execucao": "execucao-ficticia-001",
        "data_hora_coleta": "2026-10-15T15:30:00-03:00",
        "natureza": "PESQUISA",
        "status_execucao": "CONCLUIDO",
    }

    metadados = {
        "cargos": {
            **identificacao,
            "tipo": "cargos",
        },
        "competencias": {
            **identificacao,
            "tipo": "competencias",
        },
    }

    resultados = {
        "cargos": [
            {
                "nome": "Pessoa Fictícia A",
                "nome_linkedin": "Pessoa Exemplo",
                "link": (
                    "https://www.linkedin.com/"
                    "in/exemplo-abas-atuais/"
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
                "nome_linkedin": "Pessoa Exemplo",
                "link": (
                    "https://www.linkedin.com/"
                    "in/exemplo-abas-atuais/"
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

    planejamento = preparar_abas_atuais(
        resultados,
        metadados,
    )

    assert len(planejamento) == 2

    cargos, competencias = planejamento

    assert cargos["nome_aba"] == "Cargos_Atual"
    assert competencias["nome_aba"] == "Competencias_Atual"

    assert len(cargos["valores"][0]) == 11
    assert len(competencias["valores"][0]) == 6

    assert cargos["quantidade"] == 1
    assert competencias["quantidade"] == 1

    assert (
        competencias["valores"][1][3]
        == "Python; SQL; Power BI"
    )

    print("\nABAS FIXAS SIMULADAS:")

    for item in planejamento:
        print(
            f"- {item['nome_aba']}: "
            f"{item['quantidade']} registro(s), "
            f"{len(item['valores'][0])} colunas"
        )

    # Teste de bloqueio para natureza TESTE.
    metadados_teste = {
        **metadados["cargos"],
        "natureza": "TESTE",
    }

    verificar_bloqueio(
        lambda: preparar_aba_atual(
            "cargos",
            resultados["cargos"],
            metadados_teste,
        ),
        "Bloqueio de natureza TESTE",
    )

    # Teste de bloqueio para execução incompleta.
    metadados_pendente = {
        **metadados["competencias"],
        "status_execucao": "EM_ANDAMENTO",
    }

    verificar_bloqueio(
        lambda: preparar_aba_atual(
            "competencias",
            resultados["competencias"],
            metadados_pendente,
        ),
        "Bloqueio de execução EM_ANDAMENTO",
    )

    # Teste de bloqueio para links duplicados.
    registros_duplicados = [
        resultados["cargos"][0],
        resultados["cargos"][0].copy(),
    ]

    verificar_bloqueio(
        lambda: preparar_aba_atual(
            "cargos",
            registros_duplicados,
            metadados["cargos"],
        ),
        "Bloqueio de links duplicados",
    )

    print("\nVALIDAÇÕES:")
    print("Cargos - 11 colunas: OK")
    print("Competências - 6 colunas: OK")
    print("Uma linha por pessoa: OK")
    print("Identificador compartilhado: OK")
    print("Data de coleta compartilhada: OK")
    print("Nenhum Google Sheets foi acessado.")
    print("Nenhum CSV foi modificado.")
    print("Nenhum Selenium foi executado.")
    print("\nTeste local concluído com sucesso!")


if __name__ == "__main__":
    main()
