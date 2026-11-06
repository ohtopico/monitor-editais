"""Descobre o chat_id do Telegram.

1. Mande qualquer mensagem para o seu bot no Telegram.
2. Rode:  TELEGRAM_TOKEN=123:abc python -m monitor.telegram_chat_id
"""

import os
import sys

import requests


def main() -> int:
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("Defina TELEGRAM_TOKEN com o token que o @BotFather deu.")
        return 1
    dados = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30).json()
    chats = {}
    for upd in dados.get("result", []):
        msg = upd.get("message") or upd.get("channel_post") or {}
        chat = msg.get("chat")
        if chat:
            chats[chat["id"]] = chat.get("title") or chat.get("first_name") or chat.get("username")
    if not chats:
        print("Nenhuma mensagem encontrada. Mande um 'oi' para o bot e rode de novo.")
        return 1
    for cid, nome in chats.items():
        print(f"TELEGRAM_CHAT_ID = {cid}   ({nome})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
