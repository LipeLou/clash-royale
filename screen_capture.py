import platform
import numpy as np
import cv2
import mss
from PIL import ImageGrab
import subprocess
import os

class ScreenCapture:
    def __init__(self, monitor_index=1):
        self.system = platform.system()
        self.monitor_index = monitor_index
        self.sct = None
        self.backend = None
        # Valor padrão seguro
        self.monitor_info = {"top": 0, "left": 0, "width": 1920, "height": 1080}
        
        print("[ScreenCapture] Inicializando sistema de captura...")

        # 1. Tenta MSS (Melhor Performance - Windows/Linux X11)
        try:
            self.sct = mss.mss()
            if len(self.sct.monitors) > monitor_index:
                self.monitor = self.sct.monitors[monitor_index]
            else:
                self.monitor = self.sct.monitors[0]
            
            # Teste real de captura
            self.sct.grab(self.monitor)
            self.backend = "mss"
            print(f"[ScreenCapture] ✓ Backend MSS ativo.")
            return 
        except Exception as e:
            print(f"[ScreenCapture] ✗ MSS falhou: {e}")
            self.sct = None

        # 2. Tenta PIL ImageGrab (Compatível X11/Alguns Wayland)
        try:
            img = ImageGrab.grab()
            # Apenas acessa propriedades para forçar erro se não funcionar
            w, h = img.size
            self.backend = "pil"
            self.monitor_info = {"top": 0, "left": 0, "width": w, "height": h}
            print(f"[ScreenCapture] ✓ Backend PIL ativo.")
            return 
        except Exception as e:
            print(f"[ScreenCapture] ✗ PIL falhou: {e}")

        # 3. Tenta Gnome Screenshot (Wayland Fallback - Lento)
        try:
            # Verifica se comando existe
            subprocess.run(["gnome-screenshot", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            self.backend = "gnome"
            print(f"[ScreenCapture] ✓ Backend Gnome Screenshot ativo (AVISO: Lento!).")
            # Não conseguimos pegar resolução fácil aqui, mantemos padrão HD
            return
        except Exception as e:
            print(f"[ScreenCapture] ✗ Gnome Screenshot falhou/não instalado: {e}")

        print("\n[ScreenCapture] ERRO FATAL: Nenhum método de captura funcionou.")
        print("DICA: Se estiver no Linux Wayland, tente logar na sessão 'Ubuntu on Xorg'.")
        # Não lança erro aqui para permitir que o usuário veja a mensagem, 
        # mas o método grab() vai falhar.
        self.backend = "none"

    def grab(self):
        """Captura a tela e retorna imagem BGR (OpenCV)."""
        try:
            if self.backend == "mss":
                sct_img = self.sct.grab(self.monitor)
                return cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
            
            elif self.backend == "pil":
                img = ImageGrab.grab()
                return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            elif self.backend == "gnome":
                # Método lento: salva em arquivo temporário e lê
                filename = "/tmp/clash_screen_capture.png"
                subprocess.run(["gnome-screenshot", "-f", filename], check=True)
                img = cv2.imread(filename)
                return img
                
        except Exception as e:
            # Evita spammar erro no loop
            # print(f"Erro captura: {e}")
            pass
        
        return None

    def get_monitor_info(self):
        if self.backend == "mss":
            return self.monitor
        return self.monitor_info
