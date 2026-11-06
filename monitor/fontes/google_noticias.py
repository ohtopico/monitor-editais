"""Busca no RSS do Google Notícias (sem chave de API)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from . import Item, baixar

BASE = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"


def montar_buscas(config: dict) -> list[str]:
    cfg = config["fontes"]["google_noticias"]
    por_busca = int(cfg.get("municipios_por_busca", 8))
    nomes = list(config.get("municipios", []))
    buscas = []
    for i in range(0, len(nomes), por_busca):
        grupo = " OR ".join(f'"{n}"' for n in nomes[i:i + por_busca])
        buscas.append(f'(concurso OR "processo seletivo" OR "contratação emergencial") professor RS ({grupo})')
    buscas += cfg.get("buscas_extras", [])
    dias = int(config.get("dias_maximos", 45))
    return [f"{b} when:{dias}d" for b in buscas]


def ler_rss(xml: str) -> list[Item]:
    itens = []
    raiz = ET.fromstring(xml)
    for el in raiz.iter("item"):
        titulo = (el.findtext("title") or "").strip()
        link = (el.findtext("link") or "").strip()
        veiculo = (el.findtext("source") or "").strip()
        descricao = re.sub(r"<[^>]+>", " ", el.findtext("description") or "")
        data = None
        if el.findtext("pubDate"):
            try:
                data = parsedate_to_datetime(el.findtext("pubDate"))
            except (TypeError, ValueError):
                pass
        # O Google põe " - Nome do veículo" no fim do título.
        if veiculo and titulo.endswith(" - " + veiculo):
            titulo = titulo[: -len(veiculo) - 3]
        itens.append(Item(
            titulo=titulo,
            link=link,
            fonte=f"Google Notícias · {veiculo}" if veiculo else "Google Notícias",
            texto=f"{titulo} {descricao}",
            data=data,
        ))
    return itens


def coletar(config: dict) -> list[Item]:
    itens: dict[str, Item] = {}
    for busca in montar_buscas(config):
        for item in ler_rss(baixar(BASE.format(q=quote_plus(busca)))):
            itens.setdefault(item.id, item)
    return list(itens.values())
