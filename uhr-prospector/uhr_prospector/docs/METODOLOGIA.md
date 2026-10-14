# Metodologia do UHR Prospector

Documento de apoio à seção de metodologia do TCC. Cada seção descreve **exatamente o que o código faz** (arquivo indicado entre colchetes), incluindo as simplificações adotadas. Os valores padrão dos parâmetros estão em `PARAMETROS.md` e os campos de saída em `DICIONARIO_DADOS.md`; ambos são gerados do código.

Para o efeito de cada parâmetro nos reservatórios, veja `INFLUENCIA_DOS_PARAMETROS.md`.

O método é de **prospecção preliminar** (triagem em nível de reconhecimento/inventário): identifica e ordena sítios plausíveis a partir apenas de topografia e de parâmetros técnicos informados. Não substitui estudos de engenharia, geologia, hidrologia, meio ambiente ou custos.

## 1. Visão geral do fluxo

```
Pontos de referência (tomadas) próximos ao reservatório principal + MDE
  1. Preparação: CRS métrico, recorte, resolução
  2. Área de busca: união dos círculos de raio R ao redor dos pontos
  3. Condicionamento hidrológico: Priority-Flood -> direção e acúmulo de fluxo
  4. Sítios de barragem: células de talvegue espaçadas
  5. Para cada sítio e cada altura de barragem:
       eixo da barragem -> inundação -> área, cota, volume, volume útil
  6. Queda, circuito hidráulico, potência e energia
  7. Filtros (geométricos, volumétricos, hidráulicos)
  8. Melhor altura por sítio -> eliminação de sobreposições -> candidatos
  9. Ranking multicritério (soma ponderada ou TOPSIS)
```

## 2. Preparação das entradas [`raster_io.py`]

