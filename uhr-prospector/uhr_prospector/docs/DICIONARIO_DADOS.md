# Dicionário de dados dos candidatos

Campos das camadas `UHR - Reservatórios candidatos`, `UHR - Eixos das barragens`, `UHR - Circuitos hidráulicos` e do arquivo `candidatos.csv`.

| Campo | Descrição | Unidade | Tipo |
|---|---|---|---|
| `id` | ID | - | int |
| `posicao` | Posição | - | int |
| `pontuacao` | Pontuação | 0-1 | float |
| `altura_barragem_m` | Altura da barragem | m | float |
| `cota_leito_m` | Cota do leito no eixo | m | float |
| `cota_crista_m` | Cota da crista | m | float |
| `na_max_m` | NA máximo | m | float |
| `na_min_m` | NA mínimo | m | float |
| `cota_fundo_m` | Cota do fundo | m | float |
| `prof_max_m` | Profundidade máxima | m | float |
| `deplecionamento_m` | Deplecionamento | m | float |
| `area_ha` | Área inundada | ha | float |
| `volume_total_hm3` | Volume total | hm³ | float |
| `volume_util_hm3` | Volume útil | hm³ | float |
| `comprimento_crista_m` | Comprimento da crista | m | float |
| `volume_barragem_hm3` | Volume da barragem | hm³ | float |
| `razao_agua_rocha` | Razão água/maciço | - | float |
| `area_contrib_ha` | Área de contribuição | ha | float |
| `ponto_tomada` | Ponto de referência mais próximo | - | int |
| `dist_borda_m` | Distância ao ponto (borda do reservatório) | m | float |
| `dist_centroide_m` | Distância ao ponto (centroide) | m | float |
| `configuracao` | Configuração | - | str |
| `queda_bruta_m` | Queda bruta média | m | float |
| `queda_bruta_max_m` | Queda bruta máxima | m | float |
| `queda_bruta_min_m` | Queda bruta mínima | m | float |
| `comprimento_circuito_m` | Comprimento do circuito | m | float |
| `razao_L_H` | Razão L/H | - | float |
| `q_geracao_m3s` | Vazão de geração | m³/s | float |
| `diametro_m` | Diâmetro do conduto | m | float |
| `perda_geracao_m` | Perda de carga (geração) | m | float |
| `queda_liquida_m` | Queda líquida | m | float |
| `potencia_mw` | Potência de geração | MW | float |
| `potencia_bomba_mw` | Potência de bombeamento | MW | float |
| `energia_ciclo_mwh` | Energia por ciclo | MWh | float |
| `energia_bombeada_mwh` | Energia bombeada por ciclo | MWh | float |
| `energia_anual_gwh` | Energia anual | GWh | float |
| `energia_armazenada_mwh` | Energia armazenada (sem perdas) | MWh | float |
| `eficiencia_ciclo` | Eficiência do ciclo | - | float |
| `n_alturas_viaveis` | Alturas viáveis no sítio | - | int |
| `sobreposicao` | Sobreposição com melhores | fração | float |
| `x_barragem` | X da barragem | m | float |
| `y_barragem` | Y da barragem | m | float |
| `x_centroide` | X do centroide | m | float |
| `y_centroide` | Y do centroide | m | float |

## Motivos de descarte registrados

| Chave | Significado |
|---|---|
| `sitio_sem_queda_possivel` | Sítio sem queda possível (poda antecipada, antes de simular) |
| `local_crista_longa` | Crista não fecha nas margens dentro do comprimento máximo |
| `local_sem_semente` | Sem célula inundável a montante do eixo |
| `monotono_janela` | Reservatório atinge a borda da janela de simulação |
| `monotono_area_max` | Reservatório maior que a área máxima |
| `monotono_conecta_principal` | Reservatório alcança a zona de exclusão do ponto (conexão com o principal) |
| `monotono_vazamento` | Vazamento: reservatório alcança cotas abaixo do leito do sítio |
| `queda_nao_positiva` | Queda bruta não positiva na configuração escolhida |
| `queda_liquida_nao_positiva` | Queda líquida não positiva (perdas maiores que a queda) |
| `area_menor_que_minima` | Área inundada menor que a mínima |
| `volume_util_menor_que_minimo` | Volume útil menor que o mínimo |
| `razao_agua_rocha_menor_que_minima` | Razão água/maciço menor que a mínima |
| `queda_menor_que_minima` | Queda bruta menor que a mínima |
| `queda_maior_que_maxima` | Queda bruta maior que a máxima |
| `razao_LH_acima_do_limite` | Razão L/H acima do limite |
| `eficiencia_abaixo_do_minimo` | Eficiência do ciclo abaixo do mínimo |
| `sobreposicao_com_candidato_melhor` | Sobreposição com candidato de maior prioridade |
| `acima_do_maximo_de_candidatos` | Acima do número máximo de candidatos |
