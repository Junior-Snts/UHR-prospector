# -*- coding: utf-8 -*-
"""Preparação das entradas com GDAL/OGR (executa fora da thread principal).

Não importa o QGIS: recebe caminhos e WKT já extraídos pela interface.

Passos: escolhe o CRS métrico de trabalho, recorta o MDE à área de busca
(união dos círculos de raio R ao redor dos pontos de referência + margem),
reamostra se necessário (bilinear) e limita o número de células.
"""
import hashlib
import math
import os

import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()
ogr.UseExceptions()
osr.UseExceptions()

NODATA = -32768.0


def driver_vetorial_memoria():
    """Driver vetorial em memória ('Memory' até o GDAL 3.10; 'MEM' no 3.11+)."""
    for nome in ("Memory", "MEM"):
        drv = ogr.GetDriverByName(nome)
        if drv is not None:
            return drv
    raise RuntimeError("Driver vetorial em memória indisponível no GDAL.")


def _srs(wkt):
    s = osr.SpatialReference()
    s.ImportFromWkt(wkt)
    s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return s


def _metrico(srs):
    return bool(srs.IsProjected()) and abs(srs.GetLinearUnits() - 1.0) < 1e-6


def _utm_epsg(lon, lat):
    zona = int((lon + 180.0) // 6.0) + 1
    return (32600 if lat >= 0 else 32700) + zona


def sha256_arquivo(caminho, limite_mb=2048):
    """SHA-256 do arquivo (para registrar a versão exata do MDE usado)."""
    if os.path.getsize(caminho) > limite_mb * 1024 * 1024:
        return "(arquivo grande demais para calcular hash)"
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def preparar_entradas(dem_caminho, dem_crs_wkt, pontos_wkt, pontos_crs_wkt,
                      p, log=lambda m: None):
    """Retorna dicionário com as matrizes e a geometria de trabalho.

    dem_crs_wkt é usado apenas se o arquivo não tiver CRS embutido."""
    ds = gdal.Open(dem_caminho)
    banda = ds.GetRasterBand(1)
    nodata_src = banda.GetNoDataValue()
    gt = ds.GetGeoTransform()
    wkt_dem = ds.GetProjection() or dem_crs_wkt
    srs_dem = _srs(wkt_dem)

    geom = ogr.CreateGeometryFromWkt(pontos_wkt)      # MULTIPOINT
    srs_geom = _srs(pontos_crs_wkt)

    # CRS de trabalho: o do MDE se for métrico, senão UTM dos pontos
    if _metrico(srs_dem):
        srs_trab = srs_dem
        log("CRS de trabalho: o do MDE (%s)." % (srs_dem.GetName() or "projetado"))
    else:
        g_ll = geom.Clone()
        srs_ll = osr.SpatialReference()
        srs_ll.ImportFromEPSG(4326)
        srs_ll.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        g_ll.Transform(osr.CoordinateTransformation(srs_geom, srs_ll))
        cx, cy = g_ll.Centroid().GetX(), g_ll.Centroid().GetY()
        epsg = _utm_epsg(cx, cy)
        srs_trab = osr.SpatialReference()
        srs_trab.ImportFromEPSG(epsg)
        srs_trab.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        log("MDE em coordenadas geográficas/não métricas: reprojetando para "
            "UTM (EPSG:%d)." % epsg)
    wkt_trab = srs_trab.ExportToWkt()

    geom.Transform(osr.CoordinateTransformation(srs_geom, srs_trab))
    raio = p.raio_busca_km * 1000.0
    busca = geom.Buffer(raio, 32)
    xmin, xmax, ymin, ymax = geom.Buffer(raio + p.margem_dem_km * 1000.0, 8).GetEnvelope()

    # resolução de trabalho
    mesmo_crs = bool(srs_dem.IsSame(srs_trab))
    if mesmo_crs:
        res_nativa = abs(gt[1])
    else:
        lat = gt[3] + gt[5] * ds.RasterYSize / 2.0 if srs_dem.IsGeographic() else 0.0
        if srs_dem.IsGeographic():
            res_nativa = 0.5 * (abs(gt[1]) * 111320.0 * math.cos(math.radians(lat))
                                + abs(gt[5]) * 110574.0)
        else:  # projetado em outra unidade (pés etc.)
            res_nativa = abs(gt[1]) * srs_dem.GetLinearUnits()
    tam = p.resolucao_trabalho_m if p.resolucao_trabalho_m > 0 else res_nativa
    tam = round(tam, 1) if tam < 10 else round(tam)
    if tam <= 0:
        raise ValueError("Resolução de trabalho inválida.")

    def n_cel(t):
        return math.ceil((xmax - xmin) / t) * math.ceil((ymax - ymin) / t)

    if n_cel(tam) > p.max_celulas:
        t_novo = tam * math.sqrt(n_cel(tam) / p.max_celulas)
        tam = math.ceil(t_novo * 10) / 10.0
        log("Recorte com mais de %d células: resolução ajustada para %.1f m "
            "(nativa %.1f m)." % (p.max_celulas, tam, res_nativa))

    # alinhamento da grade: à grade original quando possível (evita reamostrar)
    if mesmo_crs and abs(tam - abs(gt[1])) < 1e-9:
        x_ini = gt[0] + math.floor((xmin - gt[0]) / tam) * tam
        y_fim = gt[3] - math.floor((gt[3] - ymax) / tam) * tam
        metodo = "near"
    else:
        x_ini = math.floor(xmin / tam) * tam
        y_fim = math.ceil(ymax / tam) * tam
        metodo = "bilinear"
    ncol = int(math.ceil((xmax - x_ini) / tam))
    nlin = int(math.ceil((y_fim - ymin) / tam))
    limites = (x_ini, y_fim - nlin * tam, x_ini + ncol * tam, y_fim)
    log("Grade de trabalho: %d x %d células de %.1f m (%s)." % (ncol, nlin, tam, metodo))

    opts = dict(format="MEM", outputBounds=limites, xRes=tam, yRes=tam,
                dstSRS=wkt_trab, resampleAlg=metodo, dstNodata=NODATA,
                outputType=gdal.GDT_Float32)
    if not ds.GetProjection():
        opts["srcSRS"] = wkt_dem
    if nodata_src is not None:
        opts["srcNodata"] = nodata_src
    rec = gdal.Warp("", ds, **opts)
    dem = rec.GetRasterBand(1).ReadAsArray().astype(np.float32)
    valido = np.isfinite(dem) & (dem != np.float32(NODATA))
    if valido.sum() == 0:
        raise ValueError("O MDE não cobre a área de busca (CRS ou extensão incompatível).")

    pontos_xy = [(geom.GetGeometryRef(i).GetX(), geom.GetGeometryRef(i).GetY())
                 for i in range(geom.GetGeometryCount())]
    if not pontos_xy:
        raise ValueError("Nenhum ponto de referência na camada.")
    log("%d ponto(s) de referência; raio de busca %.1f km." % (len(pontos_xy), p.raio_busca_km))

    return dict(dem=dem, valido=valido, tam=float(tam), x0=float(x_ini),
                y0=float(y_fim), pontos_xy=pontos_xy, crs_wkt=wkt_trab,
                busca_wkt=busca.ExportToWkt(),
                res_nativa_m=float(res_nativa), metodo_reamostragem=metodo)
