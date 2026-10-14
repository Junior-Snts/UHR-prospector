# -*- coding: utf-8 -*-
"""Monta o repositório GitHub do UHR Prospector e o repositório de plugins do QGIS.

Gera, na pasta de saída:
    uhr_prospector/                  código do plugin (cópia limpa)
    dist/uhr_prospector-<versao>.zip pacote instalável
    plugins.xml                      índice lido pelo QGIS (repositório de plugins próprio)
    README.md, LICENSE, .gitignore, scripts/construir_repositorio.py

Uso:
    python scripts/construir_repositorio.py --usuario SEU_USUARIO_GITHUB
    (de fora do repositório: --origem /caminho/uhr_prospector --saida /caminho/uhr-prospector)

Também grava homepage/tracker/repository em metadata.txt (código-fonte e cópia).
Para publicar uma nova versão: aumente `version` em metadata.txt, rode de novo e
faça commit/push de tudo.
"""
import argparse
import configparser
import datetime
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

NOME_PACOTE = "uhr_prospector"
OBRIGATORIOS = ("name", "qgisMinimumVersion", "description", "about", "version",
                "author", "email", "repository", "tracker", "homepage")
IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".DS_Store",
                                 "*.zip")


def ler_metadata(caminho):
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str          # preserva maiúsculas (qgisMinimumVersion)
    with open(caminho, encoding="utf-8") as fh:
        cp.read_file(fh)
    return dict(cp["general"])


def gravar_urls_metadata(caminho, homepage, tracker, repositorio):
    """Preenche homepage/tracker/repository sem reescrever o resto do arquivo."""
    with open(caminho, encoding="utf-8") as fh:
        linhas = fh.read().splitlines()
    alvo = {"homepage": homepage, "tracker": tracker, "repository": repositorio}
    for i, ln in enumerate(linhas):
        chave = ln.split("=", 1)[0].strip()
        if chave in alvo and "=" in ln:
            linhas[i] = "%s=%s" % (chave, alvo.pop(chave))
    for chave, valor in alvo.items():      # campos ausentes: acrescenta
        linhas.append("%s=%s" % (chave, valor))
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write("\n".join(linhas) + "\n")


def copiar_plugin(origem, destino):
    if os.path.realpath(origem) == os.path.realpath(destino):
        return                      # já é a pasta do repositório: nada a copiar
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    shutil.copytree(origem, destino, ignore=IGNORAR)


def validar_pacote(pasta, meta):
    erros = []
    for campo in OBRIGATORIOS:
        if not meta.get(campo, "").strip():
            erros.append("metadata.txt: campo obrigatório vazio: %s" % campo)
    for arq in ("__init__.py", "metadata.txt", "LICENSE"):
        if not os.path.isfile(os.path.join(pasta, arq)):
            erros.append("arquivo obrigatório ausente: %s" % arq)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-]*", os.path.basename(pasta)):
        erros.append("nome de pasta inválido: %s" % os.path.basename(pasta))
    for raiz, _, arqs in os.walk(pasta):
        if "__pycache__" in raiz:
            erros.append("há __pycache__ no pacote: %s" % raiz)
    return erros


