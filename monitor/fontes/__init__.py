"""Fontes de editais. Cada fonte devolve uma lista de Item."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime

import requests

USER_AGENT = "Mozilla/5.0 (compatible; monitor-editais/1.0; +https://github.com/ohtopico/monitor-editais)"
TIMEOUT = 30


@dataclass
class Item:
    titulo: str
    link: str
    fonte: str
    texto: str = ""          # texto usado no filtro (título + detalhes)
    data: datetime | None = None
    detalhes: str = ""       # linha curta para o aviso (vagas, salário, prazo)
    lugares: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        chave = self.link.split("#")[0].rstrip("/").lower()
        return hashlib.sha1(chave.encode()).hexdigest()[:16]


def baixar(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return resp.text
