# Design System Playbook (Access)

## Objetivo
Este playbook define padrões visuais, de interação e de conteúdo para evitar drift de interface ao longo do tempo.

## Princípios
1. **Consistência antes de customização**: use componentes/helpers centrais.
2. **Acessibilidade por padrão**: contraste AA, foco visível e teclado completo.
3. **Feedback explícito**: toda ação importante deve informar estado (carregando, sucesso, erro).
4. **Semântica de cor**: tokens de estado e superfície em vez de hex hardcoded.

---

## Tokens e quando usar

### Superfícies
- `bg`: fundo macro da tela (área externa/estrutura).
- `light_bg`: fundo claro para telas de entrada (quando o contexto exigir).
- `surface`: cartões, blocos de conteúdo principal.
- `surface_alt`: campos e áreas secundárias.

### Texto
- `on_surface`: texto padrão sobre `surface` e `surface_alt`.
- `muted_text`: texto auxiliar/metadata.
- `on_primary`: texto em botões primários.

### Seleção vs foco
- `selection_bg` / `selection_fg`: seleção persistente (Treeview/lista, item selecionado).
- `focus_bg` / `focus_text`: foco momentâneo (navegação por teclado, highlight de foco).

### Estados
- `info`, `success`, `warning`, `danger` + `on_*` correspondente.
- `disabled_bg`, `disabled_fg` para controles desativados.

### Tipografia e espaçamento
- Fonte via `theme_font(...)`.
- Espaçamento via `theme_space(...)`.
- Evitar valores literais de `padx/pady/font` em novas implementações.

---

## Tokens obrigatórios por componente

### Botões
- Primário: `primary` + `on_primary`.
- Secundário: `surface_alt` + `on_surface`.
- Estado hover/focus obrigatório.

### Inputs
- Fundo `surface_alt`.
- Texto `on_surface`.
- Disabled com `disabled_bg/disabled_fg`.

### Tree/Lista
- Base em `surface`.
- Cabeçalho em `surface_alt`.
- Seleção em `selection_bg/selection_fg`.

### Banners e badges
- Nunca usar hex hardcoded para estado.
- Sempre usar tokens semânticos (`success/warning/danger/info`).

---

## Tabela de estados (UI)

| Estado | Visual esperado | Texto esperado |
|---|---|---|
| default | contraste normal | objetivo da ação |
| hover | leve variação de bg | opcional |
| focus | contorno/foco visível | opcional |
| disabled | contraste reduzido, legível | explicitar indisponibilidade |
| loading | indicador de progresso | "Salvando…", "Aplicando…" |
| success | cor de sucesso + confirmação curta | "Salvo com sucesso" |
| error | cor de erro + ação sugerida | "Falha ao salvar. Tente novamente" |

---

## A11y (AA operacional) checklist por tela

- [ ] Todos os controles alcançáveis por teclado.
- [ ] Ordem de Tab previsível.
- [ ] Foco visível em todos os controles interativos.
- [ ] Contraste validado para todos os temas (`escuro`, `claro`, `alto_contraste`).
- [ ] Estados transitórios claros (salvando/salvo/erro).
- [ ] Atalhos visíveis em hints/tooltip quando aplicável.

---

## Information design

- Priorizar o que exige ação (cards de estado no topo).
- Agrupar por prioridade (não apenas por origem de dado).
- Reduzir ruído de campos auxiliares no fluxo primário.
- Permitir presets por operador/turno para acelerar rotina.

---

## Fluxo transacional de edição

- `dirty state` global deve ser explícito.
- Ações de undo/redo disponíveis por teclado.
- Confirmação de sucesso com timeout e contexto do registro.

---

## Guia de microcopy

### Padrões
- Botão: verbo no infinitivo (ex.: **Aplicar filtros**).
- Resultado: verbo no particípio/passado curto (ex.: **Filtros aplicados**).
- Erro: mensagem curta + ação recomendada.

### Faça
- "Aplicar filtros"
- "Filtros aplicados"
- "Falha ao salvar. Revise o conteúdo e tente novamente."

### Não faça
- "OK"
- "Erro desconhecido"
- "Operação inválida"

---

## Regra de PR (obrigatória)

Todo novo widget/tela deve:
1. usar helper/componente central (`ui_theme.py` / `ui_components.py`), **ou**
2. justificar exceção explicitamente na descrição do PR.

Sem essa justificativa, o PR deve ser considerado incompleto.
