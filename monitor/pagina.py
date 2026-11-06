"""Gera docs/index.html (GitHub Pages) com os editais abertos na região."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .fontes import Item

MODELO = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Editais para professores</title>
<meta name="description" content="Concursos e processos seletivos para professores na Região Central e no Vale do Rio Pardo (RS).">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Lexend:wght@400;600&family=Sniglet:wght@800&display=swap" rel="stylesheet">
<style>
:root {{ --papel:#fff; --fundo:#f4f4f2; --tinta:#111; --tinta2:#4a4a4a; --linha:#d9d9d6;
  --verde:#166c40; --verde-suave:#e3f1e8; --cinza:#545a56; --grifo:#fff36b; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --papel:#1b1d1c; --fundo:#111312; --tinta:#f2f2ef; --tinta2:#c9cbc8; --linha:#3a3d3b;
  --verde:#5cc28a; --verde-suave:#1f3a2b; --cinza:#a5aaa6; --grifo:#6b6410; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; font-family:Lexend,system-ui,sans-serif; color:var(--tinta); background:var(--fundo);
  background-image:radial-gradient(var(--linha) 1.2px, transparent 1.2px); background-size:18px 18px; line-height:1.5 }}
main {{ max-width:860px; margin:32px auto; padding:0 16px }}
.janela {{ background:var(--papel); border:2.5px solid var(--tinta); border-radius:28px; box-shadow:8px 8px 0 var(--tinta); overflow:hidden }}
.barra {{ display:flex; align-items:center; gap:8px; padding:12px 20px; border-bottom:2px solid var(--tinta);
  font-family:Sniglet,sans-serif; letter-spacing:.12em; font-size:13px }}
.barra i {{ width:12px; height:12px; border-radius:50%; border:1.5px solid var(--tinta); display:inline-block }}
.barra span {{ margin-left:auto }}
.conteudo {{ padding:24px 28px 32px }}
h1 {{ font-family:Sniglet,sans-serif; font-weight:800; text-transform:uppercase; letter-spacing:.06em; font-size:clamp(26px,5vw,40px); margin:0 0 8px; line-height:1.1 }}
mark {{ background:var(--grifo); color:inherit; padding:0 .2em }}
.sub {{ color:var(--tinta2); margin:0 0 20px }}
.pilulas {{ display:flex; flex-wrap:wrap; gap:8px; margin:0 0 20px }}
.pilula {{ border:1.5px solid var(--tinta); border-radius:999px; padding:3px 12px; font-size:13px; background:var(--papel) }}
.pilula.verde {{ background:var(--verde-suave); border-color:var(--verde); color:var(--tinta) }}
ul {{ list-style:none; padding:0; margin:0 }}
li {{ border:1.5px solid var(--linha); border-radius:18px; padding:14px 18px; margin:0 0 12px }}
li a {{ color:var(--verde); font-weight:600; text-decoration:none }}
li a:hover {{ text-decoration:underline }}
.det {{ color:var(--tinta2); font-size:14px; margin-top:4px }}
.meta {{ color:var(--cinza); font-size:13px; margin-top:6px; display:flex; flex-wrap:wrap; gap:6px }}
.vazio {{ color:var(--tinta2) }}
footer {{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px; margin-top:28px;
  font-family:Sniglet,sans-serif; letter-spacing:.1em; font-size:13px }}
footer a {{ color:var(--tinta) }}
</style>
</head>
<body>
<main>
<div class="janela">
  <div class="barra"><i></i><i></i><i></i><span>EDITAIS.HTML</span></div>
  <div class="conteudo">
    <h1>Editais para <mark>professores</mark></h1>
    <p class="sub">Concursos e processos seletivos na Região Central e no Vale do Rio Pardo (RS). Atualizado em {atualizado}.</p>
    <div class="pilulas"><span class="pilula verde">{total}</span><span class="pilula">Google Notícias</span><span class="pilula">PCI Concursos</span><span class="pilula">Sites de editais</span></div>
    {lista}
    <footer><span>JÚLIA ROBERTA QUOOS ALVES</span><a class="pilula" href="https://ohtopico.com.br">ohtopico.com.br</a></footer>
  </div>
</div>
</main>
</body>
</html>
"""


def _li(item: Item) -> str:
    det = f'<div class="det">{html.escape(item.detalhes)}</div>' if item.detalhes else ""
    meta = [item.fonte]
    if item.data:
        meta.append(item.data.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y"))
    meta += item.lugares[:3]
    meta_html = " · ".join(f"<span>{html.escape(m)}</span>" for m in meta)
    return (f'<li><a href="{html.escape(item.link, quote=True)}" rel="noopener">{html.escape(item.titulo)}</a>'
            f'{det}<div class="meta">{meta_html}</div></li>')


def gerar(itens: list[Item], pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(timezone.utc).astimezone(ZoneInfo("America/Sao_Paulo"))
    total = f"{len(itens)} edital" if len(itens) == 1 else f"{len(itens)} editais"
    lista = ("<ul>" + "".join(_li(i) for i in itens) + "</ul>") if itens else \
        '<p class="vazio">Nenhum edital de professor encontrado nos últimos dias.</p>'
    (pasta / "index.html").write_text(
        MODELO.format(atualizado=agora.strftime("%d/%m/%Y às %Hh%M"), total=total, lista=lista),
        encoding="utf-8")
    (pasta / "editais.json").write_text(json.dumps([
        {"titulo": i.titulo, "link": i.link, "fonte": i.fonte, "detalhes": i.detalhes,
         "lugares": i.lugares, "data": i.data.isoformat() if i.data else None}
        for i in itens], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
