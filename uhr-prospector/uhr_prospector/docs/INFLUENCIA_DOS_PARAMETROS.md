# Como cada parâmetro influencia os reservatórios candidatos

Complemento de `METODOLOGIA.md` (que descreve *o que* o código faz). Este documento explica *o que cada parâmetro altera* nos reservatórios encontrados, com evidência numérica de uma análise de sensibilidade reproduzível (`python tools/sensibilidade.py --extras`).

> **Como interpretar os números.** Os valores vêm de um **MDE sintético** (três bacias, descritas na seção 2), escolhido para que se conheça a resposta. Mostram a **direção e a ordem de grandeza** dos efeitos, não previsões para um caso real. Em terreno real, refaça a análise (seção 9). As variações são feitas **um parâmetro por vez**, partindo de um conjunto base; os efeitos combinados podem diferir.

## 1. Os quatro papéis de um parâmetro

Todo parâmetro age em uma (ou mais) destas etapas, e saber qual deles é a melhor forma de prever o efeito:

| Papel | Pergunta que o parâmetro responde | Efeito típico | Parâmetros |
|---|---|---|---|
| **A. Existência** | Este sítio/altura/reservatório pode entrar na lista? | Muda **quais** reservatórios existem (pode zerar a lista) | raio de busca, distância mínima, raio de exclusão, área de contribuição mínima, espaçamento, alturas mín/máx/passo, comprimento máx. da crista, janela, área mín/máx, volume útil mín., razão água/maciço mín., queda mín/máx, razão L/H máx., eficiência mín., configuração |
| **B. Medida** | Como o reservatório é medido (cota, área, volume)? | Muda os **números de um mesmo reservatório** (e, por consequência, a energia) | borda livre, deplecionamento (m e fração), nível do principal, resolução e qualidade do MDE |
| **C. Energia** | Dado o reservatório, quanta potência/energia? | Muda **só** potência, energia e eficiência; a geometria não muda | rendimentos, horas de geração/bombeamento, velocidade, nº de condutos, atrito, perdas localizadas, fator de traçado, ciclos/dia, dias/ano |
| **D. Escolha** | Entre alternativas viáveis, qual é mantida? | Muda **qual altura/sítio** representa a bacia e quantas variantes sobram | critério de seleção, sobreposição máxima, máx. de candidatos, passo de altura, espaçamento |

Alguns parâmetros têm papel duplo: o **passo de altura** e o **espaçamento** (A e D) e o **comprimento máximo da crista** (A, mas atua de fato como limitador da altura útil).

### Cadeia causal resumida

```
altura da barragem H ──► cota da crista ──► NA máx = crista − borda livre ──► área e volume total
                                                    │                            │
   deplecionamento ─────────────────────────────────┴─► NA mín ──► volume ÚTIL ──┤
                                                                                  ▼
 níveis do principal ──► queda bruta H_méd ──────────────────────────► energia ≈ η·ρ·g·V_útil·H_líq
 distância ao ponto ──► comprimento do circuito ──► perdas ──► H_líq e eficiência
```

Duas relações explicam grande parte dos resultados:

* **Energia por ciclo ≈ η_t · ρ · g · V_útil · H_líq.** Logo, +10 % de volume útil ≈ +10 % de energia; +10 % de queda ≈ +10 % de energia (menos perdas).
* **Potência = energia / horas de geração.** Horas de geração mudam a potência instalada, quase não mudam a energia.

## 2. O terreno sintético da análise

Três bacias ligadas ao reservatório principal (oeste, cota 300 m) por gargantas, com três pontos de referência sobre a água:

| Bacia | Perfil | Por que é útil |
|---|---|---|
| **A** | média, garganta estreita (≈ 90 m) | reservatório intermediário, referência |
| **B** | pequena e funda, garganta estreita | muita queda e volume por área; alta razão água/maciço |
| **C** | grande e rasa, garganta larga | exige crista longa; baixa razão água/maciço |

**Conjunto base** (o que não está no quadro abaixo é o padrão do plugin): raio 8 km; alturas 20–80 m, passo 10 m; crista ≤ 1200 m; área 10–2000 ha; volume útil ≥ 2 hm³; queda 50–700 m; L/H ≤ 30; área de contribuição ≥ 30 ha; espaçamento 150 m.

**Resultado base:** 3 candidatos. Candidato de maior prioridade de cada bacia: **A** = 70 m de barragem, 38 ha, 5,5 hm³ úteis, queda 311 m, 4 021 MWh/ciclo; **B** = 80 m, 51 ha, 9,0 hm³, queda 536 m, 11 530 MWh/ciclo. A bacia **C não aparece** (ver `comprimento_max_m`, seção 3.2). Nesse terreno, 87 % das avaliações de altura foram descartadas por *crista longa demais*: o parâmetro que mais restringe o resultado é o comprimento máximo da crista.

