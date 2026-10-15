
"""
Alumni Profile Finder
Processamento mensal de resultados.

Integra os módulos existentes:
- abas_mensais.py
- salvar_resultados_sheets.py
- google_sheets.py (o serviço OAuth é recebido pronto)

Cada execução cria abas mensais novas.
Não lê CSVs antigos.
Não executa Selenium.
Não sobrescreve abas já existentes.

Ao executar este arquivo diretamente, o teste é
somente local, com dados fictícios e sem acesso à API.
"""

from datetime import date

from src.abas_mensais import proximo_nome_aba
from src.salvar_resultados_sheets import (
    obter_colunas,
    preparar_linhas,
    salvar_resultados,
)


LIMITE_RESULTADOS = 200

TIPOS_VALIDOS = ("cargos", "competencias")


def validar_resultados(tipo, resultados):
    """
    Valida resultados antes de qualquer gravação.

    Evita resultados vazios, registros sem link
    e links repetidos dentro da mesma pesquisa.
    """

    if tipo not in TIPOS_VALIDOS:
        raise ValueError(
            "Tipo inválido: use cargos ou competencias."
        )

    if not isinstance(resultados, list):
        raise TypeError(
            "Os resultados devem ser uma lista."
        )

    if not resultados:
        raise ValueError(
            f"A pesquisa de {tipo} está sem resultados. "
            "Nenhuma aba será criada."
        )

    if len(resultados) > LIMITE_RESULTADOS:
        raise ValueError(
            "O limite inicial é de 200 resultados."
        )

    links_vistos = set()

    for numero, resultado in enumerate(
        resultados,
        start=1
    ):
        if not isinstance(resultado, dict):
            raise TypeError(
                f"Registro {numero}: esperado dicionário."
            )

        link = str(
            resultado.get("link") or ""
        ).strip()

        if not link:
            raise ValueError(
                f"Registro {numero}: link vazio."
            )

        chave = link.rstrip("/").lower()

        if chave in links_vistos:
            raise ValueError(
                f"Registro {numero}: link duplicado "
                "na mesma pesquisa."
            )

        links_vistos.add(chave)

    linhas = preparar_linhas(tipo, resultados)

    quantidade_colunas = len(obter_colunas(tipo))

    for numero, linha in enumerate(linhas, start=1):
        if len(linha) != quantidade_colunas:
            raise ValueError(
                f"Registro {numero}: número incorreto "
                "de colunas."
            )

    return linhas


def preparar_processamento(
    resultados_por_tipo,
    abas_existentes,
    data_coleta=None
):
    """
    Prepara nomes e valida todos os resultados.

    Não acessa o Google Sheets.
    Não cria abas.
    """

    if not isinstance(resultados_por_tipo, dict):
        raise TypeError(
            "Informe um dicionário de resultados "
            "por tipo de pesquisa."
        )

    if not resultados_por_tipo:
        raise ValueError(
            "Nenhum tipo de pesquisa foi informado."
        )

    if data_coleta is None:
        data_coleta = date.today()

    tipos_desconhecidos = (
        set(resultados_por_tipo) - set(TIPOS_VALIDOS)
    )

    if tipos_desconhecidos:
        raise ValueError(
            "Tipo de pesquisa desconhecido: "
            + ", ".join(sorted(tipos_desconhecidos))
        )

    planejamento = []
    nomes_reservados = list(abas_existentes)

    for tipo in TIPOS_VALIDOS:
        if tipo not in resultados_por_tipo:
            continue

        resultados = resultados_por_tipo[tipo]

        linhas = validar_resultados(
            tipo,
            resultados
        )

        nome_aba = proximo_nome_aba(
            tipo,
            nomes_reservados,
            data_coleta
        )

        planejamento.append(
            {
                "tipo": tipo,
                "nome_aba": nome_aba,
                "quantidade": len(linhas),
                "resultados": resultados,
            }
        )

        nomes_reservados.append(nome_aba)

    return planejamento


def criar_abas_mensais(
    servico,
    planilha_id,
    planejamento
):
    """
    Cria as novas abas mensais.

    Não modifica abas anteriores.
    """

    requisicoes = [
        {
            "addSheet": {
                "properties": {
                    "title": item["nome_aba"]
                }
            }
        }
        for item in planejamento
    ]

    servico.spreadsheets().batchUpdate(
        spreadsheetId=planilha_id,
        body={
            "requests": requisicoes
        }
    ).execute()


def escrever_cabecalhos(
    servico,
    planilha_id,
    planejamento
):
    """
    Insere os cabeçalhos originais nas novas abas.
    """

    dados = []

    for item in planejamento:
        nome = item["nome_aba"]
        tipo = item["tipo"]

        dados.append(
            {
                "range": f"'{nome}'!A1",
                "values": [
                    obter_colunas(tipo)
                ],
            }
        )

    servico.spreadsheets().values().batchUpdate(
        spreadsheetId=planilha_id,
        body={
            "valueInputOption": "RAW",
            "data": dados,
        }
    ).execute()


