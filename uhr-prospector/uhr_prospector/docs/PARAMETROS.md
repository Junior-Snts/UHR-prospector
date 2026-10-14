# Parâmetros do UHR Prospector

Gerado automaticamente por `tools/gerar_docs.py` a partir de `core/params.py`. Os valores padrão são pontos de partida genéricos: **devem ser justificados e ajustados** para cada estudo de caso.

### Área de busca e MDE

| Parâmetro | Nome interno | Padrão | Unidade | Intervalo | Descrição |
|---|---|---|---|---|---|
| Raio de busca ao redor de cada ponto | `raio_busca_km` | 8.0 | km | 0.5 a 200 | Distância máxima entre um ponto de referência e o sítio da barragem. A área de busca é a união dos círculos de cada ponto. |
| Distância mínima ao ponto de referência | `distancia_min_m` | 100.0 | m | 0 a 50000 | Sítios de barragem mais próximos que isto de qualquer ponto de referência são descartados. |
| Raio de exclusão ao redor de cada ponto | `raio_ponto_m` | 50.0 | m | 0 a 5000 | Zona ao redor do ponto considerada parte do reservatório principal: não recebe sítios e reservatórios candidatos que a alcancem são descartados (conectados ao principal). |
| Margem do MDE além da área de busca | `margem_dem_km` | 2.0 | km | 0 a 50 | Faixa extra do MDE usada no condicionamento hidrológico (evita que a área de contribuição seja truncada na borda da área de busca). |
| Resolução de trabalho (0 = nativa do MDE) | `resolucao_trabalho_m` | 0.0 | m | 0 a 1000 | Se maior que zero, o MDE é reamostrado (bilinear) para esta resolução. |
| Máximo de células processadas | `max_celulas` | 3000000 | células | 100000 a 5e+07 | Se o recorte do MDE exceder este valor, a resolução é reduzida automaticamente (o fator usado é registrado no log). |
| Área de contribuição mínima do talvegue | `area_contribuicao_min_ha` | 20.0 | ha | 0.1 a 1e+06 | Células com área drenante maior que este valor formam a rede de talvegues onde são buscados os sítios de barragem. |
| Espaçamento entre sítios de barragem | `espacamento_sitios_m` | 150.0 | m | 30 a 5000 | Distância mínima entre sítios avaliados ao longo dos talvegues. |

### Barragem

| Parâmetro | Nome interno | Padrão | Unidade | Intervalo | Descrição |
|---|---|---|---|---|---|
| Altura mínima da barragem | `altura_min_m` | 15.0 | m | 2 a 500 | Altura da crista acima do talvegue no sítio. |
| Altura máxima da barragem | `altura_max_m` | 80.0 | m | 2 a 500 | - |
| Passo de variação da altura | `passo_altura_m` | 5.0 | m | 0.5 a 100 | Alturas testadas: mínima, mínima+passo, ..., máxima. |
| Borda livre | `borda_livre_m` | 3.0 | m | 0 a 50 | Nível d'água máximo = cota da crista - borda livre. |
| Comprimento máximo da crista | `comprimento_max_m` | 1500.0 | m | 50 a 20000 | Sítios cuja crista excede este comprimento são descartados. |
| Largura da crista | `largura_crista_m` | 8.0 | m | 1 a 100 | Usada na estimativa do volume do maciço. |
| Talude de montante (H:V) | `talude_montante` | 2.5 | H/V | 0.5 a 10 | - |
| Talude de jusante (H:V) | `talude_jusante` | 2.0 | H/V | 0.5 a 10 | - |

### Reservatório candidato

| Parâmetro | Nome interno | Padrão | Unidade | Intervalo | Descrição |
|---|---|---|---|---|---|
| Raio da janela de inundação | `janela_reservatorio_km` | 4.0 | km | 0.5 a 50 | Reservatórios que ultrapassam esta janela ao redor do sítio são descartados (limita o custo computacional). |
| Área inundada mínima | `area_min_ha` | 20.0 | ha | 0.1 a 1e+06 | - |
| Área inundada máxima | `area_max_ha` | 2000.0 | ha | 0.1 a 1e+06 | - |
| Volume útil mínimo | `volume_util_min_hm3` | 5.0 | hm³ | 0 a 100000 | - |
| Deplecionamento máximo de operação | `deplecionamento_max_m` | 20.0 | m | 1 a 200 | Diferença entre NA máximo e NA mínimo operacionais. |
| Fração máxima da profundidade deplecionável | `fracao_deplecionamento_max` | 0.6 | - | 0.05 a 0.95 | O deplecionamento efetivo é o menor entre o valor em metros e esta fração da profundidade máxima do reservatório. |
| Razão água/maciço mínima (0 = desativada) | `razao_agua_rocha_min` | 0.0 | - | 0 a 1000 | Volume útil de água dividido pelo volume do maciço da barragem. |