## 3. Parâmetros de existência (papel A)

### 3.1 Busca e MDE

| Parâmetro | O que faz | Efeito nos reservatórios | Evidência (sintético) |
|---|---|---|---|
| `raio_busca_km` | Distância máxima ponto → sítio da barragem | Só **elimina** reservatórios cujo sítio está além do raio; não altera os que permanecem | 2 km → **0 candidatos** (as gargantas ficam a mais de 2 km dos pontos); 4 km e 8 km → idênticos |
| `distancia_min_m` | Sítios mais próximos que isso de um ponto são descartados | Empurra a barragem para montante: reservatório menor, com maior queda e circuito mais longo | 3 000 m: **A** cai de 4 021 para 1 967 MWh (−51 %; 15 ha, 2,2 hm³) e **B** de 11 530 para 10 812 (−6 %) |
| `raio_ponto_m` | Zona de exclusão ao redor do ponto | Evita sítios na margem do principal e descarta reservatórios que a alcancem (conexão com o principal) | não variado nesta análise; o efeito esperado é do mesmo tipo que o de `distancia_min_m`, mas em torno do ponto |
| `area_contribuicao_min_ha` | Limiar para uma célula ser talvegue | Define **onde** há sítios. Limiar alto demais elimina talvegues pequenos (e os reservatórios off-river de cabeceira) | 3 000 ha → **0 candidatos** (nenhum talvegue com essa área drenante) |
| `espacamento_sitios_m` | Distância mínima entre sítios avaliados | É uma **discretização**: posições diferentes dos eixos geram barragens diferentes. Pode melhorar ou piorar cada bacia | 600 m: **A** +15 % (4 619 MWh), **B** −32 % (7 873 MWh) |
| `resolucao_trabalho_m`, `max_celulas`, `margem_dem_km` | Resolução e extensão do recorte | Ver seção 8 (resolução do MDE). A margem evita truncar a área de contribuição na borda | ver seção 8 |

**Regra prática.** Aumentar o raio de busca nunca piora o melhor candidato já achado (só acrescenta opções) mas aumenta o tempo. Já o espaçamento e a distância mínima **mudam os números** dos candidatos: de −51 % a +15 % de energia no sintético. Reporte-os como parte da metodologia.

### 3.2 Barragem

| Parâmetro | O que faz | Efeito nos reservatórios | Evidência (sintético) |
|---|---|---|---|
| `altura_max_m` | Maior altura testada | Alturas maiores dão mais área/volume **até** a crista exceder o comprimento máximo ou o reservatório vazar | 40 m: A **−64 %**, B **−49 %** de energia; 60 m: A −19 %, B −15 %; 120 m: nenhuma mudança em A/B (crista limita; descartes por crista longa 1 539 → 2 558), mas surge um 4º candidato (barragem de 120 m a montante em B) |
| `altura_min_m` | Menor altura aceita | Só remove barragens baixas; sem efeito se a melhor altura já é maior | 50 m: sem mudança |
| `passo_altura_m` | Resolução da varredura de alturas | A melhor altura só é achada se estiver na grade `min, min+passo, ...`; passo grosso pode perder o ótimo | 5 m: A **+22 %** (75 m, 6,6 hm³); 20 m: A −4 %; B inalterado |
| `borda_livre_m` | Folga entre NA máximo e crista | Reduz a cota de operação: perde área, volume e queda. Pesa mais em reservatórios **rasos/pequenos** | 8 m: A **−20 %** (33 ha, 4,5 hm³), B −8 %; 1 m: A +9 %, B +3 % |
| `comprimento_max_m` | Crista máxima | Restringe a altura útil. Reservatórios em gargantas **largas** só existem com limite alto | 600 m: A **−49 %**, B **−34 %** (altura cai para 50 m); 2 500 m: **10 candidatos**, incluindo a bacia **C** (crista de 2 310 m, 35 ha, 4,8 hm³, queda 258 m, razão água/maciço 0,75) |
| `largura_crista_m`, `talude_montante`, `talude_jusante` | Geometria do maciço | Só mudam o **volume da barragem** e a razão água/maciço; energia inalterada | largura 8→20 m: volume do maciço A +12 %, B +10 %; talude de montante 2→3: A +23 % (2,09→2,57 hm³) |
| `janela_reservatorio_km` | Raio da janela de simulação | Reservatórios que tocam a borda da janela são descartados; janela pequena demais trunca reservatórios grandes | 1 km: sem mudança (todas as bacias cabem); aumente se esperar reservatórios grandes |

**Observação.** Em reservatórios reais o limite de crista costuma ser o **filtro dominante** (como no sintético). Se a lista vier vazia, olhe primeiro os motivos de descarte (seção 7).

### 3.3 Reservatório

