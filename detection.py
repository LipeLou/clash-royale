"""Deteccao em tempo real das cartas do oponente por slots fixos."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple
import time

import cv2
import numpy as np

from screen_capture import ScreenCapture

CARD_WIDTH = 61
CARD_HEIGHT = 90

SLOTS_CONFIG = [
    {"id": 0, "left": 731, "top": 58},
    {"id": 1, "left": 796, "top": 58},
    {"id": 2, "left": 861, "top": 58},
    {"id": 3, "left": 926, "top": 58},
    {"id": 4, "left": 991, "top": 58},
    {"id": 5, "left": 1056, "top": 58},
    {"id": 6, "left": 1121, "top": 58},
    {"id": 7, "left": 1186, "top": 58},
]

TEMPLATES_DIR = Path(__file__).parent / "cards" / "cards-templates"
USER_TEMPLATES_DIR = Path(__file__).parent / "cards" / "cards-templates-user"
CONFIRMATION_THRESHOLD = 0.75
SATURATION_THRESHOLD = 60
MAX_CAPTURE_FAILURES = 5
CAPTURE_RETRY_SECONDS = 1.0
POST_PLAY_CAPTURE_DELAY_SECONDS = 1.5
DEBUG_VIEW_SCALE = 0.5
SLOT_ROI_CENTER_SIZE = 40
RED_COLOR_TOLERANCE = 25.0
RED_BACKGROUND_COLORS_HEX = ("#92463a", "#843c32", "#9c4c3c", "#8c3c34", "#7c342c")


class CardIdentifier:
    """Resolve a carta mais provavel por comparacao de templates."""

    def __init__(self, templates_dirs: list[Path]):
        self.templates_dirs = templates_dirs
        self.templates_cache: Dict[str, list[np.ndarray]] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Carrega templates em memoria e agrega por nome de carta."""
        total_loaded = 0
        for templates_dir in self.templates_dirs:
            if not templates_dir.exists():
                print(f"[WARN][TEMPLATES] Diretorio nao encontrado: {templates_dir}")
                continue

            png_files = list(templates_dir.glob("*.png"))
            print(f"[INIT][TEMPLATES] {templates_dir.name}: carregando {len(png_files)} arquivo(s)")

            for template_path in png_files:
                try:
                    template_img = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
                    if template_img is None:
                        continue

                    clean_name = template_path.stem.replace("_medium", "").replace("_evolutionMedium", "")
                    if "_" in clean_name:
                        parts = clean_name.rsplit("_", 1)
                        if len(parts) > 1 and parts[1].isdigit():
                            clean_name = parts[0]

                    is_evo = "evolution" in clean_name.lower() or "evo" in clean_name.lower()
                    base_name = clean_name.replace("evolution", "").replace("evo", "").strip("_- ")
                    card_name = base_name.replace("-", " ").title()
                    if is_evo:
                        card_name += " Evo"

                    self.templates_cache.setdefault(card_name, []).append(template_img)
                    total_loaded += 1
                except Exception as exc:
                    print(f"[WARN][TEMPLATES] Falha em {template_path.name}: {exc}")

        print(f"[INIT][TEMPLATES] Total={total_loaded} | Cartas unicas={len(self.templates_cache)}")

    def get_best_guess(self, target_img: np.ndarray) -> Tuple[Optional[str], float]:
        """Retorna o nome e score da melhor correspondencia encontrada."""
        if not self.templates_cache:
            return (None, 0.0)

        target_gray = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY)
        target_gray = cv2.GaussianBlur(target_gray, (3, 3), 0)

        best_match: Optional[str] = None
        best_score = 0.0

        for card_name, templates in self.templates_cache.items():
            for template in templates:
                try:
                    template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                    template_gray = cv2.GaussianBlur(template_gray, (3, 3), 0)
                    if template_gray.shape[:2] != target_gray.shape[:2]:
                        template_gray = cv2.resize(
                            template_gray,
                            (target_gray.shape[1], target_gray.shape[0]),
                        )

                    result = cv2.matchTemplate(target_gray, template_gray, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    if max_val > best_score:
                        best_score = max_val
                        best_match = card_name
                except Exception:
                    continue

        return (best_match, best_score)


@dataclass
class SlotInfo:
    """Representa a carta conhecida para um slot."""

    nome_carta: Optional[str] = None


class GameState:
    """Armazena o estado identificado dos oito slots."""

    def __init__(self):
        self.slots_info: Dict[int, SlotInfo] = {i: SlotInfo() for i in range(8)}

    def registrar_carta_identificada(self, slot_id: int, nome_carta: str) -> None:
        """Registra ou atualiza a carta de um slot."""
        self.slots_info[slot_id].nome_carta = nome_carta
        print(f"[STATE] S{slot_id}={nome_carta}")


class GameWatcher:
    """Monitora os slots em tempo real e identifica cartas por memoria fixa."""

    def __init__(self):
        self.capturer = ScreenCapture()
        self.monitor = self.capturer.get_monitor_info()
        self.slots_status = {i: "UNKNOWN" for i in range(len(SLOTS_CONFIG))}
        self.slots_identity: Dict[int, Optional[str]] = {i: None for i in range(len(SLOTS_CONFIG))}
        self.card_identifier = CardIdentifier([TEMPLATES_DIR, USER_TEMPLATES_DIR])
        self.game_state = GameState()

    def capture_screen(self) -> Optional[np.ndarray]:
        """Captura o frame atual da tela."""
        return self.capturer.grab()

    def get_slot_roi(self, frame: np.ndarray, slot_id: int) -> Optional[np.ndarray]:
        """Recorta a regiao do slot no frame atual."""
        cfg = SLOTS_CONFIG[slot_id]
        x = cfg["left"] - self.monitor["left"]
        y = cfg["top"] - self.monitor["top"]
        if x < 0 or y < 0 or x + CARD_WIDTH > frame.shape[1] or y + CARD_HEIGHT > frame.shape[0]:
            return None
        return frame[y : y + CARD_HEIGHT, x : x + CARD_WIDTH]

    @staticmethod
    def get_slot_saturation(slot_img: np.ndarray) -> float:
        """Calcula saturacao media do slot em HSV."""
        hsv = cv2.cvtColor(slot_img, cv2.COLOR_BGR2HSV)
        return float(np.mean(hsv[:, :, 1]))

    @staticmethod
    def hex_to_bgr(hex_color: str) -> Tuple[int, int, int]:
        """Converte cor hexadecimal para tupla BGR."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (b, g, r)

    def is_background_red(self, slot_img: np.ndarray) -> bool:
        """Verifica se o fundo do slot corresponde ao padrao vermelho de vazio."""
        red_colors_bgr = [self.hex_to_bgr(color) for color in RED_BACKGROUND_COLORS_HEX]
        h, w, _ = slot_img.shape
        center_roi = slot_img[
            max(0, h // 2 - SLOT_ROI_CENTER_SIZE) : min(h, h // 2 + SLOT_ROI_CENTER_SIZE),
            max(0, w // 2 - SLOT_ROI_CENTER_SIZE) : min(w, w // 2 + SLOT_ROI_CENTER_SIZE),
        ]
        if center_roi.size == 0:
            return False

        avg_color = np.mean(center_roi, axis=(0, 1))
        for reference_color in red_colors_bgr:
            distance = np.linalg.norm(avg_color - np.array(reference_color))
            if distance < RED_COLOR_TOLERANCE:
                return True
        return False

    def _register_slot_identity(self, slot_id: int, card_name: str) -> None:
        """Grava a primeira identidade da carta do slot e evita remapeamento."""
        known_card = self.slots_identity[slot_id]
        if known_card is None:
            self.slots_identity[slot_id] = card_name
            self.game_state.registrar_carta_identificada(slot_id, card_name)
            return

        if known_card != card_name:
            print(
                f"[WARN][SLOT] S{slot_id} ja mapeado para '{known_card}'. "
                f"Ignorando tentativa '{card_name}'."
            )

    def _save_user_template(self, card_name: str, slot_img: np.ndarray) -> None:
        """Salva um template corrigido manualmente pelo operador."""
        user_templates_dir = Path(__file__).parent / "cards" / "cards-templates-user"
        user_templates_dir.mkdir(exist_ok=True, parents=True)

        safe_name = card_name.strip().lower().replace(" ", "-").replace("_", "-")
        timestamp = int(time.time() * 1000)
        filename = f"{safe_name}_{timestamp}.png"
        save_path = user_templates_dir / filename

        try:
            cv2.imwrite(str(save_path), slot_img)
        except Exception as exc:
            print(f"[ERROR][TEMPLATE_SAVE] Falha ao salvar '{save_path.name}': {exc}")

    def _identify_unknown_slot(self, slot_id: int) -> Tuple[Optional[str], str]:
        """Identifica uma carta ainda desconhecida para o slot informado."""
        time.sleep(POST_PLAY_CAPTURE_DELAY_SECONDS)
        frame_updated = self.capture_screen()
        if frame_updated is None:
            return (None, "FALHA_CAPTURA")

        slot_img_updated = self.get_slot_roi(frame_updated, slot_id)
        if slot_img_updated is None:
            return (None, "FALHA_ROI")

        best_guess, best_score = self.card_identifier.get_best_guess(slot_img_updated)
        if best_score >= CONFIRMATION_THRESHOLD and best_guess:
            print(f"[LEARN][TEMPLATE] S{slot_id}={best_guess} (score={best_score:.2f})")
            return (best_guess, "TEMPLATE")

        cv2.imshow(f"CONFIRMACAO - Slot {slot_id}", slot_img_updated)
        cv2.waitKey(100)

        print(f"[REVIEW] S{slot_id} sugestao='{best_guess}' score={best_score:.2f}")
        print("[REVIEW] ENTER confirma sugestao; digite nome para corrigir.")

        try:
            user_input = input("Revisao> ").strip()
        except EOFError:
            user_input = ""

        cv2.destroyWindow(f"CONFIRMACAO - Slot {slot_id}")

        final_name = best_guess
        if user_input:
            final_name = user_input.strip().title()

        if final_name:
            print(f"[LEARN][MANUAL] S{slot_id}={final_name}")
            self._save_user_template(final_name, slot_img_updated)
            return (final_name, "MANUAL")

        print(f"[LEARN][SKIP] S{slot_id}")
        return (None, "IGNORADO")

    @staticmethod
    def _log_play_event(slot_id: int, card_name: str, source: str) -> None:
        """Registra no terminal a jogada detectada para o slot."""
        print(f"[PLAY][{source}] S{slot_id}={card_name}")

    def _handle_play_transition(self, slot_id: int) -> None:
        """Processa a transicao EMPTY->FULL para um slot especifico."""
        known_card = self.slots_identity[slot_id]
        if known_card:
            self._log_play_event(slot_id, known_card, "MEMORIA")
            return

        identified_card, source = self._identify_unknown_slot(slot_id)
        if identified_card:
            self._register_slot_identity(slot_id, identified_card)
            self._log_play_event(slot_id, identified_card, source)

    def run(self) -> None:
        """Executa o loop principal de monitoramento dos slots."""
        print("[SYS] Watcher iniciado")
        print(f"[SYS] Slots monitorados: {len(SLOTS_CONFIG)}")
        print("[SYS] Pressione 'q' para sair")

        consecutive_failures = 0

        while True:
            try:
                frame = self.capture_screen()
                if frame is None:
                    consecutive_failures += 1
                    print(
                        f"[ERROR][CAPTURE] Falha ao capturar tela "
                        f"({consecutive_failures}/{MAX_CAPTURE_FAILURES})"
                    )
                    if consecutive_failures >= MAX_CAPTURE_FAILURES:
                        print("[ERROR][CAPTURE] Limite de falhas atingido. Encerrando watcher.")
                        break
                    time.sleep(CAPTURE_RETRY_SECONDS)
                    continue

                consecutive_failures = 0
                debug_frame = frame.copy()

                for slot_id in range(len(SLOTS_CONFIG)):
                    slot_img = self.get_slot_roi(frame, slot_id)
                    if slot_img is None:
                        continue

                    is_red_bg = self.is_background_red(slot_img)
                    is_saturated = self.get_slot_saturation(slot_img) > SATURATION_THRESHOLD
                    current_state = "FULL" if (not is_red_bg and is_saturated) else "EMPTY"
                    previous_state = self.slots_status[slot_id]

                    cfg = SLOTS_CONFIG[slot_id]
                    x = cfg["left"] - self.monitor["left"]
                    y = cfg["top"] - self.monitor["top"]
                    color = (0, 255, 0) if current_state == "FULL" else (0, 0, 255)
                    cv2.rectangle(debug_frame, (x, y), (x + CARD_WIDTH, y + CARD_HEIGHT), color, 2)

                    label = f"S{slot_id}: {self.slots_identity[slot_id] or '?'}"
                    cv2.putText(
                        debug_frame,
                        label,
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                    )

                    if previous_state == "EMPTY" and current_state == "FULL":
                        self._handle_play_transition(slot_id)

                    self.slots_status[slot_id] = current_state

                try:
                    dim = (
                        int(debug_frame.shape[1] * DEBUG_VIEW_SCALE),
                        int(debug_frame.shape[0] * DEBUG_VIEW_SCALE),
                    )
                    resized = cv2.resize(debug_frame, dim, interpolation=cv2.INTER_AREA)
                    cv2.imshow("Debug View", resized)
                except Exception:
                    pass

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            except KeyboardInterrupt:
                break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    GameWatcher().run()
