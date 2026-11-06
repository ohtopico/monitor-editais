"""PCI Concursos: listas de concursos abertos.

Cada concurso aparece como um link para /noticias/..., seguido da UF, das
vagas, dos cargos, da escolaridade e do prazo de inscrição. O parser procura
os blocos conhecidos (div.ca, div.cc, div.cd, div.ce) e, se o site mudar,
cai num modo genérico que usa só os links de notícia.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from . import Item, baixar

DATA = re.compile(r"\d{2}/\d{2}/\d{4}")


def _limpo(tag) -> str:
    return re.sub(r"\s+", " ", tag.get_text(" ", strip=True)) if tag else ""


def ler_pagina(html: str, url: str) -> list[Item]:
    sopa = BeautifulSoup(html, "html.parser")
    itens: list[Item] = []

    blocos = sopa.select("div.ca")
    for ca in blocos:
        a = ca.find("a", href=True)
        if not a:
            continue
        pai = ca.parent
        uf = _limpo(pai.select_one("div.cc")) if pai else ""
        info = _limpo(pai.select_one("div.cd")) if pai else ""
        prazo = _limpo(pai.select_one("div.ce")) if pai else ""
        if uf and uf.strip().upper() != "RS":
            continue
        titulo = a.get("title") or _limpo(a)
        orgao = _limpo(a)
        datas = DATA.findall(prazo)
        detalhes = " · ".join(p for p in [info, f"inscrições até {datas[-1]}" if datas else prazo] if p)
        itens.append(Item(
            titulo=titulo,
            link=urljoin(url, a["href"]),
            fonte="PCI Concursos",
            texto=f"{orgao} {titulo} {info}",
            detalhes=detalhes,
        ))

    if blocos:
        return itens

    # Modo genérico: todo link para /noticias/ com o texto ao redor.
    for a in sopa.select('a[href*="/noticias/"]'):
        titulo = a.get("title") or _limpo(a)
        contexto = _limpo(a.find_parent(["div", "li", "article"]))
        if not re.search(r"(?<![A-Za-z])RS(?![A-Za-z])", f"{titulo} {contexto}"):
            continue
        itens.append(Item(
            titulo=titulo,
            link=urljoin(url, a["href"]),
            fonte="PCI Concursos",
            texto=f"{titulo} {contexto}",
            detalhes=contexto[:200],
        ))
    return itens


def coletar(config: dict) -> list[Item]:
    itens: dict[str, Item] = {}
    for url in config["fontes"]["pci_concursos"].get("paginas", []):
        for item in ler_pagina(baixar(url), url):
            itens.setdefault(item.id, item)
    return list(itens.values())
