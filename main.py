"""Simulacao de deck FIFO usando dados da API do Clash Royale."""

from collections import deque
from dataclasses import dataclass
import os
from typing import List, Optional, Sequence

from dotenv import load_dotenv
import requests


@dataclass(frozen=True)
class Carta:
    """Representa uma carta com nome, custo de elixir e icone opcional."""

    nome: str
    elixir: int
    icon_url: Optional[str] = None


class ClashRoyaleAPI:
    """Cliente minimo para consulta de cartas na API oficial."""

    BASE_URL = "https://api.clashroyale.com/v1"

    def __init__(self, token: str):
        if not token:
            raise ValueError("O token da API nao pode ser vazio.")
        self._token = token

    def listar_cartas(self) -> List[Carta]:
        """Retorna todas as cartas disponiveis na API."""
        url = f"{self.BASE_URL}/cards"
        headers = {"Authorization": f"Bearer {self._token}"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        payload = response.json()
        cartas: List[Carta] = []
        for item in payload.get("items", []):
            nome = item.get("name")
            elixir = item.get("elixirCost")
            icon_url = item.get("iconUrls", {}).get("medium")
            if nome is None or elixir is None:
                continue
            cartas.append(Carta(nome=nome, elixir=elixir, icon_url=icon_url))
        return cartas

    def cartas_por_nomes(self, nomes: Sequence[str]) -> List[Carta]:
        """Busca cartas pelo nome exato, ignorando diferenca de caixa."""
        cartas_disponiveis = self.listar_cartas()
        cartas_encontradas: List[Carta] = []
        for nome in nomes:
            carta = next((c for c in cartas_disponiveis if c.nome.lower() == nome.lower()), None)
            if carta is None:
                raise ValueError(f"Carta '{nome}' nao encontrada na API.")
            cartas_encontradas.append(carta)
        return cartas_encontradas


class DeckState:
    """Mantem o estado do deck com mao e fila FIFO."""

    def __init__(self, cartas: Sequence[Carta]):
        if len(cartas) != 8:
            raise ValueError("Um deck valido precisa conter exatamente 8 cartas.")
        self._mao = list(cartas[:4])
        self._fila = deque(cartas[4:])

    @property
    def mao(self) -> List[Carta]:
        """Retorna uma copia da mao atual."""
        return list(self._mao)

    @property
    def fila(self) -> List[Carta]:
        """Retorna uma copia da fila de espera."""
        return list(self._fila)

    def registrar_jogada(self, indice_mao: int) -> None:
        """Aplica uma jogada e atualiza mao/fila preservando FIFO."""
        if not 0 <= indice_mao < len(self._mao):
            raise IndexError("A posicao informada deve estar entre 0 e 3.")
        if not self._fila:
            raise RuntimeError("Fila vazia; estado invalido para o deck.")

        carta_jogada = self._mao[indice_mao]
        self._fila.append(carta_jogada)
        self._mao[indice_mao] = self._fila.popleft()


def formatar_cartas(cartas: Sequence[Carta]) -> List[str]:
    """Converte cartas para representacao textual legivel."""
    return [f"{carta.nome} ({carta.elixir} elixir)" for carta in cartas]


def main() -> None:
    """Executa uma simulacao simples de jogada com deck fixo."""
    load_dotenv()
    token = os.getenv("CR_API_TOKEN")
    if not token:
        raise RuntimeError("A variavel de ambiente 'CR_API_TOKEN' nao esta definida.")

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
            print("Falha ao consultar a API (401 Unauthorized): verifique se o token esta correto.")
        elif status == 403:
            print(
                "Falha ao consultar a API (403 Forbidden): confirme se o token esta ativo "
                "e se o IP desta maquina foi autorizado no portal de desenvolvedores do Clash Royale."
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
    print("Mao inicial:", formatar_cartas(deck.mao))
    print("Fila inicial:", formatar_cartas(deck.fila))

    try:
        indice_jogada = int(input("Digite o indice da carta a ser jogada: "))
    except ValueError:
        print("O indice deve ser um numero inteiro.")
        return

    if not 0 <= indice_jogada < 4:
        print("O indice informado deve estar entre 0 e 3.")
        return

    carta_jogada = deck.mao[indice_jogada]
    print(f"\nJogando a carta na posicao {indice_jogada}: {carta_jogada.nome}")

    deck.registrar_jogada(indice_jogada)
    print("\nMao apos a jogada:", formatar_cartas(deck.mao))
    print("Fila atualizada:", formatar_cartas(deck.fila))


if __name__ == "__main__":
    main()
