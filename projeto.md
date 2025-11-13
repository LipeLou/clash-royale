## 📝 Resumo do Projeto: Rastreador de Mão do Oponente no Clash Royale

### 1. Objetivo Principal

Desenvolver uma ferramenta em **Python** que utiliza **OpenCV** para analisar a tela do **modo espectador (ao vivo)** do Clash Royale. O objetivo é rastrear, em tempo real, as 8 cartas do deck do oponente, a sua ordem de ciclo (fila FIFO) e, secundariamente, sua contagem de elixir.

### 2. Fonte de Dados (Input)

* **Captura de Tela em Tempo Real:** A ferramenta deve capturar o monitor (especificamente a janela do jogo no modo espectador) em tempo real.
* **Restrição:** O modo espectador é essencial, pois é o único local que exibe os 8 slots de cartas do oponente.

### 3. Lógica Central e Mecânicas do Jogo

O projeto é dividido em três fases lógicas que ocorrem simultaneamente após a inicialização.

#### Fase 1: Descoberta do Deck (Treinamento/Identificação)

* **Problema:** O espectador mostra 8 cartas viradas ("?") que são reveladas apenas quando jogadas pela primeira vez.
* **Solução:** O modelo (treinado com imagens das cartas) deve:
    1.  Observar os 8 slots fixos.
    2.  Quando uma carta "?" é substituída por uma imagem de tropa (ex: "Bruxa"), o sistema deve identificar essa carta.
    3.  O sistema deve "travar" aquela identidade àquele slot (ex: `Slot[0] = Bruxa`, `Slot[1] = Gigante`, etc.).
* **Resultado:** Após o oponente usar todas as 8 cartas pelo menos uma vez, o sistema saberá o deck completo e a posição fixa de cada carta na interface do espectador.

#### Fase 2: Detecção de Jogo (O Gatilho)

* **Problema:** Como saber *quando* o oponente joga uma carta específica, se as 8 cartas agora ficam visíveis nos slots?
* **Solução (O Gatilho):** Quando o oponente joga uma carta (ex: a "Bruxa" do `Slot[0]`), a carta naquele slot desaparece brevemente, **revelando o fundo da tela (uma cor vermelha distinta)**.
* **Tarefa do OpenCV:** Monitorar continuamente as 8 regiões (slots). Quando uma **abundância da cor vermelha** for detectada em uma região específica (ex: `Slot[0]`), o sistema registra que a "Bruxa" foi jogada.

#### Fase 3: Rastreamento de Mão (Lógica FIFO)

* **Problema:** O oponente tem 8 cartas, mas apenas 4 estão na "mão" (jogáveis). Como saber quais são?
* **Mecânica:** O deck funciona como uma fila (First In, First Out). As 4 primeiras da fila são a mão.
* **Solução (Lógica do Sistema):**
    1.  O sistema mantém uma estrutura de dados (ex: uma lista ou `deque`) com as 8 cartas identificadas (Fase 1).
    2.  Quando o Gatilho (Fase 2) detecta que a "Bruxa" (que estava no `Slot[0]` e era a 1ª da fila) foi jogada:
    3.  O sistema move a "Bruxa" para o **final** da fila.
    4.  Todas as outras cartas sobem uma posição.
    5.  A carta que estava na 5ª posição agora é a 4ª (e entra na mão).
* **Resultado:** A ferramenta pode exibir, em tempo real, as 4 primeiras cartas da fila, que representam a mão atual do oponente.

### 4. Funcionalidade Adicional: Rastreamento de Elixir

* **Objetivo:** Além da mão, rastrear o elixir do oponente.
* **Lógica:**
    1.  O sistema deve ter um banco de dados com o custo de elixir de cada carta (identificadas na Fase 1).
    2.  Quando o Gatilho (Fase 2) dispara (ex: "Bruxa" jogada), o sistema subtrai o custo (ex: 5 elixir) do contador de elixir do oponente.
    3.  O sistema deve, simultaneamente, simular a regeneração de elixir (aprox. 1 elixir a cada X segundos) até o máximo de 10.

### 5. Requisitos Técnicos e Desafios

1.  **Captura de Tela:** O OpenCV deve capturar a tela de forma eficiente e em tempo real (ex: usando a biblioteca `mss` em conjunto com o NumPy e OpenCV).
2.  **Velocidade de Processamento:** O ciclo (Capturar -> Detectar Gatilho Vermelho -> Atualizar Fila) deve ser mais rápido que a jogada, para ser útil.
3.  **Modelo de Reconhecimento (Fase 1):** Necessidade de treinar um modelo (Template Matching do OpenCV pode ser suficiente, dado que as cartas são estáticas e distintas) para identificar as ~100+ cartas do jogo.
4.  **Robustez do Gatilho (Fase 2):** A detecção da "cor vermelha" deve ser precisa (baseada em *região* e *cor*, não em um único pixel) para evitar falsos positivos.