### Nível do reservatório principal e queda

| Parâmetro | Nome interno | Padrão | Unidade | Intervalo | Descrição |
|---|---|---|---|---|---|
| Posição do reservatório secundário | `configuracao` | secundario_superior | - | secundario_superior, secundario_inferior, automatica | Superior: o principal funciona como reservatório inferior. Inferior: o secundário fica abaixo do principal. Automática: definida pelo sinal da queda em cada candidato. |
| Informar níveis do reservatório principal manualmente | `usar_nivel_principal_manual` | False | - | - | Se desmarcado, estima NA máximo = NA mínimo como o platô de cota mais frequente (espelho d'água plano no MDE) ao redor dos pontos. Confira o valor estimado no log; para estudos formais informe os níveis operacionais. |
| Raio de amostragem do nível ao redor dos pontos | `raio_amostragem_nivel_m` | 200.0 | m | 10 a 5000 | Usado apenas na estimativa automática do nível do principal. Deve alcançar a água, mas não incluir muito terreno plano de outra cota. |
| NA máximo normal do principal | `nivel_principal_max_m` | 0.0 | m | -500 a 9000 | - |
| NA mínimo operacional do principal | `nivel_principal_min_m` | 0.0 | m | -500 a 9000 | - |
| Queda bruta média mínima | `queda_bruta_min_m` | 100.0 | m | 1 a 3000 | - |
| Queda bruta máxima | `queda_bruta_max_m` | 600.0 | m | 1 a 3000 | - |
| Razão L/H máxima (circuito / queda) | `razao_LH_max` | 20.0 | - | 1 a 500 | Comprimento estimado do circuito hidráulico dividido pela queda bruta média. Valores menores indicam circuitos mais curtos e econômicos. |
| Fator de traçado do circuito | `fator_tracado` | 1.2 | - | 1 a 3 | Multiplica a distância em linha reta para considerar o traçado real. |

### Circuito hidráulico e energia

| Parâmetro | Nome interno | Padrão | Unidade | Intervalo | Descrição |
|---|---|---|---|---|---|
| Velocidade de projeto no conduto | `velocidade_projeto_m_s` | 5.0 | m/s | 1 a 12 | - |
| Número de condutos forçados | `n_condutos` | 2 | - | 1 a 12 | - |
| Fator de atrito de Darcy-Weisbach | `fator_atrito` | 0.015 | - | 0.005 a 0.08 | - |
| Soma dos coeficientes de perdas localizadas | `k_perdas_localizadas` | 2.0 | - | 0 a 20 | - |
| Rendimento da turbina (modo gerador) | `rendimento_turbina` | 0.9 | - | 0.3 a 1 | - |
| Rendimento da bomba (modo bombeamento) | `rendimento_bomba` | 0.88 | - | 0.3 a 1 | - |
| Horas de geração por ciclo | `horas_geracao` | 6.0 | h | 0.5 a 48 | Define a vazão turbinada: volume útil / duração. |
| Horas de bombeamento por ciclo | `horas_bombeamento` | 8.0 | h | 0.5 a 48 | - |
| Ciclos por dia | `ciclos_por_dia` | 1.0 | - | 0.1 a 4 | - |
| Dias de operação por ano | `dias_operacao_ano` | 330.0 | dias | 1 a 366 | - |
| Eficiência mínima do ciclo | `eficiencia_ciclo_min` | 0.6 | - | 0 a 1 | Energia gerada / energia consumida no bombeamento. |

### Seleção de candidatos

| Parâmetro | Nome interno | Padrão | Unidade | Intervalo | Descrição |
|---|---|---|---|---|---|
| Critério de escolha da altura e de priorização | `criterio_selecao` | energia | - | energia, razao_agua_rocha | Para cada sítio escolhe-se a altura viável que maximiza este critério; sítios são então priorizados por ele na eliminação de sobreposições. |
| Sobreposição máxima entre candidatos | `sobreposicao_max` | 0.2 | fração | 0 a 1 | Fração da área do candidato que pode coincidir com candidatos já aceitos (mais prioritários). |
| Número máximo de candidatos | `max_candidatos` | 100 | - | 1 a 5000 | - |
