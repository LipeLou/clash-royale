import cv2
import numpy as np
import mss
from pathlib import Path

# ==============================================================================
# CALIBRAÇÃO INTERATIVA DE SLOTS
# ==============================================================================
# Este script ajuda você a descobrir as coordenadas exatas de cada slot.
# 
# INSTRUÇÕES:
# 1. Execute este script enquanto o jogo está aberto
# 2. Mova o mouse sobre a tela e veja as coordenadas em tempo real
# 3. Clique no canto superior esquerdo de cada slot (começando pelo Slot 0)
# 4. O slot ficará AMARELO. Pressione ENTER para confirmar ou BACKSPACE para cancelar.
# 5. Após marcar os 8 slots, pressione 's' para salvar
# 6. Pressione 'q' para sair sem salvar
# ==============================================================================

CARD_WIDTH = 61
CARD_HEIGHT = 90

class SlotCalibrator:
    def __init__(self):
        self.sct = mss.mss()
        
        # Monitor 1 é geralmente o principal
        if len(self.sct.monitors) > 1:
            self.monitor = self.sct.monitors[1] 
        else:
            self.monitor = self.sct.monitors[0]
            
        self.slots = []  # Lista de coordenadas marcadas e confirmadas
        self.pending_slot = None # Slot aguardando confirmação
        self.mouse_pos = (0, 0)
        self.window_name = "Calibracao de Slots - Clique nos cantos superiores esquerdos"
        
    def capture_screen(self):
        """Captura a tela."""
        screenshot = self.sct.grab(self.monitor)
        img = np.array(screenshot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    
    def mouse_callback(self, event, x, y, flags, param):
        """Callback para eventos do mouse."""
        if event == cv2.EVENT_MOUSEMOVE:
            self.mouse_pos = (x, y)
        elif event == cv2.EVENT_LBUTTONDOWN:
            if self.pending_slot is not None:
                print("AVISO: Confirme ou cancele o slot atual antes de marcar outro!")
                return

            if len(self.slots) >= 8:
                print("\nAVISO: Limite de 8 slots atingido! Pressione 's' para salvar ou 'q' para sair.")
                return

            # Converte coordenadas da janela para coordenadas da tela
            scale = 0.5  # Mesmo scale usado na visualização
            real_x = int(x / scale)
            real_y = int(y / scale)
            
            # Ajusta para coordenadas absolutas do monitor
            screen_x = self.monitor["left"] + real_x
            screen_y = self.monitor["top"] + real_y
            
            # Cria slot temporário
            self.pending_slot = {
                "id": len(self.slots),
                "left": screen_x,
                "top": screen_y
            }
            print(f"\nSlot {len(self.slots)} marcado provisoriamente em ({screen_x}, {screen_y})")
            print("Pressione ENTER para confirmar ou BACKSPACE para cancelar.")
    
    def run(self):
        print("=" * 60)
        print("CALIBRAÇÃO DE SLOTS - CLASH ROYALE")
        print("=" * 60)
        print("\nINSTRUÇÕES:")
        print("1. Mova o mouse para ver as coordenadas em tempo real")
        print("2. Clique no CANTO SUPERIOR ESQUERDO de cada slot")
        print("3. O slot ficará AMARELO. Confirme com ENTER ou Cancele com BACKSPACE.")
        print("4. Marque os 8 slots na ordem (Slot 0, 1, 2, 3, 4, 5, 6, 7)")
        print("5. Pressione 's' para salvar as coordenadas (após confirmar todos)")
        print("6. Pressione 'q' para sair")
        print("\n" + "=" * 60)
        
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        while True:
            frame = self.capture_screen()
            debug_frame = frame.copy()
            
            # Desenha retângulos nos slots já CONFIRMADOS (Verde)
            for slot in self.slots:
                x = slot["left"] - self.monitor["left"]
                y = slot["top"] - self.monitor["top"]
                cv2.rectangle(debug_frame, (x, y), (x+CARD_WIDTH, y+CARD_HEIGHT), (0, 255, 0), 3)
                cv2.putText(debug_frame, f"Slot {slot['id']}", (x, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Desenha slot PENDENTE (Amarelo/Azul)
            if self.pending_slot:
                slot = self.pending_slot
                x = slot["left"] - self.monitor["left"]
                y = slot["top"] - self.monitor["top"]
                cv2.rectangle(debug_frame, (x, y), (x+CARD_WIDTH, y+CARD_HEIGHT), (0, 255, 255), 3)
                cv2.putText(debug_frame, f"Confirmar?", (x, y-30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                cv2.putText(debug_frame, f"ENTER/BACK", (x, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            # Mostra coordenadas do mouse
            scale = 0.5
            dim = (int(debug_frame.shape[1] * scale), int(debug_frame.shape[0] * scale))
            resized = cv2.resize(debug_frame, dim, interpolation=cv2.INTER_AREA)
            
            # Converte coordenadas do mouse para a escala da janela
            mouse_x_scaled = int(self.mouse_pos[0] / scale)
            mouse_y_scaled = int(self.mouse_pos[1] / scale)
            
            # Calcula coordenadas reais da tela
            real_x = self.monitor["left"] + mouse_x_scaled
            real_y = self.monitor["top"] + mouse_y_scaled
            
            # Desenha linha cruzada no mouse
            cv2.line(resized, (self.mouse_pos[0]-20, self.mouse_pos[1]), 
                    (self.mouse_pos[0]+20, self.mouse_pos[1]), (0, 255, 255), 2)
            cv2.line(resized, (self.mouse_pos[0], self.mouse_pos[1]-20), 
                    (self.mouse_pos[0], self.mouse_pos[1]+20), (0, 255, 255), 2)
            
            # Texto com coordenadas
            coord_text = f"X: {real_x}, Y: {real_y} | Slots marcados: {len(self.slots)}/8"
            cv2.putText(resized, coord_text, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            if self.pending_slot:
                cv2.putText(resized, "CONFIRME O SLOT (ENTER / BACKSPACE)", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.imshow(self.window_name, resized)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nCalibração cancelada.")
                break
            elif key == 13: # ENTER key
                if self.pending_slot:
                    self.slots.append(self.pending_slot)
                    print(f"Slot {self.pending_slot['id']} CONFIRMADO.")
                    self.pending_slot = None
            elif key == 8: # BACKSPACE key
                if self.pending_slot:
                    print("Slot cancelado. Tente novamente.")
                    self.pending_slot = None
            elif key == ord('s'):
                if len(self.slots) == 8 and self.pending_slot is None:
                    self.save_config()
                    break
                elif self.pending_slot is not None:
                    print("\nAVISO: Confirme o último slot antes de salvar!")
                else:
                    print(f"\nAVISO: Você marcou apenas {len(self.slots)} slots. Preciso de 8!")
        
        cv2.destroyAllWindows()
    
    def save_config(self):
        """Salva a configuração no formato correto para detection.py"""
        print("\n" + "=" * 60)
        print("COORDENADAS SALVAS:")
        print("=" * 60)
        print("\nCopie e cole isso no arquivo detection.py, substituindo SLOTS_CONFIG:\n")
        print("SLOTS_CONFIG = [")
        for slot in self.slots:
            print(f'    {{"id": {slot["id"]}, "left": {slot["left"]}, "top": {slot["top"]}}},  # Slot {slot["id"]}')
        print("]")
        print("\n" + "=" * 60)
        
        # Também salva em arquivo para facilitar
        output_file = Path(__file__).parent / "slots_config.txt"
        with open(output_file, 'w') as f:
            f.write("SLOTS_CONFIG = [\n")
            for slot in self.slots:
                f.write(f'    {{"id": {slot["id"]}, "left": {slot["left"]}, "top": {slot["top"]}}},  # Slot {slot["id"]}\n')
            f.write("]\n")
        
        print(f"\nConfiguração também salva em: {output_file}")
        print("Você pode copiar o conteúdo desse arquivo para detection.py")

if __name__ == "__main__":
    calibrator = SlotCalibrator()
    calibrator.run()
