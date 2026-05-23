# README — FASE 2 do Projeto Integrador

## Visão geral

Esta pasta reúne os arquivos da **Fase 2** do projeto, responsável pela **geração de relatórios personalizáveis** a partir da saída do sistema **Insight Calculado**.

A ideia desta etapa é receber o arquivo JSON produzido pelo módulo principal do Insight Calculado e transformá-lo em relatórios úteis para análise e apresentação, com possibilidade de exportação em diferentes formatos, incluindo **CSV**, **Excel** e **PDF** com aparência de relatório corporativo financeiro.

---

## Arquivos da pasta

### 1. `insight_relatorio_generator.py`
Este é o **gerador principal de relatórios**.

#### Função
Lê o arquivo JSON de saída do Insight Calculado e gera os relatórios finais.

#### O que ele pode gerar
- arquivos **CSV**
- arquivo **Excel (.xlsx)** com múltiplas abas
- arquivo **PDF** com resumo executivo, KPIs, gráficos e informações relevantes

#### Quando usar
Use este arquivo quando quiser executar o sistema de forma mais direta, normalmente via linha de comando, passando os parâmetros manualmente.

#### Exemplo de uso
```bash
python insight_relatorio_generator.py saida_insight.json pasta_saida config_relatorio_corporativo.json
```

---

### 2. `insight_relatorio_generator_interativo_corrigido.py`
Esta é a versão **interativa via terminal** do gerador de relatórios.

#### Função
Em vez de exigir todos os parâmetros na linha de comando, o programa faz perguntas ao usuário durante a execução.

#### O que ele solicita
- arquivo JSON de saída do Insight Calculado
- pasta de destino dos relatórios
- arquivo opcional de configuração visual
- prefixo opcional para os nomes dos arquivos

#### Quando usar
Use esta versão quando quiser uma experiência mais amigável, mas ainda aceitando entradas por texto no terminal.

#### Exemplo de uso
```bash
python insight_relatorio_generator_interativo_corrigido.py
```

---

### 3. `insight_relatorio_generator_explorador_windows.py`
Esta é a versão mais amigável para o usuário final, utilizando o **Explorador de Arquivos do Windows**.

#### Função
Permite selecionar o arquivo JSON e a pasta de saída usando janelas gráficas do Windows, sem precisar digitar caminhos manualmente.

#### Recursos
- seleção de arquivo por janela
- seleção de pasta por janela
- possibilidade de usar configuração visual opcional
- ideal para usuários com menos familiaridade com terminal

#### Quando usar
Esta é a versão mais indicada para demonstrações, uso em aula e utilização por usuários finais.

#### Exemplo de uso
```bash
python insight_relatorio_generator_explorador_windows.py
```

---

### 4. `config_relatorio_corporativo.json`
Este arquivo contém a **configuração visual e estrutural** do relatório.

#### Função
Permite personalizar a identidade do relatório gerado, especialmente o PDF.

#### Pode incluir
- nome da empresa
- subtítulo do relatório
- textos institucionais
- seções habilitadas
- títulos personalizados
- estilo executivo/corporativo
- parâmetros usados para apresentação do relatório

#### Quando usar
Use este arquivo quando quiser dar ao relatório uma aparência mais profissional, institucional ou adaptada ao contexto do empreendedor, da disciplina ou da empresa.

---

## Fluxo geral de funcionamento

O fluxo desta fase funciona assim:

1. O módulo **Insight Calculado** gera um arquivo JSON com os cálculos organizados por aula.
2. Um dos geradores de relatório desta pasta lê esse JSON.
3. O sistema processa os dados e cria arquivos de saída em formatos úteis para análise e apresentação.
4. Os relatórios podem ser entregues ao empreendedor, usados em aula ou incorporados ao projeto maior.

---

## Diferença entre os scripts

### `insight_relatorio_generator.py`
Versão principal e mais direta.

### `insight_relatorio_generator_interativo_corrigido.py`
Versão com perguntas no terminal.

### `insight_relatorio_generator_explorador_windows.py`
Versão com janelas do Windows para seleção de arquivo e pasta.

---

## Sugestão de uso prático

### Para desenvolvimento e testes
Use:
- `insight_relatorio_generator.py`

### Para aulas e demonstrações guiadas
Use:
- `insight_relatorio_generator_interativo_corrigido.py`

### Para uso mais amigável por usuários finais
Use:
- `insight_relatorio_generator_explorador_windows.py`

---

## Dependências recomendadas

Para que os relatórios funcionem corretamente, recomenda-se instalar:

```bash
pip install pandas openpyxl matplotlib reportlab
```

Dependendo da estrutura interna do projeto, outras bibliotecas podem ser usadas, mas essas são as principais para:
- manipulação de dados
- exportação em Excel
- geração de gráficos
- criação de PDF

---

## Observação importante

O arquivo de entrada desta fase deve ser o **JSON de saída do Insight Calculado**, ou seja, o resultado já processado pelo sistema da fase anterior.

Sem esse JSON, os geradores de relatório não terão a base necessária para produzir:
- indicadores
- tabelas
- gráficos
- resumos financeiros
- relatório executivo final

---

## Resultado esperado

Ao final da execução, o sistema poderá entregar:
- relatórios tabulares em **CSV**
- planilha consolidada em **Excel**
- relatório executivo em **PDF**
- material pronto para análise financeira, apresentação acadêmica ou entrega ao empreendedor

---

## Estrutura resumida da pasta

```text
FASE 2/
├── config_relatorio_corporativo.json
├── insight_relatorio_generator.py
├── insight_relatorio_generator_interativo_corrigido.py
└── insight_relatorio_generator_explorador_windows.py
```

---

## Conclusão

Esta pasta representa a etapa em que o projeto deixa de apenas calcular indicadores e passa a **comunicar resultados de forma profissional**.

Em termos pedagógicos, esta fase é importante porque mostra ao aluno que:
- calcular é importante
- organizar é necessário
- mas **apresentar bem os resultados** é essencial para gerar valor real ao empreendedor

