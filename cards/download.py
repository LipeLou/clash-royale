"""Download de imagens de cartas da API do Clash Royale."""

import os
from pathlib import Path

from dotenv import load_dotenv
import requests


def sanitize_filename(nome: str) -> str:
    """Normaliza o nome da carta para uso em arquivo."""
    caracteres_invalidos = '<>:"/\\|?*'
    nome_limpo = nome.lower()
    nome_limpo = nome_limpo.replace(" ", "-")
    for char in caracteres_invalidos:
        nome_limpo = nome_limpo.replace(char, "_")
    return nome_limpo


def _baixar_imagem(url: str, destino: Path, nome_carta: str, variante: str) -> bool:
    """Baixa uma imagem de carta e salva no caminho informado."""
    try:
        img_response = requests.get(url, timeout=30)
        img_response.raise_for_status()
        destino.write_bytes(img_response.content)
        print(f"  - {nome_carta} ({variante})")
        return True
    except (requests.RequestException, OSError) as exc:
        print(f"  ! Erro ao baixar {nome_carta} ({variante}): {exc}")
        return False


def download_cards() -> None:
    """Baixa imagens das cartas (medium/evolutionMedium) para a pasta local."""
    load_dotenv()
    token = os.getenv("CR_API_TOKEN")
    if not token:
        raise RuntimeError("A variavel de ambiente 'CR_API_TOKEN' nao esta definida.")

    templates_dir = Path(__file__).parent / "cards-templates"
    templates_dir.mkdir(exist_ok=True)

    url = "https://api.clashroyale.com/v1/cards"
    headers = {"Authorization": f"Bearer {token}"}

    print("Buscando cartas na API...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    payload = response.json()
    cartas = payload.get("items", [])

    print(f"Encontradas {len(cartas)} cartas. Iniciando download das imagens...")

    cartas_baixadas = 0
    imagens_baixadas = 0

    for carta in cartas:
        nome_carta = carta.get("name")
        if not nome_carta:
            continue

        nome_arquivo = sanitize_filename(nome_carta)
        icon_urls = carta.get("iconUrls", {})

        if "medium" in icon_urls:
            url_medium = icon_urls["medium"]
            caminho_medium = templates_dir / f"{nome_arquivo}_medium.png"
            if _baixar_imagem(url_medium, caminho_medium, nome_carta, "medium"):
                imagens_baixadas += 1

        if "evolutionMedium" in icon_urls:
            url_evolution = icon_urls["evolutionMedium"]
            caminho_evolution = templates_dir / f"{nome_arquivo}_evolutionMedium.png"
            if _baixar_imagem(url_evolution, caminho_evolution, nome_carta, "evolutionMedium"):
                imagens_baixadas += 1

        cartas_baixadas += 1

    print(f"\nDownload concluído!")
    print(f"  Cartas processadas: {cartas_baixadas}")
    print(f"  Imagens baixadas: {imagens_baixadas}")
    print(f"  Pasta de destino: {templates_dir.absolute()}")


if __name__ == "__main__":
    try:
        download_cards()
    except requests.HTTPError as erro_http:
        status = getattr(erro_http.response, "status_code", None)
        if status == 401:
            print("Falha ao consultar a API (401 Unauthorized): verifique se o token esta correto.")
        elif status == 403:
            print(
                "Falha ao consultar a API (403 Forbidden): confirme se o token esta ativo "
                "e se o IP desta maquina foi autorizado no portal de desenvolvedores do Clash Royale."
            )
        else:
            print(f"Falha ao consultar a API: {erro_http}")
    except requests.RequestException as erro_rede:
        print(f"Erro de rede ao acessar a API: {erro_rede}")
    except Exception as exc:
        print(f"Erro inesperado: {exc}")

