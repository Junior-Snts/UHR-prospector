# -*- coding: utf-8 -*-
"""Criação das camadas QGIS e dos arquivos de saída (thread principal)."""
import csv
import json
import os
import platform
import time

from qgis.core import (
    Qgis, QgsCoordinateReferenceSystem, QgsFeature, QgsField, QgsGeometry,
    QgsLineString, QgsPalLayerSettings, QgsPointXY, QgsProject, QgsTextFormat,
    QgsTextBufferSettings, QgsVectorFileWriter, QgsVectorLayer,
    QgsVectorLayerSimpleLabeling, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

from .core import campos

GRUPO = "UHR Prospector"
NOME_CAMADA_CANDIDATOS = "UHR - Reservatórios candidatos"
VERSAO_PLUGIN = "1.1.1"


def _tipo_qvariant(t):
    return {"int": QVariant.Int, "float": QVariant.Double}.get(t, QVariant.String)


def _valor(v, tipo):
    """Converte para tipos Python nativos (QVariant não aceita numpy)."""
    if v is None:
        return None
    if tipo == "int":
        return int(v)
    if tipo == "float":
        return float(v)
    return str(v)


def _crs(wkt):
    crs = QgsCoordinateReferenceSystem()
    crs.createFromWkt(wkt)
    return crs


def _camada(nome, geometria, crs, com_campos=True):
    cam = QgsVectorLayer("%s?crs=%s" % (geometria, crs.authid() or "EPSG:4326"),
                         nome, "memory")
    cam.setCrs(crs)
    if com_campos:
        cam.dataProvider().addAttributes(
            [QgsField(c[0], _tipo_qvariant(c[3])) for c in campos.CAMPOS])
        cam.updateFields()
    return cam


def _atributos(cand):
    return [_valor(cand.get(c[0]), c[3]) for c in campos.CAMPOS]


def _estilo_poligono(cam, cor, alfa, contorno, largura=0.4, tracejado=False):
    props = {"color": "%d,%d,%d,%d" % (cor.red(), cor.green(), cor.blue(), alfa),
             "outline_color": "%d,%d,%d,255" % (contorno.red(), contorno.green(), contorno.blue()),
             "outline_width": str(largura)}
    if tracejado:
        props["outline_style"] = "dash"
    cam.renderer().setSymbol(QgsFillSymbol.createSimple(props))


def _estilo_linha(cam, cor, largura, tracejado=False):
    props = {"line_color": "%d,%d,%d,255" % (cor.red(), cor.green(), cor.blue()),
             "line_width": str(largura)}
    if tracejado:
        props["line_style"] = "dash"
    cam.renderer().setSymbol(QgsLineSymbol.createSimple(props))


def _rotulo(cam, expressao):
    s = QgsPalLayerSettings()
    s.fieldName = expressao
    s.isExpression = True
    s.enabled = True
    fmt = QgsTextFormat()
    fmt.setSize(10)
    fmt.setColor(QColor(20, 20, 20))
    buf = QgsTextBufferSettings()
    buf.setEnabled(True)
    buf.setSize(1.0)
    buf.setColor(QColor(255, 255, 255))
    fmt.setBuffer(buf)
    s.setFormat(fmt)
    cam.setLabeling(QgsVectorLayerSimpleLabeling(s))
    cam.setLabelsEnabled(True)


def construir_camadas(res):
    """Cria as camadas em memória a partir do resultado do fluxo."""
    crs = _crs(res["crs_wkt"])
    cands = res["candidatos"]

    busca = _camada("UHR - Área de busca", "Polygon", crs, com_campos=False)
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromWkt(res["busca_wkt"]))
    busca.dataProvider().addFeatures([f])
    _estilo_poligono(busca, QColor(255, 255, 255), 0, QColor(90, 90, 90), 0.5, True)

    pts = _camada("UHR - Pontos de referência", "Point", crs, com_campos=False)
    pts.dataProvider().addAttributes([QgsField("id", QVariant.Int),
                                      QgsField("cota_nivel_m", QVariant.Double)])
    pts.updateFields()
    cotas = {i: v for i, v, _ in res.get("niveis_por_ponto", [])}
    fp = []
    for i, (x, y) in enumerate(res["pontos_xy"], start=1):
        ft = QgsFeature(pts.fields())
        ft.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        ft.setAttributes([i, cotas.get(i)])
        fp.append(ft)
    pts.dataProvider().addFeatures(fp)
    pts.renderer().setSymbol(QgsMarkerSymbol.createSimple(
        {"name": "circle", "color": "230,120,20,255", "outline_color": "0,0,0,255",
         "size": "3.5"}))

    cam_res = _camada(NOME_CAMADA_CANDIDATOS, "MultiPolygon", crs)
    cam_bar = _camada("UHR - Eixos das barragens", "LineString", crs)
    cam_cir = _camada("UHR - Circuitos hidráulicos (esquemático)", "LineString", crs)
    fr, fb, fc = [], [], []
    for c in cands:
        attrs = _atributos(c)
        wkt = res["poligonos_wkt"].get(c["id"])
        if wkt:
            g = QgsGeometry.fromWkt(wkt)
            if not g.isMultipart():
                g.convertToMultiType()
            ft = QgsFeature(cam_res.fields())
            ft.setGeometry(g)
            ft.setAttributes(attrs)
            fr.append(ft)
        (xa, ya), (xb, yb) = c["eixo"]
        ft = QgsFeature(cam_bar.fields())
        ft.setGeometry(QgsGeometry(QgsLineString([QgsPointXY(xa, ya), QgsPointXY(xb, yb)])))
        ft.setAttributes(attrs)
        fb.append(ft)
        (xt, yt), (xp, yp) = c["tomada_xy"], c["tomada_principal_xy"]
        ft = QgsFeature(cam_cir.fields())
        ft.setGeometry(QgsGeometry(QgsLineString([QgsPointXY(xt, yt), QgsPointXY(xp, yp)])))
        ft.setAttributes(attrs)
        fc.append(ft)
    cam_res.dataProvider().addFeatures(fr)
    cam_bar.dataProvider().addFeatures(fb)
    cam_cir.dataProvider().addFeatures(fc)
    _estilo_poligono(cam_res, QColor(40, 120, 200), 110, QColor(10, 60, 130), 0.5)
    _estilo_linha(cam_bar, QColor(200, 30, 30), 1.2)
    _estilo_linha(cam_cir, QColor(60, 60, 60), 0.6, True)
    _rotulo(cam_res, "'#' || \"posicao\"")
    for cam in (busca, pts, cam_res, cam_bar, cam_cir):
        cam.updateExtents()
    # ordem de desenho: de baixo para cima
    return [cam_cir, cam_bar, cam_res, pts, busca]


