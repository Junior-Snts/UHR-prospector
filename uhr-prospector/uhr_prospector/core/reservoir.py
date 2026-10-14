# -*- coding: utf-8 -*-
"""Simulação de barragem e reservatório em um sítio (sem dependência do QGIS).

Para um sítio (célula do talvegue) e uma altura de barragem H:

1. cota da crista = cota do leito no sítio + H;  NA máx = crista - borda livre;
2. o eixo da barragem é a reta perpendicular à direção do talvegue; ele é
   prolongado para cada margem até o terreno atingir a cota da crista;
3. o reservatório é a componente 4-conexa de células com cota <= NA máx que
   contém a célula imediatamente a montante do sítio, com o eixo da barragem
   como barreira (uma linha 8-conexa bloqueia fluxo 4-conexo);
4. o reservatório é rejeitado se vazar (alcança cotas abaixo do leito do
   sítio), tocar a borda da janela de simulação, conectar-se ao reservatório
   principal ou exceder a área máxima.
"""
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from . import hydrology

TOL_VAZAMENTO_M = 1.0   # tolerância do teste de vazamento (m)
RAIO_SEMENTE_CEL = 3    # busca da célula-semente a montante do eixo (células)


@dataclass
class Grade:
    """MDE recortado, em CRS projetado (metros), com máscaras auxiliares."""
    z: np.ndarray            # float32, cota original (nan = sem dado)
    zf: np.ndarray           # float32, cota após preenchimento de depressões
    tam: float               # tamanho da célula (m)
    x0: float                # coordenada X da borda esquerda
    y0: float                # coordenada Y da borda superior
    principal: np.ndarray    # bool, reservatório principal
    dist_principal: np.ndarray  # float32, distância (m) ao reservatório principal
    zona: np.ndarray         # bool, área de busca (buffer menos reservatório)

    @property
    def forma(self):
        return self.z.shape

    def xy(self, linha, coluna):
        return (self.x0 + (coluna + 0.5) * self.tam,
                self.y0 - (linha + 0.5) * self.tam)


def _perfil_eixo(g, linha, coluna, dr, dc, zc, max_cel):
    """Amostra o eixo da barragem e acha o fechamento nas duas margens.

    Retorna (rows, cols, h) ao longo do eixo (de uma margem à outra), onde h é
    a altura da barragem em cada amostra, ou None se alguma margem não fecha
    dentro de `max_cel` células."""
    pr, pc = -dc, dr          # perpendicular ao sentido do talvegue
    nl, nc = g.forma
    lados = []
    for sinal in (1, -1):
        ks, rs, cs = [], [], []
        fechou = False
        for k in range(1, max_cel + 1):
            r = int(round(linha + sinal * k * pr))
            c = int(round(coluna + sinal * k * pc))
            if r < 0 or c < 0 or r >= nl or c >= nc:
                break
            zz = g.z[r, c]
            if not np.isfinite(zz):
                break
            ks.append(k)
            rs.append(r)
            cs.append(c)
            if zz >= zc:
                fechou = True
                break
        if not fechou:
            return None
        lados.append((rs, cs))
    (r1, c1), (r2, c2) = lados
    rows = np.array(r2[::-1] + [linha] + r1, dtype=np.int64)
    cols = np.array(c2[::-1] + [coluna] + c1, dtype=np.int64)
    h = np.maximum(zc - g.z[rows, cols], 0.0).astype(np.float64)
    return rows, cols, h


def volume_barragem_m3(h, tam, p):
    """Volume do maciço por seções trapezoidais ao longo do eixo.

    Seção: A(h) = h*B + h²*(m_mont + m_jus)/2, integrada com passo `tam`."""
    area = h * p.largura_crista_m + h * h * (p.talude_montante + p.talude_jusante) / 2.0
    return float(area.sum() * tam)


def volume_acima(zr, nivel, area_cel):
    """Volume (m³) armazenado abaixo de `nivel` na região de cotas `zr`."""
    return float(np.clip(nivel - zr, 0.0, None).sum() * area_cel)


def curva_cota_area_volume(zr, na_max, area_cel, n=25):
    """Curva cota-área-volume do reservatório (cota, área em ha, volume em hm³)."""
    niveis = np.linspace(float(zr.min()), na_max, n)
    saida = []
    for nv in niveis:
        saida.append((float(nv), float((zr <= nv).sum() * area_cel / 1e4),
                      volume_acima(zr, nv, area_cel) / 1e6))
    return saida


