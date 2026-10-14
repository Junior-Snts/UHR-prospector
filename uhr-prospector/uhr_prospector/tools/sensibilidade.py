# -*- coding: utf-8 -*-
"""Análise de sensibilidade (um parâmetro por vez) em um MDE sintético.

Mostra, de forma controlada, como cada parâmetro altera cada reservatório
candidato. O terreno tem três bacias com características diferentes, ligadas ao
reservatório principal (oeste) por gargantas:

  A  bacia média, garganta estreita          (referência)
  B  bacia pequena e funda, garganta estreita
  C  bacia grande e rasa, garganta larga

Uso (a partir da pasta do plugin):
    python tools/sensibilidade.py            # imprime a tabela em Markdown
    python tools/sensibilidade.py saida.md   # grava em arquivo
    python tools/sensibilidade.py --extras   # inclui nível, resolução e ruído do MDE

Os números valem para ESTE terreno sintético: servem para entender a direção e
a ordem de grandeza dos efeitos, não para prever resultados em um caso real.
"""
import math
import os
import sys

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from core import pipeline  # noqa: E402
from core.params import Parametros  # noqa: E402

TAM = 30.0
N = 400
BACIAS = {   # nome: (cx, cy, raio, profundidade, largura_da_garganta)
    "A": (4000.0, 6000.0, 700.0, 130.0, 90.0),
    "B": (5200.0, 3000.0, 450.0, 170.0, 70.0),
    "C": (3300.0, 9000.0, 1100.0, 60.0, 160.0),
}
PONTOS = [(950.0, 3000.0), (950.0, 6000.0), (950.0, 9000.0)]


def mde():
    y0 = N * TAM
    col = (np.arange(N) + 0.5) * TAM
    lin = y0 - (np.arange(N) + 0.5) * TAM
    X, Y = np.meshgrid(col, lin)
    z = 300.0 + 0.15 * np.maximum(0.0, X - 1000.0)
    for cx, cy, raio, prof, larg in BACIAS.values():
        z -= prof * np.exp(-(np.hypot(X - cx, Y - cy) / raio) ** 2)
        faixa = (X >= 900.0) & (X <= cx)
        z -= np.where(faixa, 45.0 * np.exp(-((Y - cy) / larg) ** 2), 0.0)
    principal = (X < 1000.0) & (Y > 1500.0) & (Y < 10500.0)
    z[principal] = 300.0
    return z.astype(np.float32), np.ones(z.shape, bool), y0


BASE = dict(
    raio_busca_km=8.0, altura_min_m=20.0, altura_max_m=80.0, passo_altura_m=10.0,
    area_min_ha=10.0, area_max_ha=2000.0, volume_util_min_hm3=2.0,
    queda_bruta_min_m=50.0, queda_bruta_max_m=700.0, razao_LH_max=30.0,
    janela_reservatorio_km=3.0, area_contribuicao_min_ha=30.0,
    espacamento_sitios_m=150.0, comprimento_max_m=1200.0)

# (parâmetro, valores a testar); o valor base de cada um vem de Parametros/BASE
VARIACOES = [
    ("raio_busca_km", [2.0, 4.0, 8.0]),
    ("distancia_min_m", [100.0, 3000.0]),
    ("area_contribuicao_min_ha", [30.0, 3000.0]),
    ("espacamento_sitios_m", [150.0, 600.0]),
    ("altura_max_m", [40.0, 60.0, 80.0, 120.0]),
    ("altura_min_m", [20.0, 50.0]),
    ("passo_altura_m", [5.0, 10.0, 20.0]),
    ("borda_livre_m", [1.0, 3.0, 8.0]),
    ("comprimento_max_m", [600.0, 1200.0, 2500.0]),
    ("largura_crista_m", [8.0, 20.0]),
    ("talude_montante", [2.0, 3.0]),
    ("deplecionamento_max_m", [10.0, 20.0, 40.0]),
    ("fracao_deplecionamento_max", [0.1, 0.2, 0.3, 0.6, 0.9]),
    ("area_min_ha", [10.0, 100.0]),
    ("area_max_ha", [100.0, 2000.0]),
    ("volume_util_min_hm3", [2.0, 20.0]),
    ("razao_agua_rocha_min", [0.0, 1.0, 3.0]),
    ("janela_reservatorio_km", [1.0, 3.0]),
    ("configuracao", ["secundario_superior", "secundario_inferior"]),
    ("queda_bruta_min_m", [50.0, 300.0]),
    ("queda_bruta_max_m", [250.0, 700.0]),
    ("razao_LH_max", [5.0, 30.0]),
    ("fator_tracado", [1.0, 1.2, 2.0]),
    ("velocidade_projeto_m_s", [3.0, 5.0, 8.0]),
    ("n_condutos", [1, 2, 4]),
    ("fator_atrito", [0.010, 0.015, 0.030]),
    ("k_perdas_localizadas", [2.0, 10.0]),
    ("rendimento_turbina", [0.85, 0.90]),
    ("rendimento_bomba", [0.80, 0.88]),
    ("horas_geracao", [3.0, 6.0, 12.0]),
    ("horas_bombeamento", [8.0, 12.0]),
    ("ciclos_por_dia", [1.0, 1.7]),
    ("dias_operacao_ano", [250.0, 330.0]),
    ("eficiencia_ciclo_min", [0.60, 0.80]),
    ("criterio_selecao", ["energia", "razao_agua_rocha"]),
    ("sobreposicao_max", [0.0, 0.2, 1.0]),
]


