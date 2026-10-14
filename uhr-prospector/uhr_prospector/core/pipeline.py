# -*- coding: utf-8 -*-
"""Pipeline de prospecção (sem dependência do QGIS).

Etapas (cada uma corresponde a uma seção de docs/METODOLOGIA.md):
  1. área de busca (círculos ao redor dos pontos de referência) e níveis do principal;
  2. condicionamento hidrológico (Priority-Flood), acúmulo de fluxo e talvegues;
  3. seleção de sítios de barragem ao longo dos talvegues;
  4. para cada sítio e altura: barragem, reservatório, volumes (reservoir.py);
  5. queda, circuito, potência e energia (hydraulics.py) e filtros;
  6. melhor altura por sítio, eliminação de sobreposições e numeração.
"""
import time
from collections import Counter

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from . import hydrology, hydraulics, reservoir
from .reservoir import Grade

VERSAO_METODO = "1.1"


class Cancelado(Exception):
    pass


def pontos_para_celulas(pontos_xy, forma, x0, y0, tam):
    """Converte coordenadas (x, y) em (linha, coluna); erro se algum ponto cair fora."""
    nl, nc = forma
    rc = []
    for i, (x, y) in enumerate(pontos_xy, start=1):
        c = int(np.floor((x - x0) / tam))
        r = int(np.floor((y0 - y) / tam))
        if r < 0 or c < 0 or r >= nl or c >= nc:
            raise ValueError("O ponto de referência %d está fora da grade do MDE." % i)
        rc.append((r, c))
    return rc


def preparar_grade(dem, valido, tam, x0, y0, pontos_xy, p):
    """Monta a Grade: preenche depressões, calcula distâncias e a área de busca.

    * dist_principal : distância (m) de cada célula ao ponto de referência mais
      próximo (centro do ponto);
    * principal : zona de exclusão, círculo de raio `raio_ponto_m` em cada ponto
      (ao menos a própria célula do ponto);
    * zona : células válidas a até `raio_busca_km` de algum ponto, fora da
      zona de exclusão.
    Retorna (grade, receptor, ordem, pontos_rc)."""
    pontos_rc = pontos_para_celulas(pontos_xy, dem.shape, x0, y0, tam)
    dem = np.where(valido, dem, np.nan).astype(np.float32)
    zf, receptor, ordem = hydrology.preencher_e_rotear(dem, valido)
    celulas_ponto = np.zeros(dem.shape, dtype=bool)
    for r, c in pontos_rc:
        celulas_ponto[r, c] = True
    dist = ndimage.distance_transform_edt(~celulas_ponto, sampling=tam).astype(np.float32)
    principal = (dist <= p.raio_ponto_m) | celulas_ponto
    zona = (dist <= p.raio_busca_km * 1000.0) & ~principal & valido
    g = Grade(z=dem, zf=zf, tam=float(tam), x0=float(x0), y0=float(y0),
              principal=principal, dist_principal=dist, zona=zona)
    return g, receptor, ordem, pontos_rc


BIN_NIVEL_M = 1.0          # largura da classe do histograma de cotas (m)
PLATO_MIN_FRACAO = 0.15    # abaixo disto o platô é considerado fraco (aviso)


def _nivel_plato(zz):
    """Cota do platô (moda) de um conjunto de cotas.

    Histograma com classes de BIN_NIVEL_M; devolve a mediana das cotas da classe
    mais populosa (empate: a mais baixa) e a fração de células nessa classe."""
    cls = np.floor(zz / BIN_NIVEL_M).astype(np.int64)
    valores, contagens = np.unique(cls, return_counts=True)
    k = int(np.argmax(contagens))        # argmax devolve a primeira (mais baixa)
    dentro = zz[cls == valores[k]]
    return float(np.median(dentro)), float(contagens[k]) / zz.size


