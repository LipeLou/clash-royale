from collections import deque


class DeckState:

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

    @property
    def estado_completo(self):
        """Conveniente para inspecionar o deck completo na ordem atual."""
        return self.mao + self.fila

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
    # Exemplo de inicialização com 8 cartas fictícias
    deck_inicial = [
        "Bruxa",
        "Gigante",
        "Bola de Fogo",
        "Mago Elétrico",
        "Corredor",
        "Flechas",
        "Golem de Gelo",
        "Tornado",
    ]

    deck = DeckState(deck_inicial)

    print("Mão inicial:", deck.mao)
    print("Fila inicial:", deck.fila)

    indice_jogada = int(input("Digite o índice da carta a ser jogada: "))
    carta_jogada = deck.mao[indice_jogada]
    print(f"\nJogando a carta na posição {indice_jogada}: {carta_jogada}")

    deck.registrar_jogada(indice_jogada)

    print("\nMão após a jogada:", deck.mao)
    print("Fila atualizada:", deck.fila)


if __name__ == "__main__":
    main()