def _gravar_gpkg(camadas, caminho):
    """Grava as camadas em um GeoPackage e devolve as camadas carregadas dele."""
    ctx = QgsProject.instance().transformContext()
    for i, cam in enumerate(camadas):
        op = QgsVectorFileWriter.SaveVectorOptions()
        op.driverName = "GPKG"
        op.layerName = cam.name()
        op.actionOnExistingFile = (QgsVectorFileWriter.CreateOrOverwriteFile if i == 0
                                   else QgsVectorFileWriter.CreateOrOverwriteLayer)
        r = QgsVectorFileWriter.writeAsVectorFormatV3(cam, caminho, ctx, op)
        if r[0] != QgsVectorFileWriter.NoError:
            raise RuntimeError("Falha ao gravar '%s' no GeoPackage: %s" % (cam.name(), r[1]))
    saida = []
    for cam in camadas:
        nova = QgsVectorLayer("%s|layername=%s" % (caminho, cam.name()), cam.name(), "ogr")
        if not nova.isValid():
            raise RuntimeError("Não foi possível reabrir a camada '%s'." % cam.name())
        nova.setRenderer(cam.renderer().clone())
        if cam.labeling() is not None:
            nova.setLabeling(cam.labeling().clone())
            nova.setLabelsEnabled(True)
        saida.append(nova)
    return saida


