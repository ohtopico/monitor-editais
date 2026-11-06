"""Monitor de editais para professores.

Uso:
  python -m monitor            coleta, avisa o que for novo e salva o estado
  python -m monitor --teste    coleta e mostra o que acharia, sem avisar nem salvar
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import avisos, pagina
from .fontes import Item, google_noticias, paginas, pci
from .texto import Filtro, normalizar

RAIZ = Path(__file__).resolve().parent.parent
ESTADO = RAIZ / "dados" / "vistos.json"


def carregar_estado(caminho: Path) -> dict:
    if caminho.exists():
        return json.loads(caminho.read_text(encoding="utf-8"))
    return {"vistos": {}}


def salvar_estado(caminho: Path, estado: dict, dias: int) -> None:
    limite = (datetime.now(timezone.utc) - timedelta(days=dias * 3)).isoformat()
    estado["vistos"] = {k: v for k, v in estado["vistos"].items() if v.get("visto_em", "") >= limite}
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def coletar(config: dict, filtro: Filtro) -> tuple[list[Item], list[str]]:
    brutos: list[Item] = []
    erros: list[str] = []
    contagem: dict[str, int] = {}
    fontes = config.get("fontes", {})

    if fontes.get("google_noticias", {}).get("ativo"):
        try:
            achados = google_noticias.coletar(config)
            contagem["Google Notícias"] = len(achados)
            brutos += achados
        except Exception as e:
            erros.append(f"Google Notícias: {e}")
    if fontes.get("pci_concursos", {}).get("ativo"):
        try:
            achados = pci.coletar(config)
            contagem["PCI Concursos"] = len(achados)
            brutos += achados
        except Exception as e:
            erros.append(f"PCI Concursos: {e}")
    if fontes.get("paginas"):
        achados, errs = paginas.coletar(config, filtro)
        contagem["Sites de editais"] = len(achados)
        brutos += achados
        erros += errs

    print("Itens lidos por fonte (antes do filtro): " + ", ".join(f"{k}: {v}" for k, v in contagem.items()))
    limite = datetime.now(timezone.utc) - timedelta(days=int(config.get("dias_maximos", 45)))
    aceitos: dict[str, Item] = {}
    titulos: set[str] = set()
    for item in brutos:
        if item.data and item.data < limite:
            continue
        if not item.lugares:
            lugares = filtro.aceita(item.texto or item.titulo)
            if not lugares:
                continue
            item.lugares = lugares
        chave_titulo = normalizar(item.titulo)
        if item.id in aceitos or chave_titulo in titulos:
            continue  # a mesma notícia em vários veículos
        aceitos[item.id] = item
        titulos.add(chave_titulo)
    return list(aceitos.values()), erros


def resumo_actions(linhas: list[str]) -> None:
    caminho = os.environ.get("GITHUB_STEP_SUMMARY")
    if caminho:
        with open(caminho, "a", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--teste", action="store_true", help="não avisa nem salva o estado")
    ap.add_argument("--config", default=str(RAIZ / "config.yaml"))
    ap.add_argument("--estado", default=str(ESTADO))
    args = ap.parse_args(argv)

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    filtro = Filtro(config)
    itens, erros = coletar(config, filtro)
    itens.sort(key=lambda i: i.data or datetime.now(timezone.utc), reverse=True)

    caminho_estado = Path(args.estado)
    primeira = not caminho_estado.exists()
    estado = carregar_estado(caminho_estado)
    novos = [i for i in itens if i.id not in estado["vistos"]]

    print(f"{len(itens)} editais na região, {len(novos)} novos.")
    for e in erros:
        print(f"AVISO: fonte com problema: {e}", file=sys.stderr)
    for i in novos:
        print(f"- {i.titulo}\n  {i.link}\n  {' · '.join(dict.fromkeys([i.fonte, *i.lugares]))}")

    linhas = [f"## Monitor de editais", f"{len(itens)} editais na região, **{len(novos)} novos**.", ""]
    linhas += [f"- [{i.titulo}]({i.link}) · {i.fonte}" for i in novos[:50]]
    if erros:
        linhas += ["", "### Fontes com problema"] + [f"- {e}" for e in erros]
    resumo_actions(linhas)

    if args.teste:
        return 0

    pagina.gerar(itens, RAIZ / "docs")

    sucesso, falha = True, False
    if novos:
        if primeira:
            limite = int(config.get("avisos", {}).get("limite_primeira_execucao", 10))
            lote = novos[:limite]
            cabecalho = f"Monitor de editais ligado: {len(novos)} editais de professor abertos na região"
        else:
            lote = novos
            cabecalho = (f"{len(novos)} novo edital de professor na região" if len(novos) == 1
                         else f"{len(novos)} novos editais de professor na região")
        canais = [c for c in config.get("avisos", {}).get("canais", []) if avisos.canal_configurado(c)]
        if not canais:
            print("Nenhum canal de aviso configurado (veja o README). O estado não foi salvo "
                  "para que os editais sejam avisados quando um canal for configurado.", file=sys.stderr)
            return 0
        sucesso = False
        for canal in canais:
            try:
                avisos.CANAIS[canal](lote, cabecalho)
                sucesso = True
                print(f"Aviso enviado por {canal}.")
            except Exception as e:
                falha = True
                print(f"ERRO ao avisar por {canal}: {e}", file=sys.stderr)

    # Basta um canal funcionar para marcar como visto (evita repetir no que funcionou).
    if sucesso:
        agora = datetime.now(timezone.utc).isoformat()
        for i in novos:
            estado["vistos"][i.id] = {"titulo": i.titulo, "link": i.link, "visto_em": agora}
        salvar_estado(caminho_estado, estado, int(config.get("dias_maximos", 45)))
    return 1 if falha else 0


if __name__ == "__main__":
    sys.exit(main())
