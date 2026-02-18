# Clash Royale Opponent Tracker

Ferramenta em Python para identificar cartas do oponente em tempo real, usando visão computacional sobre slots fixos da interface do jogo.

O projeto monitora os 8 slots do deck, aprende a identidade de cada slot uma única vez e exibe no terminal:

- jogadas detectadas;
- estado de cartas por slot;
- estimativa da mão do oponente com ciclo FIFO (Opponent Hand Tracker).

## Compatibilidade de tela

O projeto está atualmente configurado para **Clash Royale em tela cheia** em um monitor **1920x1080**.

- Se você usa essa configuração (fullscreen em 1920x1080), pode executar o programa diretamente.
- Se você usa outra resolução, escala de tela ou layout de janela, é necessário recalibrar os slots.

Para recalibrar:

1. execute `python calibrate_slots.py`;
2. marque os 8 slots das cartas no replay da sua tela;
3. copie o `SLOTS_CONFIG` gerado para `detection.py`.

## Funcionalidades atuais

- Identificação visual por template matching (`OpenCV`).
- Memória por slot fixo (evita reidentificação desnecessária).
- Revisão manual quando a confiança da identificação é baixa.
- Salvamento automático de novos templates revisados pelo usuário.
- Tracker FIFO no terminal (bootstrap + atualização por jogada).
- Script interativo para calibrar coordenadas dos 8 slots.
- Script para baixar templates oficiais da API do Clash Royale.

## Estrutura do projeto

```text
clash-royale/
├── detection.py                 # Loop principal de detecção e tracker
├── screen_capture.py            # Captura de tela com fallback de backends
├── calibrate_slots.py           # Calibração interativa dos slots
├── main.py                      # Simulação local de deck FIFO via API
├── requirements.txt
├── cards/
│   ├── cards-templates/         # Templates oficiais
│   ├── cards-templates-user/    # Templates aprendidos em runtime
│   ├── download.py              # Download de cartas da API
│   └── size-adjustment.py       # Ajuste de tamanho dos templates
└── README.md
```

## Requisitos

- Python 3.10+ (recomendado)
- Dependências em `requirements.txt`
- Janela do jogo visível para captura

Dependências principais:

- `opencv-python`
- `mss`
- `numpy`
- `Pillow`
- `requests`
- `python-dotenv`

## Instalação

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração de ambiente (API)

Os scripts que consultam a API (`main.py` e `cards/download.py`) usam a variável:

- `CR_API_TOKEN`

Exemplo de `.env`:

```env
CR_API_TOKEN=seu_token_aqui
```

Observação: para a API oficial funcionar, o IP da máquina precisa estar autorizado no portal de desenvolvedores do Clash Royale.

## Fluxo recomendado de uso

### 1) Calibrar os slots

Execute:

```bash
python calibrate_slots.py
```

Ao final, o script imprime um bloco `SLOTS_CONFIG` e salva `slots_config.txt`.  
Copie o conteúdo para `SLOTS_CONFIG` em `detection.py`.

### 2) Preparar templates (opcional, mas recomendado)

Baixar templates oficiais:

```bash
python cards/download.py
```

Ajustar tamanho dos templates:

```bash
python cards/size-adjustment.py
```

### 3) Rodar a detecção em tempo real

```bash
python detection.py
```

## Como o detector funciona

1. Captura frames da tela.
2. Avalia cada slot para classificar estado (`EMPTY` ou `FULL`).
3. Em transição `EMPTY -> FULL`, considera que houve nova carta no slot.
4. Se o slot já é conhecido, reutiliza memória do slot.
5. Se o slot é desconhecido, faz identificação por templates:
   - confiança alta: aceita automaticamente;
   - confiança baixa: solicita revisão manual.
6. Atualiza o tracker FIFO e imprime estado da mão estimada.

## Opponent Hand Tracker (FIFO no terminal)

O tracker segue estratégia simples/rápida:

- **Bootstrap (4 primeiras jogadas detectadas):** preenche a fila de ciclo.
- **Da 5ª jogada em diante:**
  - remove a primeira carta da fila (`entrou`);
  - adiciona a carta jogada ao final da fila;
  - atualiza a mão estimada do oponente.

Saída típica:

```text
[HAND][BOOT] 3/4 | slot=S2 | fonte=TEMPLATE | jogada=Fireball | fila_ciclo=[Knight, Archers, Fireball, ?]
[HAND] #012 | slot=S1 | fonte=MEMORIA | jogada=Valkyrie | entrou=Knight | mao=[Knight, Wizard, ?, ?] | fila_ciclo=[...]
```

## Padrão de logs

- `[CAPTURE][...]` inicialização e fallback de captura.
- `[INIT][TEMPLATES]` carga de templates.
- `[STATE]` mapeamento de carta por slot.
- `[PLAY][TEMPLATE|MANUAL|MEMORIA]` jogadas detectadas.
- `[HAND][...]` estado do tracker FIFO.
- `[REVIEW]` confirmação manual de carta.
- `[WARN]` e `[ERROR]` alertas e falhas.

## Troubleshooting

- **Não detecta cartas corretamente**
  - recalibre os slots (`calibrate_slots.py`);
  - confirme que o tamanho do ROI está alinhado com cartas reais na tela;
  - aumente a base de templates em `cards/cards-templates-user`.

- **Muitas revisões manuais**
  - qualidade/resolução da captura pode estar baixa;
  - revise templates e mantenha variações relevantes.

- **Falha na API (401/403)**
  - valide `CR_API_TOKEN`;
  - confira autorização de IP no portal de devs da Supercell.

- **Sem captura de tela**
  - verifique permissões de captura no sistema;
  - no Linux/Wayland, teste sessão X11 quando aplicável.

## Limitações atuais

- O tracker de mão usa heurística de bootstrap simples (estimativa inicial).
- Dependência de coordenadas fixas de slot por resolução/posição de janela.
- Não há persistência de estado da partida entre execuções.

## Próximos passos sugeridos

- Persistir estado da partida (deck conhecido e histórico).
- Melhorar confiança do tracker com validação cruzada de eventos.
- Exportar logs estruturados para análise pós-partida.
