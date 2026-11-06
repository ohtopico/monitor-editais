from datetime import datetime, timezone
from pathlib import Path

import yaml

from monitor import __main__ as app
from monitor.avisos import corpo_email, mensagens_telegram
from monitor.fontes import Item, google_noticias, paginas, pci
from monitor.texto import Filtro

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
F = Filtro(CONFIG)


# --- filtro ----------------------------------------------------------------
def test_aceita_professor_da_regiao():
    assert F.aceita("Prefeitura de Candelária abre processo seletivo para professores") == ["Candelária"]
    assert F.aceita("UFSM abre concurso para docentes do magistério superior")


def test_recusa_outro_cargo_ou_lugar():
    assert F.aceita("Prefeitura de Santa Maria abre concurso para enfermeiros") is None
    assert F.aceita("Prefeitura de Canoas abre concurso para professor") is None


def test_homonimos_de_outros_estados():
    assert F.aceita("Santa Maria de Jetibá abre processo seletivo para professores") is None
    assert F.aceita("Prefeitura de Santa Maria do Herval abre concurso para professor") is None
    assert F.aceita("Concurso para professor em Rio Pardo de Minas") is None
    assert F.aceita("Vera Cruz/SP abre concurso para professor") is None
    assert F.aceita("Sobradinho abre processo seletivo para professores") is None
    assert F.aceita("Prefeitura de Sobradinho abre processo seletivo para professores")
    assert F.aceita("Concurso Sobradinho/RS tem vagas para professor")


def test_acentos_nao_importam():
    assert F.aceita("PROCESSO SELETIVO PROFESSOR VENANCIO AIRES")
    assert F.aceita("Seleção de educadores em São João do Polêsine")


# --- Google Notícias -------------------------------------------------------
RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Prefeitura de Agudo abre seleção para professores - Gaúcha ZH</title>
<link>https://news.google.com/a1</link><pubDate>Thu, 05 Nov 2026 12:00:00 GMT</pubDate>
<description>&lt;a&gt;Vagas para professor&lt;/a&gt;</description><source url="https://gzh">Gaúcha ZH</source></item>
<item><title>Prefeitura de Agudo abre seleção para professores - Diário de SM</title>
<link>https://news.google.com/a2</link><pubDate>Thu, 05 Nov 2026 13:00:00 GMT</pubDate>
<source url="https://dsm">Diário de SM</source></item>
<item><title>Antiga: concurso professor Agudo - X</title><link>https://news.google.com/a3</link>
<pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate><source url="x">X</source></item>
</channel></rss>"""


def test_rss_e_deduplicacao(monkeypatch):
    itens = google_noticias.ler_rss(RSS)
    assert itens[0].titulo == "Prefeitura de Agudo abre seleção para professores"
    assert itens[0].fonte == "Google Notícias · Gaúcha ZH"

    cfg = {**CONFIG, "fontes": {"google_noticias": {"ativo": True}}}
    monkeypatch.setattr(google_noticias, "coletar", lambda c: itens)
    aceitos, erros = app.coletar(cfg, F)
    assert [i.link for i in aceitos] == ["https://news.google.com/a1"]  # duplicada e antiga saem
    assert erros == []


def test_buscas_cobrem_todos_os_municipios():
    buscas = " ".join(google_noticias.montar_buscas(CONFIG))
    for m in CONFIG["municipios"]:
        assert f'"{m}"' in buscas


# --- PCI Concursos -----------------------------------------------------------
PCI = """<html><body>
<div class="na"><div class="ca"><a href="/noticias/ufsm-rs-abre-concurso-para-professores"
 title="UFSM - RS abre concurso para professores do magistério superior">UFSM</a></div>
