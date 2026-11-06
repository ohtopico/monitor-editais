"""Envio dos avisos por Telegram e e-mail.

As credenciais vêm de variáveis de ambiente (secrets do GitHub):
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
  EMAIL_USUARIO, EMAIL_SENHA, EMAIL_PARA  (e opcionais SMTP_HOST, SMTP_PORTA)
"""

from __future__ import annotations

import html
import os
import smtplib
from email.message import EmailMessage

import requests

from .fontes import Item

LIMITE_TELEGRAM = 3800  # a API aceita 4096 caracteres por mensagem


def _linha_telegram(item: Item) -> str:
    partes = [f'• <a href="{html.escape(item.link, quote=True)}">{html.escape(item.titulo)}</a>']
    if item.detalhes:
        partes.append(f"  {html.escape(item.detalhes)}")
    rodape = item.fonte
    lugares = [l for l in item.lugares[:3] if l != item.fonte]
    if lugares:
        rodape += " · " + ", ".join(lugares)
    partes.append(f"  <i>{html.escape(rodape)}</i>")
    return "\n".join(partes)


def mensagens_telegram(itens: list[Item], cabecalho: str) -> list[str]:
    msgs, atual = [], f"<b>{html.escape(cabecalho)}</b>\n"
    for item in itens:
        linha = _linha_telegram(item) + "\n"
        if len(atual) + len(linha) > LIMITE_TELEGRAM:
            msgs.append(atual)
            atual = ""
        atual += "\n" + linha
    msgs.append(atual)
    return msgs


def enviar_telegram(itens: list[Item], cabecalho: str) -> None:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        raise RuntimeError("faltam os secrets TELEGRAM_TOKEN e/ou TELEGRAM_CHAT_ID")
    for texto in mensagens_telegram(itens, cabecalho):
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": texto, "parse_mode": "HTML",
                  "disable_web_page_preview": True},
            timeout=30,
        )
        if not r.ok:
            raise RuntimeError(f"Telegram respondeu {r.status_code}: {r.text[:200]}")


def corpo_email(itens: list[Item], cabecalho: str) -> tuple[str, str]:
    texto = [cabecalho, ""]
    blocos = []
    for item in itens:
        texto += [f"- {item.titulo}", f"  {item.link}"]
        if item.detalhes:
            texto.append(f"  {item.detalhes}")
        texto.append(f"  ({item.fonte})")
        texto.append("")
        detalhe = f'<div style="color:#4a4a4a">{html.escape(item.detalhes)}</div>' if item.detalhes else ""
        blocos.append(
            '<li style="margin:0 0 14px">'
            f'<a href="{html.escape(item.link, quote=True)}" style="color:#166c40;font-weight:600">'
            f"{html.escape(item.titulo)}</a>{detalhe}"
            f'<div style="color:#545a56;font-size:13px">{html.escape(item.fonte)}</div></li>'
        )
    corpo_html = (
        '<div style="font-family:Lexend,Arial,sans-serif;color:#111;max-width:640px">'
        f'<h2 style="font-family:Sniglet,Arial,sans-serif;letter-spacing:.04em">{html.escape(cabecalho)}</h2>'
        f'<ul style="padding-left:18px">{"".join(blocos)}</ul>'
        '<p style="color:#545a56;font-size:12px">Monitor de editais · ohtopico.com.br</p></div>'
    )
    return "\n".join(texto), corpo_html


def enviar_email(itens: list[Item], cabecalho: str) -> None:
    usuario = os.environ.get("EMAIL_USUARIO")
    senha = os.environ.get("EMAIL_SENHA")
    para = os.environ.get("EMAIL_PARA") or usuario
    if not (usuario and senha):
        raise RuntimeError("faltam os secrets EMAIL_USUARIO e/ou EMAIL_SENHA")
    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    porta = int(os.environ.get("SMTP_PORTA") or 465)

    msg = EmailMessage()
    msg["Subject"] = cabecalho
    msg["From"] = usuario
    msg["To"] = para
    texto, corpo_html = corpo_email(itens, cabecalho)
    msg.set_content(texto)
    msg.add_alternative(corpo_html, subtype="html")

    with smtplib.SMTP_SSL(host, porta, timeout=30) as smtp:
        smtp.login(usuario, senha)
        smtp.send_message(msg)


CANAIS = {"telegram": enviar_telegram, "email": enviar_email}


def canal_configurado(canal: str) -> bool:
    if canal == "telegram":
        return bool(os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))
    if canal == "email":
        return bool(os.environ.get("EMAIL_USUARIO") and os.environ.get("EMAIL_SENHA"))
    return False
