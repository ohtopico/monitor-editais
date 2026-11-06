"""Páginas de editais de prefeituras e universidades.

Não precisa conhecer o HTML de cada site: guarda os links da página que
parecem edital de professor. Como a própria página já é da região, o filtro
de município não se aplica aqui (o nome da página entra como lugar).
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import Item, baixar


def ler_pagina(html: str, url: str, nome: str, filtro) -> list[Item]:
    sopa = BeautifulSoup(html, "html.parser")
    itens = []
    for a in sopa.find_all("a", href=True):
        if a["href"].startswith(("#", "javascript:", "mailto:")):
            continue
        texto = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        titulo = a.get("title") or texto
        alvo = f"{titulo} {texto} {a['href'].replace('-', ' ').replace('_', ' ')}"
        if not (filtro.eh_professor(alvo) and filtro.eh_selecao(alvo)):
            continue
        itens.append(Item(
            titulo=titulo or a["href"],
            link=urljoin(url, a["href"]),
            fonte=nome,
            texto=alvo,
            lugares=[nome],
        ))
    return itens


def coletar(config: dict, filtro) -> list[Item]:
    itens: dict[str, Item] = {}
    erros = []
    for pag in config["fontes"].get("paginas", []) or []:
        try:
            for item in ler_pagina(baixar(pag["url"]), pag["url"], pag["nome"], filtro):
                itens.setdefault(item.id, item)
        except Exception as e:  # uma página fora do ar não para as outras
            erros.append(f"{pag['nome']}: {e}")
    return list(itens.values()), erros
