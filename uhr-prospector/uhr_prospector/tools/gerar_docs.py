# -*- coding: utf-8 -*-
"""Gera docs/PARAMETROS.md e docs/DICIONARIO_DADOS.md a partir do código,
para que a documentação nunca divirja dos valores padrão reais.

Uso (a partir da pasta do plugin):  python tools/gerar_docs.py"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from core import campos, params  # noqa: E402


def main():
    docs = os.path.join(RAIZ, "docs")
    os.makedirs(docs, exist_ok=True)
    with open(os.path.join(docs, "PARAMETROS.md"), "w", encoding="utf-8") as f:
        f.write("# Parâmetros do UHR Prospector\n\n"
                "Gerado automaticamente por `tools/gerar_docs.py` a partir de "
                "`core/params.py`. Os valores padrão são pontos de partida "
                "genéricos: **devem ser justificados e ajustados** para cada "
                "estudo de caso.\n")
        f.write(params.tabela_markdown() + "\n")
    with open(os.path.join(docs, "DICIONARIO_DADOS.md"), "w", encoding="utf-8") as f:
        f.write("# Dicionário de dados dos candidatos\n\n"
                "Campos das camadas `UHR - Reservatórios candidatos`, `UHR - Eixos das "
                "barragens`, `UHR - Circuitos hidráulicos` e do arquivo "
                "`candidatos.csv`.\n\n| Campo | Descrição | Unidade | Tipo |\n|---|---|---|---|\n")
        for nome, rot, un, tipo, _ in campos.CAMPOS:
            f.write("| `%s` | %s | %s | %s |\n" % (nome, rot, un or "-", tipo))
        f.write("\n## Motivos de descarte registrados\n\n| Chave | Significado |\n|---|---|\n")
        for k, v in campos.MOTIVOS.items():
            f.write("| `%s` | %s |\n" % (k, v))
    print("docs/PARAMETROS.md e docs/DICIONARIO_DADOS.md gerados.")


if __name__ == "__main__":
    main()
