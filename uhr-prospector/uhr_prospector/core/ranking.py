# -*- coding: utf-8 -*-
"""Ranking multicritério dos candidatos (sem dependência do QGIS).

Dois métodos, ambos com normalização explícita e pesos definidos pelo usuário:

* soma ponderada (WSM) com normalização min-max;
* TOPSIS (Hwang & Yoon, 1981) com normalização vetorial.

Os critérios, sua direção (maximizar/minimizar) e os pesos padrão ficam em
CRITERIOS, e são os mesmos usados pela tabela da interface.
"""
import math

# campo, rótulo, direção (+1 maximizar / -1 minimizar), peso padrão
CRITERIOS = (
    ("energia_ciclo_mwh", "Energia por ciclo (MWh)", +1, 0.25),
    ("potencia_mw", "Potência (MW)", +1, 0.15),
    ("queda_bruta_m", "Queda bruta média (m)", +1, 0.10),
    ("razao_L_H", "Razão L/H", -1, 0.15),
    ("razao_agua_rocha", "Razão água/maciço", +1, 0.20),
    ("eficiencia_ciclo", "Eficiência do ciclo", +1, 0.05),
    ("comprimento_crista_m", "Comprimento da crista (m)", -1, 0.10),
)

METODOS = ("soma_ponderada", "topsis")


def pesos_padrao():
    return {c[0]: c[3] for c in CRITERIOS}


def _normalizar_pesos(pesos):
    s = sum(max(0.0, v) for v in pesos.values())
    if s <= 0:
        raise ValueError("A soma dos pesos deve ser positiva.")
    return {k: max(0.0, v) / s for k, v in pesos.items()}


def ranquear(candidatos, pesos=None, metodo="soma_ponderada"):
    """Calcula `pontuacao` e `posicao` (1 = melhor) em cada dicionário.

    Modifica e devolve a mesma lista. Com um único candidato, a pontuação é 1."""
    if metodo not in METODOS:
        raise ValueError("Método desconhecido: %s" % metodo)
    if not candidatos:
        return candidatos
    pesos = _normalizar_pesos(pesos or pesos_padrao())
    campos = [(c[0], c[2]) for c in CRITERIOS if pesos.get(c[0], 0) > 0]
    n = len(candidatos)

    if metodo == "soma_ponderada":
        escore = [0.0] * n
        for campo, sinal in campos:
            v = [c[campo] for c in candidatos]
            lo, hi = min(v), max(v)
            for i, x in enumerate(v):
                if hi == lo:
                    norm = 1.0
                else:
                    norm = (x - lo) / (hi - lo)
                    if sinal < 0:
                        norm = 1.0 - norm
                escore[i] += pesos[campo] * norm
    else:  # TOPSIS
        mat = []
        for campo, sinal in campos:
            v = [c[campo] for c in candidatos]
            nrm = math.sqrt(sum(x * x for x in v)) or 1.0
            mat.append([pesos[campo] * x / nrm for x in v])
        ideal, anti = [], []
        for (campo, sinal), col in zip(campos, mat):
            ideal.append(max(col) if sinal > 0 else min(col))
            anti.append(min(col) if sinal > 0 else max(col))
        escore = []
        for i in range(n):
            dp = math.sqrt(sum((mat[k][i] - ideal[k]) ** 2 for k in range(len(campos))))
            dn = math.sqrt(sum((mat[k][i] - anti[k]) ** 2 for k in range(len(campos))))
            escore.append(dn / (dp + dn) if (dp + dn) > 0 else 1.0)

    ordem = sorted(range(n), key=lambda i: -escore[i])
    for pos, i in enumerate(ordem, start=1):
        candidatos[i]["pontuacao"] = escore[i]
        candidatos[i]["posicao"] = pos
    return candidatos