| Parâmetro | O que faz | Efeito | Evidência |
|---|---|---|---|
| `area_min_ha` / `area_max_ha` | Faixa de área inundada | Elimina reservatórios pequenos/grandes; não muda os que ficam | área mín. 100 ha → **0**; área máx. 100 ha → sem mudança (todos < 60 ha) |
| `volume_util_min_hm3` | Volume útil mínimo | Elimina reservatórios com pouco armazenamento | 20 hm³ → **0** (os maiores têm 9 hm³) |
| `razao_agua_rocha_min` | Volume útil / volume do maciço mínimo | Favorece barragens **menores e eficientes**; força altura menor | ≥ 3: A e B passam a 60 m (razão 3,2 e 6,6); energia **−19 % / −15 %** |

### 3.4 Queda e circuito

| Parâmetro | O que faz | Efeito | Evidência |
|---|---|---|---|
| `configuracao` | Posição do secundário (acima/abaixo/automática) | Define o sinal da queda. Escolha errada elimina **tudo** | `secundario_inferior` → **0** (todas as bacias estão acima do principal) |
| `queda_bruta_min_m` / `queda_bruta_max_m` | Faixa da queda bruta **média** | Filtro; não altera valores | máx. 250 m → **0** (A 311 m, B 536 m). Mín. 300 m: sem mudança |
| `razao_LH_max` | Máx. (comprimento do circuito / queda) | Elimina sítios longe do ponto ou com pouca queda | L/H ≤ 5 → **0** (valores de 8,7 a 9,7) |
| `eficiencia_ciclo_min` | Eficiência mínima do ciclo | Elimina circuitos com muitas perdas (longos, estreitos, velocidade alta) | ≥ 0,8 → **0** (eficiências de 0,74–0,76) |

## 4. Parâmetros de medida (papel B)

Estes mudam os números de **um mesmo reservatório**:

| Parâmetro | Mecanismo | Efeito | Evidência |
|---|---|---|---|
| `deplecionamento_max_m` e `fracao_deplecionamento_max` | O deplecionamento efetivo é **o menor** entre os dois: `min(d_máx, fração × profundidade)`. Define NA mínimo e **volume útil** | É o parâmetro de medida mais influente: volume útil e energia crescem quase proporcionalmente | 10 m: A **−40 %**, B **−47 %**; 40 m: A **+41 %**, B **+72 %** (V. útil de 9,0 para 15,7 hm³). A queda cai ~10 m (NA médio desce). Fração 0,1: A **−55 %**, B **−29 %**; 0,2: A −19 %; 0,3–0,9: **sem efeito** (o limite de 20 m já é o menor) |
| Nível do principal (`usar_nivel_principal_manual`, `nivel_principal_max/min_m`) | Define a queda; **só a média dos dois níveis** entra na queda de projeto | Variação de 1 m no nível ≈ 1 m de queda: o efeito **relativo** é maior onde a queda é menor | ±20 m: A **±6,7 %**, B **±3,8 %** de energia |
| MDE: resolução e erro vertical | Define como o terreno é visto | Ver seção 8 | ver seção 8 |

**Por que a fração pode "não fazer nada".** Se `fração × profundidade` for maior que o limite em metros, a fração não é o fator ativo. Nesse caso, mudar a fração é inócuo; aumente o limite em metros ou reduza a fração.

## 5. Parâmetros de energia (papel C)

A geometria dos reservatórios **não muda** com eles. Variação da energia por ciclo (A / B), a partir do base:

| Parâmetro | Variação | Δ energia (A / B) | Outros efeitos |
|---|---|---|---|
| `rendimento_turbina` | 0,90 → 0,85 | −6 % / −6 % | proporcional ao rendimento |
| `rendimento_bomba` | 0,88 → 0,80 | 0 / 0 | só a **eficiência do ciclo** cai (0,74 → 0,68) |
| `velocidade_projeto_m_s` | 5 → 8 | −9 % / −6 % | eficiência 0,74 → 0,65; **um candidato sai**: as perdas fazem a queda líquida ficar ≤ 0 em 53 avaliações (eram 2) e a eficiência ficar < 0,60 em 9 |
| `velocidade_projeto_m_s` | 5 → 3 | +3 % / +2 % | eficiência sobe para 0,78 |
| `fator_atrito` | 0,015 → 0,030 | −3 % / −2 % | eficiência 0,71 |
| `k_perdas_localizadas` | 2 → 10 | −3 % / −2 % | eficiência 0,70 |
| `n_condutos` | 2 → 4 / 2 → 1 | −1 % / −1 % ; +1 % / +1 % | mais condutos = menor diâmetro = mais perda |
| `fator_tracado` | 1,2 → 2,0 | −2 % / −2 % | **L/H sobe** de 9,7 para 16,0 (relevante para o filtro e o ranking) |
| `horas_geracao` | 6 → 3 / 6 → 12 | +1 % / +1 % ; −1 % / −1 % | **potência dobra/cai à metade** (670 → 1 353 / 330 MW em A); eficiência 0,74 → 0,76 / 0,67 |
| `horas_bombeamento` | 8 → 12 | ≈ 0 | eficiência 0,74 → 0,75; mais tempo = menor vazão de bombeamento = menor perda |
| `ciclos_por_dia`, `dias_operacao_ano` | — | 0 (por ciclo) | **energia anual proporcional** ao produto `ciclos × dias` |

