import cv2
import numpy as np
import time
import os
from pathlib import Path
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from screen_capture import ScreenCapture

# Importações do main.py para lógica de jogo
import sys
sys.path.append(str(Path(__file__).parent.parent))
from main import ClashRoyaleAPI, Carta, DeckState
from dotenv import load_dotenv

# ==============================================================================
# CONFIGURAÇÃO DOS SLOTS (ROI)
# ==============================================================================
# Dimensões padrão de uma carta (ajuste conforme size-adjustment.py)
CARD_WIDTH = 61
CARD_HEIGHT = 90

# Defina o canto superior esquerdo (Left, Top) para cada um dos 8 slots
# DICA: Use o Paint para pegar as coordenadas exatas do início de cada carta
# IMPORTANTE: Você deve ajustar estes valores para a posição real no seu monitor!
SLOTS_CONFIG = [
    {"id": 0, "left": 731, "top": 58},  # Slot 0
    {"id": 1, "left": 796, "top": 58},  # Slot 1
    {"id": 2, "left": 861, "top": 58},  # Slot 2
    {"id": 3, "left": 926, "top": 58},  # Slot 3
    {"id": 4, "left": 991, "top": 58},  # Slot 4
    {"id": 5, "left": 1056, "top": 58},  # Slot 5
    {"id": 6, "left": 1121, "top": 58},  # Slot 6
    {"id": 7, "left": 1186, "top": 58},  # Slot 7
]

# ==============================================================================
# CALIBRAÇÃO DE COR (Detecção de Fundo Vermelho)
# ==============================================================================
# O slot é considerado "VAZIO" se a cor média da região central for avermelhada
RED_MIN_R = 130  # Mínimo de componente Vermelho (0-255)
RED_MAX_G = 80   # Máximo de componente Verde (0-255)
RED_MAX_B = 80   # Máximo de componente Azul (0-255)

# ==============================================================================
# CONFIGURAÇÃO DE IDENTIFICAÇÃO
# ==============================================================================
TEMPLATES_DIR = Path(__file__).parent / "cards" / "cards-templates"
MATCH_THRESHOLD = 0.15  # Score mínimo para considerar uma correspondência válida

# ==============================================================================
# CONFIGURAÇÃO DE ELIXIR
# ==============================================================================
ELIXIR_INICIAL = 5.0  # Elixir inicial do oponente
ELIXIR_MAX = 10.0     # Elixir máximo
ELIXIR_REGENERACAO = 0.7  # Elixir regenerado por segundo (aproximado)

