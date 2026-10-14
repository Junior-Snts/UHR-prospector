# -*- coding: utf-8 -*-
"""Painel de resultados: tabela de candidatos, ranking multicritério e exportação."""
import csv
import json

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QAbstractItemView, QComboBox, QDockWidget, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

from . import camadas as mod_camadas
from .core import campos, ranking

ROTULOS_METODO = {"soma_ponderada": "Soma ponderada (min-max)",
                  "topsis": "TOPSIS"}


class ItemNumerico(QTableWidgetItem):
    """Item que ordena por valor numérico, não por texto."""

    def __init__(self, valor, texto):
        super().__init__(texto)
        self.valor = valor
        self.setFlags(self.flags() & ~Qt.ItemIsEditable)

    def __lt__(self, outro):
        try:
            return self.valor < outro.valor
        except (AttributeError, TypeError):
            return super().__lt__(outro)


class ResultadosDock(QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("UHR Prospector - Resultados", parent)
        self.iface = iface
        self.setObjectName("UHRProspectorResultados")
        self.candidatos = []
        self.camadas = []
        self.pesos_widgets = {}

        corpo = QWidget()
        lay = QVBoxLayout(corpo)
        self.resumo = QLabel("Sem resultados.")
        self.resumo.setWordWrap(True)
        lay.addWidget(self.resumo)

        # --- ranking
        form = QFormLayout()
        self.cb_metodo = QComboBox()
        for k in ranking.METODOS:
            self.cb_metodo.addItem(ROTULOS_METODO[k], k)
        form.addRow("Método:", self.cb_metodo)
        for campo, rotulo, sinal, peso in ranking.CRITERIOS:
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 1.0)
            sp.setSingleStep(0.05)
            sp.setDecimals(2)
            sp.setValue(peso)
            sp.setToolTip("Critério a %s." % ("maximizar" if sinal > 0 else "minimizar"))
            self.pesos_widgets[campo] = sp
            form.addRow(rotulo + (" ↑" if sinal > 0 else " ↓") + ":", sp)
        lay.addLayout(form)
        nota = QLabel("Os pesos são normalizados para somar 1. ↑ maximizar, ↓ minimizar.")
        nota.setWordWrap(True)
        lay.addWidget(nota)

        linha = QHBoxLayout()
        b_rank = QPushButton("Recalcular ranking")
        b_rank.clicked.connect(self.recalcular)
        b_csv = QPushButton("Exportar CSV...")
        b_csv.clicked.connect(self.exportar)
        linha.addWidget(b_rank)
        linha.addWidget(b_csv)
        lay.addLayout(linha)

        # --- tabela
        self.tabela = QTableWidget()
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.itemSelectionChanged.connect(self._selecionado)
        lay.addWidget(self.tabela, 1)
        self.setWidget(corpo)

    # ------------------------------------------------------------------- dados
    def definir(self, res, camadas):
        self.candidatos = res["candidatos"]
        self.camadas = camadas
        self.resumo.setText(
            "%d candidatos (de %d sítios avaliados). Clique em uma linha para "
            "localizar o candidato no mapa." % (len(self.candidatos), res["n_sitios"]))
        self._preencher()

    def _camada_candidatos(self):
        for c in self.camadas:
            if c.name() == mod_camadas.NOME_CAMADA_CANDIDATOS:
                return c
        return None

    def _preencher(self):
        cols = [campos.POR_NOME[n] for n in campos.COLUNAS_TABELA]
        self.tabela.setSortingEnabled(False)
        self.tabela.clear()
        self.tabela.setColumnCount(len(cols))
        self.tabela.setHorizontalHeaderLabels(
            [c[1] + (" (%s)" % c[2] if c[2] else "") for c in cols])
        self.tabela.setRowCount(len(self.candidatos))
        for i, cand in enumerate(self.candidatos):
            for j, (nome, _rot, _un, tipo, casas) in enumerate(cols):
                v = cand.get(nome)
                if v is None:
                    item = ItemNumerico(float("-inf"), "")
                elif tipo == "int":
                    item = ItemNumerico(int(v), str(int(v)))
                elif tipo == "float":
                    item = ItemNumerico(float(v), ("%." + str(casas) + "f") % float(v))
                else:
                    item = ItemNumerico(0, str(v))
                item.setData(Qt.UserRole, cand["id"])
                self.tabela.setItem(i, j, item)
        self.tabela.resizeColumnsToContents()
        self.tabela.setSortingEnabled(True)
        self.tabela.sortItems(0, Qt.AscendingOrder)   # coluna 0 = posição

    def _selecionado(self):
        itens = self.tabela.selectedItems()
        cam = self._camada_candidatos()
        if not itens or cam is None:
            return
        cid = itens[0].data(Qt.UserRole)
        cam.selectByExpression('"id" = %d' % int(cid))
        canvas = self.iface.mapCanvas()
        canvas.zoomToSelected(cam)
        canvas.zoomByFactor(2.5)

    # ----------------------------------------------------------------- ranking
    def pesos(self):
        return {k: w.value() for k, w in self.pesos_widgets.items()}

    def recalcular(self):
        try:
            ranking.ranquear(self.candidatos, self.pesos(), self.cb_metodo.currentData())
        except ValueError as e:
            QMessageBox.warning(self, "UHR Prospector", str(e))
            return
        mod_camadas.atualizar_ranking(self.camadas, self.candidatos)
        self._preencher()

    def exportar(self):
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Exportar candidatos", "candidatos_ranking.csv", "CSV (*.csv)")
        if not caminho:
            return
        ordem = sorted(self.candidatos, key=lambda c: c.get("posicao", 10 ** 9))
        with open(caminho, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow([c[0] for c in campos.CAMPOS])
            for cand in ordem:
                w.writerow([cand.get(c[0]) for c in campos.CAMPOS])
        with open(caminho.rsplit(".", 1)[0] + "_ranking.json", "w", encoding="utf-8") as fh:
            json.dump(dict(metodo=self.cb_metodo.currentData(), pesos=self.pesos(),
                           criterios={c[0]: ("max" if c[2] > 0 else "min")
                                      for c in ranking.CRITERIOS}),
                      fh, indent=2, ensure_ascii=False)
