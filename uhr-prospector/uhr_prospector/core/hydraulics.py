# -*- coding: utf-8 -*-
"""Queda, circuito hidráulico, potência e energia (sem dependência do QGIS).

Todas as equações estão descritas em docs/METODOLOGIA.md.
"""
import math

RHO = 1000.0   # kg/m³
G = 9.80665    # m/s²


def quedas(na_sec_max, na_sec_min, na_p_max, na_p_min, configuracao):
    """Quedas brutas (m) conforme a posição do reservatório secundário.

    Retorna (configuracao_efetiva, h_media, h_max, h_min).
    * superior : o secundário está acima do principal.
        h_media = média(NA sec) - média(NA principal)
        h_max   = NA sec máx - NA principal mín
        h_min   = NA sec mín - NA principal máx
    * inferior : o secundário está abaixo do principal (sinais trocados).
    * automatica : decide pelo sinal de h_media na hipótese 'superior'.
    """
    m_sec = 0.5 * (na_sec_max + na_sec_min)
    m_p = 0.5 * (na_p_max + na_p_min)
    if configuracao == "automatica":
        configuracao = "secundario_superior" if m_sec >= m_p else "secundario_inferior"
    if configuracao == "secundario_superior":
        return (configuracao, m_sec - m_p, na_sec_max - na_p_min,
                na_sec_min - na_p_max)
    return (configuracao, m_p - m_sec, na_p_max - na_sec_min,
            na_p_min - na_sec_max)


def comprimento_circuito(dist_horizontal_m, h_media_m, fator_tracado):
    """Comprimento estimado do circuito: hipotenusa entre o traçado horizontal
    (distância em linha reta x fator de traçado) e a queda média."""
    lh = dist_horizontal_m * fator_tracado
    return math.hypot(lh, h_media_m)


def energia_potencia(v_util_m3, h_media_m, comprimento_m, p):
    """Dimensionamento hidráulico preliminar e energia por ciclo.

    p : objeto Parametros. Retorna dicionário com vazões, diâmetro, perdas,
    potências (MW), energias (MWh) e eficiência do ciclo.
    """
    t_g = p.horas_geracao * 3600.0
    t_b = p.horas_bombeamento * 3600.0
    q_g = v_util_m3 / t_g
    q_b = v_util_m3 / t_b
    n = max(1, int(p.n_condutos))
    # diâmetro para a velocidade de projeto na vazão de geração
    area_total = q_g / p.velocidade_projeto_m_s
    d = math.sqrt(4.0 * area_total / (n * math.pi))
    area_conduto = math.pi * d * d / 4.0

    def perda(q):
        v = q / (n * area_conduto)
        return (p.fator_atrito * comprimento_m / d + p.k_perdas_localizadas) * \
            v * v / (2.0 * G)

    hf_g = perda(q_g)
    hf_b = perda(q_b)
    h_liq_g = h_media_m - hf_g
    h_bomb = h_media_m + hf_b
    if h_liq_g <= 0:
        return None
    pot_g = p.rendimento_turbina * RHO * G * q_g * h_liq_g / 1e6
    pot_b = RHO * G * q_b * h_bomb / p.rendimento_bomba / 1e6
    e_g = pot_g * p.horas_geracao
    e_b = pot_b * p.horas_bombeamento
    return dict(
        q_geracao_m3s=q_g, q_bombeamento_m3s=q_b, diametro_m=d,
        perda_geracao_m=hf_g, perda_bombeamento_m=hf_b,
        queda_liquida_m=h_liq_g, potencia_mw=pot_g, potencia_bomba_mw=pot_b,
        energia_ciclo_mwh=e_g, energia_bombeada_mwh=e_b,
        eficiencia_ciclo=e_g / e_b if e_b > 0 else 0.0,
        energia_anual_gwh=e_g * p.ciclos_por_dia * p.dias_operacao_ano / 1000.0,
        energia_armazenada_mwh=RHO * G * v_util_m3 * h_media_m / 3.6e9,
    )
