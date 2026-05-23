import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Funções auxiliares
# ============================================================

def load_json(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        clean = value.strip().replace("R$", "").replace(".", "").replace(",", ".")
        try:
            return float(clean)
        except ValueError:
            return None
    return None


def to_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "sim", "s", "yes", "y"}:
            return True
        if text in {"false", "0", "nao", "não", "n", "no"}:
            return False
    return None


def parse_date(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return value
    return None


def safe_mean(values: List[float]) -> Optional[float]:
    return statistics.mean(values) if values else None


def safe_median(values: List[float]) -> Optional[float]:
    return statistics.median(values) if values else None


def safe_mode(values: List[float]) -> Optional[float]:
    if not values:
        return None
    counts = Counter(values)
    top_count = max(counts.values())
    top_values = [k for k, v in counts.items() if v == top_count]
    return top_values[0] if top_values else None


def safe_variance(values: List[float]) -> Optional[float]:
    return statistics.variance(values) if len(values) > 1 else 0.0 if values else None


def safe_std(values: List[float]) -> Optional[float]:
    return statistics.stdev(values) if len(values) > 1 else 0.0 if values else None


def safe_min(values: List[float]) -> Optional[float]:
    return min(values) if values else None


def safe_max(values: List[float]) -> Optional[float]:
    return max(values) if values else None


def amplitude(values: List[float]) -> Optional[float]:
    return (max(values) - min(values)) if values else None


def percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[int(idx)]
    fraction = idx - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * fraction


def quartiles(values: List[float]) -> Dict[str, Optional[float]]:
    return {
        "q1": percentile(values, 0.25),
        "q2_mediana": percentile(values, 0.50),
        "q3": percentile(values, 0.75),
    }


def deciles(values: List[float]) -> Dict[str, Optional[float]]:
    return {f"d{i}": percentile(values, i / 10) for i in range(1, 10)}


def percentiles_selected(values: List[float]) -> Dict[str, Optional[float]]:
    return {
        "p10": percentile(values, 0.10),
        "p25": percentile(values, 0.25),
        "p50": percentile(values, 0.50),
        "p75": percentile(values, 0.75),
        "p90": percentile(values, 0.90),
    }


def frequency_table(values: List[Any], top_n: int = 10) -> List[Dict[str, Any]]:
    counts = Counter(v for v in values if v is not None and v != "")
    total = sum(counts.values())
    table = []
    for item, count in counts.most_common(top_n):
        table.append({
            "valor": item,
            "frequencia": count,
            "percentual": round((count / total) * 100, 2) if total else 0.0,
        })
    return table


def contingency_table(rows: List[Any], cols: List[Any], top_n: int = 10) -> Dict[str, Dict[str, int]]:
    result: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r, c in zip(rows, cols):
        if r is None or c is None or r == "" or c == "":
            continue
        result[str(r)][str(c)] += 1
    # Limita para não explodir o JSON
    limited = {}
    for i, (rk, rv) in enumerate(result.items()):
        if i >= top_n:
            break
        limited[rk] = dict(list(rv.items())[:top_n])
    return limited


def pearson_correlation(x: List[float], y: List[float]) -> Optional[float]:
    if len(x) != len(y) or len(x) < 2:
        return None
    mx = safe_mean(x)
    my = safe_mean(y)
    sx = safe_std(x)
    sy = safe_std(y)
    if mx is None or my is None or sx in (None, 0) or sy in (None, 0):
        return None
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denominator = (len(x) - 1) * sx * sy
    if denominator == 0:
        return None
    return numerator / denominator


def min_max_normalize(values: List[float]) -> List[Optional[float]]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def z_score_standardize(values: List[float]) -> List[Optional[float]]:
    if not values:
        return []
    mu = safe_mean(values)
    sigma = safe_std(values)
    if mu is None:
        return []
    if sigma in (None, 0):
        return [0.0 for _ in values]
    return [(v - mu) / sigma for v in values]


def iqr_outliers(values: List[float]) -> Dict[str, Any]:
    if len(values) < 4:
        return {
            "q1": percentile(values, 0.25),
            "q3": percentile(values, 0.75),
            "iqr": None,
            "limite_inferior": None,
            "limite_superior": None,
            "indices_outliers": [],
            "valores_outliers": [],
        }
    q1 = percentile(values, 0.25)
    q3 = percentile(values, 0.75)
    assert q1 is not None and q3 is not None
    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    indices = [i for i, v in enumerate(values) if v < low or v > high]
    out_vals = [values[i] for i in indices]
    return {
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "limite_inferior": low,
        "limite_superior": high,
        "indices_outliers": indices,
        "valores_outliers": out_vals,
    }


def null_report(records: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = Counter()
    for rec in records:
        for k, v in rec.items():
            if v is None or v == "":
                counts[k] += 1
    return dict(counts)


def infer_field_type(values: List[Any]) -> str:
    not_null = [v for v in values if v is not None and v != ""]
    if not not_null:
        return "indefinido"
    numeric = sum(1 for v in not_null if isinstance(v, (int, float)) or to_float(v) is not None)
    if numeric == len(not_null):
        unique = len(set(float(to_float(v)) for v in not_null if to_float(v) is not None))
        if unique <= 12:
            return "quantitativa_discreta"
        return "quantitativa_continua"
    unique = len(set(str(v) for v in not_null))
    if unique <= 12:
        return "qualitativa_nominal"
    return "qualitativa_ordinal_ou_textual"


def round_or_none(value: Optional[float], ndigits: int = 4) -> Optional[float]:
    return round(value, ndigits) if isinstance(value, (int, float)) else value


def round_list(values: List[Optional[float]], ndigits: int = 4) -> List[Optional[float]]:
    return [round_or_none(v, ndigits) for v in values]


def normal_loglik(values: List[float]) -> Optional[float]:
    if not values:
        return None
    mu = safe_mean(values)
    sigma = safe_std(values)
    if mu is None or sigma in (None, 0):
        return None
    return sum(-0.5 * math.log(2 * math.pi * sigma ** 2) - ((x - mu) ** 2) / (2 * sigma ** 2) for x in values)


def exponential_loglik(values: List[float]) -> Optional[float]:
    if not values or any(v <= 0 for v in values):
        return None
    mu = safe_mean(values)
    if mu in (None, 0):
        return None
    lam = 1 / mu
    return sum(math.log(lam) - lam * x for x in values)


def uniform_loglik(values: List[float]) -> Optional[float]:
    if not values:
        return None
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return None
    return len(values) * math.log(1 / (hi - lo))


def poisson_loglik(counts: List[int]) -> Optional[float]:
    if not counts or any(c < 0 for c in counts):
        return None
    lam = safe_mean([float(c) for c in counts])
    if lam is None or lam <= 0:
        return None
    total = 0.0
    for k in counts:
        total += k * math.log(lam) - lam - math.lgamma(k + 1)
    return total


def bernoulli_loglik(values: List[int]) -> Optional[float]:
    if not values or any(v not in (0, 1) for v in values):
        return None
    p = safe_mean([float(v) for v in values])
    if p is None or p in (0, 1):
        return None
    return sum(v * math.log(p) + (1 - v) * math.log(1 - p) for v in values)


def binomial_loglik(values: List[int], n: Optional[int] = None) -> Optional[float]:
    if not values or any(v < 0 for v in values):
        return None
    if n is None:
        n = max(values) if values else 0
    if n <= 0:
        return None
    mean_val = safe_mean([float(v) for v in values])
    if mean_val is None:
        return None
    p = mean_val / n
    if p <= 0 or p >= 1:
        return None
    total = 0.0
    for k in values:
        if k > n:
            return None
        total += math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
        total += k * math.log(p) + (n - k) * math.log(1 - p)
    return total


@dataclass
class PreparedData:
    negocio: Dict[str, Any]
    transacoes: List[Dict[str, Any]]
    dias: List[Dict[str, Any]]
    recepcao: Dict[str, Any]


class InsightCalculadoEngine:
    def __init__(self, data: Dict[str, Any]):
        self.raw = data
        self.prepared = self._prepare_data(data)

    # --------------------------------------------------------
    # Preparação
    # --------------------------------------------------------
    def _prepare_data(self, data: Dict[str, Any]) -> PreparedData:
        negocio = data.get("negocio", {})
        dados = data.get("dados", {})
        recepcao = data.get("recepcao", {})

        transacoes = []
        for item in dados.get("transacoes", []):
            record = dict(item)
            record["data"] = parse_date(record.get("data"))
            if "valor" in record:
                record["valor"] = to_float(record.get("valor"))
            if "pago_no_prazo" in record:
                record["pago_no_prazo"] = to_bool(record.get("pago_no_prazo"))
            if "desconto" in record:
                record["desconto"] = to_float(record.get("desconto"))
            if "marketing" in record:
                record["marketing"] = to_float(record.get("marketing"))
            transacoes.append(record)

        dias = []
        for item in dados.get("dias", []):
            record = dict(item)
            record["data"] = parse_date(record.get("data"))
            for field in ["receita", "despesa", "vendas_qtd", "clientes", "marketing", "desconto_medio"]:
                if field in record:
                    record[field] = to_float(record.get(field))
            dias.append(record)

        if not dias and transacoes:
            dias = self._derive_daily_records(transacoes)

        return PreparedData(negocio=negocio, transacoes=transacoes, dias=dias, recepcao=recepcao)

    def _derive_daily_records(self, transacoes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_day: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "receita": 0.0,
            "despesa": 0.0,
            "vendas_qtd": 0,
            "clientes": set(),
            "marketing": 0.0,
            "desconto_medio_soma": 0.0,
            "desconto_medio_qtd": 0,
            "transacoes_qtd": 0,
        })

        for t in transacoes:
            day = t.get("data") or "sem_data"
            info = by_day[day]
            info["transacoes_qtd"] += 1
            valor = t.get("valor") or 0.0
            tipo = str(t.get("tipo", "")).lower()
            if tipo == "receita":
                info["receita"] += valor
                info["vendas_qtd"] += 1
            elif tipo == "despesa":
                info["despesa"] += valor
            info["marketing"] += (t.get("marketing") or 0.0)
            desconto = t.get("desconto")
            if desconto is not None:
                info["desconto_medio_soma"] += desconto
                info["desconto_medio_qtd"] += 1
            cliente = t.get("cliente")
            if cliente:
                info["clientes"].add(str(cliente))

        daily_records = []
        for day, info in sorted(by_day.items(), key=lambda x: x[0]):
            qtd_desc = info["desconto_medio_qtd"]
            daily_records.append({
                "data": day,
                "receita": round(info["receita"], 2),
                "despesa": round(info["despesa"], 2),
                "vendas_qtd": int(info["vendas_qtd"]),
                "clientes": int(len(info["clientes"])),
                "marketing": round(info["marketing"], 2),
                "desconto_medio": round((info["desconto_medio_soma"] / qtd_desc), 4) if qtd_desc else 0.0,
                "transacoes_qtd": int(info["transacoes_qtd"]),
            })
        return daily_records

    # --------------------------------------------------------
    # Séries auxiliares
    # --------------------------------------------------------
    def _series_from_days(self) -> Dict[str, List[float]]:
        dias = self.prepared.dias
        receita = [d.get("receita") for d in dias if d.get("receita") is not None]
        despesa = [d.get("despesa") for d in dias if d.get("despesa") is not None]
        lucro = []
        for d in dias:
            if d.get("receita") is not None and d.get("despesa") is not None:
                lucro.append(float(d["receita"]) - float(d["despesa"]))
        vendas_qtd = [int(d.get("vendas_qtd") or 0) for d in dias]
        clientes = [float(d.get("clientes") or 0) for d in dias]
        marketing = [float(d.get("marketing") or 0) for d in dias]
        desconto_medio = [float(d.get("desconto_medio") or 0) for d in dias]
        transacoes_qtd = [int(d.get("transacoes_qtd") or d.get("vendas_qtd") or 0) for d in dias]
        return {
            "receita": receita,
            "despesa": despesa,
            "lucro": lucro,
            "vendas_qtd": vendas_qtd,
            "clientes": clientes,
            "marketing": marketing,
            "desconto_medio": desconto_medio,
            "transacoes_qtd": transacoes_qtd,
        }

    def _ticket_values(self) -> List[float]:
        tickets = []
        for t in self.prepared.transacoes:
            if str(t.get("tipo", "")).lower() == "receita" and t.get("valor") is not None:
                tickets.append(float(t["valor"]))
        return tickets

    # --------------------------------------------------------
    # Aulas
    # --------------------------------------------------------
    def aula_1(self) -> Dict[str, Any]:
        transacoes = self.prepared.transacoes
        dias = self.prepared.dias
        if transacoes:
            keys = sorted({k for rec in transacoes for k in rec.keys()})
            classificacao = {}
            for key in keys:
                valores = [rec.get(key) for rec in transacoes]
                classificacao[key] = infer_field_type(valores)
        else:
            classificacao = {}

        sample_size = min(5, len(transacoes))
        amostra = transacoes[:sample_size]

        return {
            "tema": "Entender os dados do negócio",
            "problema_financeiro": "O empreendedor possui dados, mas não sabe o que está registrando nem como organizar isso para análise.",
            "calculos": {
                "populacao_transacoes": len(transacoes),
                "populacao_registros_diarios": len(dias),
                "amostra_exibida": sample_size,
                "classificacao_campos_transacoes": classificacao,
                "campos_faltantes_transacoes": null_report(transacoes),
                "campos_faltantes_dias": null_report(dias),
                "amostra_transacoes": amostra,
            },
            "insights": [
                "Nesta etapa o sistema identifica quais campos são qualitativos e quais são quantitativos.",
                "Também aponta lacunas iniciais para preparar a análise exploratória das próximas aulas.",
            ],
        }

    def aula_2(self) -> Dict[str, Any]:
        series = self._series_from_days()
        tickets = self._ticket_values()

        def resumo(values: List[float]) -> Dict[str, Optional[float]]:
            return {
                "media": round_or_none(safe_mean(values), 4),
                "mediana": round_or_none(safe_median(values), 4),
                "moda": round_or_none(safe_mode(values), 4),
                "amplitude": round_or_none(amplitude(values), 4),
                "variancia": round_or_none(safe_variance(values), 4),
                "desvio_padrao": round_or_none(safe_std(values), 4),
                "minimo": round_or_none(safe_min(values), 4),
                "maximo": round_or_none(safe_max(values), 4),
            }

        return {
            "tema": "Descobrir o comportamento financeiro central do negócio",
            "problema_financeiro": "O empreendedor não sabe qual é o comportamento financeiro típico do negócio.",
            "calculos": {
                "receita_diaria": resumo(series["receita"]),
                "despesa_diaria": resumo(series["despesa"]),
                "lucro_diario": resumo(series["lucro"]),
                "ticket_receita": resumo(tickets),
            },
            "insights": [
                "A média mostra o comportamento central, enquanto mediana e moda ajudam a validar se há distorções.",
                "A variância e o desvio padrão ajudam a medir estabilidade financeira.",
            ],
        }

    def aula_3(self) -> Dict[str, Any]:
        transacoes = self.prepared.transacoes
        series = self._series_from_days()
        tickets = self._ticket_values()
        categorias = [t.get("categoria") for t in transacoes]
        formas_pagamento = [t.get("forma_pagamento") for t in transacoes]

        return {
            "tema": "Organizar os dados para entender distribuição e faixas de desempenho",
            "problema_financeiro": "O empreendedor vê números soltos, mas não enxerga faixas de valor, frequência ou concentração.",
            "calculos": {
                "tabela_frequencia_categoria": frequency_table(categorias),
                "tabela_frequencia_forma_pagamento": frequency_table(formas_pagamento),
                "tabela_contingencia_categoria_pagamento": contingency_table(categorias, formas_pagamento),
                "quartis_receita_diaria": {k: round_or_none(v, 4) for k, v in quartiles(series["receita"]).items()},
                "quartis_lucro_diario": {k: round_or_none(v, 4) for k, v in quartiles(series["lucro"]).items()},
                "decis_ticket": {k: round_or_none(v, 4) for k, v in deciles(tickets).items()},
                "percentis_ticket": {k: round_or_none(v, 4) for k, v in percentiles_selected(tickets).items()},
            },
            "insights": [
                "As tabelas ajudam a descobrir onde há maior concentração de receitas, despesas e formas de pagamento.",
                "Quartis, decis e percentis permitem segmentar clientes, tickets e períodos do negócio.",
            ],
        }

    def aula_4(self) -> Dict[str, Any]:
        series = self._series_from_days()
        corr_pairs = {
            "marketing_x_receita": pearson_correlation(series["marketing"], series["receita"]),
            "marketing_x_lucro": pearson_correlation(series["marketing"], series["lucro"]),
            "desconto_x_receita": pearson_correlation(series["desconto_medio"], series["receita"]),
            "clientes_x_receita": pearson_correlation(series["clientes"], series["receita"]),
            "vendas_qtd_x_receita": pearson_correlation([float(v) for v in series["vendas_qtd"]], series["receita"]),
            "despesa_x_lucro": pearson_correlation(series["despesa"], series["lucro"]),
        }
        rounded = {k: round_or_none(v, 4) for k, v in corr_pairs.items()}
        valid = {k: v for k, v in rounded.items() if v is not None}
        strongest = None
        if valid:
            strongest = max(valid.items(), key=lambda item: abs(item[1]))

        return {
            "tema": "Entender o que influencia o resultado financeiro",
            "problema_financeiro": "O empreendedor quer saber o que parece impactar faturamento, lucro ou estabilidade.",
            "calculos": {
                "correlacoes": rounded,
                "relacao_mais_forte": {
                    "par": strongest[0],
                    "correlacao": strongest[1],
                } if strongest else None,
                "nota_causalidade": "Correlação não prova causalidade; os resultados indicam associação estatística e devem ser validados no contexto do negócio.",
            },
            "insights": [
                "Esta etapa ajuda a entender o que se move junto com receita ou lucro.",
                "Ela não substitui análise causal, mas orienta testes e decisões do projeto.",
            ],
        }

    def aula_5(self) -> Dict[str, Any]:
        transacoes = self.prepared.transacoes
        series = self._series_from_days()
        dias = self.prepared.dias

        pagamentos = [t.get("pago_no_prazo") for t in transacoes if t.get("pago_no_prazo") is not None]
        atrasos = [not p for p in pagamentos]
        lucro_negativo = [1 if v < 0 else 0 for v in series["lucro"]]
        dias_com_venda = [1 if (d.get("vendas_qtd") or 0) > 0 else 0 for d in dias]

        prob_atraso = (sum(atrasos) / len(atrasos)) if atrasos else None
        prob_lucro_negativo = (sum(lucro_negativo) / len(lucro_negativo)) if lucro_negativo else None
        prob_dia_com_venda = (sum(dias_com_venda) / len(dias_com_venda)) if dias_com_venda else None

        return {
            "tema": "Trabalhar incerteza e risco financeiro",
            "problema_financeiro": "O empreendedor precisa decidir mesmo sem garantias, medindo chance e risco.",
            "calculos": {
                "espaco_amostral_dias": len(dias),
                "eventos_observados": {
                    "dias_com_venda": sum(dias_com_venda),
                    "dias_com_lucro_negativo": sum(lucro_negativo),
                    "pagamentos_em_atraso": sum(atrasos) if atrasos else 0,
                },
                "probabilidade_empirica_atraso_pagamento": round_or_none(prob_atraso, 4),
                "probabilidade_empirica_lucro_negativo": round_or_none(prob_lucro_negativo, 4),
                "probabilidade_empirica_dia_com_venda": round_or_none(prob_dia_com_venda, 4),
                "explicacao": {
                    "classica": "Depende de eventos equiprováveis previamente definidos.",
                    "empirica": "Calculada a partir da frequência observada nos dados do negócio.",
                    "subjetiva": "Pode ser adicionada pelo especialista do negócio como expectativa gerencial.",
                },
            },
            "insights": [
                "Aqui o sistema deixa de ser apenas descritivo e começa a lidar com risco financeiro.",
                "As probabilidades empíricas ajudam na tomada de decisão sob incerteza.",
            ],
        }

    def aula_6(self) -> Dict[str, Any]:
        series = self._series_from_days()
        tickets = self._ticket_values()
        vendas_qtd = series["vendas_qtd"]
        venda_ocorrencia = [1 if v > 0 else 0 for v in vendas_qtd]

        discrete_models = {
            "poisson": poisson_loglik(vendas_qtd),
            "binomial": binomial_loglik(vendas_qtd),
            "bernoulli": bernoulli_loglik(venda_ocorrencia),
        }
        continuous_models = {
            "gaussiana": normal_loglik(tickets),
            "exponencial": exponential_loglik(tickets),
            "uniforme": uniform_loglik(tickets),
        }

        valid_discrete = {k: v for k, v in discrete_models.items() if v is not None}
        valid_continuous = {k: v for k, v in continuous_models.items() if v is not None}

        best_discrete = max(valid_discrete.items(), key=lambda item: item[1]) if valid_discrete else None
        best_continuous = max(valid_continuous.items(), key=lambda item: item[1]) if valid_continuous else None

        return {
            "tema": "Modelar cenários financeiros com distribuições probabilísticas",
            "problema_financeiro": "O empreendedor quer escolher o modelo probabilístico mais adequado ao comportamento do negócio.",
            "calculos": {
                "comparacao_modelos_discretos": {k: round_or_none(v, 4) for k, v in discrete_models.items()},
                "modelo_discreto_mais_apropriado": {
                    "nome": best_discrete[0],
                    "score_loglik": round_or_none(best_discrete[1], 4),
                } if best_discrete else None,
                "comparacao_modelos_continuos": {k: round_or_none(v, 4) for k, v in continuous_models.items()},
                "modelo_continuo_mais_apropriado": {
                    "nome": best_continuous[0],
                    "score_loglik": round_or_none(best_continuous[1], 4),
                } if best_continuous else None,
                "criterio": "O modelo com maior log-verossimilhança é tratado como o mais aderente aos dados observados.",
            },
            "insights": [
                "Esta etapa compara modelos para escolher o mais coerente com contagens e valores do negócio.",
                "O resultado serve como base para simulações e projeções futuras.",
            ],
        }

    def aula_7(self) -> Dict[str, Any]:
        transacoes = self.prepared.transacoes
        series = self._series_from_days()
        tickets = self._ticket_values()

        ticket_outliers = iqr_outliers(tickets)
        lucro_outliers = iqr_outliers(series["lucro"])
        receita_norm = min_max_normalize(series["receita"])
        receita_z = z_score_standardize(series["receita"])
        lucro_norm = min_max_normalize(series["lucro"])
        lucro_z = z_score_standardize(series["lucro"])

        correlations = {
            "clientes": pearson_correlation(series["clientes"], series["lucro"]),
            "marketing": pearson_correlation(series["marketing"], series["lucro"]),
            "desconto_medio": pearson_correlation(series["desconto_medio"], series["lucro"]),
            "vendas_qtd": pearson_correlation([float(v) for v in series["vendas_qtd"]], series["lucro"]),
            "despesa": pearson_correlation(series["despesa"], series["lucro"]),
        }
        selected_features = [k for k, v in correlations.items() if v is not None and abs(v) >= 0.3]

        return {
            "tema": "Preparar dados reais para gerar insights confiáveis",
            "problema_financeiro": "Os dados reais chegam com ruídos, lacunas e escalas diferentes, o que compromete a análise.",
            "calculos": {
                "lacunas_transacoes": null_report(transacoes),
                "outliers_ticket": ticket_outliers,
                "outliers_lucro": lucro_outliers,
                "normalizacao_receita_preview": round_list(receita_norm[:10], 4),
                "padronizacao_receita_preview": round_list(receita_z[:10], 4),
                "normalizacao_lucro_preview": round_list(lucro_norm[:10], 4),
                "padronizacao_lucro_preview": round_list(lucro_z[:10], 4),
                "selecao_de_recursos_por_correlacao": {
                    "correlacoes_com_lucro": {k: round_or_none(v, 4) for k, v in correlations.items()},
                    "atributos_selecionados": selected_features,
                },
                "tlc_nota": "Com amostras suficientemente grandes, a distribuição da média amostral tende à normalidade.",
            },
            "insights": [
                "Esta fase limpa a base e prepara os dados para análises mais confiáveis.",
                "Também indica quais variáveis parecem mais úteis para prever ou explicar o lucro.",
            ],
        }

    def aula_8(self) -> Dict[str, Any]:
        series = self._series_from_days()
        tickets = self._ticket_values()
        receita_total = sum(series["receita"])
        despesa_total = sum(series["despesa"])
        lucro_total = sum(series["lucro"])
        margem = (lucro_total / receita_total) if receita_total else None
        prob_atraso = self.aula_5()["calculos"]["probabilidade_empirica_atraso_pagamento"]
        prob_lucro_negativo = self.aula_5()["calculos"]["probabilidade_empirica_lucro_negativo"]
        modelo_cont = self.aula_6()["calculos"]["modelo_continuo_mais_apropriado"]
        modelo_disc = self.aula_6()["calculos"]["modelo_discreto_mais_apropriado"]
        out_lucro = self.aula_7()["calculos"]["outliers_lucro"]
        categorias = [t.get("categoria") for t in self.prepared.transacoes]
        top_categorias = frequency_table(categorias, top_n=5)

        alertas = []
        if margem is not None and margem < 0.1:
            alertas.append("Margem de lucro baixa para o período analisado.")
        if prob_atraso is not None and prob_atraso > 0.2:
            alertas.append("Probabilidade de atraso de pagamento acima de 20%.")
        if prob_lucro_negativo is not None and prob_lucro_negativo > 0.3:
            alertas.append("Há risco relevante de dias com lucro negativo.")
        if out_lucro.get("valores_outliers"):
            alertas.append("Foram detectados outliers no lucro diário; convém investigar eventos excepcionais.")

        insights_acionaveis = [
            f"Receita total do período: R$ {receita_total:.2f}",
            f"Despesa total do período: R$ {despesa_total:.2f}",
            f"Lucro total do período: R$ {lucro_total:.2f}",
            f"Ticket médio: R$ {(safe_mean(tickets) or 0):.2f}",
        ]
        if modelo_disc:
            insights_acionaveis.append(f"Melhor modelo discreto observado: {modelo_disc['nome']}.")
        if modelo_cont:
            insights_acionaveis.append(f"Melhor modelo contínuo observado: {modelo_cont['nome']}.")

        return {
            "tema": "Detectar anomalias e apresentar insights visuais para decisão",
            "problema_financeiro": "O empreendedor precisa receber resultados claros, acionáveis e prontos para decisão.",
            "calculos": {
                "kpis_finais": {
                    "receita_total": round(receita_total, 2),
                    "despesa_total": round(despesa_total, 2),
                    "lucro_total": round(lucro_total, 2),
                    "margem_lucro": round_or_none(margem, 4),
                    "ticket_medio": round_or_none(safe_mean(tickets), 4),
                    "probabilidade_atraso_pagamento": prob_atraso,
                    "probabilidade_lucro_negativo": prob_lucro_negativo,
                },
                "alertas": alertas,
                "top_categorias": top_categorias,
                "dados_prontos_para_graficos": {
                    "receita_diaria": round_list(series["receita"], 2),
                    "despesa_diaria": round_list(series["despesa"], 2),
                    "lucro_diario": round_list(series["lucro"], 2),
                    "vendas_qtd_diaria": series["vendas_qtd"],
                },
                "normas_e_legislacao_nota": "Os resultados devem ser utilizados respeitando privacidade, finalidade dos dados, transparência analítica e normas vigentes aplicáveis ao contexto do negócio.",
            },
            "insights": insights_acionaveis,
        }

    def run(self) -> Dict[str, Any]:
        aulas = {
            "aula_1": self.aula_1(),
            "aula_2": self.aula_2(),
            "aula_3": self.aula_3(),
            "aula_4": self.aula_4(),
            "aula_5": self.aula_5(),
            "aula_6": self.aula_6(),
            "aula_7": self.aula_7(),
            "aula_8": self.aula_8(),
        }
        return {
            "sistema": "Insight Calculado",
            "versao": "1.0",
            "negocio": self.prepared.negocio,
            "recepcao": self.prepared.recepcao,
            "resumo_processamento": {
                "qtd_transacoes_recebidas": len(self.prepared.transacoes),
                "qtd_registros_diarios": len(self.prepared.dias),
                "campos_observados_transacoes": sorted({k for t in self.prepared.transacoes for k in t.keys()}),
                "campos_observados_dias": sorted({k for d in self.prepared.dias for k in d.keys()}),
            },
            **aulas,
            "modulo_final": {
                "descricao": "Módulo consolidado que recebe dados do empreendedor e retorna os cálculos aplicados ao longo das 8 aulas.",
                "saida_principal": aulas["aula_8"]["calculos"],
            },
        }


# ============================================================
# Exemplo de uso em linha de comando
# ============================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Uso: python insight_calculado_engine.py entrada.json saida.json")
        sys.exit(1)

    entrada = sys.argv[1]
    saida = sys.argv[2]

    dados = load_json(entrada)
    engine = InsightCalculadoEngine(dados)
    resultado = engine.run()
    save_json(saida, resultado)
    print(f"Arquivo gerado com sucesso: {saida}")
