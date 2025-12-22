# Arquivo para baixar as cartas da API do Clash Royale

import os
import requests
from pathlib import Path
from dotenv import load_dotenv


def sanitize_filename(nome: str) -> str:
    """Remove caracteres inválidos do nome do arquivo."""
    caracteres_invalidos = '<>:"/\\|?*'
    nome_limpo = nome.lower()  # Converter para minúsculas
    nome_limpo = nome_limpo.replace(' ', '-')  # Substituir espaços por hífen
    for char in caracteres_invalidos:
        nome_limpo = nome_limpo.replace(char, '_')
    return nome_limpo


def download_cards():
    """Baixa todas as imagens das cartas da API do Clash Royale."""
    load_dotenv()
    
    token = os.getenv("CR_API_TOKEN")
    if not token:
        raise RuntimeError("A variável de ambiente 'CR_API_TOKEN' não está definida.")
    
    # Criar diretório se não existir
    templates_dir = Path(__file__).parent / "cards-templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Fazer requisição à API
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
        
        # Baixar imagem medium
        if "medium" in icon_urls:
            url_medium = icon_urls["medium"]
            caminho_medium = templates_dir / f"{nome_arquivo}_medium.png"
            
            try:
                img_response = requests.get(url_medium, timeout=30)
                img_response.raise_for_status()
                caminho_medium.write_bytes(img_response.content)
                imagens_baixadas += 1
                print(f"  ✓ {nome_carta} (medium)")
            except Exception as e:
                print(f"  ✗ Erro ao baixar {nome_carta} (medium): {e}")
        
        # Baixar imagem evolutionMedium se existir
        if "evolutionMedium" in icon_urls:
            url_evolution = icon_urls["evolutionMedium"]
            caminho_evolution = templates_dir / f"{nome_arquivo}_evolutionMedium.png"
            
            try:
                img_response = requests.get(url_evolution, timeout=30)
                img_response.raise_for_status()
                caminho_evolution.write_bytes(img_response.content)
                imagens_baixadas += 1
                print(f"  ✓ {nome_carta} (evolutionMedium)")
            except Exception as e:
                print(f"  ✗ Erro ao baixar {nome_carta} (evolutionMedium): {e}")
        
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
            print("Falha ao consultar a API (401 Unauthorized): verifique se o token está correto.")
        elif status == 403:
            print("Falha ao consultar a API (403 Forbidden): confirme se o token está ativo "
                "e se o IP desta máquina foi autorizado no portal de desenvolvedores do Clash Royale.")
        else:
            print(f"Falha ao consultar a API: {erro_http}")
    except requests.RequestException as erro_rede:
        print(f"Erro de rede ao acessar a API: {erro_rede}")
    except Exception as e:
        print(f"Erro inesperado: {e}")

