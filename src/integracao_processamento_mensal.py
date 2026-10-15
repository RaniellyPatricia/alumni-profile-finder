
"""
Alumni Profile Finder
Integração do processamento mensal com metadados e status.

Reutiliza módulos já validados:
- processamento_mensal.py
- integracao_metadados_mensais.py
- metadados_coleta.py
- status_execucao.py
- salvar_resultados_sheets.py

Fluxo de gravação:
1. Preparar e validar a pesquisa.
2. Confirmar autorização de gravação.
3. Criar novas abas mensais.
4. Registrar metadados EM_ANDAMENTO.
5. Escrever cabeçalhos e resultados.
6. Conferir os resultados pela API.
7. Atualizar os status para CONCLUIDO.

Em caso de falha, tenta marcar ERRO nas abas
ainda EM_ANDAMENTO, sem apagar dados.

A execução direta deste arquivo realiza
somente testes locais, sem acessar o Google.
"""

from datetime import date

from src.integracao_metadados_mensais import (
    preparar_pesquisa_com_metadados,
)

from src.processamento_mensal import (
    criar_abas_mensais,
    escrever_cabecalhos,
)

from src.metadados_coleta import (
    registrar_metadados,
)

from src.status_execucao import (
    atualizar_status_execucao,
)

from src.salvar_resultados_sheets import (
    obter_colunas,
    preparar_linhas,
    salvar_resultados,
)


def consultar_abas(servico, planilha_id):
    """
    Retorna um dicionário:
        nome_da_aba -> sheetId

    Não modifica a planilha.
    """

    resposta = servico.spreadsheets().get(
        spreadsheetId=planilha_id,
        fields="sheets(properties(title,sheetId))",
    ).execute()

    abas = {}

    for item in resposta.get("sheets", []):
        propriedades = item["properties"]

        abas[propriedades["title"]] = (
            propriedades["sheetId"]
        )

    return abas


def conferir_resultados(
    servico,
    planilha_id,
    item,
):
    """
    Confere cabeçalho e todos os resultados
    gravados na aba mensal.

    Não modifica a planilha.
    """

    nome_aba = item["nome_aba"]
    tipo = item["tipo"]

    nome_seguro = nome_aba.replace("'", "''")

    resposta = servico.spreadsheets().values().get(
        spreadsheetId=planilha_id,
        range=f"'{nome_seguro}'!A1:K202",
    ).execute()

    recebidos = resposta.get("values", [])

    cabecalho = obter_colunas(tipo)

    linhas_esperadas = preparar_linhas(
        tipo,
        item["resultados"],
    )

    if len(recebidos) != len(linhas_esperadas) + 1:
        raise AssertionError(
            f"Aba '{nome_aba}': quantidade "
            "de registros diferente da esperada."
        )

    if recebidos[0] != cabecalho:
        raise AssertionError(
            f"Aba '{nome_aba}': cabeçalho incorreto."
        )

    for numero, linha_esperada in enumerate(
        linhas_esperadas,
        start=1,
    ):
        linha_recebida = recebidos[numero]

        esperado_texto = [
            str(valor)
            for valor in linha_esperada
        ]

        recebido_texto = [
            str(valor)
            for valor in linha_recebida
        ]

        if recebido_texto != esperado_texto:
            raise AssertionError(
                f"Aba '{nome_aba}': divergência "
                f"na linha {numero + 1}."
            )

    return len(linhas_esperadas)