**Leitura.** Para o *ranking por energia por ciclo*, os parâmetros de energia contam pouco (≤ 9 %), exceto o rendimento da turbina. Para **potência instalada**, as `horas_geracao` são decisivas. Para **filtro de eficiência**, velocidade, atrito e comprimento do circuito contam. O plugin recusa combinações em que `ciclos × (horas de geração + bombeamento)` ultrapasse 24 h.

## 6. Parâmetros de escolha (papel D)

| Parâmetro | O que faz | Efeito | Evidência |
|---|---|---|---|
| `criterio_selecao` | Critério para escolher **a altura de cada sítio** e a prioridade entre sítios | Troca o tipo de reservatório que representa cada bacia: "máxima energia" favorece barragens altas; "máxima razão água/maciço" favorece barragens baixas | `razao_agua_rocha`: A passa de 70 m para **40 m** (razão 2,4 → 5,2; energia **−64 %**); B de 80 m para **20 m** (razão 2,0 → 37; energia **−73 %**; crista de 150 m) |
| `sobreposicao_max` | Fração do reservatório que pode coincidir com outros já aceitos | 0 e 0,2: 3 candidatos; **1,0: 16 candidatos** (variantes do mesmo reservatório) | use valores baixos para obter alternativas realmente distintas |
| `max_candidatos` | Corte final | Mantém os de maior prioridade | — |
| `passo_altura_m`, `espacamento_sitios_m` | (ver 3.1 e 3.2) | | |

**Cuidado.** O critério de seleção não é o *ranking*: ele escolhe uma altura por sítio **antes** do ranking multicritério. Se o ranking dá peso à razão água/maciço, convém que o critério de seleção seja compatível, senão boas alternativas (barragens baixas) já foram descartadas.

## 7. Diagnóstico: "por que a lista veio vazia ou pequena?"

O log da execução (`Execução`, `execucao.json`) conta os **motivos de descarte**. Cada motivo aponta para os parâmetros a revisar:

| Motivo de descarte | Parâmetros a revisar |
|---|---|
| Crista não fecha dentro do comprimento máximo | `comprimento_max_m` (primeiro), `altura_max_m`, resolução do MDE |
| Reservatório atinge a borda da janela | `janela_reservatorio_km` |
| Reservatório maior que a área máxima | `area_max_ha` |
| Alcança a zona de exclusão do ponto | `raio_ponto_m`; posição dos pontos |
| Vazamento (a água escapa por uma sela) | `altura_max_m`; o terreno pode exigir dique de sela (não modelado) |
| Sítio sem queda possível / queda não positiva | `configuracao`, níveis do principal, `altura_max_m`, `queda_bruta_min_m` |
| Área menor que a mínima | `area_min_ha`, `altura_max_m`, `borda_livre_m` |
| Volume útil menor que o mínimo | `volume_util_min_hm3`, `deplecionamento_max_m`, `fracao_deplecionamento_max` |
| Razão água/maciço menor que a mínima | `razao_agua_rocha_min`, geometria do maciço |
| Queda fora da faixa | `queda_bruta_min_m`, `queda_bruta_max_m` |
| Razão L/H acima do limite | `razao_LH_max`, `fator_tracado`, `distancia_min_m` |
| Eficiência abaixo do mínimo | `eficiencia_ciclo_min`, velocidade, atrito, `horas_geracao`/`horas_bombeamento` |
| Sobreposição / acima do máximo | `sobreposicao_max`, `max_candidatos` |

## 8. Sensibilidade aos dados de entrada

| Fator | Variação | Efeito (A / B) |
|---|---|---|
| **Resolução do MDE** (as gargantas têm 70–160 m; média em blocos, espaçamento de sítios = 2 células) | 30 m → 60 m | A +3 %, B −0,1 %; **1 candidato a menos** (2 no total) |
| | 30 m → 120 m | A **−25 %** (4,1 hm³), B **−37 %** (altura cai para 40 m): as gargantas deixam de ser resolvidas |
| **Ruído vertical** (gaussiano, semente fixa) | σ = 1 m | A −2 %, B +2 % (mas a altura ótima de A muda de 70 para 80 m) |
| | σ = 3 m | A +4 %, B −7 % |
| | σ = 6 m | A **−20 %**, B +1 %; **surge um candidato novo** em C (15 ha, 2,0 hm³, 945 MWh) que não existia sem ruído: artefato do ruído |
| **Nível do principal** | ±20 m | A ±6,7 %, B ±3,8 % (seção 4) |

