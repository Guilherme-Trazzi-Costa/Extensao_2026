# Insight Calculado — motor didático em Python

Este projeto recebe um arquivo JSON com dados do empreendedor, executa os cálculos estatísticos e probabilísticos organizados pelas 8 aulas da disciplina e devolve um novo JSON com os resultados aula a aula.

## Arquivos

- `insight_calculado_engine.py` → motor principal
- `exemplo_entrada_insight_calculado.json` → entrada de teste
- `exemplo_saida_insight_calculado.json` → saída gerada pelo sistema

## Estrutura esperada de entrada

```json
{
  "negocio": {
    "nome": "Nome do negócio",
    "segmento": "Segmento",
    "cidade": "Cidade"
  },
  "recepcao": {
    "origem": "formulario_web"
  },
  "dados": {
    "transacoes": [
      {
        "id": "T001",
        "data": "2026-04-01",
        "tipo": "receita",
        "categoria": "Venda",
        "valor": 320.50,
        "cliente": "Cliente A",
        "forma_pagamento": "pix",
        "pago_no_prazo": true,
        "desconto": 0.0,
        "marketing": 25.0
      }
    ],
    "dias": []
  }
}
```

## Como executar

```bash
python insight_calculado_engine.py exemplo_entrada_insight_calculado.json exemplo_saida_insight_calculado.json
```

## O que o sistema devolve

O JSON de saída contém:

- `aula_1` até `aula_8`
- `resumo_processamento`
- `modulo_final`

Cada aula contém:

- `tema`
- `problema_financeiro`
- `calculos`
- `insights`

## O que cada aula calcula

- **Aula 1**: classificação dos dados, amostra e lacunas iniciais
- **Aula 2**: média, mediana, moda, amplitude, variância e desvio padrão
- **Aula 3**: frequência, contingência, quartis, decis e percentis
- **Aula 4**: correlações e associações entre variáveis
- **Aula 5**: probabilidades empíricas de eventos financeiros
- **Aula 6**: comparação de modelos probabilísticos por log-verossimilhança
- **Aula 7**: lacunas, outliers, normalização, padronização e seleção de atributos
- **Aula 8**: KPIs finais, alertas e dados prontos para visualização

## Observações didáticas

- Se o bloco `dias` não for enviado, o sistema deriva os registros diários a partir das transações.
- O motor foi escrito com foco didático e sem dependência de bibliotecas externas.
- Você pode acoplar este módulo a um formulário web, Streamlit, Flask, FastAPI ou n8n.
