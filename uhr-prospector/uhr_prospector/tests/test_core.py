# -*- coding: utf-8 -*-
"""Testes do núcleo (sem QGIS). Execute:  python -m unittest tests.test_core -v
a partir da pasta que contém `uhr_prospector/`... ou, dentro da pasta do plugin,
`python -m unittest discover -s tests -v`."""
import math
import os
import sys
import unittest

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

from core import hydrology, hydraulics, pipeline, ranking, reservoir  # noqa: E402
from core.params import Parametros  # noqa: E402


PONTOS = [(950.0, 4500.0), (900.0, 3600.0)]   # pontos de referência sobre o reservatório principal


def mde_sintetico(tam=30.0, n=300):
    """Planalto inclinado para leste, reservatório principal a oeste e uma bacia
    (futuro reservatório) conectada por uma garganta estreita."""
    y0 = n * tam
    col = (np.arange(n) + 0.5) * tam
    lin = y0 - (np.arange(n) + 0.5) * tam
    X, Y = np.meshgrid(col, lin)
    z = 300.0 + 0.15 * np.maximum(0.0, X - 1000.0)
    # bacia circular fechada
    d = np.hypot(X - 4000.0, Y - 4500.0)
    z -= 130.0 * np.exp(-(d / 700.0) ** 2)
    # garganta estreita em direção ao reservatório principal
    faixa = (X >= 900.0) & (X <= 4000.0)
    z -= np.where(faixa, 45.0 * np.exp(-((Y - 4500.0) / 90.0) ** 2), 0.0)
    principal = (X < 1000.0) & (Y > 3000.0) & (Y < 6000.0)
    z[principal] = 300.0
    return z.astype(np.float32), np.ones_like(z, bool), principal, tam, y0


class TestHidrologia(unittest.TestCase):
    def test_preenchimento_e_acumulo(self):
        z = np.array([[5, 5, 5, 5, 5],
                      [5, 4, 4, 4, 5],
                      [5, 4, 1, 4, 5],
                      [5, 4, 4, 2, 3],
                      [5, 5, 5, 5, 5]], dtype=float)
        v = np.ones_like(z, bool)
        zf, rec, ordem = hydrology.preencher_e_rotear(z, v)
        # a depressão (cota 1) extravasa por (3,3)=2 -> (3,4)=3: nível de preenchimento = 3
        self.assertEqual(float(zf[2, 2]), 3.0)
        self.assertTrue(np.all(zf >= z))
        acc = hydrology.acumular_fluxo(rec, ordem)
        exutorios = rec.ravel() == -1
        self.assertAlmostEqual(float(acc.ravel()[exutorios].sum()), z.size)  # conservação de massa

    def test_nodata(self):
        z = np.arange(25, dtype=float).reshape(5, 5)
        v = np.ones_like(z, bool)
        v[2, 2] = False
        zf, rec, ordem = hydrology.preencher_e_rotear(z, v)
        self.assertTrue(np.isnan(zf[2, 2]))
        self.assertEqual(len(ordem), 24)


class TestHidraulica(unittest.TestCase):
    def test_quedas(self):
        cfg, hm, hmax, hmin = hydraulics.quedas(600, 590, 300, 298, "secundario_superior")
        self.assertEqual(cfg, "secundario_superior")
        self.assertAlmostEqual(hm, 595 - 299)
        self.assertAlmostEqual(hmax, 600 - 298)
        self.assertAlmostEqual(hmin, 590 - 300)
        cfg2, hm2, _, _ = hydraulics.quedas(100, 90, 300, 298, "automatica")
        self.assertEqual(cfg2, "secundario_inferior")
        self.assertAlmostEqual(hm2, 299 - 95)

    def test_energia_consistente(self):
        p = Parametros()
        V, H, L = 10e6, 300.0, 3000.0
        r = hydraulics.energia_potencia(V, H, L, p)
        # E = eta * rho * g * V * H_liq  (J -> MWh)
        e_ref = p.rendimento_turbina * 1000 * 9.80665 * V * r["queda_liquida_m"] / 3.6e9
        self.assertAlmostEqual(r["energia_ciclo_mwh"], e_ref, places=6)
        # continuidade e geometria do conduto
        v = r["q_geracao_m3s"] / (p.n_condutos * math.pi * r["diametro_m"] ** 2 / 4)
        self.assertAlmostEqual(v, p.velocidade_projeto_m_s, places=6)
        self.assertLess(r["eficiencia_ciclo"], p.rendimento_turbina * 1.0)
        self.assertGreater(r["eficiencia_ciclo"], 0.5)
        # perda de Darcy-Weisbach
        hf = (p.fator_atrito * L / r["diametro_m"] + p.k_perdas_localizadas) * v ** 2 / (2 * 9.80665)
        self.assertAlmostEqual(r["perda_geracao_m"], hf, places=9)