* **Entrada por pontos.** O usuário marca, em uma camada de pontos, um ou mais **pontos de referência** próximos ao reservatório principal (por exemplo, possíveis locais de tomada d'água). Não é necessário o polígono do espelho d'água. Cada ponto é o extremo do circuito hidráulico no reservatório principal e o centro de um círculo de busca.
* **CRS de trabalho.** Se o MDE já está em CRS projetado com unidade em metros, ele é usado. Caso contrário, o MDE é reprojetado para a zona UTM do centroide dos pontos (EPSG 326xx/327xx). Todas as distâncias, áreas e volumes são calculados nesse CRS.
* **Recorte.** O MDE é recortado ao envelope da união dos círculos de raio `raio_busca_km + margem_dem_km` ao redor dos pontos. A margem evita truncar a área de contribuição na borda da área de busca.
* **Resolução.** Usa-se a resolução nativa (ou `resolucao_trabalho_m`, se informada). Se o recorte exceder `max_celulas`, a célula é aumentada por `t' = t·√(N/N_max)` (arredondada para cima a 0,1 m). Quando a grade de trabalho coincide com a grade original (mesmo CRS e resolução), usa-se vizinho mais próximo (sem reamostrar); nos demais casos, interpolação bilinear. A resolução efetiva, o método e o número de células ficam registrados em `execucao.json`.
* **Nível d'água do reservatório principal** [`core/pipeline.py: niveis_principal`]. Sem polígono, o nível é obtido de duas formas:
  * **Manual** (recomendado para estudos formais): NA máximo e mínimo operacionais informados pelo usuário.
  * **Automática** (padrão): para cada ponto, usam-se as cotas válidas do MDE em um círculo de raio `raio_amostragem_nivel_m`; agrupam-se em classes de 1 m e adota-se a **mediana das cotas da classe mais populosa** (o **platô**: a água aparece como superfície plana no MDE e domina o histograma). Esse estimador é robusto a terreno mais alto (margem) e mais baixo (canal a jusante, vale escavado) dentro do círculo, ao contrário de percentis ou da média. O nível do reservatório é a **mediana entre os pontos**, com NA máximo = NA mínimo (sem deplecionamento do principal). O log registra a cota e a fração de células do platô em cada ponto. Emitem-se **avisos** se o platô de algum ponto ocupa menos de 15 % das células (ponto possivelmente longe da água) ou se os níveis dos pontos diferem em mais de 5 m (pontos em reservatórios distintos).
* **Zona de exclusão.** Cada ponto tem um círculo de raio `raio_ponto_m` considerado parte do reservatório principal: não recebe sítios de barragem e, se um reservatório candidato o alcançar, é descartado como conectado ao principal.

## 3. Área de busca [`core/pipeline.py: preparar_grade`]

Calcula-se, por transformada de distância euclidiana exata (`scipy.ndimage.distance_transform_edt`) a partir das células dos pontos, a distância `d_p` de cada célula ao **ponto de referência mais próximo**. A área de busca é a união dos círculos de raio R ao redor dos pontos:

```
zona = { células válidas fora das zonas de exclusão com d_p <= raio_busca }
```

## 4. Condicionamento hidrológico [`core/hydrology.py`]

Usa-se o algoritmo **Priority-Flood** (Barnes et al., 2014): as células de borda dos dados entram em uma fila de prioridade ordenada pela cota; a cada extração, os vizinhos (8-conexos) ainda não visitados recebem como cota `max(cota_própria, cota_da_célula_extraída)` e como **receptor** a célula extraída. O resultado é um MDE sem depressões espúrias e uma árvore de drenagem contínua (inclusive em áreas planas). A ordem de extração é uma ordenação topológica, usada para acumular fluxo:

```
acc(c) = 1 + Σ acc(células cujo receptor é c)        [em número de células]
A_contrib(c) = acc(c) · Δ² / 10⁴                      [ha]
```

onde Δ é o tamanho da célula. **Talvegue** é toda célula com `A_contrib >= area_contribuicao_min_ha`. O MDE preenchido é usado apenas para o roteamento, para a cota do leito no sítio e para o teste de vazamento (seção 7); as **áreas e volumes são calculados sobre o MDE original** (assim, depressões reais dentro do reservatório contam como volume).

## 5. Sítios de barragem [`core/pipeline.py: selecionar_sitios`]

Candidatos a sítio são células de talvegue dentro da zona de busca com `d_p >= distancia_min_m`. Elas são ordenadas por área de contribuição decrescente e aceitas de forma gulosa se estiverem a mais de `espacamento_sitios_m` de qualquer sítio já aceito. A **direção do talvegue** no sítio é a direção até a célula alcançada seguindo `max(3, 100/Δ)` receptores a jusante. Sítios cuja cadeia de receptores termina de imediato (exutório) são descartados.

**Poda antecipada.** Antes de simular, descarta-se o sítio se mesmo a maior barragem permitida não puder produzir a queda bruta mínima (superior: `z_leito + H_max − borda_livre − NA_médio_principal < H_min`; inferior: `NA_médio_principal − z_leito < H_min`).

## 6. Barragem [`core/reservoir.py: _perfil_eixo, volume_barragem_m3`]

Para cada sítio e cada altura `H` em `{H_min, H_min+passo, ..., H_max}`:

```
z_crista = z_leito(sítio, MDE preenchido) + H
NA_max   = z_crista − borda_livre
```

**Eixo.** É a reta perpendicular à direção do talvegue, amostrada a cada 1 célula para cada margem, até o terreno (MDE original) atingir `z_crista`. Se alguma margem não fechar dentro de `comprimento_max/2`, ou se o comprimento total exceder `comprimento_max`, a altura é inviável naquele sítio (sem simular inundação).

**Volume do maciço.** Em cada amostra do eixo a altura é `h_i = max(0, z_crista − z_i)` e a seção é trapezoidal:

```
A(h) = h·B + h²·(m_mont + m_jus)/2          B = largura da crista, m = talude H:V
V_barragem = Σ A(h_i) · Δ
```

É uma estimativa de ordem de grandeza (seção típica de barragem de terra/enrocamento, eixo reto, sem fundação, sem ombreiras).

## 7. Simulação da inundação [`core/reservoir.py: simular`]

1. Em uma janela de raio `janela_reservatorio_km` ao redor do sítio, marca-se `z_original ≤ NA_max`.
2. As células do eixo da barragem são removidas da máscara (**barreira**). Como a linha amostrada é 8-conexa e a rotulagem é 4-conexa, a água não atravessa a barreira na diagonal.
3. A **semente** é a célula de menor cota, em um raio de 3 células do sítio, no lado de montante do eixo.
4. O reservatório é a **componente 4-conexa** da máscara que contém a semente.

**Rejeições** (a altura é descartada e, como são monotônicas, alturas maiores também; o sítio deixa de ser avaliado):

| Condição | Interpretação |
|---|---|
| a região toca a borda da janela | reservatório maior que a janela de simulação |
| `área > area_max` | reservatório maior que o limite |
| a região contém células da zona de exclusão de um ponto | conexão com o reservatório principal |
| existe célula da região com cota (MDE preenchido) `< z_leito − 1 m` | **vazamento**: a água contorna o eixo e escapa a jusante |

## 8. Área, cota e volume

Para a região `R` com células de cota `z_i` e área de célula `a = Δ²`:

```
Área         = |R| · a
Volume V(L)  = a · Σ_{i∈R} max(0, L − z_i)           [para um nível L]
V_total      = V(NA_max)
Prof_máx     = NA_max − min(z_i)
Deplec.      = min( deplecionamento_max , fracao_deplecionamento_max · Prof_máx )
NA_min       = NA_max − Deplec.
V_útil       = V(NA_max) − V(NA_min)
```

`V(NA_min)` é calculado sobre a mesma região (bolsões desconectados abaixo de `NA_min` são ignorados, o que é conservador). Também é gerada a **curva cota-área-volume** (25 níveis entre o fundo e `NA_max`) de cada candidato final em `curvas_cota_area_volume.csv`.

**Razão água/maciço** = `V_útil / V_barragem` (adimensional; indicador de eficiência de armazenamento por volume de barragem).

## 9. Distância, queda e circuito [`core/hydraulics.py`]

**Distância ao ponto de referência.** `dist_borda_m` é a menor distância entre qualquer célula do candidato e o ponto de referência mais próximo (`ponto_tomada`), assumida como o trecho horizontal do circuito (tomada no secundário até o ponto); `dist_centroide_m` é a distância do centroide do candidato a esse conjunto de pontos. Se a camada tem vários pontos, cada candidato usa o mais próximo; o circuito esquemático desenhado no mapa liga a célula do candidato ao ponto.

**Queda bruta.** Seja `NA_s` o nível do secundário e `NA_p` o do principal, com médias `m_s = (NA_max+NA_min)/2` e `m_p`.

```
Secundário superior:  H_média = m_s − m_p     H_máx = NA_s,máx − NA_p,mín     H_mín = NA_s,mín − NA_p,máx
Secundário inferior:  H_média = m_p − m_s     H_máx = NA_p,máx − NA_s,mín     H_mín = NA_p,mín − NA_s,máx
Automática:           superior se m_s ≥ m_p, inferior caso contrário
```

A queda de projeto é `H_média`; candidatos com `H_média ≤ 0` são descartados.

**Comprimento do circuito e razão L/H.**

```
L = √( (fator_traçado · dist_borda)² + H_média² )          razão L/H = L / H_média
```

`fator_traçado` (≥ 1) converte a distância em linha reta em traçado provável. L/H é o indicador clássico de economicidade do circuito (quanto menor, mais curto e barato o circuito para a queda disponível).

## 10. Vazão, perdas, potência e energia [`core/hydraulics.py: energia_potencia`]

Constantes: `ρ = 1000 kg/m³`, `g = 9,80665 m/s²`.

```
Q_ger = V_útil / (horas_geração · 3600)          Q_bomb = V_útil / (horas_bombeamento · 3600)
D = √( 4·Q_ger / (n · π · v_projeto) )           (n condutos em paralelo, velocidade de projeto)
v = Q / (n · π D²/4)
h_f = ( f · L/D + ΣK ) · v² / (2g)               (Darcy-Weisbach + perdas localizadas)
H_líq,ger = H_média − h_f(Q_ger)                 H_bomb = H_média + h_f(Q_bomb)
P_ger  = η_t · ρ g Q_ger · H_líq,ger             [MW]
P_bomb = ρ g Q_bomb · H_bomb / η_b               [MW]
E_ciclo   = P_ger · horas_geração                [MWh]
E_bombeada= P_bomb · horas_bombeamento           [MWh]
Eficiência do ciclo = E_ciclo / E_bombeada
E_anual   = E_ciclo · ciclos_por_dia · dias_operação / 1000   [GWh/ano]
E_armazenada = ρ g V_útil H_média / 3,6·10⁹      [MWh, sem perdas nem rendimentos]
```

Candidatos com queda líquida ≤ 0 são descartados. O diâmetro do conduto é um dimensionamento *preliminar* usado só para estimar perdas (o fator de atrito é constante e informado).

## 11. Filtros e seleção [`core/pipeline.py: executar`]

Para cada sítio, cada altura que sobrevive à simulação passa pelos filtros, nesta ordem: área mínima; volume útil mínimo; razão água/maciço mínima (se > 0); queda bruta mínima e máxima; razão L/H máxima; eficiência de ciclo mínima. (Área máxima e comprimento máximo da crista são aplicados na simulação.) Cada descarte é contado por motivo (`descartes` em `execucao.json`), o que permite relatar no trabalho **por que** os sítios foram eliminados.

**Melhor altura por sítio.** Entre as alturas viáveis escolhe-se a que maximiza o critério `criterio_selecao` (energia por ciclo ou razão água/maciço).

**Sobreposição.** Os sítios resultantes são ordenados pelo mesmo critério (decrescente). Cada candidato é aceito se a fração de suas células já ocupada por candidatos aceitos for `≤ sobreposicao_max`, até `max_candidatos`. Os reservatórios finais são vetorizados (sem sobrepor) a partir de um raster de rótulos.

## 12. Ranking multicritério [`core/ranking.py`]

Critérios padrão (↑ maximizar, ↓ minimizar) e pesos padrão — **os pesos são uma escolha do pesquisador e devem ser justificados** (por exemplo, por AHP ou consulta a especialistas) e analisados por sensibilidade:

| Critério | Sentido | Peso padrão |
|---|---|---|
| Energia por ciclo | ↑ | 0,25 |
| Potência | ↑ | 0,15 |
| Queda bruta média | ↑ | 0,10 |
| Razão L/H | ↓ | 0,15 |
| Razão água/maciço | ↑ | 0,20 |
| Eficiência do ciclo | ↑ | 0,05 |
| Comprimento da crista | ↓ | 0,10 |

Os pesos são normalizados para somar 1. Dois métodos:

* **Soma ponderada (min-max):** `s_i = Σ_j w_j · x̃_ij`, com `x̃ = (x − min)/(max − min)` para critérios a maximizar e `1 − x̃` para os a minimizar. Se todos os candidatos têm o mesmo valor, `x̃ = 1`.
* **TOPSIS** (Hwang e Yoon, 1981): normalização vetorial `r_ij = x_ij/√Σ x²`, ponderação `v_ij = w_j r_ij`, soluções ideal e anti-ideal por critério, e `s_i = D⁻/(D⁺ + D⁻)`.

No QGIS, os pesos e o método podem ser alterados no painel de resultados e o ranking é recalculado (atualizando também as camadas).

## 13. Reprodutibilidade

* O processamento é **determinístico** (sem componentes aleatórias; ordenações estáveis). Há teste automatizado que executa duas vezes e compara os resultados.
* Cada execução com pasta de saída grava `execucao.json` com: todos os parâmetros, versões (plugin, QGIS, Python), **SHA-256 do arquivo do MDE**, resolução e método de reamostragem, CRS, níveis do principal, contagem de sítios avaliados/viáveis, motivos de descarte e tempo. Esse arquivo pode ser recarregado no diálogo (botão *Carregar parâmetros*) para repetir a execução.
* Resultados: `resultados.gpkg` (camadas), `candidatos.csv`, `curvas_cota_area_volume.csv`, `log.txt`.

## 14. Verificação do núcleo de cálculo

O diretório `tests/` contém testes automatizados do núcleo (sem QGIS) com um MDE sintético de geometria conhecida (planalto inclinado, reservatório principal a oeste com pontos de referência sobre ele, bacia fechada ligada por uma garganta). Eles verificam, entre outros: conservação de massa do acúmulo de fluxo; preenchimento de depressões; identidade `E = η ρ g V H_líq`; continuidade e perda de carga no conduto; volume do maciço em caso analítico; coerência entre área, volume e máscara do reservatório; ausência de vazamento; queda = diferença de níveis; aceitação de limites; reprodutibilidade; que um vale aberto (sem bacia) não gera reservatório grande; e, para a entrada por pontos: nível automático pelo platô (inclusive com ponto na margem e canal abaixo da água), nível manual, ponto fora da grade, ausência de pontos, ausência de dados ao redor do ponto, e que o circuito termina em um ponto de referência.

**O que esses testes não cobrem:** a integração com a API do QGIS/GDAL (leitura de raster, reprojeção, vetorização, camadas e interface) precisa ser verificada no QGIS com dados reais. Recomenda-se, como validação científica, aplicar o método a um caso com UHRs ou estudos de inventário conhecidos na mesma região e comparar sítios, quedas e volumes.

## 15. Hipóteses e limitações (para a seção de discussão)

1. **Qualidade do MDE.** Resultados dependem da resolução e do erro vertical do MDE (SRTM/Copernicus/ALOS podem incluir vegetação e edificações). Volumes e áreas são sensíveis a erros verticais de poucos metros em vales rasos.
2. **Nível do reservatório principal.** O padrão (platô de cota mais frequente do MDE ao redor dos pontos) retrata a data de aquisição do MDE e pressupõe que a água apareça plana no MDE e ocupe parte relevante do círculo de amostragem; em MDEs que mascaram a água (NoData) ou com pontos distantes dela, a estimativa falha ou emite aviso. Para estudos formais informe os níveis operacionais. Erros de poucos metros no nível alteram diretamente a queda e a energia.
2b. **Pontos de referência.** O resultado depende de onde os pontos são marcados: o raio de busca é medido a partir deles e a distância/queda do circuito usam o ponto mais próximo. Recomenda-se analisar a sensibilidade à posição e ao número de pontos.
3. **Barragem simplificada.** Eixo reto perpendicular ao talvegue; seção trapezoidal genérica; sem vertedouro, desvio, tomada d'água, diques de sela (*saddle dams*) nem fundação. O volume do maciço é indicativo. Fechamentos que exigem diques em selas fora do eixo principal não são modelados: nesses casos o método reporta vazamento e descarta o sítio (pode haver falsos negativos).
4. **Inundação por nível único** (bacia conectada a montante do eixo com cota ≤ NA_max), sem modelagem de infiltração/estanqueidade, evaporação, assoreamento ou vazão afluente natural. A área de contribuição é registrada (`area_contrib_ha`) para análise posterior do balanço hídrico e do enchimento inicial.
5. **Janela de simulação.** Reservatórios que atingem a borda da janela são descartados; aumente `janela_reservatorio_km` se forem esperados reservatórios grandes.
6. **Sítios em talvegues.** Só se avaliam eixos sobre células de talvegue (limiar de área de contribuição), espaçadas; sítios em locais fora da rede definida pelo limiar não são considerados. O espaçamento e o limiar afetam o conjunto de candidatos (análise de sensibilidade recomendada).
7. **Circuito hidráulico.** Comprimento estimado a partir da distância em linha reta, fator de traçado e queda; não há traçado real, túneis, chaminés de equilíbrio nem topografia ao longo do circuito (a linha desenhada no mapa é esquemática).
8. **Hidráulica e energia.** Queda média constante (variação com o deplecionamento não é integrada), fator de atrito e rendimentos constantes, sem curvas de turbina/bomba, sem limitações de submergência (cavitação) nem de profundidade de poço. Energia anual assume o mesmo número de ciclos todos os dias de operação.
9. **Critérios não considerados:** geologia, solos, uso e ocupação, unidades de conservação, populações afetadas, conexão elétrica, acessos e custos. O ranking reflete apenas critérios topográficos, volumétricos e hidráulicos.
10. **Resolução.** Quando `max_celulas` força a redução de resolução, geometrias estreitas (gargantas) podem ser perdidas; verifique a resolução efetiva no `execucao.json`.

## Referências citadas no código

* Barnes, R.; Lehman, C.; Mulla, D. (2014). Priority-flood: An optimal depression-filling and watershed-labeling algorithm for digital elevation models. *Computers & Geosciences*, 62, 117-127.
* Hwang, C.-L.; Yoon, K. (1981). *Multiple Attribute Decision Making: Methods and Applications*. Springer.
