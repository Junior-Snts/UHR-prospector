# -*- coding: utf-8 -*-
"""Tarefa em segundo plano (QgsTask): a interface do QGIS não trava."""
import traceback

from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from . import workflow
from .core.pipeline import Cancelado


class ProspeccaoTask(QgsTask):
    mensagem = pyqtSignal(str)

    def __init__(self, entrada, params, ao_terminar):
        super().__init__("UHR Prospector: prospecção de reservatórios", QgsTask.CanCancel)
        self.entrada = entrada
        self.params = params
        self.ao_terminar = ao_terminar
        self.resultado = None
        self.erro = None
        self.cancelada = False

    def _progresso(self, fracao, msg):
        self.setProgress(max(0.0, min(100.0, fracao * 100.0)))
        self.mensagem.emit(msg)

    def run(self):
        try:
            self.resultado = workflow.executar_completo(
                self.entrada, self.params, self._progresso, self.isCanceled)
            return True
        except Cancelado:
            self.cancelada = True
            return False
        except Exception:  # noqa: BLE001 - repassa o traceback para a interface
            self.erro = traceback.format_exc()
            return False

    def finished(self, ok):
        # executa na thread principal
        self.ao_terminar(self, ok)
