import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Any

class Dashboard:
    def __init__(self):
        self.width = 1100
        self.height = 400
        self.bg_color = (30, 30, 30) # Cinza escuro
        
        # Diretório onde estão os templates oficiais (imagens bonitas da API)
        self.templates_dir = Path(__file__).parent / "cards" / "cards-templates"
        
        self.assets_cache = {} # Cache: "Nome Bonito" -> Imagem Carregada
        self._load_assets()
        
        # Placeholder image (cinza com interrogação)
        self.placeholder = np.zeros((150, 120, 3), dtype=np.uint8)
        self.placeholder[:] = (50, 50, 50)
        cv2.putText(self.placeholder, "?", (45, 90), cv2.FONT_HERSHEY_SIMPLEX, 2, (100, 100, 100), 3)

    def _load_assets(self):
        """Pré-carrega todas as imagens de cards-templates para memória."""
        if not self.templates_dir.exists():
            print(f"[Dashboard] AVISO: Diretório de assets não encontrado: {self.templates_dir}")
            return

        png_files = list(self.templates_dir.glob("*.png"))
        print(f"[Dashboard] Carregando {len(png_files)} assets visuais...")
        
        count = 0
        for path in png_files:
            try:
                # Carrega imagem
                img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
                if img is None: continue
                
                # Normaliza o nome do arquivo para o "Nome Bonito" (Title Case)
                # Ex: "hog-rider_medium.png" -> "Hog Rider"
                # Ex: "mini-p.e.k.k.a_medium.png" -> "Mini P.E.K.K.A"
                # Ex: "barbarians_evolutionMedium.png" -> "Barbarians Evo"

                raw_name = path.stem # "hog-rider_medium"
                
                # Tratamento especial para evolução
                is_evo = "_evolution" in raw_name
                
                # Remove sufixos comuns
                name_clean = raw_name.replace("_medium", "").replace("_evolutionMedium", "")
                
                # Estrategia: Normalizar para chave de busca simplificada
                key_name = name_clean.replace("-", "").replace(" ", "").replace(".", "").lower()
                
                # Se for evo, adicionamos o sufixo "evo" na chave para diferenciar
                if is_evo:
                    key_name += "evo"

                self.assets_cache[key_name] = img
                count += 1
                
            except Exception as e:
                print(f"Erro ao carregar asset {path.name}: {e}")
                
        print(f"[Dashboard] {count} assets carregados.")

    def _get_image(self, nome_carta: Optional[str] = None) -> np.ndarray:
        if not nome_carta:
            return self.placeholder
            
        # Verifica se o nome indica uma evolução (geralmente termina com " evo" ou similar vindo do detection.py)
        # O detection.py formata nomes como "Barbarians Evo" se o arquivo de template tiver essa indicacao?
        # NÃO, o detection.py pega o nome do arquivo do usuario.
        # Se o usuario salvou "barbarians evo", o nome virá "Barbarians Evo".
        
        # Normalização de busca
        clean_name = nome_carta.lower().replace("-", "").replace(" ", "").replace(".", "")
        
        # Se o nome já contiver 'evo', remove e trata como flag, ou mantem na chave?
        # Minha logica de load adicionou "evo" no final da chave se o arquivo era evolution.
        # Então se o usuario salvou "Barbarians Evo", clean_name vira "barbariansevo", que bate com a chave!
        
        # Caso especial: Se o usuario salvou apenas "Barbarians" mas queremos mostrar a Evo se disponível?
        # Não, devemos confiar no nome que vem.
        
        key = clean_name
        
        if key in self.assets_cache:
            return self.assets_cache[key]
            
        return self.placeholder

    def draw_card(self, background, img, x, y, width, height):
        """Desenha a carta no background com suporte a transparência."""
        try:
            # Garante que as dimensões são válidas
            if width <= 0 or height <= 0: return

            # Redimensiona a imagem da carta
            resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
            
            # Limites para não desenhar fora do canvas
            bg_h, bg_w = background.shape[:2]
            
            # Clipa as coordenadas se necessário (simples)
            if x + width > bg_w: width = bg_w - x
            if y + height > bg_h: height = bg_h - y
            if width <= 0 or height <= 0: return
            
            resized = resized[:height, :width]
            
            # Overlay com transparencia se tiver canal Alpha
            if resized.shape[2] == 4:
                alpha_s = resized[:, :, 3] / 255.0
                alpha_l = 1.0 - alpha_s
                
                for c in range(0, 3):
                    background[y:y+height, x:x+width, c] = (alpha_s * resized[:, :, c] +
                                                            alpha_l * background[y:y+height, x:x+width, c])
            else:
                background[y:y+height, x:x+width] = resized
        except Exception as e:
            print(f"Erro ao desenhar carta em ({x},{y}): {e}")

    def update(self, slots_info: Dict[int, Any]):
        """
        slots_info: Dict onde a chave é o índice do slot e o valor é um objeto SlotInfo 
                    (conforme definido em detection.py)
        """
        # Cria fundo
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        canvas[:] = self.bg_color
        
        # Cabeçalho
        cv2.putText(canvas, "OPPONENT HAND TRACKER", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.line(canvas, (30, 50), (self.width - 30, 50), (100, 100, 100), 1)

        # Configurações de Layout
        start_x = 40
        start_y = 100
        card_w = 100
        card_h = 120 # Proporção aproximada carta
        gap = 25
        
        for i in range(8):
            slot = slots_info.get(i)
            # Como removemos a API, não existe mais carta_obj, apenas nome_carta
            nome_carta = getattr(slot, 'nome_carta', None) if slot else None
            
            # Busca imagem
            img = self._get_image(nome_carta)
                
            x = start_x + (i * (card_w + gap))
            
            # Adiciona um espaço extra entre slot 3 e 4 para separar visualmente "mão" de "fila"
            if i >= 4:
                x += gap * 2
                
                # Se for o primeiro da fila, desenha um label
                if i == 4:
                    cv2.putText(canvas, "QUEUE / CYCLE", (x, start_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            elif i == 0:
                cv2.putText(canvas, "CURRENT HAND", (x, start_y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

            y = start_y
            
            # Fundo do slot (card placeholder border)
            cv2.rectangle(canvas, (x-2, y-2), (x+card_w+2, y+card_h+2), (60, 60, 60), -1)
            
            self.draw_card(canvas, img, x, y, card_w, card_h)
            
            # Nome da carta (abreviado se longo)
            name = "?"
            if nome_carta: name = nome_carta
            
            # Trunca nome
            if len(name) > 12:
                name = name[:10] + ".."
                
            cv2.putText(canvas, name, (x, y + card_h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
            
            # Slot ID pequeno
            cv2.putText(canvas, str(i), (x + card_w - 15, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2)
            cv2.putText(canvas, str(i), (x + card_w - 15, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        cv2.imshow("Opponent Dashboard", canvas)
