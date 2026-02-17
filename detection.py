import cv2
import numpy as np
import time
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Deque
from dataclasses import dataclass
from collections import deque
from screen_capture import ScreenCapture
from dashboard import Dashboard

# ==============================================================================
# CONFIGURAÇÃO DOS SLOTS (ROI)
# ==============================================================================
CARD_WIDTH = 61
CARD_HEIGHT = 90

# Defina o canto superior esquerdo (Left, Top) para cada um dos 8 slots
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
# CONFIGURAÇÃO DE IDENTIFICAÇÃO
# ==============================================================================
TEMPLATES_DIR = Path(__file__).parent / "cards" / "cards-templates"
USER_TEMPLATES_DIR = Path(__file__).parent / "cards" / "cards-templates-user"
MATCH_THRESHOLD = 0.15  # Score mínimo para considerar uma correspondência válida

class CardIdentifier:
    """Identifica cartas comparando imagens com templates usando matchTemplate."""
    
    def __init__(self, templates_dirs: list[Path]):
        self.templates_dirs = templates_dirs
        self.templates_cache = {}  # Cache de templates carregados
        self._load_templates()
    
    def _load_templates(self):
        """Carrega todos os templates PNG dos diretórios."""
        total_loaded = 0
        for templates_dir in self.templates_dirs:
            if not templates_dir.exists():
                print(f"AVISO: Diretório de templates não encontrado: {templates_dir}")
                continue
            
            png_files = list(templates_dir.glob("*.png"))
            print(f"Carregando {len(png_files)} templates de {templates_dir.name}...")
            
            for template_path in png_files:
                try:
                    template_img = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
                    if template_img is not None:
                        nome_arquivo = template_path.stem
                        
                        # Remove sufixos padrões
                        nome_limpo = nome_arquivo.replace("_medium", "").replace("_evolutionMedium", "")
                        
                        # Remove timestamp/sufixo numérico se houver
                        if "_" in nome_limpo:
                            parts = nome_limpo.rsplit("_", 1)
                            if len(parts) > 1 and parts[1].isdigit():
                                nome_limpo = parts[0]
                                
                        # Converte para formato de nome (primeira letra maiúscula)
                        # Se contiver 'evolution' ou 'evo', mantém essa info no nome para o dashboard saber
                        # Ex: "barbarians_evolution" -> "Barbarians Evo"
                        is_evo = "evolution" in nome_limpo.lower() or "evo" in nome_limpo.lower()
                        
                        base_name = nome_limpo.replace("evolution", "").replace("evo", "").strip("_- ")
                        nome_carta = base_name.replace("-", " ").title()
                        
                        if is_evo:
                            nome_carta += " Evo"
                        
                        if nome_carta not in self.templates_cache:
                            self.templates_cache[nome_carta] = []
                        self.templates_cache[nome_carta].append(template_img)
                        total_loaded += 1
                except Exception as e:
                    print(f"Erro ao carregar template {template_path.name}: {e}")
        
        print(f"Total de templates carregados: {total_loaded} ({len(self.templates_cache)} cartas únicas)")
    
    def get_best_guess(self, target_img) -> Tuple[Optional[str], float]:
        """Retorna a melhor correspondência encontrada, independente do threshold."""
        if not self.templates_cache:
            return (None, 0.0)
        
        target_gray = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
        target_gray = cv2.GaussianBlur(target_gray, (3, 3), 0)
        
        best_match = None
        best_score = 0.0
        
        for nome_carta, templates in self.templates_cache.items():
            for template in templates:
                try:
                    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    template_gray = cv2.GaussianBlur(template_gray, (3, 3), 0)
                    
                    if template_gray.shape[:2] != target_gray.shape[:2]:
                        template_resized = cv2.resize(template_gray, (target_gray.shape[1], target_gray.shape[0]))
                    else:
                        template_resized = template_gray
                    
                    result = cv2.matchTemplate(target_gray, template_resized, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    
                    if max_val > best_score:
                        best_score = max_val
                        best_match = nome_carta
                except Exception as e:
                    continue
        
        return (best_match, best_score)


@dataclass
class SlotInfo:
    """Informações sobre um slot específico."""
    nome_carta: Optional[str] = None


class GameState:
    """Gerencia o estado do jogo (quais cartas estão identificadas)."""
    
    def __init__(self):
        self.slots_info: Dict[int, SlotInfo] = {i: SlotInfo() for i in range(8)}
        
    def registrar_carta_identificada(self, slot_id: int, nome_carta: str):
        """Registra que uma carta foi identificada em um slot."""
        self.slots_info[slot_id].nome_carta = nome_carta
        print(f"[GameState] Slot {slot_id}: {nome_carta}")

    def limpar_slot(self, slot_id: int):
        self.slots_info[slot_id].nome_carta = None


class OpponentHandTracker:
    """Rastreia mão atual (0-3) e fila/ciclo (4-7) do oponente."""

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.current_hand = [None, None, None, None]
        self.queue: Deque[str] = deque()
        self._sync_game_state()

    def _sync_game_state(self):
        # Slots 0-3: mão atual
        for idx in range(4):
            nome = self.current_hand[idx]
            if nome:
                self.game_state.registrar_carta_identificada(idx, nome)
            else:
                self.game_state.limpar_slot(idx)

        # Slots 4-7: fila/ciclo (padded com None quando <4)
        queue_snapshot = list(self.queue)
        for idx in range(4):
            slot_id = 4 + idx
            if idx < len(queue_snapshot):
                self.game_state.registrar_carta_identificada(slot_id, queue_snapshot[idx])
            else:
                self.game_state.limpar_slot(slot_id)

    def register_detected_play(self, slot_id: int, detected_card: str):
        """
        Regras:
        - Bootstrap: primeiras 4 detecções entram na fila em ordem.
        - A partir da 5ª: popleft da fila -> entra na mão no slot detectado;
          carta detectada vai para o final da fila.
        """
        if slot_id < 0 or slot_id > 3:
            return

        if len(self.queue) < 4:
            self.queue.append(detected_card)
            print(f"[Tracker] Bootstrap fila ({len(self.queue)}/4): {detected_card}")
            self._sync_game_state()
            return

        next_card = self.queue.popleft()
        self.current_hand[slot_id] = next_card
        self.queue.append(detected_card)
        print(
            f"[Tracker] Slot {slot_id} <= {next_card} | "
            f"jogada detectada: {detected_card} -> fim da fila"
        )
        self._sync_game_state()


class GameWatcher:
    def __init__(self):
        self.capturer = ScreenCapture()
        self.monitor = self.capturer.get_monitor_info()

        # Estado dos slots: "UNKNOWN", "EMPTY", "FULL"
        self.slots_status = {i: "UNKNOWN" for i in range(len(SLOTS_CONFIG))}
        
        # Memória: Qual carta está em cada slot? (Nome da carta ou None)
        self.slots_identity = {i: None for i in range(len(SLOTS_CONFIG))}
        
        self.card_identifier = CardIdentifier([TEMPLATES_DIR, USER_TEMPLATES_DIR])
        
        # Dashboard Visual
        self.dashboard = Dashboard()
        
        # GameState simplificado (sem API)
        self.game_state = GameState()
        self.opponent_tracker = OpponentHandTracker(self.game_state)

    def capture_screen(self):
        return self.capturer.grab()

    def get_slot_roi(self, frame, slot_id):
        cfg = SLOTS_CONFIG[slot_id]
        x = cfg["left"] - self.monitor["left"]
        y = cfg["top"] - self.monitor["top"]
        w = CARD_WIDTH
        h = CARD_HEIGHT
        
        if x < 0 or y < 0 or x+w > frame.shape[1] or y+h > frame.shape[0]:
            return None
            
        return frame[y:y+h, x:x+w]

    def get_slot_saturation(self, slot_img):
        hsv = cv2.cvtColor(slot_img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1] # Canal S
        return np.mean(saturation)

    def hex_to_bgr(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (b, g, r)

    def is_background_red(self, slot_img):
        red_colors_hex = ["#92463a", "#843c32", "#9c4c3c", "#8c3c34", "#7c342c"]
        red_colors_bgr = [self.hex_to_bgr(c) for c in red_colors_hex]
        
        h, w, _ = slot_img.shape
        roi_size = 40
        center_roi = slot_img[max(0, h//2 - roi_size):min(h, h//2 + roi_size), 
                            max(0, w//2 - roi_size):min(w, w//2 + roi_size)]
        
        if center_roi.size == 0: return False
        
        avg_color = np.mean(center_roi, axis=(0, 1)) # BGR
        
        TOLERANCE = 25.0 
        for ref_color in red_colors_bgr:
            dist = np.linalg.norm(avg_color - np.array(ref_color))
            if dist < TOLERANCE:
                return True
        return False

    def run(self):
        print("--- CLASH ROYALE WATCHER INICIADO ---")
        print(f"Monitorando {len(SLOTS_CONFIG)} slots.")
        print("Pressione 'q' para sair.")

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
                        break
                    time.sleep(1)
                    continue
                
                consecutive_failures = 0
                debug_frame = frame.copy()

                for i in range(len(SLOTS_CONFIG)):
                    slot_img = self.get_slot_roi(frame, i)
                    if slot_img is None:
                        continue

                    is_red_bg = self.is_background_red(slot_img)
                    sat = self.get_slot_saturation(slot_img)
                    is_saturated = sat > SATURATION_THRESHOLD
                    
                    if is_red_bg:
                        current_state = "EMPTY"
                    elif is_saturated:
                        current_state = "FULL"
                    else:
                        current_state = "EMPTY"
                    
                    previous_state = self.slots_status[i]

                    # Visualização Debug simples
                    cfg = SLOTS_CONFIG[i]
                    x, y = cfg["left"] - self.monitor["left"], cfg["top"] - self.monitor["top"]
                    color = (0, 255, 0) if current_state == "FULL" else (0, 0, 255)
                    cv2.rectangle(debug_frame, (x, y), (x+CARD_WIDTH, y+CARD_HEIGHT), color, 2)
                    
                    label = f"S{i}: {self.game_state.slots_info[i].nome_carta or '?'}"
                    cv2.putText(debug_frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                    # Lógica de Transição: somente slots da mão (0-3) alteram estado interno
                    if i <= 3 and previous_state == "EMPTY" and current_state == "FULL":
                        print(f"[Slot {i}] Nova carta detectada!")
                        time.sleep(1.5) 
                        
                        frame_updated = self.capture_screen()
                        if frame_updated is not None:
                            slot_img_updated = self.get_slot_roi(frame_updated, i)
                            best_guess, best_score = self.card_identifier.get_best_guess(slot_img_updated)
                            
                            CONFIRMATION_THRESHOLD = 0.75

                            if best_score >= CONFIRMATION_THRESHOLD and best_guess:
                                print(f"[Slot {i}] Auto-identificado: {best_guess} ({best_score:.2f})")
                                self.opponent_tracker.register_detected_play(i, best_guess)
                            else:
                                # Modo Treinamento Interativo
                                cv2.imshow(f"CONFIRMACAO - Slot {i}", slot_img_updated)
                                cv2.waitKey(100)
                                
                                print(f"\n--- REVISÃO NECESSÁRIA (Slot {i}) ---")
                                print(f"Identificado: '{best_guess}' ({best_score:.2f})")
                                print("ENTER=Confirmar | Digite nome correto se errado.")
                                
                                try:
                                    user_input = input("Correto? ").strip()
                                except EOFError:
                                    user_input = ""

                                cv2.destroyWindow(f"CONFIRMACAO - Slot {i}")
                                
                                final_name = best_guess
                                if user_input:
                                    final_name = user_input.strip().title()
                                
                                if final_name:
                                    print(f"Confirmado: {final_name}")
                                    
                                    # Salva template
                                    user_templates_dir = Path(__file__).parent / "cards" / "cards-templates-user"
                                    user_templates_dir.mkdir(exist_ok=True, parents=True)
                                    # Formatação do nome do arquivo: minusculo, espaços por hifens
                                    # Ex: "Mini P.E.K.K.A" -> "mini-p.e.k.k.a"
                                    safe_name = final_name.strip().lower().replace(" ", "-").replace("_", "-")
                                    timestamp = int(time.time() * 1000)
                                    filename = f"{safe_name}_{timestamp}.png"
                                    save_path = user_templates_dir / filename
                                    try:
                                        cv2.imwrite(str(save_path), slot_img_updated)
                                    except Exception as e:
                                        print(f"Erro ao salvar: {e}")

                                    self.opponent_tracker.register_detected_play(i, final_name)
                                else:
                                    print("Ignorado.")

                    self.slots_status[i] = current_state

                # Atualiza Dashboard
                self.dashboard.update(self.game_state.slots_info)
                
                # Visualização Debug (opcional, redimensionada)
                try:
                    scale = 0.5
                    dim = (int(debug_frame.shape[1] * scale), int(debug_frame.shape[0] * scale))
                    resized = cv2.resize(debug_frame, dim, interpolation=cv2.INTER_AREA)
                    cv2.imshow("Debug View", resized)
                except Exception:
                    pass

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            except KeyboardInterrupt:
                break

        cv2.destroyAllWindows()

if __name__ == "__main__":
    GameWatcher().run()
