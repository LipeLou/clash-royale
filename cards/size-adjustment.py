import os
from pathlib import Path
from PIL import Image

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================
# DICA: Use o Paint ou ferramenta de print para medir EXATAMENTE o tamanho (px)
# que a carta ocupa dentro do slot no seu monitor/screenshot.
# Exemplo: Se no print o slot tem 82x96 pixels, coloque esses valores aqui.
LARGURA_DESEJADA = 250  # Ajuste para o valor medido no print
ALTURA_DESEJADA = 400   # Ajuste para o valor medido no print

def redimensionar_e_salvar(caminho_imagem: Path, largura: int, altura: int) -> str:
    """
    Força o redimensionamento da imagem para preencher exatamente largura x altura.
    Retorna: 'processada', 'ignorada' (já estava ok) ou 'erro'.
    """
    try:
        img_para_salvar = None
        
        with Image.open(caminho_imagem) as img:
            # Verifica se já está no tamanho correto e no modo correto
            if img.size == (largura, altura) and img.mode == 'RGBA':
                return 'ignorada'

            # Trabalha com uma cópia ou conversão
            img_work = img
            if img_work.mode != 'RGBA':
                img_work = img_work.convert('RGBA')
            
            # Redimensiona (cria nova imagem em memória)
            img_redimensionada = img_work.resize(
                (largura, altura),
                Image.Resampling.LANCZOS
            )
            
            # Prepara para salvar fora do contexto
            img_para_salvar = img_redimensionada

        # Salva o arquivo (agora que o original está fechado)
        if img_para_salvar:
            img_para_salvar.save(caminho_imagem, "PNG", optimize=True)
            return 'processada'
        
        return 'erro'
            
    except Exception as e:
        print(f"  ✗ Erro ao processar {caminho_imagem.name}: {e}")
        return 'erro'

def processar_templates(pasta_templates: Path, largura: int, altura: int) -> None:
    if not pasta_templates.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {pasta_templates}")
    
    imagens = list(pasta_templates.glob("*.png"))
    
    if not imagens:
        print(f"Nenhuma imagem PNG encontrada em {pasta_templates}")
        return
    
    print(f"--- INICIANDO PROCESSAMENTO DE {len(imagens)} IMAGENS ---")
    print(f"Alvo: {largura}px (L) x {altura}px (A) | Modo: Esticar (Fill)")
    
    processadas = 0
    ignoradas = 0
    erros = 0
    
    for caminho in imagens:
        status = redimensionar_e_salvar(caminho, largura, altura)
        
        if status == 'processada':
            processadas += 1
        elif status == 'ignorada':
            ignoradas += 1
        else:
            erros += 1
            print(f"Falha em {caminho.name}")
    
    print(f"\nConcluído!")
    print(f"  Redimensionadas: {processadas}")
    print(f"  Já no tamanho:   {ignoradas}")
    print(f"  Erros:           {erros}")
    print(f"  Total:           {len(imagens)}")

if __name__ == "__main__":
    # Garante que pega a pasta relativa ao local deste script
    templates_dir = Path(__file__).parent / "cards-templates"
    
    # Executa
    processar_templates(templates_dir, LARGURA_DESEJADA, ALTURA_DESEJADA)