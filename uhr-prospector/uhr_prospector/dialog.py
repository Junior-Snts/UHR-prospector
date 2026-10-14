# -*- coding: utf-8 -*-
"""Diálogo principal: entradas, parâmetros (gerados de core/params.py) e execução."""
import json
import os

from qgis.core import (QgsApplication, QgsMapLayerProxyModel,
                       QgsRasterLayer, QgsSettings, QgsVectorLayer)
from qgis.gui import QgsFileWidget, QgsMapLayerComboBox
from qgis.PyQt.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from .core import campos
from .core.params import GRUPOS, Parametros, metadados_campos
from .task import ProspeccaoTask

CHAVE_CONFIG = "uhr_prospector/parametros"

ROTULOS_OPCOES = {
    "secundario_superior": "Secundário acima do principal",
    "secundario_inferior": "Secundário abaixo do principal",
    "automatica": "Automática (pelo sinal da queda)",
    "energia": "Maximizar a energia por ciclo",
    "razao_agua_rocha": "Maximizar a razão água/maciço",
}


class UHRDialog(QDialog):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.task = None
        self.widgets = {}
        self.setWindowTitle("UHR Prospector - prospecção de reservatórios secundários")
        self.resize(760, 760)
        raiz = QVBoxLayout(self)

        abas = QTabWidget()
        raiz.addWidget(abas, 1)
        abas.addTab(self._aba_entradas(), "Entradas")
        for grupo in GRUPOS:
            abas.addTab(self._aba_parametros(grupo), grupo)
        abas.addTab(self._aba_log(), "Execução")
        self.abas = abas

        linha = QHBoxLayout()
        for texto, slot in (("Carregar parâmetros...", self._carregar),
                            ("Salvar parâmetros...", self._salvar),
                            ("Restaurar padrões", self._padroes)):
            b = QPushButton(texto)
            b.clicked.connect(slot)
            linha.addWidget(b)
        linha.addStretch(1)
        self.btn_exec = QPushButton("Executar")
        self.btn_exec.clicked.connect(self._executar)
        self.btn_canc = QPushButton("Cancelar execução")
        self.btn_canc.setEnabled(False)
        self.btn_canc.clicked.connect(self._cancelar)
        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(self.close)
        for b in (self.btn_exec, self.btn_canc, btn_fechar):
            linha.addWidget(b)
        raiz.addLayout(linha)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        raiz.addWidget(self.barra)

        self._restaurar_ultimos()
        self._atualizar_dependencias()

    # ------------------------------------------------------------------ abas
    def _aba_entradas(self):
        w = QWidget()
        f = QFormLayout(w)
        self.cb_res = QgsMapLayerComboBox()
        self.cb_res.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.cb_dem = QgsMapLayerComboBox()
        self.cb_dem.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.chk_sel = QCheckBox("Usar apenas as feições selecionadas")
        self.saida = QgsFileWidget()
        self.saida.setStorageMode(QgsFileWidget.GetDirectory)
        self.saida.setToolTip("Pasta onde será criada uma subpasta datada com o "
                              "GeoPackage, CSVs e o registro da execução. "
                              "Vazio = apenas camadas temporárias.")
        f.addRow("Pontos de referência (tomadas):", self.cb_res)
        f.addRow("", self.chk_sel)
        f.addRow("Modelo Digital de Elevação (raster):", self.cb_dem)
        f.addRow("Pasta de saída:", self.saida)
        nota = QLabel(
            "Marque, em uma camada de pontos, um ou mais pontos próximos ao "
            "reservatório principal (por exemplo, onde poderia ficar a tomada "
            "d'água). O plugin varre o raio de busca ao redor de cada ponto. Os "
            "pontos devem estar sobre a água ou na margem; o nível do reservatório "
            "é estimado do MDE ao redor deles (ou informado na aba de nível/queda). "
            "O MDE deve ser um arquivo local com a elevação em metros; se estiver em "
            "coordenadas geográficas, é reprojetado automaticamente para UTM.")
        nota.setWordWrap(True)
        f.addRow(nota)
        return w

    def _aba_parametros(self, grupo):
        conteudo = QWidget()
        f = QFormLayout(conteudo)
        for m in metadados_campos():
            if m["grupo"] != grupo:
                continue
            w = self._criar_widget(m)
            self.widgets[m["nome"]] = w
            rotulo = m["label"] + (" [%s]" % m["unidade"] if m["unidade"] and
                                   not isinstance(w, QDoubleSpinBox) else "")
            f.addRow(rotulo + ":", w)
        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setWidget(conteudo)
        return rolagem

    def _aba_log(self):
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        return self.log

    def _criar_widget(self, m):
        padrao = m["padrao"]
        if m["opcoes"]:
            w = QComboBox()
            for o in m["opcoes"]:
                w.addItem(ROTULOS_OPCOES.get(o, o), o)
        elif isinstance(padrao, bool):
            w = QCheckBox()
            w.stateChanged.connect(self._atualizar_dependencias)
        elif isinstance(padrao, int):
            w = QSpinBox()
            w.setRange(int(m["min"]), int(m["max"]))
            w.setSingleStep(int(m["passo"] or 1))
            w.setKeyboardTracking(False)
        else:
            w = QDoubleSpinBox()
            w.setDecimals(int(m["casas"]))
            w.setRange(float(m["min"]), float(m["max"]))
            w.setSingleStep(float(m["passo"] or 1.0))
            w.setKeyboardTracking(False)
            if m["unidade"]:
                w.setSuffix(" " + m["unidade"])
        if m["dica"]:
            w.setToolTip(m["dica"])
        return w

    # -------------------------------------------------------------- parâmetros
    def _ler_params(self):
        d = {}
        for nome, w in self.widgets.items():
            if isinstance(w, QComboBox):
                d[nome] = w.currentData()
            elif isinstance(w, QCheckBox):
                d[nome] = w.isChecked()
            else:
                d[nome] = w.value()
        return Parametros.from_dict(d)

    def _definir_params(self, p):
        for nome, w in self.widgets.items():
            v = getattr(p, nome)
            if isinstance(w, QComboBox):
                i = w.findData(v)
                if i >= 0:
                    w.setCurrentIndex(i)
            elif isinstance(w, QCheckBox):
                w.setChecked(bool(v))
            else:
                w.setValue(v)
        self._atualizar_dependencias()

    def _atualizar_dependencias(self, *_):
        manual = self.widgets["usar_nivel_principal_manual"].isChecked()
        for nome in ("nivel_principal_max_m", "nivel_principal_min_m"):
            self.widgets[nome].setEnabled(manual)

    def _padroes(self):
        self._definir_params(Parametros())

    def _salvar(self):
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Salvar parâmetros", "parametros_uhr.json", "JSON (*.json)")
        if caminho:
            with open(caminho, "w", encoding="utf-8") as fh:
                fh.write(self._ler_params().to_json())

    def _carregar(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Carregar parâmetros", "", "JSON (*.json)")
        if not caminho:
            return
        try:
            with open(caminho, "r", encoding="utf-8") as fh:
                # aceita tanto o arquivo de parâmetros quanto o execucao.json
                dados = json.load(fh)
            self._definir_params(Parametros.from_dict(dados.get("parametros", dados)))
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "UHR Prospector", "Arquivo inválido: %s" % e)

    def _restaurar_ultimos(self):
        txt = QgsSettings().value(CHAVE_CONFIG, "")
        if txt:
            try:
                self._definir_params(Parametros.from_json(txt))
                return
            except Exception:  # noqa: BLE001
                pass
        self._definir_params(Parametros())

    # ----------------------------------------------------------------- execução
    def _escrever(self, msg):
        self.log.appendPlainText(msg)

    def _montar_entrada(self):
        """Extrai, na thread principal, tudo o que a tarefa precisa."""
        pts_lay = self.cb_res.currentLayer()
        dem = self.cb_dem.currentLayer()
        if not isinstance(pts_lay, QgsVectorLayer):
            raise ValueError("Selecione a camada de pontos de referência.")
        if not isinstance(dem, QgsRasterLayer):
            raise ValueError("Selecione o MDE.")
        caminho = dem.source().split("|")[0]
        if not os.path.isfile(caminho):
            raise ValueError("O MDE precisa ser um arquivo local (fonte atual: %s)."
                             % dem.source())
        feicoes = pts_lay.selectedFeatures() if self.chk_sel.isChecked() and \
            pts_lay.selectedFeatureCount() > 0 else list(pts_lay.getFeatures())
        pontos = []
        for ft in feicoes:
            if ft.hasGeometry():
                pontos.extend((v.x(), v.y()) for v in ft.geometry().vertices())
        if not pontos:
            raise ValueError("A camada de pontos não tem geometrias.")
        if len(pontos) > 200:
            raise ValueError("Pontos demais (%d); use no máximo 200." % len(pontos))
        wkt = "MULTIPOINT (%s)" % ", ".join("(%.9f %.9f)" % q for q in pontos)
        entrada = dict(dem_caminho=caminho, dem_crs_wkt=dem.crs().toWkt(),
                       pontos_wkt=wkt, pontos_crs_wkt=pts_lay.crs().toWkt())
        info = dict(camada_pontos=pts_lay.name(), n_pontos=len(pontos),
                    crs_pontos=pts_lay.crs().authid(), camada_mde=dem.name(),
                    crs_mde=dem.crs().authid())
        return entrada, info

    def _executar(self):
        if self.task is not None:
            return
        p = self._ler_params()
        erros = p.validar()
        if erros:
            QMessageBox.warning(self, "UHR Prospector",
                                "Corrija os parâmetros:\n\n- " + "\n- ".join(erros))
            return
        try:
            entrada, info = self._montar_entrada()
        except ValueError as e:
            QMessageBox.warning(self, "UHR Prospector", str(e))
            return
        QgsSettings().setValue(CHAVE_CONFIG, p.to_json())
        self.log.clear()
        self.abas.setCurrentIndex(self.abas.count() - 1)
        self._escrever("Parâmetros desta execução:\n" + p.to_json() + "\n")
        self._info, self._p = info, p
        self.task = ProspeccaoTask(entrada, p, self._terminou)
        self.task.mensagem.connect(self._escrever)
        self.task.progressChanged.connect(lambda v: self.barra.setValue(int(v)))
        self.btn_exec.setEnabled(False)
        self.btn_canc.setEnabled(True)
        QgsApplication.taskManager().addTask(self.task)

    def _cancelar(self):
        if self.task is not None:
            self._escrever("Cancelando...")
            self.task.cancel()

    def _terminou(self, task, ok):
        self.btn_exec.setEnabled(True)
        self.btn_canc.setEnabled(False)
        self.task = None
        self.barra.setValue(100 if ok else 0)
        if ok:
            res = task.resultado
            self._escrever("\nTempo total: %.1f s. Sítios avaliados: %d; com altura "
                           "viável: %d; candidatos finais: %d."
                           % (res["tempo_s"], res["n_sitios"], res["n_sitios_viaveis"],
                              len(res["candidatos"])))
            self._escrever("\nMotivos de descarte (contagem de avaliações):")
            for k, n in sorted(res["descartes"].items(), key=lambda kv: -kv[1]):
                self._escrever("  %6d  %s" % (n, campos.MOTIVOS.get(k, k)))
            if not res["candidatos"]:
                QMessageBox.information(
                    self, "UHR Prospector",
                    "Nenhum candidato atendeu aos critérios. Veja na aba Execução os "
                    "motivos de descarte e ajuste os parâmetros.")
                return
            try:
                self.plugin.exibir_resultados(res, self._info, self.saida.filePath())
            except Exception as e:  # noqa: BLE001
                self._escrever("Erro ao criar as camadas: %s" % e)
                QMessageBox.critical(self, "UHR Prospector", str(e))
        elif task.cancelada:
            self._escrever("Execução cancelada.")
        else:
            self._escrever("\nERRO:\n" + (task.erro or "desconhecido"))
            QMessageBox.critical(
                self, "UHR Prospector",
                "A execução falhou. Detalhes na aba Execução.\n\n"
                + ((task.erro or "").strip().splitlines() or ["erro desconhecido"])[-1])
