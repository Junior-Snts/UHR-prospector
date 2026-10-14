# -*- coding: utf-8 -*-
"""Ponto de entrada do plugin: ação na barra/menu, diálogo e painel de resultados."""
import os

from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from . import camadas as mod_camadas
from .dialog import UHRDialog
from .results_dock import ResultadosDock

MENU = "&UHR Prospector"


class UHRProspectorPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.acao = None
        self.dialogo = None
        self.dock = None
        self.dir = os.path.dirname(__file__)

    def initGui(self):
        icone = QIcon(os.path.join(self.dir, "icon.svg"))
        self.acao = QAction(icone, "UHR Prospector", self.iface.mainWindow())
        self.acao.setToolTip("Prospecção de reservatórios secundários para UHR")
        self.acao.triggered.connect(self.executar)
        self.iface.addToolBarIcon(self.acao)
        self.iface.addPluginToMenu(MENU, self.acao)

    def unload(self):
        if self.acao is not None:
            self.iface.removePluginMenu(MENU, self.acao)
            self.iface.removeToolBarIcon(self.acao)
            self.acao = None
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        if self.dialogo is not None:
            self.dialogo.deleteLater()
            self.dialogo = None

    @staticmethod
    def _dependencias_ok(pai):
        try:
            import numpy  # noqa: F401
            import scipy.ndimage  # noqa: F401
            import scipy.spatial  # noqa: F401
            from osgeo import gdal  # noqa: F401
        except ImportError as e:
            QMessageBox.critical(
                pai, "UHR Prospector",
                "Dependência Python ausente: %s\n\nO plugin precisa de numpy, scipy "
                "e GDAL (osgeo) no Python do QGIS. No Windows, abra o 'OSGeo4W Shell' "
                "e execute: pip install scipy. No Linux: instale python3-scipy."
                % e)
            return False
        return True

    def executar(self):
        if not self._dependencias_ok(self.iface.mainWindow()):
            return
        if self.dialogo is None:
            self.dialogo = UHRDialog(self, self.iface.mainWindow())
        self.dialogo.show()
        self.dialogo.raise_()
        self.dialogo.activateWindow()

    def exibir_resultados(self, res, info, pasta_saida):
        camadas, pasta = mod_camadas.publicar(res, info, pasta_saida)
        if self.dock is None:
            self.dock = ResultadosDock(self.iface, self.iface.mainWindow())
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.definir(res, camadas)
        self.dock.show()
        for cam in camadas:
            if cam.name() == mod_camadas.NOME_CAMADA_CANDIDATOS:
                self.iface.mapCanvas().setExtent(cam.extent())
                self.iface.mapCanvas().refresh()
        msg = "%d candidatos encontrados." % len(res["candidatos"])
        if pasta:
            msg += " Arquivos em: %s" % pasta
        self.iface.messageBar().pushMessage("UHR Prospector", msg, level=Qgis.Success,
                                            duration=10)