def _rotulo_bacia(c):
    """Associa o candidato à bacia cujo centro está mais próximo do centroide."""
    return min(BACIAS, key=lambda k: math.hypot(
        c["x_centroide"] - BACIAS[k][0], c["y_centroide"] - BACIAS[k][1]))


def executar(z, v, y0, **alt):
    p = Parametros.from_dict(dict(BASE, **alt))
    erros = p.validar()
    if erros:
        return None, erros
    return pipeline.executar(z, v, TAM, 0.0, y0, PONTOS, p), []


def tabela():
    z, v, y0 = mde()
    base_p = Parametros.from_dict(BASE)
    linhas = []
    cab = ("| Parâmetro | Valor | Nº cand. | Bacia | Altura (m) | Área (ha) | V.útil (hm³) | "
           "Queda (m) | L/H | Crista (m) | V.barr. (hm³) | Água/maciço | Potência (MW) | E.ciclo (MWh) | Efic. |")
    linhas.append(cab)
    linhas.append("|" + "---|" * 15)

    def adiciona(nome, valor, res):
        if res is None or not res["candidatos"]:
            linhas.append("| `%s` | %s | %d | - | - | - | - | - | - | - | - | - | - | - | - |"
                          % (nome, valor, 0))
            return
        por_bacia = {}
        for c in res["candidatos"]:
            por_bacia.setdefault(_rotulo_bacia(c), c)
        for b in sorted(por_bacia):
            c = por_bacia[b]
            linhas.append(
                "| `%s` | %s | %d | %s | %.0f | %.0f | %.1f | %.0f | %.1f | %.0f | %.2f | %.2f | %.0f | %.0f | %.2f |"
                % (nome, valor, len(res["candidatos"]), b, c["altura_barragem_m"],
                   c["area_ha"], c["volume_util_hm3"], c["queda_bruta_m"], c["razao_L_H"],
                   c["comprimento_crista_m"], c["volume_barragem_hm3"],
                   c["razao_agua_rocha"], c["potencia_mw"], c["energia_ciclo_mwh"],
                   c["eficiencia_ciclo"]))

    res, _ = executar(z, v, y0)
    adiciona("(base)", "-", res)
    for nome, valores in VARIACOES:
        for val in valores:
            padrao = BASE.get(nome, getattr(base_p, nome))
            marca = "%s%s" % (val, " (base)" if val == padrao else "")
            res, erros = executar(z, v, y0, **{nome: val})
            if erros:
                linhas.append("| `%s` | %s | inválido | | | | | | | | | | | | |" % (nome, marca))
                continue
            adiciona(nome, marca, res)
    return "\n".join(linhas)


def _resumo(res, rotulo):
    """Linhas de tabela (uma por bacia) para os experimentos extras."""
    if res is None or not res["candidatos"]:
        return ["| %s | 0 | - | - | - | - | - | - |" % rotulo]
    por_bacia = {}
    for c in res["candidatos"]:
        por_bacia.setdefault(_rotulo_bacia(c), c)
    return ["| %s | %d | %s | %.0f | %.0f | %.1f | %.0f | %.0f |" % (
        rotulo, len(res["candidatos"]), b, c["altura_barragem_m"], c["area_ha"],
        c["volume_util_hm3"], c["queda_bruta_m"], c["energia_ciclo_mwh"])
        for b, c in sorted(por_bacia.items())]


def extras():
    """Nível do principal, resolução do MDE e ruído vertical do MDE."""
    z, v, y0 = mde()
    cab = ["| Variação | Nº cand. | Bacia | Altura (m) | Área (ha) | V.útil (hm³) | Queda (m) | E.ciclo (MWh) |",
           "|---|---|---|---|---|---|---|---|"]
    saida = []
    # 1) nível do reservatório principal (manual)
    t = list(cab)
    for na in (280.0, 300.0, 320.0):
        res, _ = executar(z, v, y0, usar_nivel_principal_manual=True,
                          nivel_principal_max_m=na, nivel_principal_min_m=na)
        t += _resumo(res, "NA do principal = %.0f m" % na)
    saida.append(("Nível do reservatório principal (manual)", t))
    # 2) resolução: média em blocos (60 m e 120 m) do MDE de 30 m
    t = list(cab)
    for f in (1, 2, 4):
        zz = z.reshape(N // f, f, N // f, f).mean(axis=(1, 3)).astype(np.float32) if f > 1 else z
        tam = TAM * f
        p = Parametros.from_dict(dict(BASE, espacamento_sitios_m=max(150.0, tam * 2)))
        res = pipeline.executar(zz, np.ones(zz.shape, bool), tam, 0.0, y0, PONTOS, p)
        t += _resumo(res, "célula de %.0f m" % tam)
    saida.append(("Resolução do MDE", t))
    # 3) ruído vertical (gaussiano, sementes fixas)
    t = list(cab)
    for sigma in (0.0, 1.0, 3.0, 6.0):
        rng = np.random.default_rng(42)
        zz = (z + rng.normal(0.0, sigma, z.shape)).astype(np.float32) if sigma else z
        res, _ = executar(zz, v, y0)
        t += _resumo(res, "ruído σ = %.0f m" % sigma)
    saida.append(("Ruído vertical do MDE", t))
    return "\n\n".join("### %s\n\n%s" % (nome, "\n".join(l)) for nome, l in saida)


if __name__ == "__main__":
    saida = tabela() + ("\n\n" + extras() if "--extras" in sys.argv else "")
    sys.argv = [a for a in sys.argv if a != "--extras"]
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(saida + "\n")
        print("Tabela gravada em", sys.argv[1])
    else:
        print(saida)
