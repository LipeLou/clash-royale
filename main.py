import os
from collections import deque
from dataclasses import dataclass
from typing import List, Optional

import requests
from dotenv import load_dotenv


@dataclass(frozen=True)
class Carta:
    nome: str
    elixir: int
    icon_url: Optional[str] = None


class ClashRoyaleAPI:
    BASE_URL = "https://api.clashroyale.com/v1"

    def __init__(self, token: str):
        if not token:
            raise ValueError("O token da API não pode ser vazio.")
        self._token = token

    def listar_cartas(self) -> List[Carta]:
        url = f"{self.BASE_URL}/cards"
        headers = {"Authorization": f"Bearer {self._token}"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        payload = response.json()
        cartas = []
        for item in payload.get("items", []):
            nome = item.get("name")
            elixir = item.get("elixirCost")
            icon_urls = item.get("iconUrls", {})
            icon_url = icon_urls.get("medium")
            
            if nome is None or elixir is None:
                continue
            cartas.append(Carta(nome=nome, elixir=elixir, icon_url=icon_url))
        return cartas

    def cartas_por_nomes(self, nomes: List[str]) -> List[Carta]:
        cartas_disponiveis = self.listar_cartas()
        cartas_encontradas = []
        for nome in nomes:
            carta = next(
                (c for c in cartas_disponiveis if c.nome.lower() == nome.lower()),
                None,
            )
            if carta is None:
                raise ValueError(f"Carta '{nome}' não encontrada na API.")
            cartas_encontradas.append(carta)
        return cartas_encontradas


class DeckState:
    """Mantém o estado do deck com a mão separada da fila FIFO."""

    def __init__(self, cartas):
        if len(cartas) != 8:
            raise ValueError("Um deck válido precisa conter exatamente 8 cartas.")

        self._mao = list(cartas[:4])
        self._fila = deque(cartas[4:])

    @property
    def mao(self):
        """Retorna uma cópia da mão atual (4 cartas jogáveis)."""
        return list(self._mao)

    @property
    def fila(self):
        """Retorna a fila de espera (4 cartas que ainda não estão na mão)."""
        return list(self._fila)

    def registrar_jogada(self, indice_mao):
        """
        Atualiza o estado após a jogada da carta na posição `indice_mao`.

        A carta sai da mão, vai para o final da fila e a primeira carta da fila
        preenche o espaço liberado na mão.
        """
        if not 0 <= indice_mao < len(self._mao):
            raise IndexError("A posição informada deve estar entre 0 e 3.")

        if not self._fila:
            raise RuntimeError("Fila vazia; estado inválido para o deck.")

        carta_jogada = self._mao[indice_mao]
        self._fila.append(carta_jogada)

        proxima_carta = self._fila.popleft()
        self._mao[indice_mao] = proxima_carta


def main():
    load_dotenv()

    token = os.getenv("CR_API_TOKEN")
    if not token:
        raise RuntimeError("A variável de ambiente 'CR_API_TOKEN' não está definida.")

    api = ClashRoyaleAPI(token)

    deck_nomes = [
        "Witch",
        "Giant",
        "Fireball",
        "Electro Wizard",
        "Hog Rider",
        "Arrows",
        "Ice Golem",
        "Tornado",
    ]

    try:
        deck_cartas = api.cartas_por_nomes(deck_nomes)
    except requests.HTTPError as erro_http:
        status = getattr(erro_http.response, "status_code", None)
        if status == 401:
            print(
                "Falha ao consultar a API (401 Unauthorized): verifique se o token está correto."
            )
        elif status == 403:
            print(
                "Falha ao consultar a API (403 Forbidden): confirme se o token está ativo "
                "e se o IP desta máquina foi autorizado no portal de desenvolvedores do Clash Royale."
            )
        else:
            print(f"Falha ao consultar a API: {erro_http}")
        return
    except requests.RequestException as erro_rede:
        print(f"Erro de rede ao acessar a API: {erro_rede}")
        return
    except ValueError as erro_busca:
        print(f"Erro ao montar o deck: {erro_busca}")
        return

    deck = DeckState(deck_cartas)

    def formatar(cartas):
        return [f"{carta.nome} ({carta.elixir} elixir)" for carta in cartas]

    print("Mão inicial:", formatar(deck.mao))
    print("Fila inicial:", formatar(deck.fila))

    try:
        indice_jogada = int(input("Digite o índice da carta a ser jogada: "))
    except ValueError:
        print("O índice deve ser um número inteiro.")
        return

    if not 0 <= indice_jogada < 4:
        print("O índice informado deve estar entre 0 e 3.")
        return

    carta_jogada = deck.mao[indice_jogada]
    print(f"\nJogando a carta na posição {indice_jogada}: {carta_jogada.nome}")

    deck.registrar_jogada(indice_jogada)

    print("\nMão após a jogada:", formatar(deck.mao))
    print("Fila atualizada:", formatar(deck.fila))


if __name__ == "__main__":
    main()