def simular(g, p, sitio, altura, com_regiao=False):
    """Simula barragem + reservatório em um sítio.

    sitio : dict com linha, coluna, dr, dc (direção unitária a jusante, em
            coordenadas de pixel).
    Retorna (resultado_ou_None, motivo). `motivo` é '' se válido, e quando
    inválido indica se aumentar a altura também será inviável
    ('monotono_*') ou não ('local_*')."""
    linha, coluna = sitio["linha"], sitio["coluna"]
    zleito = float(g.zf[linha, coluna])
    zc = zleito + altura
    na_max = zc - p.borda_livre_m
    tam = g.tam
    max_cel = int(p.comprimento_max_m / tam / 2.0) + 1

    perfil = _perfil_eixo(g, linha, coluna, sitio["dr"], sitio["dc"], zc, max_cel)
    if perfil is None:
        return None, "local_crista_longa"
    rows, cols, h = perfil
    comp_crista = (len(rows) - 1) * tam
    if comp_crista > p.comprimento_max_m:
        return None, "local_crista_longa"

    # janela de simulação
    raio = int(p.janela_reservatorio_km * 1000.0 / tam)
    nl, nc = g.forma
    r0, r1 = max(0, linha - raio), min(nl, linha + raio + 1)
    c0, c1 = max(0, coluna - raio), min(nc, coluna + raio + 1)
    zw = g.z[r0:r1, c0:c1]
    mask = zw <= na_max            # nan -> False
    dentro = (rows >= r0) & (rows < r1) & (cols >= c0) & (cols < c1)
    mask[rows[dentro] - r0, cols[dentro] - c0] = False   # barreira (eixo da barragem)

    # semente: célula de menor cota, a montante do eixo, perto do sítio
    sem = None
    melhor = np.inf
    for rr in range(linha - RAIO_SEMENTE_CEL, linha + RAIO_SEMENTE_CEL + 1):
        for cc in range(coluna - RAIO_SEMENTE_CEL, coluna + RAIO_SEMENTE_CEL + 1):
            if rr < r0 or rr >= r1 or cc < c0 or cc >= c1:
                continue
            if (rr - linha) * sitio["dr"] + (cc - coluna) * sitio["dc"] >= 0:
                continue   # lado de jusante ou sobre o eixo
            if mask[rr - r0, cc - c0] and zw[rr - r0, cc - c0] < melhor:
                melhor = zw[rr - r0, cc - c0]
                sem = (rr - r0, cc - c0)
    if sem is None:
        return None, "local_sem_semente"

    rot, _ = ndimage.label(mask)     # estrutura padrão = 4-conexa
    regiao = rot == rot[sem]
    n_cel = int(regiao.sum())
    area_cel = tam * tam

    # tocou a borda da janela -> maior que a janela de simulação
    if regiao[0, :].any() or regiao[-1, :].any() or regiao[:, 0].any() \
            or regiao[:, -1].any():
        return None, "monotono_janela"
    if n_cel * area_cel / 1e4 > p.area_max_ha:
        return None, "monotono_area_max"
    if g.principal[r0:r1, c0:c1][regiao].any():
        return None, "monotono_conecta_principal"
    if float(np.nanmin(g.zf[r0:r1, c0:c1][regiao])) < zleito - TOL_VAZAMENTO_M:
        return None, "monotono_vazamento"

    zr = zw[regiao]
    z_min = float(zr.min())
    prof_max = na_max - z_min
    deple = min(p.deplecionamento_max_m, p.fracao_deplecionamento_max * prof_max)
    na_min = na_max - deple
    v_tot = volume_acima(zr, na_max, area_cel)
    v_util = v_tot - volume_acima(zr, na_min, area_cel)
    v_dam = volume_barragem_m3(h, tam, p)

    rr_idx, cc_idx = np.nonzero(regiao)
    rr_idx = rr_idx + r0
    cc_idx = cc_idx + c0
    dist_reg = g.dist_principal[rr_idx, cc_idx]
    cr, cc_ = float(rr_idx.mean()), float(cc_idx.mean())
    x_c, y_c = g.xy(cr, cc_)
    xa, ya = g.xy(rows[0], cols[0])
    xb, yb = g.xy(rows[-1], cols[-1])
    xs, ys = g.xy(linha, coluna)

    res = dict(
        altura_barragem_m=float(altura), cota_leito_m=zleito, cota_crista_m=zc,
        na_max_m=na_max, na_min_m=na_min, cota_fundo_m=z_min,
        prof_max_m=prof_max, prof_media_m=v_tot / (n_cel * area_cel),
        area_ha=n_cel * area_cel / 1e4, volume_total_hm3=v_tot / 1e6,
        volume_util_hm3=v_util / 1e6, deplecionamento_m=deple,
        comprimento_crista_m=comp_crista, volume_barragem_hm3=v_dam / 1e6,
        razao_agua_rocha=(v_util / v_dam) if v_dam > 0 else 0.0,
        dist_borda_m=float(dist_reg.min()),
        dist_centroide_m=float(g.dist_principal[int(round(cr)), int(round(cc_))]),
        x_barragem=xs, y_barragem=ys, x_centroide=x_c, y_centroide=y_c,
        eixo=((xa, ya), (xb, yb)),
    )
    if com_regiao:
        res["_regiao_linear"] = np.ravel_multi_index((rr_idx, cc_idx), g.forma)
        res["_zr"] = zr
    return res, ""


def direcao_jusante(g, receptor, linha, coluna, passos):
    """Direção unitária (dr, dc) do talvegue a jusante do sítio."""
    idx = linha * g.forma[1] + coluna
    fim = hydrology.seguir_jusante(receptor, idx, passos)
    if fim == idx:
        return None
    r2, c2 = divmod(fim, g.forma[1])
    dr, dc = float(r2 - linha), float(c2 - coluna)
    n = np.hypot(dr, dc)
    if n == 0:
        return None
    return dr / n, dc / n
