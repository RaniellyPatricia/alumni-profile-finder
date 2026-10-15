
"""
Alumni Profile Finder
Nomes das abas mensais de resultados.

Este módulo apenas calcula o próximo nome disponível.
Não acessa nem modifica planilhas.
"""

from datetime import date


def proximo_nome_aba(tipo, abas_existentes, data_coleta=None):
    """
    Retorna um nome de aba disponível.

    Exemplos:
        Competencias 10-2026
        Competencias 10-2026 (1)
        Competencias 10-2026 (2)
    """

    tipos_permitidos = {
        "cargos": "Cargos",
        "competencias": "Competencias",
    }

    tipo_normalizado = str(tipo).strip().lower()

    if tipo_normalizado not in tipos_permitidos:
        raise ValueError(
            "O tipo deve ser 'cargos' ou 'competencias'."
        )

    if data_coleta is None:
        data_coleta = date.today()

    prefixo = tipos_permitidos[tipo_normalizado]

    nome_base = (
        f"{prefixo} "
        f"{data_coleta.month:02d}-{data_coleta.year}"
    )

    existentes = set(abas_existentes)

    if nome_base not in existentes:
        return nome_base

    numero = 1

    while f"{nome_base} ({numero})" in existentes:
        numero += 1

    return f"{nome_base} ({numero})"


def main():
    # Exemplo inteiramente fictício.
    data_teste = date(2026, 10, 15)

    abas = [
        "BASE 00",
        "Página2",
        "Cargos 10-2026",
        "Cargos 10-2026 (1)",
        "Competencias 10-2026",
    ]

    cargo = proximo_nome_aba(
        "cargos", abas, data_teste
    )

    competencia = proximo_nome_aba(
        "competencias", abas, data_teste
    )

    print("=== TESTE DE NOMES DAS ABAS ===")
    print("Próxima aba de cargos:", cargo)
    print("Próxima aba de competências:", competencia)

    assert cargo == "Cargos 10-2026 (2)"
    assert competencia == "Competencias 10-2026 (1)"

    print("Teste de numeração: OK")
    print("Nenhuma planilha foi modificada.")


if __name__ == "__main__":
    main()
