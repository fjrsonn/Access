# Modernização do Painel Operacional (sem poluição visual)

## Objetivo
Evoluir o visual e a usabilidade do Painel Operacional com foco em clareza, hierarquia e eficiência, mantendo o produto enxuto e orientado a operação.

## O que já existe e deve ser preservado
- Base de design tokens com tema, tipografia, espaçamento e contraste.
- Cards de métricas com tendência/capacidade e modos de densidade.
- Modo Operação, atalhos de teclado e métricas de UX já instrumentadas.

## Propostas de melhoria (priorizadas)

### 1) Hierarquia visual mais forte no topo do painel
- Transformar o bloco superior em 3 níveis visuais:
  1. **Contexto** (título + timestamp de atualização global);
  2. **KPI principal** (1 card destaque com maior impacto operacional);
  3. **KPIs secundários** (demais cards em escala visual menor).
- Benefício: leitura em 2-3 segundos, sem adicionar novos widgets.

### 2) Cards mais “limpos” e orientados a decisão
- Reduzir ruído textual nos cards:
  - `meta` e `capacity` com menor proeminência visual.
  - destacar **valor atual + variação** como informação primária.
- Padronizar semântica de tendência:
  - `↑` melhora, `↓` piora, `→` estável;
  - usar limiar mínimo para evitar “oscilação de ruído” em variações pequenas.
- Ativar visual donut apenas sob demanda (hover/foco), mantendo padrão minimalista.

### 3) Paleta e contraste com consistência operacional
- Consolidar escala de tons por severidade:
  - info (azul), success (verde), warning (âmbar), danger (vermelho), já existentes.
- Criar nível de contraste “foco operação”:
  - textos críticos com contraste AA+;
  - elementos secundários com opacidade reduzida controlada.
- Resultado: visual mais moderno com menos “peso”, sem perder legibilidade.

### 4) Gráficos úteis (somente os necessários)
Adicionar **apenas 2 visualizações de alto valor**:
- **Sparkline por card (últimos 30-60 min)** para tendência imediata;
- **Barras empilhadas por status** para distribuição atual.

Evitar:
- pizza múltipla, gauges redundantes e animações contínuas.
- mais de 1 gráfico por bloco sem pergunta operacional clara.

### 5) Layout responsivo por densidade real
- Manter os modos confortável/compacto, mas com regras explícitas:
  - Compacto: menos padding, sem textos auxiliares longos;
  - Confortável: com dicas/contexto.
- Grid adaptativo de cards:
  - 4 colunas (largura ampla),
  - 2x2 (média),
  - 1 coluna (estreita).

### 6) Microinterações modernas, porém discretas
- Manter animação de entrada apenas no primeiro carregamento.
- Atualização periódica: usar transição curta de número/cor (120-200ms), sem “piscar”.
- Estados vazios e erro com mensagens curtas e ação recomendada (“Recarregar”, “Reaplicar filtro”).

### 7) Acessibilidade e padronização de interação
- Teclado: foco visível mais forte em ações críticas.
- Tooltip: mostrar somente em truncamento ou dúvida contextual.
- Tipografia: preservar preset acessível e elevar para padrão quando monitor > 1080p.

### 8) Governança de UX (decidir por dados, não opinião)
Usar as métricas já existentes para ciclo mensal de melhoria:
- `time_to_apply_filter_ms` (alvo: queda de p95);
- `edit_save_success_rate` (alvo: aumento);
- adoção de atalhos e trocas de tema para validar utilidade real.

## Roadmap enxuto (30 dias)

### Semana 1
- Ajuste de hierarquia visual do topo e prioridade textual dos cards.
- Revisão de espaçamento/contraste por token (sem criar componentes novos).

### Semana 2
- Implementar sparkline leve por card (toggle por preferência).
- Implementar barras empilhadas por status no bloco analítico.

### Semana 3
- Refino de microinterações + estados vazios/erro.
- Melhorias de acessibilidade e teclado.

### Semana 4
- A/B interno entre layout atual vs. modernizado.
- Decisão por métricas UX já coletadas e feedback operacional.

## Checklist de “não poluir”
- Cada novo elemento responde a uma pergunta operacional clara?
- Remove ou reduz algo antigo ao introduzir algo novo?
- Mantém leitura em menos de 3 segundos no topo?
- Funciona em modo compacto sem perda de decisão?
- Não adiciona animação contínua decorativa?

Se qualquer resposta for “não”, a mudança deve ser revista.