def integrar_processamento_mensal(
    servico,
    planilha_id,
    resultados_por_tipo,
    natureza="PESQUISA",
    aba_origem="",
    confirmar_gravacao=False,
):
    """
    Processa e grava resultados mensais.

    Esta função realmente modifica o Google Sheets
    quando confirmar_gravacao=True.

    resultados_por_tipo:
        {
            "cargos": [dicionarios],
            "competencias": [dicionarios]
        }

    Os resultados devem estar adaptados
    às colunas originais de cada tipo.

    Não executa os extratores.
    Não lê resultados de CSVs antigos.
    """

    # 1. Consultar abas existentes.
    abas_anteriores = consultar_abas(
        servico,
        planilha_id,
    )

    # 2. Preparar resultados e metadados.
    planejamento = preparar_pesquisa_com_metadados(
        resultados_por_tipo=resultados_por_tipo,
        abas_existentes=list(abas_anteriores),
        natureza=natureza,
        aba_origem=aba_origem,
    )

    if not planejamento:
        raise ValueError(
            "Nenhuma pesquisa foi preparada."
        )

    # 3. Exigir confirmação explícita.
    if confirmar_gravacao is not True:
        raise PermissionError(
            "Gravação não confirmada. "
            "Nenhuma aba foi criada."
        )

    # 4. Reconsultar nomes para evitar reutilizar
    # abas criadas desde o planejamento.
    abas_atuais = consultar_abas(
        servico,
        planilha_id,
    )

    for item in planejamento:
        if item["nome_aba"] in abas_atuais:
            raise RuntimeError(
                "Uma das abas propostas já existe. "
                "Inicie novamente para recalcular "
                "os nomes mensais."
            )

    # Depois da criação, não apagamos automaticamente
    # nenhuma aba em caso de falha.
    criacao_iniciada = False

    # Abas com metadados EM_ANDAMENTO.
    pendentes = {}

    # Abas cuja gravação já foi conferida.
    conferidos = {}

    # Resultado retornado ao final.
    resumo = []

    try:
        # 5. Criar as novas abas mensais.
        criacao_iniciada = True

        criar_abas_mensais(
            servico,
            planilha_id,
            planejamento,
        )

        # Obter o sheetId de cada aba criada.
        abas_criadas = consultar_abas(
            servico,
            planilha_id,
        )

        for item in planejamento:
            nome_aba = item["nome_aba"]

            if nome_aba not in abas_criadas:
                raise RuntimeError(
                    f"Aba não encontrada: {nome_aba}"
                )

            sheet_id = abas_criadas[nome_aba]

            # 6. Registrar metadados iniciais.
            quantidade = registrar_metadados(
                servico,
                planilha_id,
                sheet_id,
                item["metadados"],
            )

            if quantidade != len(item["metadados"]):
                raise RuntimeError(
                    f"Metadados incompletos: {nome_aba}"
                )

            pendentes[nome_aba] = sheet_id

        # 7. Escrever cabeçalhos originais.
        escrever_cabecalhos(
            servico,
            planilha_id,
            planejamento,
        )

        # 8. Gravar resultados.
        for item in planejamento:
            quantidade = salvar_resultados(
                servico=servico,
                planilha_id=planilha_id,
                nome_aba=item["nome_aba"],
                tipo=item["tipo"],
                resultados=item["resultados"],
            )

            if quantidade != item["quantidade"]:
                raise AssertionError(
                    "Quantidade de resultados gravados "
                    "diferente da esperada."
                )

        # 9. Conferir todos os resultados antes
        # de concluir qualquer aba.
        for item in planejamento:
            quantidade = conferir_resultados(
                servico,
                planilha_id,
                item,
            )

            conferidos[item["nome_aba"]] = quantidade

        # 10. Atualizar os status para CONCLUIDO.
        for item in planejamento:
            nome_aba = item["nome_aba"]

            atualizar_status_execucao(
                servico=servico,
                planilha_id=planilha_id,
                sheet_id=pendentes[nome_aba],
                novo_status="CONCLUIDO",
                resultados_conferidos=True,
            )

            # Remove da lista de pendentes somente
            # após a confirmação da atualização.
            del pendentes[nome_aba]

            resumo.append(
                {
                    "tipo": item["tipo"],
                    "aba": nome_aba,
                    "gravados": conferidos[nome_aba],
                    "status": "CONCLUIDO",
                    "id_execucao": (
                        item["metadados"]["id_execucao"]
                    ),
                }
            )

        return resumo

    except Exception as erro:
        # Tenta marcar ERRO onde o status ainda
        # pode estar EM_ANDAMENTO.
        #
        # Uma falha na própria API pode impedir isso.
        # Nesse caso, a aba permanece para inspeção.
        for nome_aba, sheet_id in pendentes.items():
            try:
                atualizar_status_execucao(
                    servico=servico,
                    planilha_id=planilha_id,
                    sheet_id=sheet_id,
                    novo_status="ERRO",
                )
            except Exception:
                print(
                    "Não foi possível confirmar o status "
                    f"ERRO da aba '{nome_aba}'. "
                    "Verifique manualmente."
                )

        if criacao_iniciada:
            print(
                "\nATENÇÃO: a execução pode ter criado "
                "abas ou gravado resultados parciais."
            )
            print(
                "Nenhuma aba foi apagada. "
                "Não repita automaticamente a gravação."
            )

        raise RuntimeError(
            "Falha no processamento mensal integrado: "
            f"{erro}"
        ) from erro


def main():
    """
    Teste local fictício.

    Exercita o planejamento compartilhado.
    Não chama a função que escreve na API.
    """

    print("=" * 60)
    print("ALUMNI PROFILE FINDER")
    print("TESTE LOCAL DA INTEGRAÇÃO MENSAL")
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
                    "in/exemplo-integracao-final-a/"
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
                    "in/exemplo-integracao-final-a/"
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

    assert all(
        item["metadados"]["status_execucao"]
        == "EM_ANDAMENTO"
        for item in planejamento
    )

    assert all(
        item["metadados"]["natureza"] == "TESTE"
        for item in planejamento
    )

    print("\nABAS SIMULADAS:")

    for item in planejamento:
        print(
            f"- {item['nome_aba']}: "
            f"{item['quantidade']} registro(s)"
        )

    print("\nVALIDAÇÕES:")
    print("Criação de planejamento: OK")
    print("Numeração mensal: OK")
    print("Identificador compartilhado: OK")
    print("Natureza TESTE: OK")
    print("Status inicial EM_ANDAMENTO: OK")
    print("Colunas originais preservadas: OK")

    print("\nNenhum Google Sheets foi acessado.")
    print("Nenhum CSV foi modificado.")
    print("Nenhum Selenium foi executado.")
    print("\nTeste local concluído com sucesso!")


if __name__ == "__main__":
    main()
