"""Ferramenta interativa para calibrar os 8 slots de cartas na tela."""

from pathlib import Path

import cv2
import mss
import numpy as np

CARD_WIDTH = 61
CARD_HEIGHT = 90
VIEW_SCALE = 0.5
MAX_SLOTS = 8


class SlotCalibrator:
    """Permite mapear manualmente os slots e exportar `SLOTS_CONFIG`."""

    def __init__(self):
        self.sct = mss.mss()
        if len(self.sct.monitors) > 1:
            self.monitor = self.sct.monitors[1]
        else:
            self.monitor = self.sct.monitors[0]

        self.slots = []
        self.pending_slot = None
        self.mouse_pos = (0, 0)
        self.window_name = "Calibracao de Slots - Clique nos cantos superiores esquerdos"

    def capture_screen(self) -> np.ndarray:
        """Captura a tela atual e retorna frame em BGR."""
        screenshot = self.sct.grab(self.monitor)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def mouse_callback(self, event, x, y, flags, param) -> None:
        """Processa eventos de mouse para marcar novos slots."""
        if event == cv2.EVENT_MOUSEMOVE:
            self.mouse_pos = (x, y)
            return

        if event != cv2.EVENT_LBUTTONDOWN:
            return

        if self.pending_slot is not None:
            print("AVISO: Confirme ou cancele o slot atual antes de marcar outro!")
            return

        if len(self.slots) >= MAX_SLOTS:
            print("\nAVISO: Limite de 8 slots atingido! Pressione 's' para salvar ou 'q' para sair.")
            return

        real_x = int(x / VIEW_SCALE)
        real_y = int(y / VIEW_SCALE)
        screen_x = self.monitor["left"] + real_x
        screen_y = self.monitor["top"] + real_y

        self.pending_slot = {"id": len(self.slots), "left": screen_x, "top": screen_y}
        print(f"\nSlot {len(self.slots)} marcado provisoriamente em ({screen_x}, {screen_y})")
        print("Pressione ENTER para confirmar ou BACKSPACE para cancelar.")

    def run(self) -> None:
        """Executa o fluxo interativo de calibracao dos oito slots."""
        print("=" * 60)
        print("CALIBRACAO DE SLOTS - CLASH ROYALE")
        print("=" * 60)
        print("\nINSTRUCOES:")
        print("1. Mova o mouse para ver as coordenadas em tempo real")
        print("2. Clique no canto superior esquerdo de cada slot")
        print("3. Confirme com ENTER ou cancele com BACKSPACE")
        print("4. Marque os 8 slots na ordem (0 ate 7)")
        print("5. Pressione 's' para salvar")
        print("6. Pressione 'q' para sair")
        print("\n" + "=" * 60)

        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        while True:
            frame = self.capture_screen()
            debug_frame = frame.copy()

            for slot in self.slots:
                x = slot["left"] - self.monitor["left"]
                y = slot["top"] - self.monitor["top"]
                cv2.rectangle(debug_frame, (x, y), (x + CARD_WIDTH, y + CARD_HEIGHT), (0, 255, 0), 3)
                cv2.putText(
                    debug_frame,
                    f"Slot {slot['id']}",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )

            if self.pending_slot:
                slot = self.pending_slot
                x = slot["left"] - self.monitor["left"]
                y = slot["top"] - self.monitor["top"]
                cv2.rectangle(
                    debug_frame,
                    (x, y),
                    (x + CARD_WIDTH, y + CARD_HEIGHT),
                    (0, 255, 255),
                    3,
                )
                cv2.putText(
                    debug_frame,
                    "Confirmar?",
                    (x, y - 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                )
                cv2.putText(
                    debug_frame,
                    "ENTER/BACK",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )

            dim = (
                int(debug_frame.shape[1] * VIEW_SCALE),
                int(debug_frame.shape[0] * VIEW_SCALE),
            )
            resized = cv2.resize(debug_frame, dim, interpolation=cv2.INTER_AREA)

            mouse_x_scaled = int(self.mouse_pos[0] / VIEW_SCALE)
            mouse_y_scaled = int(self.mouse_pos[1] / VIEW_SCALE)
            real_x = self.monitor["left"] + mouse_x_scaled
            real_y = self.monitor["top"] + mouse_y_scaled

            cv2.line(
                resized,
                (self.mouse_pos[0] - 20, self.mouse_pos[1]),
                (self.mouse_pos[0] + 20, self.mouse_pos[1]),
                (0, 255, 255),
                2,
            )
            cv2.line(
                resized,
                (self.mouse_pos[0], self.mouse_pos[1] - 20),
                (self.mouse_pos[0], self.mouse_pos[1] + 20),
                (0, 255, 255),
                2,
            )

            coord_text = f"X: {real_x}, Y: {real_y} | Slots marcados: {len(self.slots)}/{MAX_SLOTS}"
            cv2.putText(resized, coord_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            if self.pending_slot:
                cv2.putText(
                    resized,
                    "CONFIRME O SLOT (ENTER / BACKSPACE)",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            cv2.imshow(self.window_name, resized)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print("\nCalibracao cancelada.")
                break
            if key == 13:
                if self.pending_slot:
                    self.slots.append(self.pending_slot)
                    print(f"Slot {self.pending_slot['id']} CONFIRMADO.")
                    self.pending_slot = None
                continue
            if key == 8:
                if self.pending_slot:
                    print("Slot cancelado. Tente novamente.")
                    self.pending_slot = None
                continue
            if key == ord("s"):
                if len(self.slots) == MAX_SLOTS and self.pending_slot is None:
                    self.save_config()
                    break
                if self.pending_slot is not None:
                    print("\nAVISO: Confirme o ultimo slot antes de salvar!")
                else:
                    print(f"\nAVISO: Voce marcou apenas {len(self.slots)} slots. Preciso de 8!")

        cv2.destroyAllWindows()

    def save_config(self) -> None:
        """Imprime e salva a configuracao no formato usado em `detection.py`."""
        print("\n" + "=" * 60)
        print("COORDENADAS SALVAS:")
        print("=" * 60)
        print("\nCopie e cole no arquivo detection.py, substituindo SLOTS_CONFIG:\n")
        print("SLOTS_CONFIG = [")
        for slot in self.slots:
            print(f'    {{"id": {slot["id"]}, "left": {slot["left"]}, "top": {slot["top"]}}},')
        print("]")
        print("\n" + "=" * 60)

        output_file = Path(__file__).parent / "slots_config.txt"
        with open(output_file, "w", encoding="utf-8") as file:
            file.write("SLOTS_CONFIG = [\n")
            for slot in self.slots:
                file.write(f'    {{"id": {slot["id"]}, "left": {slot["left"]}, "top": {slot["top"]}}},\n')
            file.write("]\n")

        print(f"\nConfiguracao tambem salva em: {output_file}")
        print("Voce pode copiar o conteudo desse arquivo para detection.py")


if __name__ == "__main__":
    calibrator = SlotCalibrator()
    calibrator.run()
