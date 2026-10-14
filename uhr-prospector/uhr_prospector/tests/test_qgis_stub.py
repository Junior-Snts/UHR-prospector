# -*- coding: utf-8 -*-
"""Teste de fumaça das partes que dependem do QGIS, com módulos *simulados*.

NÃO valida a API real do QGIS/GDAL (isso só é possível dentro do QGIS). Serve
para pegar erros de nome, de chave de dicionário e de fluxo entre os módulos."""
import os
import sys
import types
import unittest
from unittest.mock import MagicMock


AQUI = os.path.dirname(os.path.abspath(__file__))
PAI = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)


class _Meta(type):
    def __getattr__(cls, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)
        return MagicMock()


class _Base(MagicMock, metaclass=_Meta):
    def __init__(self, *a, **k):
        super().__init__()

    def _get_child_mock(self, **kw):
        return MagicMock(**kw)


class _Modulo(types.ModuleType):
    def __getattr__(self, nome):
        if nome.startswith("__"):
            raise AttributeError(nome)
        cls = _Meta(nome, (_Base,), {})
        setattr(self, nome, cls)
        return cls


def _instalar():
    for nome in ("qgis", "qgis.core", "qgis.gui", "qgis.PyQt", "qgis.PyQt.QtCore",
                 "qgis.PyQt.QtGui", "qgis.PyQt.QtWidgets", "osgeo"):
        sys.modules[nome] = _Modulo(nome)
    class _Combo(_Base):
        def findData(self, *_):
            return 0

    sys.modules["qgis.PyQt.QtWidgets"].QComboBox = _Combo
    sys.modules["qgis.core"].Qgis = types.SimpleNamespace(QGIS_VERSION="stub")
    sys.modules["osgeo"].gdal = MagicMock()
    sys.modules["osgeo"].ogr = MagicMock()
    sys.modules["osgeo"].osr = MagicMock()
    sys.modules["qgis.PyQt.QtCore"].pyqtSignal = lambda *a, **k: MagicMock()
    sys.path.insert(0, PAI)


_instalar()
import importlib  # noqa: E402

PKG = os.path.basename(os.path.dirname(AQUI))
pk_camadas = importlib.import_module(PKG + ".camadas")
pk_dialog = importlib.import_module(PKG + ".dialog")
pk_dock = importlib.import_module(PKG + ".results_dock")
pk_plugin = importlib.import_module(PKG + ".plugin")
pk_task = importlib.import_module(PKG + ".task")
pk_params = importlib.import_module(PKG + ".core.params")
pk_pipeline = importlib.import_module(PKG + ".core.pipeline")
pk_ranking = importlib.import_module(PKG + ".core.ranking")

from test_core import PONTOS, mde_sintetico  # noqa: E402


def _resultado_falso():
    z, v, pr, tam, y0 = mde_sintetico()
    p = pk_params.Parametros(
        raio_busca_km=5.0, altura_min_m=20, altura_max_m=80, passo_altura_m=10,
        area_min_ha=10, volume_util_min_hm3=2, queda_bruta_min_m=50,
        queda_bruta_max_m=700, razao_LH_max=30, janela_reservatorio_km=3.0,
        area_contribuicao_min_ha=30, comprimento_max_m=1200)
    res = pk_pipeline.executar(z, v, tam, 0.0, y0, PONTOS, p)
    pk_ranking.ranquear(res["candidatos"])
    res.pop("grade"), res.pop("rotulos")
    res.update(poligonos_wkt={c["id"]: "MULTIPOLYGON(((0 0,1 0,1 1,0 0)))"
                              for c in res["candidatos"]},
               crs_wkt="X", busca_wkt="POLYGON((0 0,1 0,1 1,0 0))",
               tam=tam,
               res_nativa_m=tam, metodo_reamostragem="near", n_celulas=1,
               sha256_dem="x", dem_caminho="x.tif", log=["a"])
    return res


class TestFumaca(unittest.TestCase):
    def test_construir_camadas_usa_chaves_existentes(self):
        res = _resultado_falso()
        self.assertGreater(len(res["candidatos"]), 0)
        camadas = pk_camadas.construir_camadas(res)
        self.assertEqual(len(camadas), 5)

    def test_gravar_execucao_e_csv(self):
        import json
        import tempfile
        res = _resultado_falso()
        with tempfile.TemporaryDirectory() as d:
            pk_camadas.gravar_csv(res, os.path.join(d, "c.csv"))
            pk_camadas.gravar_curvas(res, os.path.join(d, "v.csv"))
            pk_camadas.gravar_execucao(res, {"a": 1}, os.path.join(d, "e.json"))
            with open(os.path.join(d, "e.json"), encoding="utf-8") as fh:
                reg = json.load(fh)
            self.assertIn("parametros", reg)
            self.assertEqual(reg["resultados"]["candidatos"], len(res["candidatos"]))
            with open(os.path.join(d, "c.csv"), encoding="utf-8-sig") as fh:
                linhas = fh.read().splitlines()
            self.assertEqual(len(linhas), 1 + len(res["candidatos"]))
            with open(os.path.join(d, "v.csv")) as fh:
                self.assertGreater(len(fh.read().splitlines()), 1)

    def test_todo_parametro_tem_widget(self):
        dlg = pk_dialog.UHRDialog(MagicMock())
        nomes = {m["nome"] for m in pk_params.metadados_campos()}
        self.assertEqual(set(dlg.widgets), nomes)

    def test_colunas_da_tabela_existem(self):
        campos = importlib.import_module(PKG + ".core.campos")
        for n in campos.COLUNAS_TABELA:
            self.assertIn(n, campos.POR_NOME)
        res = _resultado_falso()
        for c in res["candidatos"]:
            linha = campos.linha(c)
            faltando = [k for k, v in linha.items() if v is None]
            self.assertEqual(faltando, [], "campos sem valor: %s" % faltando)


if __name__ == "__main__":
    unittest.main(verbosity=2)