<div class="cc">RS</div><div class="cd">6 vagas até R$ 13.753,98<br>Professor assistente<br><span>Superior</span></div>
<div class="ce"><span>02/12/2026</span></div></div>
<div class="na"><div class="ca"><a href="/noticias/prefeitura-de-canoas" title="Prefeitura de Canoas - RS abre concurso">Prefeitura de Canoas</a></div>
<div class="cc">RS</div><div class="cd">76 vagas<br>Professor de Educação Básica</div><div class="ce"><span>17/11/2026</span></div></div>
<div class="na"><div class="ca"><a href="/noticias/santa-maria-pr" title="Prefeitura de Santa Maria do Oeste - PR abre concurso">Santa Maria do Oeste</a></div>
<div class="cc">PR</div><div class="cd">Professor</div><div class="ce">10/11/2026</div></div>
</body></html>"""


def test_pci():
    itens = pci.ler_pagina(PCI, "https://www.pciconcursos.com.br/professores/")
    assert len(itens) == 2  # o do PR sai já no parser
    ufsm = itens[0]
    assert ufsm.link == "https://www.pciconcursos.com.br/noticias/ufsm-rs-abre-concurso-para-professores"
    assert "inscrições até 02/12/2026" in ufsm.detalhes
    assert F.aceita(ufsm.texto)
    assert F.aceita(itens[1].texto) is None  # Canoas não é da região


def test_pci_modo_generico():
    html = '<div><a href="/noticias/x" title="Prefeitura de Itaara - RS abre processo seletivo">Itaara</a> RS Professor</div>'
    itens = pci.ler_pagina(html, "https://www.pciconcursos.com.br/concursos/sul/")
    assert len(itens) == 1 and F.aceita(itens[0].texto)


# --- páginas -------------------------------------------------------------------
def test_paginas():
    html = """<a href="/edital-05-2026-processo-seletivo-professores.pdf">Edital 05/2026</a>
    <a href="/edital-06">Concurso para motorista</a><a href="#topo">Professor</a>"""
    itens = paginas.ler_pagina(html, "https://www.candelaria.rs.gov.br/editais", "Prefeitura de Candelária", F)
    assert [i.link for i in itens] == ["https://www.candelaria.rs.gov.br/edital-05-2026-processo-seletivo-professores.pdf"]
    assert itens[0].lugares == ["Prefeitura de Candelária"]


# --- avisos e estado -------------------------------------------------------------
def _item(n):
    return Item(titulo=f"Edital <{n}>", link=f"https://ex.com/{n}", fonte="Teste", detalhes="5 vagas",
                lugares=["agudo"], data=datetime.now(timezone.utc))


def test_telegram_divide_e_escapa():
    msgs = mensagens_telegram([_item(i) for i in range(80)], "Novos editais")
    assert len(msgs) > 1 and all(len(m) <= 4096 for m in msgs)
    assert "&lt;0&gt;" in msgs[0]


def test_email():
    texto, corpo = corpo_email([_item(1)], "1 novo edital")
    assert "https://ex.com/1" in texto and "&lt;1&gt;" in corpo


def test_fluxo_completo(tmp_path, monkeypatch):
    enviados = []
    monkeypatch.setattr(app, "RAIZ", tmp_path)
    monkeypatch.setattr(app.avisos, "canal_configurado", lambda c: c == "telegram")
    monkeypatch.setitem(app.avisos.CANAIS, "telegram", lambda itens, cab: enviados.append((len(itens), cab)))
    lote = [_item(i) for i in range(15)]
    monkeypatch.setattr(app, "coletar", lambda c, f: (list(lote), []))
    estado = tmp_path / "vistos.json"

    assert app.main(["--estado", str(estado), "--config", str(RAIZ / "config.yaml")]) == 0
    assert enviados[-1][0] == 10 and "ligado" in enviados[-1][1]  # 1ª execução: só resumo
    assert (tmp_path / "docs" / "index.html").exists()

    assert app.main(["--estado", str(estado), "--config", str(RAIZ / "config.yaml")]) == 0
    assert len(enviados) == 1  # nada novo, nada enviado

    lote.append(_item(99))
    assert app.main(["--estado", str(estado), "--config", str(RAIZ / "config.yaml")]) == 0
    assert enviados[-1] == (1, "1 novo edital de professor na região")


def test_sem_canal_nao_salva_estado(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "RAIZ", tmp_path)
    monkeypatch.setattr(app.avisos, "canal_configurado", lambda c: False)
    monkeypatch.setattr(app, "coletar", lambda c, f: ([_item(1)], []))
    estado = tmp_path / "vistos.json"
    assert app.main(["--estado", str(estado), "--config", str(RAIZ / "config.yaml")]) == 0
    assert not estado.exists()
