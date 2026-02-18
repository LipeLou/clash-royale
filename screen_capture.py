"""Camada de captura de tela com fallback entre diferentes backends."""

import subprocess

import cv2
import mss
import numpy as np
from PIL import ImageGrab


class ScreenCapture:
    """Fornece captura de tela em BGR para processamento com OpenCV."""

    def __init__(self, monitor_index: int = 1):
        self.sct = None
        self.backend = None
        self.monitor_info = {"top": 0, "left": 0, "width": 1920, "height": 1080}

        print("[CAPTURE][INIT] Inicializando sistema de captura")

        try:
            self.sct = mss.mss()
            if len(self.sct.monitors) > monitor_index:
                self.monitor = self.sct.monitors[monitor_index]
            else:
                self.monitor = self.sct.monitors[0]

            self.sct.grab(self.monitor)
            self.backend = "mss"
            print("[CAPTURE][OK] Backend selecionado: MSS")
            return
        except Exception as exc:
            print(f"[CAPTURE][WARN] MSS indisponivel: {exc}")
            self.sct = None

        try:
            img = ImageGrab.grab()
            width, height = img.size
            self.backend = "pil"
            self.monitor_info = {"top": 0, "left": 0, "width": width, "height": height}
            print("[CAPTURE][OK] Backend selecionado: PIL")
            return
        except Exception as exc:
            print(f"[CAPTURE][WARN] PIL indisponivel: {exc}")

        try:
            subprocess.run(
                ["gnome-screenshot", "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            self.backend = "gnome"
            print("[CAPTURE][OK] Backend selecionado: GNOME_SCREENSHOT (lento)")
            return
        except Exception as exc:
            print(f"[CAPTURE][WARN] GNOME_SCREENSHOT indisponivel: {exc}")

        print("[CAPTURE][ERROR] Nenhum metodo de captura funcionou")
        print("[CAPTURE][HINT] Em Linux Wayland, tente uma sessao X11")
        self.backend = "none"

    def grab(self) -> np.ndarray | None:
        """Captura a tela e retorna um frame BGR."""
        try:
            if self.backend == "mss":
                sct_img = self.sct.grab(self.monitor)
                return cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)

            if self.backend == "pil":
                img = ImageGrab.grab()
                return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            if self.backend == "gnome":
                filename = "/tmp/clash_screen_capture.png"
                subprocess.run(["gnome-screenshot", "-f", filename], check=True)
                return cv2.imread(filename)
        except Exception:
            pass

        return None

    def get_monitor_info(self) -> dict:
        """Retorna as dimensoes do monitor de captura ativo."""
        if self.backend == "mss":
            return self.monitor
        return self.monitor_info
