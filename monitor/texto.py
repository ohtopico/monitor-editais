"""Normalização de texto e filtros (região + cargo de professor)."""

from __future__ import annotations

import re
import unicodedata

UFS = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg",
    "pa", "pb", "pr", "pe", "pi", "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to",
}


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e com espaços simples."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.lower()).strip()


def _tem_palavra(texto_norm: str, palavra: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(normalizar(palavra)) + r"(?![a-z0-9])", texto_norm) is not None


class Filtro:
    """Decide se um texto é um edital de professor da região."""

    def __init__(self, config: dict):
        self.municipios = [(normalizar(m), m) for m in config.get("municipios", [])]
        self.ambiguos = [(normalizar(m), m) for m in config.get("municipios_ambiguos", [])]
        self.instituicoes = [(normalizar(i), i) for i in config.get("instituicoes", [])]
        self.palavras_cargo = [normalizar(p) for p in config.get("palavras_cargo", [])]
        self.palavras_selecao = [normalizar(p) for p in config.get("palavras_selecao", [])]

    # --- região -----------------------------------------------------------
    def _municipio_ok(self, t: str, nome: str) -> bool:
        """Achou o nome e ele não é outro lugar (Santa Maria do Herval, Vera Cruz/SP...)."""
        padrao = r"(?<![a-z0-9])" + re.escape(nome) + r"(?![a-z0-9])"
        for m in re.finditer(padrao, t):
            depois = t[m.end():m.end() + 12]
            # "Santa Maria do Herval", "Rio Pardo de Minas": é outro município.
            if re.match(r"\s(do|da|de|dos|das)\s", depois):
                continue
            # "Vera Cruz/SP", "Sobradinho - DF", "Agudo (RS)"
            uf = re.match(r"\s?[-/(,]\s?([a-z]{2})(?![a-z])", depois)
            if uf and uf.group(1) in UFS and uf.group(1) != "rs":
                continue
            return True
        return False

    def _ambiguo_ok(self, t: str, nome: str) -> bool:
        n = re.escape(nome)
        return bool(
            re.search(r"(prefeitura|municipio|camara)( municipal)? de " + n + r"(?![a-z0-9])", t)
            or re.search(r"(?<![a-z0-9])" + n + r"\s?[-/(]\s?rs(?![a-z])", t)
        )

    def regiao(self, texto: str) -> list[str]:
        """Lista dos lugares/instituições da região citados no texto."""
        t = normalizar(texto)
        achados = [orig for m, orig in self.municipios if self._municipio_ok(t, m)]
        achados += [orig for m, orig in self.ambiguos if self._ambiguo_ok(t, m)]
        achados += [orig for i, orig in self.instituicoes if _tem_palavra(t, i)]
        return achados

    # --- cargo ------------------------------------------------------------
    def eh_professor(self, texto: str) -> bool:
        t = normalizar(texto)
        return any(_tem_palavra(t, p) for p in self.palavras_cargo)

    def eh_selecao(self, texto: str) -> bool:
        t = normalizar(texto)
        return any(_tem_palavra(t, p) for p in self.palavras_selecao)

    def aceita(self, texto: str) -> list[str] | None:
        """Devolve os lugares da região se o texto passa em todos os filtros."""
        if not (self.eh_professor(texto) and self.eh_selecao(texto)):
            return None
        lugares = self.regiao(texto)
        return lugares or None
