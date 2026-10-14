# UHR Prospector (plugin QGIS)

Prospecção automatizada de locais para **reservatórios secundários de Usinas Hidrelétricas Reversíveis (UHR)** associados a um reservatório hidrelétrico existente, a partir de um MDE.

Versão 1.1.1 · QGIS 3.22 ou superior (Qt5) · Python 3 · requer `numpy`, `scipy` e GDAL (`osgeo`) no Python do QGIS.

## Instalação

1. Compacte a pasta `uhr_prospector` em `.zip` (já fornecido) .
2. QGIS → *Complementos* → *Gerenciar e instalar complementos* → *Instalar a partir do ZIP*.
3. O ícone do plugin aparece na barra de ferramentas e em *Complementos → UHR Prospector*.

Se faltar o `scipy`: no Windows, abra o *OSGeo4W Shell* e rode `pip install scipy`; no Linux, instale `python3-scipy`.

## Uso

1. Carregue no projeto o **MDE** (raster local, elevação em metros) e uma **camada de pontos** com um ou mais pontos de referência (tomadas) marcados **sobre a água ou na margem** do reservatório principal. O plugin varre o raio de busca ao redor de cada ponto.
2. Abra o plugin, escolha as camadas e (opcional) a **pasta de saída**.
3. Ajuste os parâmetros nas abas (cada campo tem *tooltip*; todos estão documentados em `docs/PARAMETROS.md`).
4. *Executar*. O processamento roda em segundo plano (o QGIS não trava) e pode ser cancelado.
5. Resultados: camadas no mapa (reservatórios candidatos, eixos das barragens, circuitos esquemáticos, pontos de referência, área de busca), painel com a **tabela de candidatos** e o **ranking** (método e pesos editáveis, recalculáveis). Clique em uma linha para localizar o candidato.

Saídas na pasta escolhida (subpasta datada): `resultados.gpkg`, `candidatos.csv`, `curvas_cota_area_volume.csv`, `execucao.json` (parâmetros, versões, SHA-256 do MDE, descartes) e `log.txt`.

## Documentação

* `docs/METODOLOGIA.md` — método completo, equações, hipóteses e limitações (base para o capítulo de metodologia).
* `docs/INFLUENCIA_DOS_PARAMETROS.md` — como cada parâmetro influencia os reservatórios (com análise de sensibilidade reproduzível: `python tools/sensibilidade.py --extras`).
* `docs/PARAMETROS.md` e `docs/DICIONARIO_DADOS.md` — gerados do código (`python tools/gerar_docs.py`).

## Estrutura

```
core/        núcleo de cálculo, sem QGIS (params, hydrology, reservoir, hydraulics, pipeline, ranking, campos)
raster_io.py GDAL: recorte e reprojeção do MDE            workflow.py  fluxo completo + vetorização
task.py      QgsTask (segundo plano)                       camadas.py   camadas QGIS, GeoPackage, CSV, JSON
dialog.py    diálogo (campos gerados de core/params.py)    results_dock.py  tabela + ranking
tests/       testes automatizados                          tools/       checagem estática e geração de docs
```

## Testes (fora do QGIS)

```
cd uhr_prospector
python -m unittest discover -s tests -t . -v
python tools/checar.py
```

`tests/test_core.py` valida o núcleo de cálculo com um MDE sintético. `tests/test_qgis_stub.py` usa módulos *simulados* do QGIS apenas para detectar erros de nome/fluxo. **A integração real com QGIS/GDAL não foi executada no ambiente de desenvolvimento** e deve ser verificada com dados reais (veja `docs/METODOLOGIA.md`, seção 14).

## Aviso

Ferramenta de **prospecção preliminar**: usa apenas topografia e parâmetros técnicos informados. Não considera geologia, hidrologia detalhada, meio ambiente, uso do solo, conexão elétrica nem custos.
