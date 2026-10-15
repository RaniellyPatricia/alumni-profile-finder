
"""
Alumni Profile Finder
Metadados das pesquisas no Google Sheets.

Registra informações sobre cada execução sem acrescentar
colunas aos resultados de Cargos ou Competências.

O teste local não acessa o Google Sheets.
A gravação real ocorre somente se a função
registrar_metadados() for chamada explicitamente.

Nenhum extrator ou CSV é modificado.
"""

from datetime import datetime
from uuid import uuid4


PREFIXO = "alumni_finder"

TIPOS_VALIDOS = ("cargos", "competencias")
NATUREZAS_VALIDAS = ("TESTE", "PESQUISA")


def criar_identificacao_execucao(
    natureza="TESTE",
    aba_origem=""
):
    """
    Cria os dados comuns a uma execução.

    Se Cargos e Competências forem processados juntos,
    ambos devem receber esta mesma identificação.
    """

    natureza = str(natureza).strip().upper()

    if natureza not in NATUREZAS_VALIDAS:
        raise ValueError(
            "Natureza inválida. Use TESTE ou PESQUISA."
        )

    return {
        "id_execucao": str(uuid4()),
        "data_hora_coleta": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "natureza": natureza,
        "aba_origem": str(aba_origem or "").strip(),
    }


def preparar_metadados(tipo, identificacao):
    """
    Prepara os metadados de uma aba específica.

    Não acessa nenhuma planilha.
    """

    if tipo not in TIPOS_VALIDOS:
        raise ValueError(
            "Tipo inválido. Use cargos ou competencias."
        )

    campos = (
        "id_execucao",
        "data_hora_coleta",
        "natureza",
        "aba_origem",
    )

    for campo in campos:
        if campo not in identificacao:
            raise ValueError(
                f"Identificação incompleta: {campo}."
            )

    natureza = str(
        identificacao["natureza"]
    ).strip().upper()

    if natureza not in NATUREZAS_VALIDAS:
        raise ValueError(
            "Natureza inválida."
        )

    return {
        "tipo": tipo,
        "id_execucao": str(
            identificacao["id_execucao"]
        ),
        "data_hora_coleta": str(
            identificacao["data_hora_coleta"]
        ),
        "natureza": natureza,
        "aba_origem": str(
            identificacao["aba_origem"]
        ),
    }


def preparar_requisicoes_metadados(
    sheet_id,
    metadados
):
    """
    Monta requisições createDeveloperMetadata
    da API Google Sheets.

    O sheet_id é o identificador numérico de uma aba,
    não o identificador da planilha inteira.
    """

    if (
        not isinstance(sheet_id, int)
        or isinstance(sheet_id, bool)
        or sheet_id < 0
    ):
        raise ValueError(
            "sheet_id deve ser um inteiro não negativo."
        )

    requisicoes = []

    for chave, valor in metadados.items():
        chave_completa = f"{PREFIXO}_{chave}"
        texto = str(valor)

        if len(texto) > 1024:
            raise ValueError(
                f"Metadado muito longo: {chave}."
            )

        requisicoes.append(
            {
                "createDeveloperMetadata": {
                    "developerMetadata": {
                        "metadataKey": chave_completa,
                        "metadataValue": texto,
                        "visibility": "DOCUMENT",
                        "location": {
                            "sheetId": sheet_id
                        },
                    }
                }
            }
        )

    return requisicoes


def registrar_metadados(
    servico,
    planilha_id,
    sheet_id,
    metadados
):
    """
    Grava metadados na aba informada.

    ATENÇÃO:
    Esta função modifica a planilha quando chamada.

    Deve ser utilizada somente após confirmar o
    identificador correto da aba e a autorização
    da execução.

    Não impede registros duplicados por si só.
    """

    requisicoes = preparar_requisicoes_metadados(
        sheet_id,
        metadados
    )

    resposta = servico.spreadsheets().batchUpdate(
        spreadsheetId=planilha_id,
        body={
            "requests": requisicoes
        }
    ).execute()

    return len(resposta.get("replies", []))


def main():
    """
    Teste local sem acesso à API.
    """

    print("=" * 60)
    print("ALUMNI PROFILE FINDER")
    print("TESTE LOCAL DOS METADADOS")
    print("=" * 60)

    identificacao = criar_identificacao_execucao(
        natureza="TESTE",
        aba_origem="Base Ficticia"
    )

    cargos = preparar_metadados(
        "cargos",
        identificacao
    )

    competencias = preparar_metadados(
        "competencias",
        identificacao
    )

    # Duas abas da mesma pesquisa compartilham o ID.
    assert (
        cargos["id_execucao"]
        == competencias["id_execucao"]
    )

    assert (
        cargos["data_hora_coleta"]
        == competencias["data_hora_coleta"]
    )

    assert cargos["tipo"] == "cargos"
    assert competencias["tipo"] == "competencias"
    assert cargos["natureza"] == "TESTE"

    # IDs de abas inteiramente fictícios.
    requisicoes_cargos = preparar_requisicoes_metadados(
        123456,
        cargos
    )

    requisicoes_competencias = (
        preparar_requisicoes_metadados(
            789012,
            competencias
        )
    )

    assert len(requisicoes_cargos) == 5
    assert len(requisicoes_competencias) == 5

    print("\nIdentificador da execução: OK")
    print("Data e hora: OK")
    print("Natureza TESTE: OK")
    print("Tipo de pesquisa: OK")
    print("Origem da pesquisa: OK")
    print("Mesmo ID para Cargos e Competências: OK")
    print("Requisições da API preparadas: OK")

    print("\nNenhum Google Sheets foi acessado.")
    print("Nenhum CSV foi modificado.")
    print("Nenhum Selenium foi executado.")
    print("\nTeste local concluído com sucesso!")


if __name__ == "__main__":
    main()
