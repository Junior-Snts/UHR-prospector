# -*- coding: utf-8 -*-
"""Condicionamento hidrológico do MDE (sem dependência do QGIS).

Algoritmo: *Priority-Flood* (Barnes et al., 2014), que preenche depressões e,
no mesmo passo, define para cada célula o receptor (direção de fluxo) como a
célula vizinha pela qual ela foi descoberta. Isso garante rede de drenagem
contínua inclusive em áreas planas, e a ordem de extração da fila já é uma
ordenação topológica válida para acumular fluxo.

Referência: Barnes, R., Lehman, C., Mulla, D. (2014). Priority-flood: An optimal
depression-filling and watershed-labeling algorithm for digital elevation
models. Computers & Geosciences, 62, 117-127.
"""
import heapq

import numpy as np
from scipy import ndimage

# vizinhança 8-conexa: (dlinha, dcoluna)
VIZINHOS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def preencher_e_rotear(mde, valido):
    """Preenche depressões e calcula receptores de fluxo.

    Parâmetros
    ----------
    mde : ndarray 2D float
    valido : ndarray 2D bool, False onde não há dado (NoData)

    Retorna
    -------
    preenchido : ndarray float32, MDE sem depressões (nan onde inválido)
    receptor : ndarray int64 (índice linear da célula para onde drena; -1 =
        exutório na borda dos dados; -2 = inválido)
    ordem : ndarray int64, índices lineares na ordem em que foram extraídos
        da fila (de jusante para montante)
    """
    nl, nc = mde.shape
    W = nc + 2
    pad_v = np.zeros((nl + 2, W), dtype=bool)
    pad_v[1:-1, 1:-1] = valido
    pad_z = np.full((nl + 2, W), np.nan, dtype=np.float64)
    pad_z[1:-1, 1:-1] = np.where(valido, mde, np.nan)

    interior = ndimage.binary_erosion(pad_v, structure=np.ones((3, 3), bool),
                                      border_value=0)
    borda = pad_v & ~interior

    z = pad_z.ravel().tolist()
    fechado = bytearray((~pad_v).ravel().astype(np.uint8).tobytes())
    receptor = [-2] * len(z)
    preench = list(z)
    deslocs = [dl * W + dc for dl, dc in VIZINHOS]

    heap = []
    for idx in np.flatnonzero(borda.ravel()).tolist():
        fechado[idx] = 1
        receptor[idx] = -1
        heap.append((z[idx], idx))
    heapq.heapify(heap)

    ordem = []
    pop, push = heapq.heappop, heapq.heappush
    while heap:
        zc, c = pop(heap)
        ordem.append(c)
        for o in deslocs:
            n = c + o
            if not fechado[n]:
                fechado[n] = 1
                receptor[n] = c
                zn = z[n]
                if zn < zc:
                    zn = zc
                preench[n] = zn
                push(heap, (zn, n))

    # converte índices do array com moldura para índices do array original
    def conv(a):
        a = np.asarray(a, dtype=np.int64)
        return (a // W - 1) * nc + (a % W - 1)

    preench = np.asarray(preench, dtype=np.float64).reshape(nl + 2, W)[1:-1, 1:-1]
    rec = np.asarray(receptor, dtype=np.int64).reshape(nl + 2, W)[1:-1, 1:-1]
    rec_conv = np.where(rec >= 0, conv(np.where(rec >= 0, rec, 0)), rec)
    ordem = conv(np.asarray(ordem, dtype=np.int64))
    preench = np.where(valido, preench, np.nan).astype(np.float32)
    return preench, rec_conv, ordem


def acumular_fluxo(receptor, ordem, peso=None):
    """Acúmulo de fluxo (em número de células ou soma de pesos).

    Percorre a ordem de extração do Priority-Flood do último para o primeiro
    (de montante para jusante), somando cada célula ao seu receptor.
    """
    n = receptor.size
    rec = receptor.ravel().tolist()
    if peso is None:
        acc = [1.0] * n
    else:
        acc = np.asarray(peso, dtype=np.float64).ravel().tolist()
    for c in reversed(ordem.tolist()):
        r = rec[c]
        if r >= 0:
            acc[r] += acc[c]
    return np.asarray(acc, dtype=np.float64).reshape(receptor.shape)


def seguir_jusante(receptor, idx, passos):
    """Segue a cadeia de receptores `passos` células a jusante de `idx`.

    Retorna o índice linear final (para antes se chegar a um exutório)."""
    rec = receptor.ravel()
    atual = int(idx)
    for _ in range(passos):
        r = int(rec[atual])
        if r < 0:
            break
        atual = r
    return atual
