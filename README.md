# Monitor de editais para professores

Procura concursos e processos seletivos para **professores** na Região Central e no Vale do Rio Pardo (RS) duas vezes por dia e avisa o que for novo por **Telegram** e/ou **e-mail**. Roda sozinho no GitHub Actions, sem servidor e sem custo.

Também publica uma página com os editais abertos (GitHub Pages, pasta `docs/`).

## De onde vêm os editais

| Fonte | Como funciona |
|---|---|
| Google Notícias | Busca no RSS público por "concurso / processo seletivo / contratação emergencial + professor + nome do município". |
| PCI Concursos | Lê as listas `/concursos/sul/` e `/professores/` e fica só com os do RS. |
| Sites de editais | Páginas de editais de prefeituras e universidades: guarda os links que parecem edital de professor e avisa quando surge um novo. |

Um item só vira aviso se (1) fala de **professor/docente/magistério/educador**, (2) fala de **concurso/seleção/edital** e (3) cita um **município ou instituição da região**. O filtro ignora acentos e descarta homônimos de outros lugares, como *Santa Maria do Herval*, *Santa Maria de Jetibá*, *Rio Pardo de Minas* e *Vera Cruz/SP*.

Tudo isso fica em [`config.yaml`](config.yaml): municípios, instituições, palavras-chave, páginas monitoradas e canais de aviso.

## Como ligar

### 1. Telegram
1. No Telegram, fale com o **@BotFather**, mande `/newbot` e guarde o **token**.
2. Mande um "oi" para o seu bot novo.
3. Descubra o seu chat_id:
   ```bash
   pip install -r requirements.txt
   TELEGRAM_TOKEN=seu_token python -m monitor.telegram_chat_id
   ```
   (Para avisar num grupo, adicione o bot ao grupo, mande uma mensagem lá e rode de novo.)

### 2. E-mail (opcional)
Com Gmail, crie uma **senha de app** em <https://myaccount.google.com/apppasswords> (exige verificação em duas etapas). A senha normal da conta não funciona.

### 3. Secrets do repositório
Em **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Valor |
|---|---|
| `TELEGRAM_TOKEN` | token do BotFather |
| `TELEGRAM_CHAT_ID` | número que o passo 1 mostrou |
| `EMAIL_USUARIO` | seu e-mail (remetente) |
| `EMAIL_SENHA` | a senha de app |
| `EMAIL_PARA` | quem recebe (se vazio, vai para o próprio remetente) |
| `SMTP_HOST`, `SMTP_PORTA` | só se não for Gmail (padrão `smtp.gmail.com`, `465`) |

Basta configurar um dos canais. Canal sem secret é pulado.

### 4. Rodar
Em **Actions → Monitor de editais → Run workflow**. Depois disso ele roda sozinho às 9h e às 18h (horário de Brasília).

Na **primeira execução** ele não despeja tudo: manda um resumo com até 10 editais abertos e, dali em diante, só os novos. O que já foi avisado fica em `dados/vistos.json`.

### 5. Página (opcional)
Em **Settings → Pages**, escolha *Deploy from a branch*, branch `main`, pasta `/docs`.

## Rodar no computador

```bash
pip install -r requirements.txt
python -m monitor --teste   # mostra o que acharia, sem avisar nem salvar
python -m pytest -q         # testes
```

## Se algo parar de funcionar

- Sites mudam de endereço e de layout. Quando uma fonte falha, as outras continuam e o problema aparece no resumo da execução no Actions ("Fontes com problema").
- Para acrescentar uma prefeitura, adicione a página de editais dela em `fontes.paginas` no `config.yaml`.
- Se nenhum canal estiver configurado, o monitor não marca nada como visto, para não perder editais antes de você ligar os avisos.

## Licença

MIT. Feito por Júlia Roberta Quoos Alves · [ohtopico.com.br](https://ohtopico.com.br)