def niveis_principal(g, pontos_rc, p, avisos=None):
    """NA máx/mín do reservatório principal.

    Manual: valores informados. Automático: para cada ponto, o platô de cota
    mais frequente entre as células válidas do MDE em um círculo de raio
    `raio_amostragem_nivel_m` (a água aparece como superfície plana no MDE e
    forma a classe dominante, mesmo que haja terreno mais alto - margem - ou
    mais baixo - canal a jusante - no círculo). O nível é a mediana entre os
    pontos (NA máximo = NA mínimo).
    Retorna (na_max, na_min, origem, [(ponto, cota, fracao_do_plato)])."""
    if p.usar_nivel_principal_manual:
        return p.nivel_principal_max_m, p.nivel_principal_min_m, "manual", []
    nl, nc = g.forma
    raio = p.raio_amostragem_nivel_m
    rc = int(np.ceil(raio / g.tam))
    por_ponto = []
    for i, (r, c) in enumerate(pontos_rc, start=1):
        r0, r1 = max(0, r - rc), min(nl, r + rc + 1)
        c0, c1 = max(0, c - rc), min(nc, c + rc + 1)
        jj, ii = np.meshgrid(np.arange(c0, c1), np.arange(r0, r1))
        dentro = np.hypot((ii - r) * g.tam, (jj - c) * g.tam) <= raio
        zz = g.z[r0:r1, c0:c1][dentro]
        zz = zz[np.isfinite(zz)]
        if zz.size == 0:
            if avisos is not None:
                avisos.append("Ponto %d: sem dados do MDE no raio de amostragem." % i)
            continue
        cota, frac = _nivel_plato(zz)
        por_ponto.append((i, cota, frac))
        if frac < PLATO_MIN_FRACAO and avisos is not None:
            avisos.append("Aviso: ponto %d com platô fraco (%.0f%% das células na cota "
                          "%.1f m); o ponto pode estar longe da água. Confira o nível "
                          "ou informe-o manualmente." % (i, 100 * frac, cota))
    if not por_ponto:
        raise ValueError("O MDE não tem dados ao redor dos pontos de referência. "
                         "Informe os níveis do reservatório principal manualmente.")
    valores = [v for _, v, _ in por_ponto]
    if max(valores) - min(valores) > 5.0 and avisos is not None:
        avisos.append("Aviso: os níveis estimados nos pontos diferem em %.1f m; "
                      "confira se todos os pontos estão no mesmo reservatório."
                      % (max(valores) - min(valores)))
    med = float(np.median(valores))
    return med, med, "platô de cota mais frequente em %g m ao redor dos pontos (mediana)" % raio, \
        por_ponto


