
"""
Alumni Profile Finder
Gravação de resultados no Google Sheets privado.

Preserva as colunas originais de cargos e competências.
Não cria abas e não executa extratores.

Segurança:
- Não altera os arquivos CSV.
- Não acessa o LinkedIn.
- Verifica o cabeçalho antes de gravar.
- Não sobrescreve registros existentes.
"""

COLUNAS_CARGOS = [
    "nome",
    "nome_linkedin",
    "link",
    "empresa",
    "tipo_contrato",
    "tempo_empresa",
    "cargo",
    "data_inicio",
    "data_fim",
    "local_cargo",
    "descricao_cargo",
]

COLUNAS_COMPETENCIAS = [
    "nome_planilha",
    "nome_linkedin",
    "link",
    "lista_competencias",
    "quantidade_competencias",
    "status",
]


def obter_colunas(tipo):
    """Retorna as colunas do tipo de pesquisa."""

    if tipo == "cargos":
        return COLUNAS_CARGOS.copy()

    if tipo == "competencias":
        return COLUNAS_COMPETENCIAS.copy()

    raise ValueError(
        "Tipo inválido. Use cargos ou competencias."
    )


def preparar_linhas(tipo, resultados):
    """
    Converte resultados em linhas do Google Sheets.

    Mantém a ordem e a quantidade das colunas originais.
    """

    colunas = obter_colunas(tipo)
    linhas = []

    for resultado in resultados:
        linha = []

        for coluna in colunas:
            valor = resultado.get(coluna, "")

            if coluna == "lista_competencias":
                if isinstance(valor, list):
                    valor = "; ".join(
                        str(item).strip()
                        for item in valor
                        if str(item).strip()
                    )

            if valor is None:
                valor = ""

            linha.append(valor)

        linhas.append(linha)

    return linhas


def verificar_cabecalho(
    servico,
    planilha_id,
    nome_aba,
    tipo
):
    """
    Verifica se o cabeçalho corresponde ao formato esperado.
    """

    colunas = obter_colunas(tipo)
    nome_seguro = nome_aba.replace("'", "''")

    resposta = servico.spreadsheets().values().get(
        spreadsheetId=planilha_id,
        range=f"'{nome_seguro}'!1:1",
    ).execute()

    valores = resposta.get("values", [])

    if not valores:
        raise ValueError(
            "A aba está sem cabeçalho."
        )

    cabecalho = [
        str(valor).strip()
        for valor in valores[0]
    ]

    if cabecalho != colunas:
        raise ValueError(
            "As colunas da aba não correspondem "
            "ao formato esperado."
        )

    return True


def salvar_resultados(
    servico,
    planilha_id,
    nome_aba,
    tipo,
    resultados
):
    """
    Adiciona resultados abaixo do cabeçalho existente.

    Não apaga registros nem sobrescreve o cabeçalho.
    """

    verificar_cabecalho(
        servico,
        planilha_id,
        nome_aba,
        tipo
    )

    linhas = preparar_linhas(
        tipo,
        resultados
    )

    if not linhas:
        return 0

    nome_seguro = nome_aba.replace("'", "''")

    servico.spreadsheets().values().append(
        spreadsheetId=planilha_id,
        range=f"'{nome_seguro}'!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": linhas},
    ).execute()

    return len(linhas)


def main():
    """
    Teste local com dados fictícios.
    Não acessa o Google Sheets.
    """

    exemplos = [
        {
            "nome_planilha": "Pessoa Fictícia A",
            "nome_linkedin": "Pessoa Exemplo",
            "link": "https://www.linkedin.com/in/exemplo/",
            "lista_competencias": [
                "Python",
                "SQL",
                "Power BI",
            ],
            "quantidade_competencias": 3,
            "status": "TESTE_FICTICIO",
        }
    ]

    linhas = preparar_linhas(
        "competencias",
        exemplos
    )

    assert len(linhas) == 1
    assert len(linhas[0]) == 6
    assert linhas[0][3] == "Python; SQL; Power BI"

    print("=== TESTE DE PREPARAÇÃO ===")
    print("Registros fictícios:", len(linhas))
    print("Colunas de competências:", len(linhas[0]))
    print("Lista na mesma célula: OK")
    print("Nenhuma planilha foi modificada.")


if __name__ == "__main__":
    main()
