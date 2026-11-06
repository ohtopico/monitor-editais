"""Envio dos avisos por e-mail.

As credenciais vêm de variáveis de ambiente (secrets do GitHub):
  EMAIL_USUARIO, EMAIL_SENHA, EMAIL_PARA  (e opcionais SMTP_HOST, SMTP_PORTA)
"""

from __future__ import annotations

import html
import os
import smtplib
from email.message import EmailMessage

from .fontes import Item

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


CANAIS = {"email": enviar_email}


def canal_configurado(canal: str) -> bool:
    if canal == "email":
        return bool(os.environ.get("EMAIL_USUARIO") and os.environ.get("EMAIL_SENHA"))
    return False
