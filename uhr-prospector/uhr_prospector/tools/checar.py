# -*- coding: utf-8 -*-
"""Verificação estática simples (substitui o pyflakes quando indisponível).

Para cada arquivo .py: compila, e procura (a) nomes globais não definidos,
(b) imports não usados. Uso:  python tools/checar.py
"""
import ast
import builtins
import os
import symtable
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def arquivos():
    for d, _, fs in os.walk(RAIZ):
        if "__pycache__" in d:
            continue
        for f in fs:
            if f.endswith(".py"):
                yield os.path.join(d, f)


def globais_nao_definidos(tabela, definidos, achados, caminho):
    for s in tabela.get_symbols():
        if s.is_global() and s.is_referenced() and s.get_name() not in definidos \
                and not hasattr(builtins, s.get_name()) and s.get_name() != "__file__":
            achados.append("%s: nome indefinido '%s' (escopo %s)" % (
                caminho, s.get_name(), tabela.get_name()))
    for filho in tabela.get_children():
        globais_nao_definidos(filho, definidos, achados, caminho)


def main():
    problemas = []
    for caminho in sorted(arquivos()):
        rel = os.path.relpath(caminho, RAIZ)
        src = open(caminho, encoding="utf-8").read()
        try:
            arvore = ast.parse(src, caminho)
            compile(src, caminho, "exec")
        except SyntaxError as e:
            problemas.append("%s: erro de sintaxe: %s" % (rel, e))
            continue
        tab = symtable.symtable(src, caminho, "exec")
        definidos = {s.get_name() for s in tab.get_symbols()
                     if s.is_assigned() or s.is_imported() or s.is_namespace()}
        globais_nao_definidos(tab, definidos, problemas, rel)
        # imports não usados
        usados = {n.id for n in ast.walk(arvore) if isinstance(n, ast.Name)} | \
                 {n.value.id for n in ast.walk(arvore)
                  if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
        for n in ast.walk(arvore):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    nome = (a.asname or a.name).split(".")[0]
                    if nome not in usados and not rel.endswith("__init__.py") \
                            and "noqa" not in src.splitlines()[n.lineno - 1]:
                        problemas.append("%s:%d: import não usado '%s'" % (rel, n.lineno, nome))
    for p in problemas:
        print(p)
    print("%d problema(s) em %d arquivos." % (len(problemas), len(list(arquivos()))))
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
