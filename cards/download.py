# Arquivo para baixar as cartas da API do Clash Royale

import requests

def download_cards():
    url = "https://api.clashroyale.com/v1/cards"
    response = requests.get(url)
    return response.json()