Em MDEs reais o erro vertical pode ser de vários metros (vegetação, edificações, ruído), então a posição ótima e a altura de cada barragem têm **incerteza intrínseca** além da dos parâmetros. Isso reforça a ideia de usar o plugin como triagem, e não como dimensionamento.

## 9. Roteiro sugerido para o TCC

1. **Congele um conjunto base** justificado (literatura, normas, projetos de referência) e registre-o (`execucao.json`).
2. **Análise de um parâmetro por vez** (como aqui) sobre os candidatos do seu caso, em torno do base. Reporte a variação percentual de energia, volume, área e da *posição* no ranking.
3. **Priorize** os parâmetros que o sintético mostrou serem mais influentes: `comprimento_max_m`, `altura_max_m`, `deplecionamento_max_m`, `borda_livre_m`, `criterio_selecao`, níveis do principal, `distancia_min_m`/posição dos pontos, resolução do MDE.
4. **Trate separadamente** os parâmetros que só filtram (papel A): reporte a sensibilidade como "quantos candidatos sobram", não como variação de valores.
5. **Estabilidade do ranking:** varie os pesos e o método (soma ponderada × TOPSIS) e verifique se os primeiros colocados permanecem.
6. **Combinações:** repita a análise variando em conjunto os 3–4 parâmetros mais influentes (grade ou amostragem) para ver interações (por exemplo, crista × altura × borda livre).
7. Rode o próprio `tools/sensibilidade.py` para reproduzir a tabela do apêndice e use-o como modelo.

## Apêndice: tabela completa da análise de sensibilidade (um parâmetro por vez)

Cada linha mostra o **candidato de maior prioridade de cada bacia** (A, B, C) para o valor indicado, e `Nº cand.` o total de candidatos finais. "-" indica que nenhum candidato atendeu aos critérios. Gerada por `python tools/sensibilidade.py`.

