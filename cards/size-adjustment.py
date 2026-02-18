from pathlib import Path

from PIL import Image

"""Redimensiona templates de cartas para o tamanho usado na deteccao."""

LARGURA_DESEJADA = 61
ALTURA_DESEJADA = 90

def redimensionar_e_salvar(caminho_imagem: Path, largura: int, altura: int) -> str:
    """Redimensiona uma imagem para o tamanho alvo e salva no mesmo arquivo."""
    try:
        img_para_salvar = None

        with Image.open(caminho_imagem) as img:
            if img.size == (largura, altura) and img.mode == "RGBA":
                return "ignorada"

            img_work = img
            if img_work.mode != "RGBA":
                img_work = img_work.convert("RGBA")

            img_redimensionada = img_work.resize(
                (largura, altura),
                Image.Resampling.LANCZOS,
            )
            img_para_salvar = img_redimensionada

        if img_para_salvar:
            img_para_salvar.save(caminho_imagem, "PNG", optimize=True)
            return "processada"

        return "erro"
    except Exception as exc:
        print(f"  ! Erro ao processar {caminho_imagem.name}: {exc}")
        return "erro"

def processar_templates(pasta_templates: Path, largura: int, altura: int) -> None:
    """Processa todos os PNGs da pasta de templates."""
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

        if status == "processada":
            processadas += 1
        elif status == "ignorada":
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
    templates_dir = Path(__file__).parent / "cards-templates"
    processar_templates(templates_dir, LARGURA_DESEJADA, ALTURA_DESEJADA)