def gerar_zip(pasta_plugin, destino_zip):
    os.makedirs(os.path.dirname(destino_zip), exist_ok=True)
    base = os.path.dirname(pasta_plugin)
    with zipfile.ZipFile(destino_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, _, arqs in os.walk(pasta_plugin):
            for a in sorted(arqs):
                caminho = os.path.join(raiz, a)
                z.write(caminho, os.path.relpath(caminho, base))
    with zipfile.ZipFile(destino_zip) as z:
        topo = {n.split("/")[0] for n in z.namelist()}
    assert topo == {NOME_PACOTE}, "o ZIP deve ter uma única pasta: %s" % topo


def _txt(pai, tag, valor):
    e = ET.SubElement(pai, tag)
    e.text = valor
    return e


def gerar_plugins_xml(caminho, meta, url_base_raw, nome_zip, url_repo):
    """Índice no formato do repositório oficial (plugins.qgis.org)."""
    agora = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    criado = agora
    if os.path.isfile(caminho):                       # preserva a data de criação
        try:
            ant = ET.parse(caminho).getroot().find("pyqgis_plugin/create_date")
            if ant is not None and ant.text:
                criado = ant.text
        except ET.ParseError:
            pass
    raiz = ET.Element("plugins")
    p = ET.SubElement(raiz, "pyqgis_plugin", name=meta["name"], version=meta["version"])
    _txt(p, "description", meta["description"])
    _txt(p, "about", meta["about"])
    _txt(p, "qgis_minimum_version", meta["qgisMinimumVersion"])
    if meta.get("qgisMaximumVersion"):
        _txt(p, "qgis_maximum_version", meta["qgisMaximumVersion"])
    _txt(p, "homepage", meta["homepage"])
    _txt(p, "file_name", nome_zip)
    _txt(p, "icon", "%s/%s/%s" % (url_base_raw, NOME_PACOTE, meta.get("icon", "icon.svg")))
    _txt(p, "author_name", meta["author"])
    _txt(p, "download_url", "%s/dist/%s" % (url_base_raw, nome_zip))
    _txt(p, "uploaded_by", meta["author"])
    _txt(p, "create_date", criado)
    _txt(p, "update_date", agora)
    _txt(p, "experimental", meta.get("experimental", "False"))
    _txt(p, "deprecated", meta.get("deprecated", "False"))
    _txt(p, "tracker", meta["tracker"])
    _txt(p, "repository", url_repo)
    _txt(p, "tags", meta.get("tags", ""))
    _txt(p, "server", "False")
    ET.indent(raiz, space="  ")
    ET.ElementTree(raiz).write(caminho, encoding="utf-8", xml_declaration=True)


README = """# UHR Prospector

Plugin do QGIS para **prospecção automatizada de reservatórios secundários de
Usinas Hidrelétricas Reversíveis (UHR)** associados a um reservatório hidrelétrico
existente, a partir de um Modelo Digital de Elevação (MDE) e de pontos de
referência marcados junto ao reservatório principal.

Desenvolvido como parte de um TCC/pesquisa acadêmica. Versão **{versao}**.

> Ferramenta de **prospecção preliminar**: usa apenas topografia e parâmetros
> técnicos informados. Não considera geologia, meio ambiente, uso do solo,
> conexão elétrica nem custos, e não substitui estudos de engenharia.

## Instalação pelo QGIS (repositório de plugins próprio)

Assim o plugin aparece na busca de *Complementos* e recebe atualizações.

1. No QGIS: **Complementos → Gerenciar e instalar complementos → Configurações**.
2. Em *Repositórios de complementos*, clique em **Adicionar...**.
3. Nome: `UHR Prospector`. URL:

   ```
   {url_xml}
   ```
4. Confirme, vá na aba **Todos**, pesquise **UHR Prospector** e clique em **Instalar**.

### Instalação manual (ZIP)

Baixe [`dist/{nome_zip}`]({url_zip}) e use **Complementos → Gerenciar e instalar
complementos → Instalar a partir do ZIP**.

## Requisitos

* QGIS 3.22 até 3.x (Qt5). Não testado no QGIS 4.
* No Python do QGIS: `numpy`, `scipy` e GDAL (`osgeo`). Se faltar o `scipy`: no
  Windows, abra o *OSGeo4W Shell* e execute `pip install scipy`; no Linux, instale
  `python3-scipy`.

## Documentação

Na pasta [`uhr_prospector/docs`]({url_repo}/tree/{ramo}/uhr_prospector/docs):

* `METODOLOGIA.md`: método completo, equações, hipóteses e limitações;
* `INFLUENCIA_DOS_PARAMETROS.md`: como cada parâmetro influencia os reservatórios;
* `PARAMETROS.md` e `DICIONARIO_DADOS.md`: parâmetros e campos de saída.

## Atualizações e problemas

* Relate erros e sugestões em [Issues]({url_repo}/issues).
* Para publicar uma nova versão: aumente `version` em `uhr_prospector/metadata.txt`,
  rode `python scripts/construir_repositorio.py --usuario {usuario}` e faça commit
  de tudo (inclusive `dist/` e `plugins.xml`).

## Como citar

SANTOS JÚNIOR, Antonio Claudio dos. *UHR Prospector: plugin QGIS para prospecção
de reservatórios secundários de usinas hidrelétricas reversíveis*. Versão {versao}.
2026. Disponível em: {url_repo}.

## Licença

Copyright (C) 2026 Antonio Claudio dos Santos Júnior. Software livre sob a
**GNU GPL, versão 2 ou posterior** (veja [LICENSE](LICENSE)).
"""

GITIGNORE = "__pycache__/\n*.pyc\n.DS_Store\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--usuario", required=True, help="usuário (ou organização) do GitHub")
    ap.add_argument("--repo", default="uhr-prospector", help="nome do repositório")
    ap.add_argument("--ramo", default="main", help="ramo publicado")
    raiz_padrao = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--origem", default=os.path.join(raiz_padrao, NOME_PACOTE),
                    help="pasta uhr_prospector com o código (padrão: a do repositório)")
    ap.add_argument("--saida", default=raiz_padrao,
                    help="pasta do repositório a montar (padrão: a raiz do repositório)")
    a = ap.parse_args()

    url_repo = "https://github.com/%s/%s" % (a.usuario, a.repo)
    url_raw = "https://raw.githubusercontent.com/%s/%s/%s" % (a.usuario, a.repo, a.ramo)
    origem = os.path.abspath(a.origem)
    saida = os.path.abspath(a.saida)

    # 1) URLs no metadata.txt do código-fonte
    gravar_urls_metadata(os.path.join(origem, "metadata.txt"), url_repo,
                         url_repo + "/issues", url_repo)
    # 2) cópia limpa do plugin para o repositório
    os.makedirs(saida, exist_ok=True)
    destino = os.path.join(saida, NOME_PACOTE)
    copiar_plugin(origem, destino)
    meta = ler_metadata(os.path.join(destino, "metadata.txt"))
    erros = validar_pacote(destino, meta)
    if erros:
        print("\n".join("ERRO: " + e for e in erros))
        return 1
    # 3) zip versionado e índice do repositório de plugins
    nome_zip = "%s-%s.zip" % (NOME_PACOTE, meta["version"])
    gerar_zip(destino, os.path.join(saida, "dist", nome_zip))
    gerar_plugins_xml(os.path.join(saida, "plugins.xml"), meta, url_raw, nome_zip, url_repo)
    # 4) arquivos do repositório
    shutil.copyfile(os.path.join(destino, "LICENSE"), os.path.join(saida, "LICENSE"))
    with open(os.path.join(saida, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write(GITIGNORE)
    with open(os.path.join(saida, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(README.format(
            versao=meta["version"], url_xml=url_raw + "/plugins.xml", nome_zip=nome_zip,
            url_zip="%s/dist/%s" % (url_raw, nome_zip), url_repo=url_repo,
            ramo=a.ramo, usuario=a.usuario))
    os.makedirs(os.path.join(saida, "scripts"), exist_ok=True)
    copia = os.path.join(saida, "scripts", "construir_repositorio.py")
    if os.path.realpath(copia) != os.path.realpath(__file__):
        shutil.copyfile(os.path.abspath(__file__), copia)
    print("Repositório montado em %s" % saida)
    print("URL para adicionar no QGIS: %s/plugins.xml" % url_raw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
