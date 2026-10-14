# -*- coding: utf-8 -*-
"""Parâmetros do UHR Prospector.

Cada parâmetro carrega metadados (rótulo, unidade, grupo, limites, dica) que são
usados em três lugares, garantindo consistência entre eles:

* a interface do plugin (os campos do diálogo são gerados a partir daqui);
* a validação dos valores informados;
* a tabela de parâmetros da documentação metodológica (tools/gerar_tabela_parametros.py).

Este módulo não depende do QGIS.
"""
import json
from dataclasses import dataclass, field, fields, asdict

GRUPOS = (
    "Área de busca e MDE",
    "Barragem",
    "Reservatório candidato",
    "Nível do reservatório principal e queda",
    "Circuito hidráulico e energia",
    "Seleção de candidatos",
)

CONFIGURACOES = ("secundario_superior", "secundario_inferior", "automatica")
CRITERIOS_SELECAO = ("energia", "razao_agua_rocha")


def _p(default, label, grupo, unidade="", dica="", minimo=None, maximo=None,
       passo=None, casas=2, opcoes=None):
    return field(default=default, metadata=dict(
        label=label, grupo=grupo, unidade=unidade, dica=dica, min=minimo,
        max=maximo, passo=passo, casas=casas, opcoes=opcoes))


@dataclass
class Parametros:
    # ------------------------------------------------------------------ busca
    raio_busca_km: float = _p(
        8.0, "Raio de busca ao redor de cada ponto", GRUPOS[0], "km",
        "Distância máxima entre um ponto de referência e o sítio da barragem. "
        "A área de busca é a união dos círculos de cada ponto.",
        0.5, 200.0, 0.5, 1)
    distancia_min_m: float = _p(
        100.0, "Distância mínima ao ponto de referência", GRUPOS[0], "m",
        "Sítios de barragem mais próximos que isto de qualquer ponto de "
        "referência são descartados.", 0.0, 50000.0, 50.0, 0)
    raio_ponto_m: float = _p(
        50.0, "Raio de exclusão ao redor de cada ponto", GRUPOS[0], "m",
        "Zona ao redor do ponto considerada parte do reservatório principal: "
        "não recebe sítios e reservatórios candidatos que a alcancem são "
        "descartados (conectados ao principal).", 0.0, 5000.0, 10.0, 0)
    margem_dem_km: float = _p(
        2.0, "Margem do MDE além da área de busca", GRUPOS[0], "km",
        "Faixa extra do MDE usada no condicionamento hidrológico (evita que a "
        "área de contribuição seja truncada na borda da área de busca).",
        0.0, 50.0, 0.5, 1)
    resolucao_trabalho_m: float = _p(
        0.0, "Resolução de trabalho (0 = nativa do MDE)", GRUPOS[0], "m",
        "Se maior que zero, o MDE é reamostrado (bilinear) para esta resolução.",
        0.0, 1000.0, 5.0, 0)
    max_celulas: int = _p(
        3_000_000, "Máximo de células processadas", GRUPOS[0], "células",
        "Se o recorte do MDE exceder este valor, a resolução é reduzida "
        "automaticamente (o fator usado é registrado no log).",
        100_000, 50_000_000, 100_000, 0)
    area_contribuicao_min_ha: float = _p(
        20.0, "Área de contribuição mínima do talvegue", GRUPOS[0], "ha",
        "Células com área drenante maior que este valor formam a rede de "
        "talvegues onde são buscados os sítios de barragem.",
        0.1, 1_000_000.0, 5.0, 1)
    espacamento_sitios_m: float = _p(
        150.0, "Espaçamento entre sítios de barragem", GRUPOS[0], "m",
        "Distância mínima entre sítios avaliados ao longo dos talvegues.",
        30.0, 5000.0, 10.0, 0)

    # --------------------------------------------------------------- barragem
    altura_min_m: float = _p(
        15.0, "Altura mínima da barragem", GRUPOS[1], "m",
        "Altura da crista acima do talvegue no sítio.", 2.0, 500.0, 1.0, 1)
    altura_max_m: float = _p(
        80.0, "Altura máxima da barragem", GRUPOS[1], "m", "", 2.0, 500.0, 1.0, 1)
    passo_altura_m: float = _p(
        5.0, "Passo de variação da altura", GRUPOS[1], "m",
        "Alturas testadas: mínima, mínima+passo, ..., máxima.", 0.5, 100.0, 0.5, 1)
    borda_livre_m: float = _p(
        3.0, "Borda livre", GRUPOS[1], "m",
        "Nível d'água máximo = cota da crista - borda livre.", 0.0, 50.0, 0.5, 1)
    comprimento_max_m: float = _p(
        1500.0, "Comprimento máximo da crista", GRUPOS[1], "m",
        "Sítios cuja crista excede este comprimento são descartados.",
        50.0, 20000.0, 50.0, 0)
    largura_crista_m: float = _p(
        8.0, "Largura da crista", GRUPOS[1], "m",
        "Usada na estimativa do volume do maciço.", 1.0, 100.0, 1.0, 1)
    talude_montante: float = _p(
        2.5, "Talude de montante (H:V)", GRUPOS[1], "H/V", "", 0.5, 10.0, 0.1, 2)
    talude_jusante: float = _p(
        2.0, "Talude de jusante (H:V)", GRUPOS[1], "H/V", "", 0.5, 10.0, 0.1, 2)

    # ------------------------------------------------------------ reservatório
    janela_reservatorio_km: float = _p(
        4.0, "Raio da janela de inundação", GRUPOS[2], "km",
        "Reservatórios que ultrapassam esta janela ao redor do sítio são "
        "descartados (limita o custo computacional).", 0.5, 50.0, 0.5, 1)
    area_min_ha: float = _p(
        20.0, "Área inundada mínima", GRUPOS[2], "ha", "", 0.1, 1_000_000.0, 5.0, 1)
    area_max_ha: float = _p(
        2000.0, "Área inundada máxima", GRUPOS[2], "ha", "", 0.1, 1_000_000.0, 50.0, 1)
    volume_util_min_hm3: float = _p(
        5.0, "Volume útil mínimo", GRUPOS[2], "hm³", "", 0.0, 100000.0, 1.0, 2)
    deplecionamento_max_m: float = _p(
        20.0, "Deplecionamento máximo de operação", GRUPOS[2], "m",
        "Diferença entre NA máximo e NA mínimo operacionais.", 1.0, 200.0, 1.0, 1)
    fracao_deplecionamento_max: float = _p(
        0.6, "Fração máxima da profundidade deplecionável", GRUPOS[2], "-",
        "O deplecionamento efetivo é o menor entre o valor em metros e esta "
        "fração da profundidade máxima do reservatório.", 0.05, 0.95, 0.05, 2)
    razao_agua_rocha_min: float = _p(
        0.0, "Razão água/maciço mínima (0 = desativada)", GRUPOS[2], "-",
        "Volume útil de água dividido pelo volume do maciço da barragem.",
        0.0, 1000.0, 0.5, 2)

    # ------------------------------------------------------ nível principal/queda
    configuracao: str = _p(
        "secundario_superior", "Posição do reservatório secundário", GRUPOS[3], "",
        "Superior: o principal funciona como reservatório inferior. Inferior: "
        "o secundário fica abaixo do principal. Automática: definida pelo sinal "
        "da queda em cada candidato.", opcoes=CONFIGURACOES)
    usar_nivel_principal_manual: bool = _p(
        False, "Informar níveis do reservatório principal manualmente", GRUPOS[3], "",
        "Se desmarcado, estima NA máximo = NA mínimo como o platô de cota mais "
        "frequente (espelho d'água plano no MDE) ao redor dos pontos. Confira o "
        "valor estimado no log; para estudos formais informe os níveis operacionais.")
    raio_amostragem_nivel_m: float = _p(
        200.0, "Raio de amostragem do nível ao redor dos pontos", GRUPOS[3], "m",
        "Usado apenas na estimativa automática do nível do principal. Deve "
        "alcançar a água, mas não incluir muito terreno plano de outra cota.",
        10.0, 5000.0, 50.0, 0)
    nivel_principal_max_m: float = _p(
        0.0, "NA máximo normal do principal", GRUPOS[3], "m", "",
        -500.0, 9000.0, 1.0, 2)
    nivel_principal_min_m: float = _p(
        0.0, "NA mínimo operacional do principal", GRUPOS[3], "m", "",
        -500.0, 9000.0, 1.0, 2)
    queda_bruta_min_m: float = _p(
        100.0, "Queda bruta média mínima", GRUPOS[3], "m", "", 1.0, 3000.0, 5.0, 1)
    queda_bruta_max_m: float = _p(
        600.0, "Queda bruta máxima", GRUPOS[3], "m", "", 1.0, 3000.0, 10.0, 1)
    razao_LH_max: float = _p(
        20.0, "Razão L/H máxima (circuito / queda)", GRUPOS[3], "-",
        "Comprimento estimado do circuito hidráulico dividido pela queda bruta "
        "média. Valores menores indicam circuitos mais curtos e econômicos.",
        1.0, 500.0, 1.0, 1)
    fator_tracado: float = _p(
        1.2, "Fator de traçado do circuito", GRUPOS[3], "-",
        "Multiplica a distância em linha reta para considerar o traçado real.",
        1.0, 3.0, 0.05, 2)

    # --------------------------------------------------------- hidráulica/energia
    velocidade_projeto_m_s: float = _p(
        5.0, "Velocidade de projeto no conduto", GRUPOS[4], "m/s", "",
        1.0, 12.0, 0.5, 1)
    n_condutos: int = _p(
        2, "Número de condutos forçados", GRUPOS[4], "", "", 1, 12, 1, 0)
    fator_atrito: float = _p(
        0.015, "Fator de atrito de Darcy-Weisbach", GRUPOS[4], "-", "",
        0.005, 0.08, 0.001, 3)
    k_perdas_localizadas: float = _p(
        2.0, "Soma dos coeficientes de perdas localizadas", GRUPOS[4], "-", "",
        0.0, 20.0, 0.5, 2)
    rendimento_turbina: float = _p(
        0.90, "Rendimento da turbina (modo gerador)", GRUPOS[4], "-", "",
        0.3, 1.0, 0.01, 2)
    rendimento_bomba: float = _p(
        0.88, "Rendimento da bomba (modo bombeamento)", GRUPOS[4], "-", "",
        0.3, 1.0, 0.01, 2)
    horas_geracao: float = _p(
        6.0, "Horas de geração por ciclo", GRUPOS[4], "h",
        "Define a vazão turbinada: volume útil / duração.", 0.5, 48.0, 0.5, 1)
    horas_bombeamento: float = _p(
        8.0, "Horas de bombeamento por ciclo", GRUPOS[4], "h", "",
        0.5, 48.0, 0.5, 1)
    ciclos_por_dia: float = _p(
        1.0, "Ciclos por dia", GRUPOS[4], "", "", 0.1, 4.0, 0.1, 1)
    dias_operacao_ano: float = _p(
        330.0, "Dias de operação por ano", GRUPOS[4], "dias", "",
        1.0, 366.0, 5.0, 0)
    eficiencia_ciclo_min: float = _p(
        0.60, "Eficiência mínima do ciclo", GRUPOS[4], "-",
        "Energia gerada / energia consumida no bombeamento.", 0.0, 1.0, 0.01, 2)

    # --------------------------------------------------------------- seleção
    criterio_selecao: str = _p(
        "energia", "Critério de escolha da altura e de priorização", GRUPOS[5], "",
        "Para cada sítio escolhe-se a altura viável que maximiza este critério; "
        "sítios são então priorizados por ele na eliminação de sobreposições.",
        opcoes=CRITERIOS_SELECAO)
    sobreposicao_max: float = _p(
        0.2, "Sobreposição máxima entre candidatos", GRUPOS[5], "fração",
        "Fração da área do candidato que pode coincidir com candidatos já "
        "aceitos (mais prioritários).", 0.0, 1.0, 0.05, 2)
    max_candidatos: int = _p(
        100, "Número máximo de candidatos", GRUPOS[5], "", "", 1, 5000, 10, 0)

    # ----------------------------------------------------------------- utilidades
    def to_dict(self):
        return asdict(self)

    def to_json(self, **kw):
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, **kw)

    @classmethod
    def from_dict(cls, d):
        """Cria a partir de um dicionário, ignorando chaves desconhecidas e
        convertendo tipos conforme o valor padrão de cada campo."""
        obj = cls()
        for f in fields(cls):
            if f.name not in d:
                continue
            padrao = getattr(obj, f.name)
            valor = d[f.name]
            if isinstance(padrao, bool):
                valor = bool(valor)
            elif isinstance(padrao, int):
                valor = int(round(float(valor)))
            elif isinstance(padrao, float):
                valor = float(valor)
            setattr(obj, f.name, valor)
        return obj

    @classmethod
    def from_json(cls, texto):
        return cls.from_dict(json.loads(texto))

    def validar(self):
        """Retorna lista de mensagens de erro (vazia se tudo consistente)."""
        e = []
        if self.altura_min_m > self.altura_max_m:
            e.append("Altura mínima da barragem maior que a máxima.")
        if self.area_min_ha > self.area_max_ha:
            e.append("Área mínima maior que a máxima.")
        if self.queda_bruta_min_m > self.queda_bruta_max_m:
            e.append("Queda bruta mínima maior que a máxima.")
        if self.usar_nivel_principal_manual and \
                self.nivel_principal_min_m > self.nivel_principal_max_m:
            e.append("NA mínimo do principal maior que o NA máximo.")
        if self.ciclos_por_dia * (self.horas_geracao + self.horas_bombeamento) > 24.0:
            e.append("Ciclos por dia x (horas de geração + horas de bombeamento) "
                     "excede 24 h por dia.")
        if self.configuracao not in CONFIGURACOES:
            e.append("Configuração desconhecida: %s" % self.configuracao)
        if self.criterio_selecao not in CRITERIOS_SELECAO:
            e.append("Critério de seleção desconhecido: %s" % self.criterio_selecao)
        if self.borda_livre_m >= self.altura_min_m:
            e.append("A borda livre deve ser menor que a altura mínima da barragem.")
        for f in fields(self):
            m = f.metadata
            v = getattr(self, f.name)
            if m.get("min") is not None and isinstance(v, (int, float)) \
                    and not isinstance(v, bool):
                if v < m["min"] or v > m["max"]:
                    e.append("%s fora do intervalo [%s, %s]." % (
                        m["label"], m["min"], m["max"]))
        return e


def metadados_campos():
    """Lista de dicionários com nome, valor padrão e metadados de cada campo."""
    base = Parametros()
    saida = []
    for f in fields(Parametros):
        d = dict(f.metadata)
        d["nome"] = f.name
        d["padrao"] = getattr(base, f.name)
        d["tipo"] = type(d["padrao"]).__name__
        saida.append(d)
    return saida


def tabela_markdown():
    """Tabela Markdown dos parâmetros (para a documentação metodológica)."""
    linhas = []
    for g in GRUPOS:
        linhas.append("\n### %s\n" % g)
        linhas.append("| Parâmetro | Nome interno | Padrão | Unidade | Intervalo | Descrição |")
        linhas.append("|---|---|---|---|---|---|")
        for m in metadados_campos():
            if m["grupo"] != g:
                continue
            if m["opcoes"]:
                intervalo = ", ".join(m["opcoes"])
            elif m["min"] is not None:
                intervalo = "%g a %g" % (m["min"], m["max"])
            else:
                intervalo = "-"
            linhas.append("| %s | `%s` | %s | %s | %s | %s |" % (
                m["label"], m["nome"], m["padrao"], m["unidade"] or "-",
                intervalo, m["dica"] or "-"))
    return "\n".join(linhas)