| Parâmetro | Valor | Nº cand. | Bacia | Altura (m) | Área (ha) | V.útil (hm³) | Queda (m) | L/H | Crista (m) | V.barr. (hm³) | Água/maciço | Potência (MW) | E.ciclo (MWh) | Efic. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `(base)` | - | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `(base)` | - | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `raio_busca_km` | 2.0 | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
| `raio_busca_km` | 4.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `raio_busca_km` | 4.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `raio_busca_km` | 8.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `raio_busca_km` | 8.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `distancia_min_m` | 100.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `distancia_min_m` | 100.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `distancia_min_m` | 3000.0 | 2 | A | 60 | 15 | 2.2 | 384 | 10.0 | 1170 | 4.74 | 0.47 | 328 | 1967 | 0.72 |
| `distancia_min_m` | 3000.0 | 2 | B | 70 | 50 | 8.6 | 526 | 8.7 | 990 | 2.43 | 3.56 | 1802 | 10812 | 0.76 |
| `area_contribuicao_min_ha` | 30.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `area_contribuicao_min_ha` | 30.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `area_contribuicao_min_ha` | 3000.0 | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
| `espacamento_sitios_m` | 150.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `espacamento_sitios_m` | 150.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `espacamento_sitios_m` | 600.0 | 2 | A | 70 | 44 | 6.3 | 311 | 9.4 | 1170 | 2.41 | 2.61 | 770 | 4619 | 0.75 |
| `espacamento_sitios_m` | 600.0 | 2 | B | 50 | 42 | 6.6 | 505 | 8.7 | 630 | 0.67 | 9.81 | 1312 | 7873 | 0.75 |
| `altura_max_m` | 40.0 | 2 | A | 40 | 15 | 2.3 | 274 | 9.7 | 330 | 0.45 | 5.19 | 244 | 1463 | 0.72 |
| `altura_max_m` | 40.0 | 2 | B | 40 | 31 | 5.0 | 496 | 9.0 | 270 | 0.37 | 13.39 | 972 | 5830 | 0.75 |
| `altura_max_m` | 60.0 | 3 | A | 60 | 37 | 4.6 | 300 | 9.4 | 1020 | 1.46 | 3.19 | 544 | 3266 | 0.74 |
| `altura_max_m` | 60.0 | 3 | B | 60 | 49 | 8.0 | 516 | 8.6 | 870 | 1.22 | 6.58 | 1639 | 9831 | 0.76 |
| `altura_max_m` | 80.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `altura_max_m` | 80.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `altura_max_m` | 120.0 | 4 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `altura_max_m` | 120.0 | 4 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `altura_min_m` | 20.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `altura_min_m` | 20.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `altura_min_m` | 50.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `altura_min_m` | 50.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `passo_altura_m` | 5.0 | 3 | A | 75 | 45 | 6.6 | 316 | 9.5 | 1200 | 2.98 | 2.21 | 818 | 4910 | 0.75 |
| `passo_altura_m` | 5.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `passo_altura_m` | 10.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `passo_altura_m` | 10.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `passo_altura_m` | 20.0 | 3 | A | 80 | 34 | 5.1 | 321 | 9.9 | 1110 | 3.59 | 1.43 | 646 | 3876 | 0.74 |
| `passo_altura_m` | 20.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `borda_livre_m` | 1.0 | 3 | A | 70 | 41 | 5.9 | 313 | 9.6 | 1050 | 2.33 | 2.54 | 728 | 4370 | 0.74 |
| `borda_livre_m` | 1.0 | 3 | B | 80 | 53 | 9.3 | 538 | 8.6 | 1110 | 4.47 | 2.08 | 1983 | 11899 | 0.76 |
| `borda_livre_m` | 3.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `borda_livre_m` | 3.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `borda_livre_m` | 8.0 | 3 | A | 70 | 33 | 4.5 | 306 | 9.8 | 1050 | 2.33 | 1.93 | 537 | 3225 | 0.74 |
| `borda_livre_m` | 8.0 | 3 | B | 80 | 48 | 8.4 | 531 | 8.7 | 1110 | 4.47 | 1.88 | 1775 | 10647 | 0.76 |
| `comprimento_max_m` | 600.0 | 2 | A | 50 | 22 | 3.1 | 290 | 9.7 | 570 | 0.81 | 3.79 | 343 | 2058 | 0.73 |
| `comprimento_max_m` | 600.0 | 2 | B | 50 | 40 | 6.4 | 506 | 8.8 | 510 | 0.67 | 9.45 | 1270 | 7618 | 0.75 |
| `comprimento_max_m` | 1200.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `comprimento_max_m` | 1200.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `comprimento_max_m` | 2500.0 | 10 | A | 80 | 50 | 7.7 | 321 | 9.4 | 1350 | 3.77 | 2.05 | 976 | 5857 | 0.75 |
| `comprimento_max_m` | 2500.0 | 10 | B | 70 | 58 | 9.8 | 526 | 8.5 | 1470 | 2.19 | 4.50 | 2057 | 12340 | 0.76 |
| `comprimento_max_m` | 2500.0 | 10 | C | 80 | 35 | 4.8 | 258 | 9.4 | 2310 | 6.34 | 0.75 | 480 | 2878 | 0.74 |
| `largura_crista_m` | 8.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `largura_crista_m` | 8.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `largura_crista_m` | 20.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.62 | 2.10 | 670 | 4021 | 0.74 |
| `largura_crista_m` | 20.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.91 | 1.84 | 1922 | 11530 | 0.76 |
| `talude_montante` | 2.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.09 | 2.63 | 670 | 4021 | 0.74 |
| `talude_montante` | 2.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.01 | 2.25 | 1922 | 11530 | 0.76 |
| `talude_montante` | 3.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.57 | 2.14 | 670 | 4021 | 0.74 |
| `talude_montante` | 3.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.94 | 1.83 | 1922 | 11530 | 0.76 |
| `deplecionamento_max_m` | 10.0 | 2 | A | 70 | 38 | 3.3 | 316 | 9.5 | 1050 | 2.33 | 1.41 | 403 | 2418 | 0.73 |
| `deplecionamento_max_m` | 10.0 | 2 | B | 80 | 51 | 4.8 | 541 | 8.6 | 1110 | 4.47 | 1.08 | 1027 | 6160 | 0.75 |
| `deplecionamento_max_m` | 20.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `deplecionamento_max_m` | 20.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `deplecionamento_max_m` | 40.0 | 3 | A | 70 | 38 | 8.0 | 301 | 10.0 | 1050 | 2.33 | 3.41 | 943 | 5657 | 0.75 |
| `deplecionamento_max_m` | 40.0 | 3 | B | 80 | 51 | 15.7 | 526 | 8.8 | 1110 | 4.47 | 3.52 | 3305 | 19829 | 0.76 |
| `fracao_deplecionamento_max` | 0.1 | 2 | A | 80 | 34 | 2.4 | 327 | 9.7 | 1110 | 3.59 | 0.67 | 304 | 1822 | 0.72 |
| `fracao_deplecionamento_max` | 0.1 | 2 | B | 80 | 51 | 6.4 | 539 | 8.6 | 1110 | 4.47 | 1.42 | 1358 | 8146 | 0.75 |
| `fracao_deplecionamento_max` | 0.2 | 2 | A | 80 | 34 | 4.3 | 323 | 9.9 | 1110 | 3.59 | 1.20 | 542 | 3251 | 0.74 |
| `fracao_deplecionamento_max` | 0.2 | 2 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `fracao_deplecionamento_max` | 0.3 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `fracao_deplecionamento_max` | 0.3 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `fracao_deplecionamento_max` | 0.6 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `fracao_deplecionamento_max` | 0.6 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `fracao_deplecionamento_max` | 0.9 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `fracao_deplecionamento_max` | 0.9 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `area_min_ha` | 10.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `area_min_ha` | 10.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `area_min_ha` | 100.0 | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
| `area_max_ha` | 100.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `area_max_ha` | 100.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `area_max_ha` | 2000.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `area_max_ha` | 2000.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `volume_util_min_hm3` | 2.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `volume_util_min_hm3` | 2.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `volume_util_min_hm3` | 20.0 | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
| `razao_agua_rocha_min` | 0.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `razao_agua_rocha_min` | 0.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `razao_agua_rocha_min` | 1.0 | 2 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `razao_agua_rocha_min` | 1.0 | 2 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `razao_agua_rocha_min` | 3.0 | 2 | A | 60 | 37 | 4.6 | 300 | 9.4 | 1020 | 1.46 | 3.19 | 544 | 3266 | 0.74 |
| `razao_agua_rocha_min` | 3.0 | 2 | B | 60 | 49 | 8.0 | 516 | 8.6 | 870 | 1.22 | 6.58 | 1639 | 9831 | 0.76 |
| `janela_reservatorio_km` | 1.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `janela_reservatorio_km` | 1.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `janela_reservatorio_km` | 3.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `janela_reservatorio_km` | 3.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `configuracao` | secundario_superior (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `configuracao` | secundario_superior (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `configuracao` | secundario_inferior | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
| `queda_bruta_min_m` | 50.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `queda_bruta_min_m` | 50.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `queda_bruta_min_m` | 300.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `queda_bruta_min_m` | 300.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `queda_bruta_max_m` | 250.0 | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
| `queda_bruta_max_m` | 700.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `queda_bruta_max_m` | 700.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `razao_LH_max` | 5.0 | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
| `razao_LH_max` | 30.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `razao_LH_max` | 30.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `fator_tracado` | 1.0 | 3 | A | 70 | 38 | 5.5 | 311 | 8.1 | 1050 | 2.33 | 2.36 | 674 | 4043 | 0.75 |
| `fator_tracado` | 1.0 | 3 | B | 80 | 51 | 9.0 | 536 | 7.2 | 1110 | 4.47 | 2.02 | 1929 | 11574 | 0.76 |
| `fator_tracado` | 1.2 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `fator_tracado` | 1.2 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `fator_tracado` | 2.0 | 3 | A | 70 | 38 | 5.5 | 311 | 16.0 | 1050 | 2.33 | 2.36 | 655 | 3931 | 0.72 |
| `fator_tracado` | 2.0 | 3 | B | 80 | 51 | 9.0 | 536 | 14.4 | 1110 | 4.47 | 2.02 | 1892 | 11352 | 0.74 |
| `velocidade_projeto_m_s` | 3.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 690 | 4141 | 0.78 |
| `velocidade_projeto_m_s` | 3.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1960 | 11760 | 0.78 |
| `velocidade_projeto_m_s` | 5.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `velocidade_projeto_m_s` | 5.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `velocidade_projeto_m_s` | 8.0 | 2 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 610 | 3663 | 0.65 |
| `velocidade_projeto_m_s` | 8.0 | 2 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1807 | 10839 | 0.69 |
| `n_condutos` | 1 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 677 | 4060 | 0.75 |
| `n_condutos` | 1 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1935 | 11609 | 0.77 |
| `n_condutos` | 2 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `n_condutos` | 2 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `n_condutos` | 4 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 661 | 3964 | 0.73 |
| `n_condutos` | 4 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1903 | 11418 | 0.75 |
| `fator_atrito` | 0.01 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 678 | 4066 | 0.76 |
| `fator_atrito` | 0.01 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1937 | 11620 | 0.77 |
| `fator_atrito` | 0.015 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `fator_atrito` | 0.015 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `fator_atrito` | 0.03 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 647 | 3885 | 0.71 |
| `fator_atrito` | 0.03 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1877 | 11261 | 0.73 |
| `k_perdas_localizadas` | 2.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `k_perdas_localizadas` | 2.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `k_perdas_localizadas` | 10.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 647 | 3883 | 0.70 |
| `k_perdas_localizadas` | 10.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1884 | 11304 | 0.74 |
| `rendimento_turbina` | 0.85 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 633 | 3797 | 0.70 |
| `rendimento_turbina` | 0.85 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1815 | 10889 | 0.72 |
| `rendimento_turbina` | 0.9 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `rendimento_turbina` | 0.9 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `rendimento_bomba` | 0.8 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.68 |
| `rendimento_bomba` | 0.8 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.69 |
| `rendimento_bomba` | 0.88 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `rendimento_bomba` | 0.88 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `horas_geracao` | 3.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 1353 | 4060 | 0.76 |
| `horas_geracao` | 3.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 3870 | 11609 | 0.77 |
| `horas_geracao` | 6.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `horas_geracao` | 6.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `horas_geracao` | 12.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 330 | 3964 | 0.67 |
| `horas_geracao` | 12.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 952 | 11418 | 0.70 |
| `horas_bombeamento` | 8.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `horas_bombeamento` | 8.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `horas_bombeamento` | 12.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.75 |
| `horas_bombeamento` | 12.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `ciclos_por_dia` | 1.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `ciclos_por_dia` | 1.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `ciclos_por_dia` | 1.7 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `ciclos_por_dia` | 1.7 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `dias_operacao_ano` | 250.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `dias_operacao_ano` | 250.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `dias_operacao_ano` | 330.0 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `dias_operacao_ano` | 330.0 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `eficiencia_ciclo_min` | 0.6 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `eficiencia_ciclo_min` | 0.6 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `eficiencia_ciclo_min` | 0.8 | 0 | - | - | - | - | - | - | - | - | - | - | - | - |
| `criterio_selecao` | energia (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `criterio_selecao` | energia (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `criterio_selecao` | razao_agua_rocha | 3 | A | 40 | 15 | 2.3 | 274 | 9.7 | 330 | 0.45 | 5.19 | 244 | 1463 | 0.72 |
| `criterio_selecao` | razao_agua_rocha | 3 | B | 20 | 19 | 2.8 | 476 | 9.4 | 150 | 0.08 | 37.14 | 519 | 3115 | 0.73 |
| `sobreposicao_max` | 0.0 | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `sobreposicao_max` | 0.0 | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `sobreposicao_max` | 0.2 (base) | 3 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `sobreposicao_max` | 0.2 (base) | 3 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |
| `sobreposicao_max` | 1.0 | 16 | A | 70 | 38 | 5.5 | 311 | 9.7 | 1050 | 2.33 | 2.36 | 670 | 4021 | 0.74 |
| `sobreposicao_max` | 1.0 | 16 | B | 80 | 51 | 9.0 | 536 | 8.7 | 1110 | 4.47 | 2.02 | 1922 | 11530 | 0.76 |


### Nível do reservatório principal (manual)

| Variação | Nº cand. | Bacia | Altura (m) | Área (ha) | V.útil (hm³) | Queda (m) | E.ciclo (MWh) |
|---|---|---|---|---|---|---|---|
| NA do principal = 280 m | 3 | A | 70 | 38 | 5.5 | 331 | 4290 |
| NA do principal = 280 m | 3 | B | 80 | 51 | 9.0 | 556 | 11972 |
| NA do principal = 300 m | 3 | A | 70 | 38 | 5.5 | 311 | 4021 |
| NA do principal = 300 m | 3 | B | 80 | 51 | 9.0 | 536 | 11530 |
| NA do principal = 320 m | 3 | A | 70 | 38 | 5.5 | 291 | 3751 |
| NA do principal = 320 m | 3 | B | 80 | 51 | 9.0 | 516 | 11087 |


### Resolução do MDE

| Variação | Nº cand. | Bacia | Altura (m) | Área (ha) | V.útil (hm³) | Queda (m) | E.ciclo (MWh) |
|---|---|---|---|---|---|---|---|
| célula de 30 m | 3 | A | 70 | 38 | 5.5 | 311 | 4021 |
| célula de 30 m | 3 | B | 80 | 51 | 9.0 | 536 | 11530 |
| célula de 60 m | 2 | A | 80 | 35 | 5.4 | 325 | 4133 |
| célula de 60 m | 2 | B | 70 | 53 | 9.1 | 532 | 11520 |
| célula de 120 m | 2 | A | 60 | 26 | 4.1 | 317 | 3033 |
| célula de 120 m | 2 | B | 40 | 39 | 6.0 | 515 | 7266 |


### Ruído vertical do MDE

| Variação | Nº cand. | Bacia | Altura (m) | Área (ha) | V.útil (hm³) | Queda (m) | E.ciclo (MWh) |
|---|---|---|---|---|---|---|---|
| ruído σ = 0 m | 3 | A | 70 | 38 | 5.5 | 311 | 4021 |
| ruído σ = 0 m | 3 | B | 80 | 51 | 9.0 | 536 | 11530 |
| ruído σ = 1 m | 3 | A | 80 | 35 | 5.2 | 322 | 3949 |
| ruído σ = 1 m | 3 | B | 80 | 53 | 9.2 | 537 | 11802 |
| ruído σ = 3 m | 3 | A | 80 | 36 | 5.5 | 324 | 4180 |
| ruído σ = 3 m | 3 | B | 70 | 48 | 8.4 | 531 | 10681 |
| ruído σ = 6 m | 3 | A | 60 | 33 | 4.6 | 301 | 3235 |
| ruído σ = 6 m | 3 | B | 70 | 52 | 9.1 | 538 | 11632 |
| ruído σ = 6 m | 3 | C | 60 | 15 | 2.0 | 206 | 945 |
