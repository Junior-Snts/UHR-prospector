# UHR Prospector

Plugin do QGIS para **prospecção automatizada de reservatórios secundários de
Usinas Hidrelétricas Reversíveis (UHR)** associados a um reservatório hidrelétrico
existente, a partir de um Modelo Digital de Elevação (MDE) e de pontos de
referência marcados junto ao reservatório principal.

Desenvolvido como parte de uma pesquisa acadêmica. Versão **1.1.1**.

> Ferramenta de **prospecção preliminar**: usa apenas topografia e parâmetros
> técnicos informados. Não considera geologia, meio ambiente, uso do solo,
> conexão elétrica nem custos, e não substitui estudos de engenharia.

## Instalação pelo QGIS (repositório de plugins próprio)

Assim o plugin aparece na busca de *Complementos* e recebe atualizações.

1. No QGIS: **Complementos → Gerenciar e instalar complementos → Configurações**.
2. Em *Repositórios de complementos*, clique em **Adicionar...**.
3. Nome: `UHR Prospector`. URL:

   ```
   https://raw.githubusercontent.com/Junior-Snts/UHR-prospector/main/uhr-prospector/plugins.xml
   ```
4. Confirme, vá na aba **Todos**, pesquise **UHR Prospector** e clique em **Instalar**.

### Instalação manual (ZIP)

Baixe [`dist/uhr_prospector-1.1.1.zip`](https://raw.githubusercontent.com/Junior-Snts/uhr-prospector/main/dist/uhr_prospector-1.1.1.zip) e use **Complementos → Gerenciar e instalar
complementos → Instalar a partir do ZIP**.

## Requisitos

* QGIS 3.22 até 3.x (Qt5). Não testado no QGIS 4.
* No Python do QGIS: `numpy`, `scipy` e GDAL (`osgeo`). Se faltar o `scipy`: no
  Windows, abra o *OSGeo4W Shell* e execute `pip install scipy`; no Linux, instale
  `python3-scipy`.

## Documentação

Na pasta [`uhr_prospector/docs`](https://github.com/Junior-Snts/uhr-prospector/tree/main/uhr_prospector/docs):

* `METODOLOGIA.md`: método completo, equações, hipóteses e limitações;
* `INFLUENCIA_DOS_PARAMETROS.md`: como cada parâmetro influencia os reservatórios;
* `PARAMETROS.md` e `DICIONARIO_DADOS.md`: parâmetros e campos de saída.

## Atualizações e problemas

* Relate erros e sugestões em [Issues](https://github.com/Junior-Snts/uhr-prospector/issues).
* Para publicar uma nova versão: aumente `version` em `uhr_prospector/metadata.txt`,
  rode `python scripts/construir_repositorio.py --usuario Junior-Snts` e faça commit
  de tudo (inclusive `dist/` e `plugins.xml`).

## Como citar

SANTOS JÚNIOR, Antonio Claudio dos. *UHR Prospector: plugin QGIS para prospecção
de reservatórios secundários de usinas hidrelétricas reversíveis*. Versão 1.1.1.
2026. Disponível em: https://github.com/Junior-Snts/uhr-prospector.

## Licença

Copyright (C) 2026 Antonio Claudio dos Santos Júnior. Software livre sob a
**GNU GPL, versão 2 ou posterior** (veja [LICENSE](LICENSE)).