class TestBarragem(unittest.TestCase):
    def test_volume_barragem_triangulo(self):
        p = Parametros(largura_crista_m=0.0, talude_montante=2.0, talude_jusante=2.0)
        h = np.array([0.0, 10.0, 0.0])
        # seção: h²*(2+2)/2 = 200 m² no ponto central; passo 30 m
        self.assertAlmostEqual(reservoir.volume_barragem_m3(h, 30.0, p), 200.0 * 30.0)


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        z, valido, principal, tam, y0 = mde_sintetico()
        cls.z, cls.valido, cls.principal, cls.tam, cls.y0 = z, valido, principal, tam, y0
        cls.p = Parametros(
            raio_busca_km=5.0, altura_min_m=20, altura_max_m=80, passo_altura_m=10,
            area_min_ha=10, volume_util_min_hm3=2, queda_bruta_min_m=50,
            queda_bruta_max_m=700, razao_LH_max=30, janela_reservatorio_km=3.0,
            area_contribuicao_min_ha=30, espacamento_sitios_m=150, comprimento_max_m=1200)
        cls.res = pipeline.executar(z, valido, tam, 0.0, y0, PONTOS, cls.p)

    def test_encontra_candidato_na_bacia(self):
        cands = self.res["candidatos"]
        self.assertGreater(len(cands), 0, self.res["descartes"])
        c = cands[0]
        # centroide dentro da bacia (centro em x=4000, y=4500)
        self.assertLess(math.hypot(c["x_centroide"] - 4000, c["y_centroide"] - 4500), 900)

    def test_volume_confere_com_calculo_independente(self):
        c = self.res["candidatos"][0]
        g = self.res["grade"]
        rot = self.res["rotulos"] == c["id"]
        # a região rotulada é a inundação completa deste candidato (maior prioridade)
        self.assertAlmostEqual(rot.sum() * self.tam ** 2 / 1e4, c["area_ha"], places=3)
        v = np.clip(c["na_max_m"] - g.z[rot], 0, None).sum() * self.tam ** 2 / 1e6
        self.assertAlmostEqual(v, c["volume_total_hm3"], places=4)
        # toda a região está abaixo do NA máx, e nenhuma célula é do reservatório principal
        self.assertTrue(np.all(g.z[rot] <= c["na_max_m"] + 1e-6))
        self.assertFalse((rot & g.principal).any())

    def test_sem_vazamento_a_jusante_da_barragem(self):
        c = self.res["candidatos"][0]
        rot = self.res["rotulos"] == c["id"]
        (xa, ya), (xb, yb) = c["eixo"]
        self.assertGreater(c["comprimento_crista_m"], 0)
        # a bacia fica a leste (montante) do eixo da barragem
        xs = c["x_barragem"]
        cols = np.nonzero(rot.any(axis=0))[0]
        self.assertGreater((cols.min() + 0.5) * self.tam, xs - 2 * self.tam)

    def test_metricas_coerentes(self):
        for c in self.res["candidatos"]:
            self.assertGreaterEqual(c["queda_bruta_m"], self.p.queda_bruta_min_m)
            self.assertLessEqual(c["razao_L_H"], self.p.razao_LH_max)
            self.assertGreaterEqual(c["altura_barragem_m"], self.p.altura_min_m)
            self.assertLessEqual(c["altura_barragem_m"], self.p.altura_max_m)
            self.assertGreater(c["volume_util_hm3"], 0)
            self.assertLessEqual(c["volume_util_hm3"], c["volume_total_hm3"])
            # queda = cota média secundária - cota principal (300 m), superior
            esperado = 0.5 * (c["na_max_m"] + c["na_min_m"]) - 300.0
            self.assertAlmostEqual(c["queda_bruta_m"], esperado, places=6)

    def test_vale_aberto_nao_gera_reservatorio_grande(self):
        # sem a bacia, o vale é apenas uma garganta longa: nenhum candidato com
        # área >= 100 ha e volume útil >= 20 hm³ deve ser aceito
        n, tam = 300, 30.0
        col = (np.arange(n) + 0.5) * tam
        X, Y = np.meshgrid(col, n * tam - (np.arange(n) + 0.5) * tam)
        z = 300.0 + 0.15 * np.maximum(0.0, X - 1000.0)
        z -= np.where(X >= 900.0, 45.0 * np.exp(-((Y - 4500.0) / 90.0) ** 2), 0.0)
        pr = (X < 1000.0) & (Y > 3000.0) & (Y < 6000.0)
        z[pr] = 300.0
        p = Parametros(raio_busca_km=5.0, area_min_ha=100, volume_util_min_hm3=20,
                       queda_bruta_min_m=50, area_contribuicao_min_ha=30)
        r = pipeline.executar(z.astype(np.float32), np.ones_like(pr), tam, 0.0,
                              n * tam, PONTOS, p)
        self.assertEqual(len(r["candidatos"]), 0)

    def test_tomada_termina_em_ponto_de_referencia(self):
        for c in self.res["candidatos"]:
            xp, yp = c["tomada_principal_xy"]
            d = min(math.hypot(xp - x, yp - y) for x, y in PONTOS)
            self.assertLess(d, self.tam)          # centro da célula do ponto
            self.assertIn(c["ponto_tomada"], (1, 2))
            self.assertLess(c["dist_borda_m"], 5000)

    def test_nivel_automatico(self):
        na_max, na_min, origem = self.res["niveis_principal"]
        self.assertAlmostEqual(na_max, 300.0, places=3)
        self.assertEqual(na_max, na_min)
        self.assertEqual(len(self.res["niveis_por_ponto"]), len(PONTOS))

    def test_nivel_automatico_com_ponto_na_margem(self):
        # ponto na margem, com terreno mais alto (margem) e mais baixo (garganta
        # escavada abaixo da água) no círculo: a moda ainda acha a água (300 m)
        avisos = []
        g, rec, ordem, rc = pipeline.preparar_grade(
            self.z, self.valido, self.tam, 0.0, self.y0, [(1150.0, 5200.0)], self.p)
        na_max, _, _, info = pipeline.niveis_principal(g, rc, self.p, avisos)
        self.assertAlmostEqual(na_max, 300.0, delta=1.0)
        self.assertLess(info[0][2], pipeline.PLATO_MIN_FRACAO)   # platô fraco
        self.assertTrue(any("platô fraco" in a for a in avisos))

    def test_nivel_automatico_nao_e_enganado_por_canal_abaixo_da_agua(self):
        # (950, 4500): a garganta escavada (~255 m) ocupa parte do círculo,
        # mas o platô da água (300 m) é a classe dominante
        na_max, _, _ = self.res["niveis_principal"]
        self.assertAlmostEqual(na_max, 300.0, places=3)

    def test_nivel_manual(self):
        p = Parametros.from_dict(dict(self.p.to_dict(), usar_nivel_principal_manual=True,
                                      nivel_principal_max_m=301.0, nivel_principal_min_m=299.0))
        g, rec, ordem, rc = pipeline.preparar_grade(
            self.z, self.valido, self.tam, 0.0, self.y0, PONTOS, p)
        self.assertEqual(pipeline.niveis_principal(g, rc, p)[:2], (301.0, 299.0))

    def test_ponto_fora_da_grade(self):
        with self.assertRaises(ValueError):
            pipeline.executar(self.z, self.valido, self.tam, 0.0, self.y0,
                              [(-500.0, 100.0)], self.p)

    def test_sem_pontos(self):
        with self.assertRaises(ValueError):
            pipeline.executar(self.z, self.valido, self.tam, 0.0, self.y0, [], self.p)

    def test_sem_dados_ao_redor_do_ponto_exige_nivel_manual(self):
        v = self.valido.copy()
        v[:, :80] = False                      # sem dados perto dos pontos (x < 2400 m)
        with self.assertRaises(ValueError):
            pipeline.executar(self.z, v, self.tam, 0.0, self.y0, [(950.0, 4500.0)], self.p)

    def test_pontos_ampliam_a_area_de_busca(self):
        # um único ponto longe da bacia, com raio curto, não alcança nenhum sítio útil
        p = Parametros.from_dict(dict(self.p.to_dict(), raio_busca_km=1.0))
        r = pipeline.executar(self.z, self.valido, self.tam, 0.0, self.y0, PONTOS, p)
        self.assertEqual(len(r["candidatos"]), 0)

    def test_reprodutivel(self):
        res2 = pipeline.executar(self.z, self.valido, self.tam, 0.0, self.y0,
                                 PONTOS, self.p)
        a = [(c["x_barragem"], c["y_barragem"], c["altura_barragem_m"]) for c in self.res["candidatos"]]
        b = [(c["x_barragem"], c["y_barragem"], c["altura_barragem_m"]) for c in res2["candidatos"]]
        self.assertEqual(a, b)

    def test_ranking(self):
        cands = self.res["candidatos"]
        for metodo in ranking.METODOS:
            ranking.ranquear(cands, metodo=metodo)
            self.assertEqual(sorted(c["posicao"] for c in cands), list(range(1, len(cands) + 1)))
            for c in cands:
                self.assertGreaterEqual(c["pontuacao"], -1e-9)
                self.assertLessEqual(c["pontuacao"], 1 + 1e-9)

    def test_operacao_diaria_nao_pode_exceder_24h(self):
        self.assertEqual(Parametros().validar(), [])          # 1 x (6 + 8) = 14 h
        erros = Parametros(ciclos_por_dia=2.0).validar()        # 2 x 14 = 28 h
        self.assertTrue(any("24 h" in e for e in erros), erros)
        self.assertEqual(Parametros(ciclos_por_dia=1.7).validar(), [])   # 23,8 h

    def test_parametros_json(self):
        p2 = Parametros.from_json(self.p.to_json())
        self.assertEqual(p2.to_dict(), self.p.to_dict())
        self.assertEqual(Parametros().validar(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
