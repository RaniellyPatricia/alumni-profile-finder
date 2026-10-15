
"""
Alumni Profile Finder
Controle do status das pesquisas no Google Sheets.

Status previstos:
- EM_ANDAMENTO
- CONCLUIDO
- ERRO

Reutiliza os metadados criados por metadados_coleta.py.

Este módulo:
- Localiza o status de uma aba específica.
- Impede transições indevidas.
- Atualiza apenas o valor do metadado de status.
- Não altera células ou cabeçalhos.

O teste main() utiliza uma API simulada.
Nenhuma planilha real é acessada nesse teste.
"""

from src.metadados_coleta import PREFIXO


CHAVE_STATUS = f"{PREFIXO}_status_execucao"

STATUS_INICIAL = "EM_ANDAMENTO"
STATUS_FINAIS = ("CONCLUIDO", "ERRO")


def localizar_metadado_status(
    servico,
    planilha_id,
    sheet_id,
):
    """
    Procura o metadado de status na aba indicada.

    Exige exatamente um metadado correspondente.
    Não modifica a planilha.
    """

    if (
        not isinstance(sheet_id, int)
        or isinstance(sheet_id, bool)
        or sheet_id < 0
    ):
        raise ValueError("sheet_id inválido.")

    resposta = (
        servico.spreadsheets()
        .developerMetadata()
        .search(
            spreadsheetId=planilha_id,
            body={
                "dataFilters": [
                    {
                        "developerMetadataLookup": {
                            "metadataKey": CHAVE_STATUS,
                            "visibility": "DOCUMENT",
                        }
                    }
                ]
            },
        )
        .execute()
    )

    correspondentes = []

    for item in resposta.get(
        "matchedDeveloperMetadata", []
    ):
        metadado = item.get(
            "developerMetadata", {}
        )

        local = metadado.get("location", {})

        if local.get("sheetId") == sheet_id:
            correspondentes.append(metadado)

    if not correspondentes:
        raise ValueError(
            "A aba não possui metadado de status. "
            "Nenhuma atualização foi realizada."
        )

    if len(correspondentes) != 1:
        raise ValueError(
            "Foram encontrados metadados de status "
            "duplicados. Atualização cancelada."
        )

    return correspondentes[0]


def preparar_atualizacao_status(
    metadado_atual,
    novo_status,
    resultados_conferidos=False,
):
    """
    Prepara a requisição de atualização.

    Não acessa a API.

    CONCLUIDO exige confirmação explícita
    de que os resultados foram conferidos.
    """

    novo_status = str(
        novo_status
    ).strip().upper()

    if novo_status not in STATUS_FINAIS:
        raise ValueError(
            "O novo status deve ser CONCLUIDO ou ERRO."
        )

    if (
        metadado_atual.get("metadataKey")
        != CHAVE_STATUS
    ):
        raise ValueError(
            "O metadado informado não é de status."
        )

    status_atual = metadado_atual.get(
        "metadataValue"
    )

    if status_atual != STATUS_INICIAL:
        raise ValueError(
            "Somente pesquisas EM_ANDAMENTO "
            "podem receber um status final."
        )

    if (
        novo_status == "CONCLUIDO"
        and resultados_conferidos is not True
    ):
        raise ValueError(
            "Não é permitido concluir uma pesquisa "
            "sem conferir os resultados."
        )

    metadata_id = metadado_atual.get(
        "metadataId"
    )

    if (
        not isinstance(metadata_id, int)
        or isinstance(metadata_id, bool)
        or metadata_id < 0
    ):
        raise ValueError(
            "Identificador do metadado inválido."
        )

    return {
        "updateDeveloperMetadata": {
            "dataFilters": [
                {
                    "developerMetadataLookup": {
                        "metadataId": metadata_id
                    }
                }
            ],
            "developerMetadata": {
                "metadataValue": novo_status
            },
            "fields": "metadataValue",
        }
    }


def atualizar_status_execucao(
    servico,
    planilha_id,
    sheet_id,
    novo_status,
    resultados_conferidos=False,
):
    """
    Atualiza um status no Google Sheets real.

    Esta função faz escrita na API quando chamada.

    Deve ser utilizada apenas pela rotina que
    verificou a gravação e conhece a aba correta.

    Não grava resultados e não cria abas.
    """

    metadado = localizar_metadado_status(
        servico,
        planilha_id,
        sheet_id,
    )

    requisicao = preparar_atualizacao_status(
        metadado,
        novo_status,
        resultados_conferidos,
    )

    resposta = servico.spreadsheets().batchUpdate(
        spreadsheetId=planilha_id,
        body={
            "requests": [requisicao]
        },
    ).execute()

    if len(resposta.get("replies", [])) != 1:
        raise RuntimeError(
            "Não foi possível confirmar a resposta "
            "da atualização de status."
        )

    return str(novo_status).strip().upper()


def main():
    """
    Testes locais sem Google Sheets.

    Utiliza um metadado fictício.
    """

    print("=" * 60)
    print("ALUMNI PROFILE FINDER")
    print("TESTE LOCAL DE STATUS DA EXECUÇÃO")
    print("=" * 60)

    metadado_ficticio = {
        "metadataId": 12345,
        "metadataKey": CHAVE_STATUS,
        "metadataValue": "EM_ANDAMENTO",
        "location": {
            "sheetId": 98765
        },
    }

    requisicao_concluido = (
        preparar_atualizacao_status(
            metadado_ficticio,
            "CONCLUIDO",
            resultados_conferidos=True,
        )
    )

    assert (
        requisicao_concluido
        ["updateDeveloperMetadata"]
        ["developerMetadata"]
        ["metadataValue"]
        == "CONCLUIDO"
    )

    requisicao_erro = preparar_atualizacao_status(
        metadado_ficticio,
        "ERRO",
    )

    assert (
        requisicao_erro
        ["updateDeveloperMetadata"]
        ["developerMetadata"]
        ["metadataValue"]
        == "ERRO"
    )

    # Não permite concluir sem conferir resultados.
    try:
        preparar_atualizacao_status(
            metadado_ficticio,
            "CONCLUIDO",
        )
    except ValueError:
        print("Bloqueio de conclusão sem conferência: OK")
    else:
        raise AssertionError(
            "A conclusão sem conferência deveria falhar."
        )

    # Não permite mudar uma execução concluída.
    metadado_concluido = {
        **metadado_ficticio,
        "metadataValue": "CONCLUIDO",
    }

    try:
        preparar_atualizacao_status(
            metadado_concluido,
            "ERRO",
        )
    except ValueError:
        print("Proteção de status final: OK")
    else:
        raise AssertionError(
            "A alteração de status final deveria falhar."
        )

    print("EM_ANDAMENTO para CONCLUIDO: OK")
    print("EM_ANDAMENTO para ERRO: OK")
    print("Requisições de atualização preparadas: OK")

    print("\nNenhum Google Sheets foi acessado.")
    print("Nenhum CSV foi modificado.")
    print("Nenhum Selenium foi executado.")
    print("\nTeste local concluído com sucesso!")


if __name__ == "__main__":
    main()