def selecionar_sitios(g, receptor, acc_ha, p):
    """Células de talvegue (acúmulo >= limiar) dentro da zona de busca,
    espaçadas de `espacamento_sitios_m`. Prioriza maior área de contribuição."""
    cand = g.zona & (acc_ha >= p.area_contribuicao_min_ha) & \
        (g.dist_principal >= p.distancia_min_m)
    rr, cc = np.nonzero(cand)
    if rr.size == 0:
        return []
    ordem = np.argsort(-acc_ha[rr, cc], kind="stable")
    rr, cc = rr[ordem], cc[ordem]
    esp = p.espacamento_sitios_m
    balde = {}
    passos = max(3, int(round(100.0 / g.tam)))
    sitios = []
    for r, c in zip(rr.tolist(), cc.tolist()):
        x, y = c * g.tam, r * g.tam
        bx, by = int(x // esp), int(y // esp)
        ocupado = False
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for (xo, yo) in balde.get((bx + i, by + j), ()):
                    if (xo - x) ** 2 + (yo - y) ** 2 < esp * esp:
                        ocupado = True
                        break
                if ocupado:
                    break
            if ocupado:
                break
        if ocupado:
            continue
        d = reservoir.direcao_jusante(g, receptor, r, c, passos)
        if d is None:
            continue
        balde.setdefault((bx, by), []).append((x, y))
        sitios.append(dict(linha=r, coluna=c, dr=d[0], dc=d[1],
                           area_contrib_ha=float(acc_ha[r, c])))
    return sitios


def _passa_filtros(cand, p, desc):
    """Filtros geométricos, hidráulicos e volumétricos. Registra o motivo."""
    if cand["area_ha"] < p.area_min_ha:
        desc["area_menor_que_minima"] += 1
        return False
    if cand["volume_util_hm3"] < p.volume_util_min_hm3:
        desc["volume_util_menor_que_minimo"] += 1
        return False
    if p.razao_agua_rocha_min > 0 and cand["razao_agua_rocha"] < p.razao_agua_rocha_min:
        desc["razao_agua_rocha_menor_que_minima"] += 1
        return False
    if cand["queda_bruta_m"] < p.queda_bruta_min_m:
        desc["queda_menor_que_minima"] += 1
        return False
    if cand["queda_bruta_m"] > p.queda_bruta_max_m:
        desc["queda_maior_que_maxima"] += 1
        return False
    if cand["razao_L_H"] > p.razao_LH_max:
        desc["razao_LH_acima_do_limite"] += 1
        return False
    if cand["eficiencia_ciclo"] < p.eficiencia_ciclo_min:
        desc["eficiencia_abaixo_do_minimo"] += 1
        return False
    return True


def _chave(cand, criterio):
    return cand["energia_ciclo_mwh"] if criterio == "energia" else cand["razao_agua_rocha"]


def _completar(res, p, na_p_max, na_p_min):
    """Acrescenta queda, circuito, potência e energia ao resultado do sítio."""
    cfg, h_med, h_max, h_min = hydraulics.quedas(
        res["na_max_m"], res["na_min_m"], na_p_max, na_p_min, p.configuracao)
    if h_med <= 0:
        return None, "queda_nao_positiva"
    L = hydraulics.comprimento_circuito(res["dist_borda_m"], h_med, p.fator_tracado)
    hid = hydraulics.energia_potencia(res["volume_util_hm3"] * 1e6, h_med, L, p)
    if hid is None:
        return None, "queda_liquida_nao_positiva"
    res.update(configuracao=cfg, queda_bruta_m=h_med, queda_bruta_max_m=h_max,
               queda_bruta_min_m=h_min, comprimento_circuito_m=L,
               razao_L_H=L / h_med)
    res.update(hid)
    return res, ""


def executar(dem, valido, tam, x0, y0, pontos_xy, p, progresso=None, cancelado=None):
    """Executa a prospecção completa. Retorna dicionário de resultados.

    dem, valido : arrays 2D alinhados (CRS projetado, metros)
    tam : tamanho da célula (m); x0, y0 : canto superior esquerdo
    pontos_xy : lista de (x, y) dos pontos de referência (tomadas) no mesmo CRS
    progresso(fracao, mensagem) e cancelado() são opcionais.
    """
    t0 = time.time()
    log = []

    def avisa(frac, msg):
        log.append(msg)
        if progresso:
            progresso(frac, msg)

    def checa():
        if cancelado and cancelado():
            raise Cancelado()

    erros = p.validar()
    if erros:
        raise ValueError("Parâmetros inválidos:\n- " + "\n- ".join(erros))
    if not len(pontos_xy):
        raise ValueError("Informe ao menos um ponto de referência.")

    avisa(0.02, "Condicionando o MDE (preenchimento de depressões, %d células)..."
          % dem.size)
    g, receptor, ordem, pontos_rc = preparar_grade(dem, valido, tam, x0, y0, pontos_xy, p)
    checa()
    avisa(0.15, "Calculando acúmulo de fluxo...")
    acc = hydrology.acumular_fluxo(receptor, ordem)
    acc_ha = acc * (tam * tam) / 1e4
    checa()

    avisos = []
    na_p_max, na_p_min, origem_nivel, por_ponto = niveis_principal(g, pontos_rc, p, avisos)
    avisa(0.2, "Níveis do reservatório principal: NA máx %.2f m, NA mín %.2f m (%s)."
          % (na_p_max, na_p_min, origem_nivel))
    for i, v, frac in por_ponto:
        avisa(0.2, "  ponto %d: cota estimada %.2f m (platô com %.0f%% das células)"
              % (i, v, 100 * frac))
    for a in avisos:
        avisa(0.2, a)

    sitios = selecionar_sitios(g, receptor, acc_ha, p)
    avisa(0.22, "%d sítios de barragem a avaliar." % len(sitios))

    alturas = np.arange(p.altura_min_m, p.altura_max_m + 1e-9, p.passo_altura_m)
    desc = Counter()
    por_sitio = []
    n = max(1, len(sitios))
    for i, s in enumerate(sitios):
        checa()
        if i % 10 == 0:
            avisa(0.22 + 0.6 * i / n, "Avaliando sítio %d de %d..." % (i + 1, n))
        zleito = float(g.zf[s["linha"], s["coluna"]])
        # poda: a queda máxima possível neste sítio já é insuficiente?
        m_p = 0.5 * (na_p_max + na_p_min)
        sup = (zleito + p.altura_max_m - p.borda_livre_m) - m_p
        inf = m_p - zleito
        if p.configuracao == "secundario_superior":
            viavel = sup >= p.queda_bruta_min_m
        elif p.configuracao == "secundario_inferior":
            viavel = inf >= p.queda_bruta_min_m
        else:
            viavel = max(sup, inf) >= p.queda_bruta_min_m
        if not viavel:
            desc["sitio_sem_queda_possivel"] += 1
            continue
        melhores = []
        for H in alturas:
            res, motivo = reservoir.simular(g, p, s, float(H))
            if res is None:
                desc[motivo] += 1
                if motivo.startswith("monotono"):
                    break
                continue
            res, motivo = _completar(res, p, na_p_max, na_p_min)
            if res is None:
                desc[motivo] += 1
                continue
            res["area_contrib_ha"] = s["area_contrib_ha"]
            if _passa_filtros(res, p, desc):
                melhores.append(res)
        if melhores:
            melhor = max(melhores, key=lambda c: _chave(c, p.criterio_selecao))
            melhor["_sitio"] = s
            melhor["n_alturas_viaveis"] = len(melhores)
            por_sitio.append(melhor)

    avisa(0.85, "%d sítios com ao menos uma altura viável. Eliminando sobreposições..."
          % len(por_sitio))
    por_sitio.sort(key=lambda c: -_chave(c, p.criterio_selecao))
    # centros das células dos pontos (mesma referência de g.xy / dist_principal)
    centros = np.array([g.xy(r, c) for r, c in pontos_rc], dtype=float)
    arvore = cKDTree(centros)
    ocupacao = np.zeros(g.forma, dtype=bool)
    rotulos = np.zeros(g.forma, dtype=np.int32)
    aceitos = []
    for c in por_sitio:
        checa()
        if len(aceitos) >= p.max_candidatos:
            desc["acima_do_maximo_de_candidatos"] += 1
            continue
        res, _ = reservoir.simular(g, p, c["_sitio"], c["altura_barragem_m"],
                                   com_regiao=True)
        if res is None:     # não deveria ocorrer (determinístico)
            continue
        idx = res["_regiao_linear"]
        sob = float(ocupacao.ravel()[idx].mean())
        if sob > p.sobreposicao_max:
            desc["sobreposicao_com_candidato_melhor"] += 1
            continue
        c["sobreposicao"] = sob
        c["id"] = len(aceitos) + 1
        c["_curva"] = reservoir.curva_cota_area_volume(
            res["_zr"], res["na_max_m"], tam * tam)
        # extremos do circuito: célula do candidato mais próxima de um ponto de
        # referência (tomada no secundário) e esse ponto (tomada no principal)
        k = int(np.argmin(g.dist_principal.ravel()[idx]))
        rt, ct = divmod(int(idx[k]), g.forma[1])
        c["tomada_xy"] = g.xy(rt, ct)
        _, j = arvore.query(c["tomada_xy"])
        c["ponto_tomada"] = int(j) + 1
        c["tomada_principal_xy"] = (float(centros[j][0]), float(centros[j][1]))
        livres = ~ocupacao.ravel()[idx]
        rotulos.ravel()[idx[livres]] = c["id"]
        ocupacao.ravel()[idx] = True
        aceitos.append(c)

    avisa(0.98, "%d candidatos finais." % len(aceitos))
    return dict(
        candidatos=aceitos, rotulos=rotulos, grade=g, log=log,
        descartes=dict(desc), n_sitios=len(sitios), n_sitios_viaveis=len(por_sitio),
        niveis_principal=(na_p_max, na_p_min, origem_nivel),
        niveis_por_ponto=por_ponto, pontos_xy=[tuple(map(float, q)) for q in pontos_xy],
        avisos=avisos,
        parametros=p.to_dict(), versao_metodo=VERSAO_METODO,
        tempo_s=time.time() - t0,
    )
