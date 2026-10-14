# -*- coding: utf-8 -*-
"""Dicionário de dados dos candidatos: usado na tabela, nas camadas e no CSV."""

# nome, rótulo, unidade, tipo ('int' | 'float' | 'str'), casas decimais
CAMPOS = (
    ("id", "ID", "", "int", 0),
    ("posicao", "Posição", "", "int", 0),
    ("pontuacao", "Pontuação", "0-1", "float", 3),
    ("altura_barragem_m", "Altura da barragem", "m", "float", 1),
    ("cota_leito_m", "Cota do leito no eixo", "m", "float", 1),
    ("cota_crista_m", "Cota da crista", "m", "float", 1),
    ("na_max_m", "NA máximo", "m", "float", 1),
    ("na_min_m", "NA mínimo", "m", "float", 1),
    ("cota_fundo_m", "Cota do fundo", "m", "float", 1),
    ("prof_max_m", "Profundidade máxima", "m", "float", 1),
    ("deplecionamento_m", "Deplecionamento", "m", "float", 1),
    ("area_ha", "Área inundada", "ha", "float", 1),
    ("volume_total_hm3", "Volume total", "hm³", "float", 2),
    ("volume_util_hm3", "Volume útil", "hm³", "float", 2),
    ("comprimento_crista_m", "Comprimento da crista", "m", "float", 0),
    ("volume_barragem_hm3", "Volume da barragem", "hm³", "float", 2),
    ("razao_agua_rocha", "Razão água/maciço", "-", "float", 2),
    ("area_contrib_ha", "Área de contribuição", "ha", "float", 1),
    ("ponto_tomada", "Ponto de referência mais próximo", "", "int", 0),
    ("dist_borda_m", "Distância ao ponto (borda do reservatório)", "m", "float", 0),
    ("dist_centroide_m", "Distância ao ponto (centroide)", "m", "float", 0),
    ("configuracao", "Configuração", "", "str", 0),
    ("queda_bruta_m", "Queda bruta média", "m", "float", 1),
    ("queda_bruta_max_m", "Queda bruta máxima", "m", "float", 1),
    ("queda_bruta_min_m", "Queda bruta mínima", "m", "float", 1),
    ("comprimento_circuito_m", "Comprimento do circuito", "m", "float", 0),
    ("razao_L_H", "Razão L/H", "-", "float", 2),
    ("q_geracao_m3s", "Vazão de geração", "m³/s", "float", 1),
    ("diametro_m", "Diâmetro do conduto", "m", "float", 2),
    ("perda_geracao_m", "Perda de carga (geração)", "m", "float", 2),
    ("queda_liquida_m", "Queda líquida", "m", "float", 1),
    ("potencia_mw", "Potência de geração", "MW", "float", 1),
    ("potencia_bomba_mw", "Potência de bombeamento", "MW", "float", 1),
    ("energia_ciclo_mwh", "Energia por ciclo", "MWh", "float", 0),
    ("energia_bombeada_mwh", "Energia bombeada por ciclo", "MWh", "float", 0),
    ("energia_anual_gwh", "Energia anual", "GWh", "float", 1),
    ("energia_armazenada_mwh", "Energia armazenada (sem perdas)", "MWh", "float", 0),
    ("eficiencia_ciclo", "Eficiência do ciclo", "-", "float", 3),
    ("n_alturas_viaveis", "Alturas viáveis no sítio", "", "int", 0),
    ("sobreposicao", "Sobreposição com melhores", "fração", "float", 3),
    ("x_barragem", "X da barragem", "m", "float", 1),
    ("y_barragem", "Y da barragem", "m", "float", 1),
    ("x_centroide", "X do centroide", "m", "float", 1),
    ("y_centroide", "Y do centroide", "m", "float", 1),
)

# colunas exibidas por padrão na tabela da interface
COLUNAS_TABELA = (
    "posicao", "id", "pontuacao", "altura_barragem_m", "na_max_m", "area_ha",
    "volume_util_hm3", "comprimento_crista_m", "razao_agua_rocha",
    "dist_borda_m", "queda_bruta_m", "razao_L_H", "potencia_mw",
    "energia_ciclo_mwh", "energia_anual_gwh", "eficiencia_ciclo",
)

POR_NOME = {c[0]: c for c in CAMPOS}


def linha(cand):
    """Dicionário apenas com os campos documentados (ordem de CAMPOS)."""
    return {c[0]: cand.get(c[0]) for c in CAMPOS}


# motivos de descarte registrados pelo pipeline (chave -> texto legível)
MOTIVOS = {
    "sitio_sem_queda_possivel": "Sítio sem queda possível (poda antecipada, antes de simular)",
    "local_crista_longa": "Crista não fecha nas margens dentro do comprimento máximo",
    "local_sem_semente": "Sem célula inundável a montante do eixo",
    "monotono_janela": "Reservatório atinge a borda da janela de simulação",
    "monotono_area_max": "Reservatório maior que a área máxima",
    "monotono_conecta_principal": "Reservatório alcança a zona de exclusão do ponto (conexão com o principal)",
    "monotono_vazamento": "Vazamento: reservatório alcança cotas abaixo do leito do sítio",
    "queda_nao_positiva": "Queda bruta não positiva na configuração escolhida",
    "queda_liquida_nao_positiva": "Queda líquida não positiva (perdas maiores que a queda)",
    "area_menor_que_minima": "Área inundada menor que a mínima",
    "volume_util_menor_que_minimo": "Volume útil menor que o mínimo",
    "razao_agua_rocha_menor_que_minima": "Razão água/maciço menor que a mínima",
    "queda_menor_que_minima": "Queda bruta menor que a mínima",
    "queda_maior_que_maxima": "Queda bruta maior que a máxima",
    "razao_LH_acima_do_limite": "Razão L/H acima do limite",
    "eficiencia_abaixo_do_minimo": "Eficiência do ciclo abaixo do mínimo",
    "sobreposicao_com_candidato_melhor": "Sobreposição com candidato de maior prioridade",
    "acima_do_maximo_de_candidatos": "Acima do número máximo de candidatos",
}
