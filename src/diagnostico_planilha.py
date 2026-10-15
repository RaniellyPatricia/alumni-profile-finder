
"""
Alumni Profile Finder
Diagnóstico e preparação de perfis do Google Sheets privado.

Funcionalidades:
- Autenticação OAuth 2.0.
- Leitura de planilha privada.
- Listagem e seleção de abas por número.
- Validação das colunas nome e link.
- Identificação de links vazios, inválidos e duplicados.
- Preparação de perfis para processamento futuro.

Segurança:
- Não imprime nomes ou links individuais.
- Não altera dados da planilha.
- Não acessa o LinkedIn.
- Não executa Selenium.
"""

from src.google_sheets import (
    autenticar,
    extrair_id,
    listar_abas,
    ler_aba,
    preparar_registros,
    preparar_perfis_processamento,
    LIMITE_PERFIS,
)


# ============================================================
# SELECIONAR ABA DA PLANILHA
# ============================================================

def selecionar_aba(servico, planilha_id):
    """
    Lista as abas disponíveis e permite selecionar pelo número.
    """

    titulo, abas = listar_abas(
        servico,
        planilha_id
    )

    print(f"\nPlanilha: {titulo}")
    print("\nAbas disponíveis:")

    if not abas:
        raise ValueError(
            "A planilha não possui abas disponíveis."
        )

    for numero, nome_aba in enumerate(abas, start=1):
        print(f"{numero}. {nome_aba}")

    while True:
        escolha = input(
            "\nDigite o número da aba desejada: "
        ).strip()

        if not escolha.isdigit():
            print("Digite apenas o número da aba.")
            continue

        indice = int(escolha) - 1

        if 0 <= indice < len(abas):
            aba = abas[indice]
            print(f"\nAba selecionada: {aba}")
            return aba

        print("Número de aba inválido. Tente novamente.")


# ============================================================
# EXIBIR RESULTADOS
# ============================================================

def exibir_diagnostico(dados, registros, perfis, resumo):
    """
    Exibe somente quantidades, sem dados pessoais.
    """

    print("\n" + "=" * 65)
    print("DIAGNÓSTICO DA PLANILHA")
    print("=" * 65)

    print(
        "Linhas lidas (incluindo cabeçalho):",
        len(dados)
    )

    print(
        "Registros preparados:",
        len(registros)
    )

    print(
        "Registros analisados:",
        resumo["analisados"]
    )

    print(
        "Registros sem nome:",
        resumo["sem_nome"]
    )

    print(
        "Registros sem link:",
        resumo["sem_link"]
    )

    print(
        "Links fora do formato LinkedIn:",
        resumo["links_invalidos"]
    )

    print(
        "Links duplicados:",
        resumo["duplicados"]
    )

    print(
        "Perfis LinkedIn únicos selecionados:",
        resumo["selecionados"]
    )

    print(
        "Perfis na lista de processamento:",
        len(perfis)
    )

    print(
        "Limite configurado:",
        LIMITE_PERFIS
    )

    print("=" * 65)

    print("\nNenhum nome ou link individual foi exibido.")
    print("Nenhuma alteração foi feita na planilha.")
    print("Nenhum perfil do LinkedIn foi acessado.")


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():
    print("=" * 65)
    print("ALUMNI PROFILE FINDER")
    print("Diagnóstico de dados do Google Sheets privado")
    print("=" * 65)

    try:
        # 1. Autenticação individual OAuth
        servico = autenticar()

        print("\nAutenticação Google concluída.")

        # 2. Informar URL da planilha privada
        url = input(
            "\nCole a URL da planilha de teste:\n> "
        ).strip()

        if not url:
            raise ValueError(
                "A URL da planilha não foi informada."
            )

        # 3. Identificar a planilha
        planilha_id = extrair_id(url)

        # 4. Listar abas e escolher pelo número
        aba = selecionar_aba(
            servico,
            planilha_id
        )

        # 5. Ler a aba selecionada
        print("\nLendo registros...")

        dados = ler_aba(
            servico,
            planilha_id,
            aba,
            limite=LIMITE_PERFIS
        )

        print(
            f"Leitura concluída: {len(dados)} linhas."
        )

        # 6. Verificar colunas nome e link
        registros = preparar_registros(dados)

        print("Colunas obrigatórias: nome e link - OK.")

        # 7. Preparar perfis e identificar duplicatas
        perfis, resumo = preparar_perfis_processamento(
            registros,
            limite=LIMITE_PERFIS
        )

        # 8. Exibir somente resultados numéricos
        exibir_diagnostico(
            dados,
            registros,
            perfis,
            resumo
        )

        print("\nDiagnóstico concluído com sucesso.")

    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")

    except Exception as erro:
        print(
            f"\nERRO: {type(erro).__name__}: {erro}"
        )


# ============================================================
# INICIAR
# ============================================================

if __name__ == "__main__":
    main()
