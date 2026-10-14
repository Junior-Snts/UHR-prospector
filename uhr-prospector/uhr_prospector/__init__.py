# -*- coding: utf-8 -*-
"""UHR Prospector - prospecção de reservatórios secundários para UHR.

Copyright (C) 2026 Antonio Claudio dos Santos Júnior

Este programa é software livre: você pode redistribuí-lo e/ou modificá-lo sob os
termos da Licença Pública Geral GNU, versão 2 da Licença ou (a seu critério)
qualquer versão posterior. Distribuído SEM QUALQUER GARANTIA; veja o arquivo
LICENSE para detalhes.
"""


def classFactory(iface):
    from .plugin import UHRProspectorPlugin
    return UHRProspectorPlugin(iface)