def processar_resultados_mensais(
    servico,
    planilha_id,
    resultados_por_tipo,
    confirmar_gravacao=False
):
    """
    Cria novas abas mensais e grava resultados.

    A função não solicita confirmação no terminal:
    a interface chamadora deve obter autorização
    explícita e passar confirmar_gravacao=True.

    Se ocorrer falha depois da criação das abas,
    não exclui nem tenta repetir a gravação.
    """

    # Consulta as abas atuais diretamente pela API.
    resposta = servico.spreadsheets().get(
        spreadsheetId=planilha_id,
        fields="sheets(properties(title))"
    ).execute()

    abas_existentes = [
        aba["properties"]["title"]
        for aba in resposta.get("sheets", [])
    ]

    planejamento = preparar_processamento(
        resultados_por_tipo,
        abas_existentes
    )

    if not confirmar_gravacao:
        raise PermissionError(
            "Gravação não confirmada. "
            "Nenhuma aba foi criada."
        )

    # Uma verificação adicional reduz o risco de
    # usar nomes que acabaram de ser ocupados.
    resposta_atual = servico.spreadsheets().get(
        spreadsheetId=planilha_id,
        fields="sheets(properties(title))"
    ).execute()

    nomes_atuais = {
        aba["properties"]["title"]
        for aba in resposta_atual.get("sheets", [])
    }

    for item in planejamento:
        if item["nome_aba"] in nomes_atuais:
            raise RuntimeError(
                "O nome de uma aba ficou indisponível. "
                "Execute novamente para recalcular os nomes."
            )

    # A partir daqui a planilha será modificada.
    criar_abas_mensais(
        servico,
        planilha_id,
        planejamento
    )

    escrever_cabecalhos(
        servico,
        planilha_id,
        planejamento
    )

    resumo = []

    for item in planejamento:
        quantidade = salvar_resultados(
            servico=servico,
            planilha_id=planilha_id,
            nome_aba=item["nome_aba"],
            tipo=item["tipo"],
            resultados=item["resultados"],
        )

        resumo.append(
            {
                "tipo": item["tipo"],
                "aba": item["nome_aba"],
                "gravados": quantidade,
            }
        )

    return resumo


def main():
    """
    Teste local fictício.

    Não autentica no Google.
    Não escreve em planilhas.
    """

    print("=" * 60)
    print("ALUMNI PROFILE FINDER")
    print("TESTE LOCAL DO PROCESSAMENTO MENSAL")
    print("=" * 60)

    # Nomes simulados apenas para testar a numeração.
    abas_ficticias = [
        "BASE 00",
        "Cargos 10-2026",
        "Competencias 10-2026",
        "Cargos 10-2026 (1)",
    ]

    # Não são resultados de extração real.
    resultados_ficticios = {
        "cargos": [
            {
                "nome": "Pessoa Fictícia A",
                "nome_linkedin": "Pessoa Exemplo A",
                "link": (
                    "https://www.linkedin.com/"
                    "in/exemplo-teste-a/"
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
                "nome_planilha": "Pessoa Fictícia B",
                "nome_linkedin": "Pessoa Exemplo B",
                "link": (
                    "https://www.linkedin.com/"
                    "in/exemplo-teste-b/"
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

    planejamento = preparar_processamento(
        resultados_ficticios,
        abas_ficticias,
        data_coleta=date(2026, 10, 15)
    )

    print("\nABAS MENSAIS SIMULADAS:")

    for item in planejamento:
        print(
            f"- {item['nome_aba']}: "
            f"{item['quantidade']} registro(s)"
        )

    assert len(planejamento) == 2

    assert (
        planejamento[0]["nome_aba"]
        == "Cargos 10-2026 (2)"
    )

    assert (
        planejamento[1]["nome_aba"]
        == "Competencias 10-2026 (1)"
    )

    # Confirma que duplicatas são recusadas.
    repetido = [
        resultados_ficticios["cargos"][0],
        resultados_ficticios["cargos"][0].copy(),
    ]

    try:
        validar_resultados("cargos", repetido)
    except ValueError:
        print("\nProteção contra links duplicados: OK")
    else:
        raise AssertionError(
            "O teste de duplicatas deveria falhar."
        )

    print("\nRESULTADO")
    print("Numeração mensal: OK")
    print("Cargos e competências: OK")
    print("Colunas originais: OK")
    print("Nenhum Google Sheets foi acessado.")
    print("Nenhum CSV foi modificado.")
    print("Nenhum Selenium foi executado.")
    print("\nTeste local concluído com sucesso!")


if __name__ == "__main__":
    main()