def gravar_csv(res, caminho):
    with open(caminho, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow([c[0] for c in campos.CAMPOS])
        for cand in res["candidatos"]:
            w.writerow([cand.get(c[0]) for c in campos.CAMPOS])


def gravar_curvas(res, caminho):
    with open(caminho, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "cota_m", "area_ha", "volume_hm3"])
        for cand in res["candidatos"]:
            for cota, area, vol in cand.get("_curva", []):
                w.writerow([cand["id"], "%.2f" % cota, "%.3f" % area, "%.4f" % vol])


def gravar_execucao(res, entrada_info, caminho):
    """Registro de reprodutibilidade: parâmetros, versões, hashes e descartes."""
    na_max, na_min, origem = res["niveis_principal"]
    reg = dict(
        plugin="UHR Prospector", versao_plugin=VERSAO_PLUGIN,
        versao_metodo=res["versao_metodo"], data_hora=time.strftime("%Y-%m-%d %H:%M:%S"),
        qgis=Qgis.QGIS_VERSION, python=platform.python_version(),
        sistema=platform.platform(),
        entradas=dict(entrada_info, dem_arquivo=res["dem_caminho"],
                      dem_sha256=res["sha256_dem"]),
        grade=dict(tamanho_celula_m=res["tam"], resolucao_nativa_m=res["res_nativa_m"],
                   reamostragem=res["metodo_reamostragem"], celulas=res["n_celulas"],
                   crs_wkt=res["crs_wkt"]),
        niveis_principal=dict(na_max_m=na_max, na_min_m=na_min, origem=origem,
                              por_ponto=[dict(ponto=i, cota_m=v, fracao_plato=f)
                                         for i, v, f in res["niveis_por_ponto"]]),
        pontos_referencia=[dict(id=i, x=x, y=y)
                           for i, (x, y) in enumerate(res["pontos_xy"], start=1)],
        avisos=res["avisos"],
        resultados=dict(sitios_avaliados=res["n_sitios"],
                        sitios_com_altura_viavel=res["n_sitios_viaveis"],
                        candidatos=len(res["candidatos"]), tempo_s=res["tempo_s"]),
        descartes=res["descartes"], parametros=res["parametros"])
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(reg, fh, indent=2, ensure_ascii=False)


def publicar(res, entrada_info, pasta_saida):
    """Cria camadas, grava arquivos (se houver pasta) e adiciona ao projeto.

    Retorna (camadas_no_projeto, pasta_da_execucao_ou_None)."""
    camadas = construir_camadas(res)
    pasta_exec = None
    if pasta_saida:
        pasta_exec = os.path.join(pasta_saida, "uhr_prospector_" + time.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(pasta_exec, exist_ok=True)
        camadas = _gravar_gpkg(camadas, os.path.join(pasta_exec, "resultados.gpkg"))
        gravar_csv(res, os.path.join(pasta_exec, "candidatos.csv"))
        gravar_curvas(res, os.path.join(pasta_exec, "curvas_cota_area_volume.csv"))
        gravar_execucao(res, entrada_info, os.path.join(pasta_exec, "execucao.json"))
        with open(os.path.join(pasta_exec, "log.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(res["log"]))
    proj = QgsProject.instance()
    raiz = proj.layerTreeRoot()
    grupo = raiz.insertGroup(0, GRUPO + time.strftime(" %H:%M:%S"))
    for cam in camadas:
        proj.addMapLayer(cam, False)
        grupo.addLayer(cam)
    return camadas, pasta_exec


def atualizar_ranking(camadas, candidatos):
    """Grava posicao/pontuacao nas camadas de candidatos."""
    por_id = {c["id"]: c for c in candidatos}
    for cam in camadas:
        i_pos = cam.fields().indexOf("posicao")
        i_pt = cam.fields().indexOf("pontuacao")
        i_id = cam.fields().indexOf("id")
        if min(i_pos, i_pt, i_id) < 0:
            continue
        mud = {}
        for ft in cam.getFeatures():
            c = por_id.get(ft.attribute(i_id))
            if c is not None:
                mud[ft.id()] = {i_pos: int(c["posicao"]), i_pt: float(c["pontuacao"])}
        cam.dataProvider().changeAttributeValues(mud)
        cam.triggerRepaint()
