# -*- coding: utf-8 -*-
"""Fluxo completo executado na thread da tarefa: entradas -> núcleo -> vetores.

Sem dependência do QGIS (usa apenas GDAL/OGR e o núcleo)."""
import numpy as np
from osgeo import gdal, ogr, osr

from .core import pipeline, ranking
from . import raster_io


def vetorizar_rotulos(rotulos, x0, y0, tam, crs_wkt):
    """Converte o raster de rótulos em {id: WKT (MultiPolygon)}."""
    nl, nc = rotulos.shape
    mem = gdal.GetDriverByName("MEM").Create("", nc, nl, 1, gdal.GDT_Int32)
    mem.SetGeoTransform((x0, tam, 0.0, y0, 0.0, -tam))
    mem.SetProjection(crs_wkt)
    banda = mem.GetRasterBand(1)
    banda.WriteArray(rotulos.astype(np.int32))
    srs = osr.SpatialReference()
    srs.ImportFromWkt(crs_wkt)
    vds = raster_io.driver_vetorial_memoria().CreateDataSource("v")
    cam = vds.CreateLayer("v", srs, ogr.wkbPolygon)
    cam.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
    # a própria banda como máscara: rótulo 0 (fundo) é ignorado
    gdal.Polygonize(banda, banda, cam, 0, [])
    partes = {}
    for f in cam:
        partes.setdefault(f.GetField("id"), []).append(f.GetGeometryRef().Clone())
    saida = {}
    for i, geoms in partes.items():
        multi = ogr.Geometry(ogr.wkbMultiPolygon)
        for gm in geoms:
            multi.AddGeometry(gm)
        saida[int(i)] = multi.ExportToWkt()
    return saida


def executar_completo(entrada, p, progresso=None, cancelado=None):
    """entrada: dict com dem_caminho, dem_crs_wkt, pontos_wkt, pontos_crs_wkt.
    Retorna dicionário com tudo o que a interface precisa."""
    def prog(f, m):
        if progresso:
            progresso(f, m)

    mensagens = []

    def log(m):
        mensagens.append(m)
        prog(0.0, m)

    prog(0.0, "Lendo e recortando o MDE...")
    dados = raster_io.preparar_entradas(
        entrada["dem_caminho"], entrada["dem_crs_wkt"], entrada["pontos_wkt"],
        entrada["pontos_crs_wkt"], p, log=log)
    hash_dem = raster_io.sha256_arquivo(entrada["dem_caminho"])

    def prog_nucleo(f, m):
        prog(0.05 + 0.85 * f, m)

    res = pipeline.executar(
        dados["dem"], dados["valido"], dados["tam"], dados["x0"], dados["y0"],
        dados["pontos_xy"], p, progresso=prog_nucleo, cancelado=cancelado)
    ranking.ranquear(res["candidatos"])

    prog(0.93, "Vetorizando reservatórios candidatos...")
    poligonos = vetorizar_rotulos(res["rotulos"], dados["x0"], dados["y0"],
                                  dados["tam"], dados["crs_wkt"])
    prog(1.0, "Concluído.")
    res.pop("grade", None)          # grandes matrizes não são mais necessárias
    res.pop("rotulos", None)
    res.update(poligonos_wkt=poligonos, crs_wkt=dados["crs_wkt"],
               busca_wkt=dados["busca_wkt"],
               tam=dados["tam"], res_nativa_m=dados["res_nativa_m"],
               metodo_reamostragem=dados["metodo_reamostragem"],
               n_celulas=int(dados["dem"].size), sha256_dem=hash_dem,
               dem_caminho=entrada["dem_caminho"],
               log=mensagens + res["log"])
    return res