class CardIdentifier:
    """Identifica cartas comparando imagens com templates usando matchTemplate."""
    
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.templates_cache = {}  # Cache de templates carregados
        self._load_templates()
    
    def _load_templates(self):
        """Carrega todos os templates PNG do diretório."""
        if not self.templates_dir.exists():
            print(f"AVISO: Diretório de templates não encontrado: {self.templates_dir}")
            return
        
        png_files = list(self.templates_dir.glob("*.png"))
        print(f"Carregando {len(png_files)} templates...")
        
        for template_path in png_files:
            try:
                template_img = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
                if template_img is not None:
                    # Extrai o nome da carta do nome do arquivo
                    # Ex: "witch_medium.png" -> "Witch"
                    nome_arquivo = template_path.stem
                    # Remove sufixos "_medium" ou "_evolutionMedium"
                    nome_carta = nome_arquivo.replace("_medium", "").replace("_evolutionMedium", "")
                    # Converte para formato de nome (primeira letra maiúscula)
                    nome_carta = nome_carta.replace("-", " ").title()
                    
                    # Armazena tanto medium quanto evolutionMedium com o mesmo nome base
                    if nome_carta not in self.templates_cache:
                        self.templates_cache[nome_carta] = []
                    self.templates_cache[nome_carta].append(template_img)
            except Exception as e:
                print(f"Erro ao carregar template {template_path.name}: {e}")
        
        print(f"Templates carregados: {len(self.templates_cache)} cartas únicas")
    
    def identify_card(self, target_img) -> Optional[Tuple[str, float]]:
        """
        Identifica a carta na imagem alvo comparando com todos os templates.
        
        Retorna: (nome_carta, score) ou None se nenhuma correspondência for encontrada.
        """
        best_match, best_score = self.get_best_guess(target_img)
        
        # Retorna apenas se o score for acima do threshold
        if best_score >= MATCH_THRESHOLD:
            return (best_match, best_score)
        
        return None

    def get_best_guess(self, target_img) -> Tuple[Optional[str], float]:
        """Retorna a melhor correspondência encontrada, independente do threshold."""
        if not self.templates_cache:
            return (None, 0.0)
        
        best_match = None
        best_score = 0.0
        
        # Compara com todos os templates
        for nome_carta, templates in self.templates_cache.items():
            for template in templates:
                try:
                    # Redimensiona o template se necessário para corresponder ao alvo
                    if template.shape[:2] != target_img.shape[:2]:
                        template_resized = cv2.resize(template, (target_img.shape[1], target_img.shape[0]))
                    else:
                        template_resized = template
                    
                    # Usa matchTemplate com método TM_CCOEFF_NORMED (retorna 0-1)
                    result = cv2.matchTemplate(target_img, template_resized, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    
                    if max_val > best_score:
                        best_score = max_val
                        best_match = nome_carta
                except Exception as e:
                    # Ignora erros de comparação e continua
                    continue
        
        return (best_match, best_score)


@dataclass
class SlotInfo:
    """Informações sobre um slot específico."""
    nome_carta: Optional[str] = None
    elixir: Optional[int] = None
    carta_obj: Optional[Carta] = None


class GameState:
    """Gerencia o estado do jogo: elixir, deck identificado, etc."""
    
    def __init__(self, api: ClashRoyaleAPI):
        self.api = api
        self.elixir_atual = ELIXIR_INICIAL
        self.ultima_atualizacao_elixir = time.time()
        
        # Mapeamento de nome da carta (como aparece na identificação) -> Carta da API
        self.cartas_cache: Dict[str, Carta] = {}
        
        # Informações de cada slot
        self.slots_info: Dict[int, SlotInfo] = {i: SlotInfo() for i in range(8)}
        
        # Deck identificado (lista de 8 cartas conforme identificadas)
        self.deck_identificado: list[Optional[Carta]] = [None] * 8
        
    def normalizar_nome_carta(self, nome_identificado: str) -> str:
        """
        Normaliza o nome identificado para corresponder ao formato da API.
        Ex: "Witch" -> "Witch", "Goblin Barrel" -> "Goblin Barrel"
        """
        # Remove espaços extras e capitaliza corretamente
        nome = nome_identificado.strip()
        # A API usa nomes como "Goblin Barrel", "Hog Rider", etc.
        return nome
    
    def obter_carta_da_api(self, nome_identificado: str) -> Optional[Carta]:
        """Busca a carta na API e retorna o objeto Carta."""
        # Verifica cache primeiro
        if nome_identificado in self.cartas_cache:
            return self.cartas_cache[nome_identificado]
        
        # Normaliza o nome
        nome_normalizado = self.normalizar_nome_carta(nome_identificado)
        
        try:
            # Busca na API
            cartas = self.api.listar_cartas()
            for carta in cartas:
                # Comparação case-insensitive
                if carta.nome.lower() == nome_normalizado.lower():
                    self.cartas_cache[nome_identificado] = carta
                    return carta
        except Exception as e:
            print(f"Erro ao buscar carta '{nome_identificado}' na API: {e}")
        
        return None
    
    def registrar_carta_identificada(self, slot_id: int, nome_carta: str):
        """Registra que uma carta foi identificada em um slot."""
        carta = self.obter_carta_da_api(nome_carta)
        
        if carta:
            self.slots_info[slot_id].nome_carta = nome_carta
            self.slots_info[slot_id].elixir = carta.elixir
            self.slots_info[slot_id].carta_obj = carta
            self.deck_identificado[slot_id] = carta
            print(f"[GameState] Slot {slot_id}: {carta.nome} ({carta.elixir} elixir)")
        else:
            print(f"[GameState] AVISO: Carta '{nome_carta}' não encontrada na API")
            self.slots_info[slot_id].nome_carta = nome_carta
    
    def registrar_carta_jogada(self, slot_id: int):
        """Registra que uma carta foi jogada e atualiza o elixir."""
        slot_info = self.slots_info[slot_id]
        
        if slot_info.carta_obj:
            # Atualiza elixir considerando regeneração desde última atualização
            agora = time.time()
            tempo_decorrido = agora - self.ultima_atualizacao_elixir
            self.elixir_atual = min(ELIXIR_MAX, self.elixir_atual + (ELIXIR_REGENERACAO * tempo_decorrido))
            
            # Subtrai o custo da carta jogada
            self.elixir_atual = max(0, self.elixir_atual - slot_info.carta_obj.elixir)
            self.ultima_atualizacao_elixir = agora
            
            print(f"[GameState] Elixir atualizado: {self.elixir_atual:.1f} (Carta: {slot_info.carta_obj.nome}, Custo: {slot_info.carta_obj.elixir})")
        else:
            print(f"[GameState] AVISO: Tentativa de jogar carta desconhecida no slot {slot_id}")
    
    def atualizar_elixir_regeneracao(self):
        """Atualiza o elixir baseado na regeneração natural (chamar periodicamente)."""
        agora = time.time()
        tempo_decorrido = agora - self.ultima_atualizacao_elixir
        self.elixir_atual = min(ELIXIR_MAX, self.elixir_atual + (ELIXIR_REGENERACAO * tempo_decorrido))
        self.ultima_atualizacao_elixir = agora
    
    def get_elixir_atual(self) -> float:
        """Retorna o elixir atual (atualizado com regeneração)."""
        self.atualizar_elixir_regeneracao()
        return self.elixir_atual


class GameWatcher:
    def __init__(self):
        self.capturer = ScreenCapture()
        self.monitor = self.capturer.get_monitor_info()

        # Estado dos slots: "UNKNOWN", "EMPTY", "FULL"
        self.slots_status = {i: "UNKNOWN" for i in range(len(SLOTS_CONFIG))}
        
        # Memória: Qual carta está em cada slot? (Nome da carta ou None)
        self.slots_identity = {i: None for i in range(len(SLOTS_CONFIG))}
        
        # Inicializa o identificador de cartas
        self.card_identifier = CardIdentifier(TEMPLATES_DIR)
        
        # Inicializa API e GameState
        load_dotenv()
        token = os.getenv("CR_API_TOKEN")
        if not token:
            print("AVISO: CR_API_TOKEN não encontrado. Funcionalidades de elixir desabilitadas.")
            self.api = None
            self.game_state = None
        else:
            try:
                self.api = ClashRoyaleAPI(token)
                self.game_state = GameState(self.api)
                print("API do Clash Royale conectada com sucesso!")
            except Exception as e:
                print(f"AVISO: Erro ao conectar com API: {e}. Funcionalidades de elixir desabilitadas.")
                self.api = None
                self.game_state = None

    def capture_screen(self):
        """Captura a tela inteira."""
        return self.capturer.grab()

    def get_slot_roi(self, frame, slot_id):
        """Recorta a imagem de um slot específico."""
        cfg = SLOTS_CONFIG[slot_id]
        x = cfg["left"] - self.monitor["left"]
        y = cfg["top"] - self.monitor["top"]
        w = CARD_WIDTH
        h = CARD_HEIGHT
        
        # Garante que não saia da tela
        if x < 0 or y < 0 or x+w > frame.shape[1] or y+h > frame.shape[0]:
            return None
            
        return frame[y:y+h, x:x+w]

    def get_slot_saturation(self, slot_img):
        """
        Calcula a saturação média da imagem do slot.
        Cartas reais são coloridas (alta saturação).
        Cartas '?' ou fundo vazio costumam ser menos saturadas.
        """
        hsv = cv2.cvtColor(slot_img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1] # Canal S
        return np.mean(saturation)

    def hex_to_bgr(self, hex_color):
        """Converte cor Hex (#RRGGBB) para BGR (formato OpenCV)."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (b, g, r)

    def is_background_red(self, slot_img):
        """
        Verifica se o slot corresponde às cores do fundo vermelho (quando a carta é jogada).
        Usa uma tolerância baseada nas cores fornecidas.
        """
        # Cores de referência fornecidas
        red_colors_hex = ["#92463a", "#843c32", "#9c4c3c", "#8c3c34", "#7c342c"]
        red_colors_bgr = [self.hex_to_bgr(c) for c in red_colors_hex]
        
        # Calcula a média de cor do slot (região central)
        h, w, _ = slot_img.shape
        roi_size = 40
        center_roi = slot_img[max(0, h//2 - roi_size):min(h, h//2 + roi_size), 
                              max(0, w//2 - roi_size):min(w, w//2 + roi_size)]
        
        if center_roi.size == 0: return False
        
        avg_color = np.mean(center_roi, axis=(0, 1)) # BGR
        
        # Verifica se a cor média está próxima de ALGUMA das cores de referência
        # Tolerância euclidiana
        TOLERANCE = 25.0 
        
        for ref_color in red_colors_bgr:
            dist = np.linalg.norm(avg_color - np.array(ref_color))
            if dist < TOLERANCE:
                return True
                
        return False

    def run(self):
        print("--- CLASH ROYALE WATCHER INICIADO ---")
        print(f"Monitorando {len(SLOTS_CONFIG)} slots.")
        print("IMPORTANTE: Certifique-se de ajustar as coordenadas em SLOTS_CONFIG!")
        print("Pressione 'q' para sair.")

        # Limiar de saturação para considerar CHEIO
        SATURATION_THRESHOLD = 60 
        
        consecutive_failures = 0
        MAX_FAILURES = 5

        while True:
            try:
                frame = self.capture_screen()
                if frame is None:
                    consecutive_failures += 1
                    print(f"ERRO: Falha ao capturar tela ({consecutive_failures}/{MAX_FAILURES}).")
                    if consecutive_failures >= MAX_FAILURES:
                        print("Muitas falhas consecutivas. Encerrando para evitar travamento.")
                        print("DICA: Instale 'gnome-screenshot' ou use ambiente X11/Windows.")
                        break
                    time.sleep(1)
                    continue
                
                consecutive_failures = 0
                debug_frame = frame.copy()

                for i in range(len(SLOTS_CONFIG)):
                    slot_img = self.get_slot_roi(frame, i)
                    if slot_img is None:
                        continue

                    # --- NOVA LÓGICA DE ESTADOS MISTOS ---
                    
                    # 1. Checa se é o fundo vermelho específico (Transição/Vazio Flash)
                    is_red_bg = self.is_background_red(slot_img)
                    
                    # 2. Checa Saturação (Carta Colorida vs Carta Cinza/?)
                    sat = self.get_slot_saturation(slot_img)
                    is_saturated = sat > SATURATION_THRESHOLD
                    
                    # Determina o estado
                    if is_red_bg:
                        current_state = "EMPTY" # Vermelho detectado = Vazio/Jogada
                    elif is_saturated:
                        current_state = "FULL"  # Colorido e não vermelho = Carta Disponível
                    else:
                        current_state = "EMPTY" # Baixa saturação (Carta ?) = Indisponível/Vazio
                    
                    previous_state = self.slots_status[i]

                    # Atualiza status visual no debug
                    cfg = SLOTS_CONFIG[i]
                    x, y = cfg["left"] - self.monitor["left"], cfg["top"] - self.monitor["top"]
                    
                    # Desenha retângulo
                    color = (0, 255, 0) if current_state == "FULL" else (0, 0, 255)
                    cv2.rectangle(debug_frame, (x, y), (x+CARD_WIDTH, y+CARD_HEIGHT), color, 2)
                    
                    # Texto indicador debug
                    label = f"S{i}: {self.slots_identity[i] or '?'}"
                    label_debug = f"Sat:{int(sat)} Red:{'SIM' if is_red_bg else 'NAO'}"
                    
                    if self.game_state and self.game_state.slots_info[i].elixir:
                        label += f" ({self.game_state.slots_info[i].elixir}E)"
                    
                    cv2.putText(debug_frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(debug_frame, label_debug, (x, y+CARD_HEIGHT+15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

                    # 2. Lógica de Transição
                    
                    # CASO: Nova carta chegou (Vazio -> Cheio)
                    if previous_state == "EMPTY" and current_state == "FULL":
                        print(f"[Slot {i}] Nova carta detectada!")
                        
                        # Pequeno delay para garantir que a animação terminou e a carta está parada
                        # Se necessário, aumente este valor
                        time.sleep(1.5) 
                        
                        # Recaptura atualizada após delay (apenas do slot, se possível, mas mss precisa de grab)
                        # Para simplificar e garantir sincronia, pegamos um novo frame cheio
                        frame_updated = self.capture_screen()
                        if frame_updated is not None:
                            slot_img_updated = self.get_slot_roi(frame_updated, i)

                            if self.slots_identity[i] is None:
                                # Carta desconhecida: Salvar alvo e identificar
                                cv2.imwrite("alvo.png", slot_img_updated)
                                print(f"[Slot {i}] Alvo salvo em 'alvo.png' para identificação...")
                                
                                # Identifica a carta usando matchTemplate
                                resultado = self.card_identifier.identify_card(slot_img_updated)
                                
                                if resultado:
                                    nome_carta, score = resultado
                                    self.slots_identity[i] = nome_carta
                                    print(f"[Slot {i}] ✓ Carta identificada: {nome_carta} (Score: {score:.3f})")
                                    
                                    # Registra no GameState para obter elixir
                                    if self.game_state:
                                        self.game_state.registrar_carta_identificada(i, nome_carta)
                                else:
                                    # Tenta pegar o melhor palpite mesmo abaixo do threshold para debug
                                    best_guess, best_score = self.card_identifier.get_best_guess(slot_img_updated)
                                    print(f"[Slot {i}] ✗ Não identificado. Melhor palpite: {best_guess} (Score: {best_score:.3f}) vs Threshold {MATCH_THRESHOLD}")
                            else:
                                # Carta já conhecida
                                print(f"[Slot {i}] Identificada por memória: {self.slots_identity[i]}")

                    # CASO: Carta jogada (Cheio -> Vazio)
                    elif previous_state == "FULL" and current_state == "EMPTY":
                        if self.slots_identity[i]:
                             print(f"[Slot {i}] Carta JOGADA: {self.slots_identity[i]}")
                             # Atualiza elixir no GameState
                             if self.game_state:
                                 self.game_state.registrar_carta_jogada(i)
                        else:
                             print(f"[Slot {i}] Carta jogada (Ainda não identificada)")

                    # Atualiza estado
                    self.slots_status[i] = current_state

                # Visualização Debug (Redimensionada)
                try:
                    scale = 0.5
                    dim = (int(debug_frame.shape[1] * scale), int(debug_frame.shape[0] * scale))
                    resized = cv2.resize(debug_frame, dim, interpolation=cv2.INTER_AREA)
                    
                    # Adiciona informação de elixir na tela
                    if self.game_state:
                        elixir = self.game_state.get_elixir_atual()
                        elixir_text = f"Elixir: {elixir:.1f}"
                        cv2.putText(resized, elixir_text, (10, resized.shape[0] - 20), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    
                    cv2.imshow("Clash Watcher Debug", resized)
                except Exception as e:
                    print(f"Erro ao mostrar debug: {e}")

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            except KeyboardInterrupt:
                print("\nInterrompido pelo usuário.")
                break

        cv2.destroyAllWindows()

if __name__ == "__main__":
    GameWatcher().run()
