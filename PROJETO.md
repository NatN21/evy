# PROJETO.md — Evy

> Documento de contexto do projeto. Serve para qualquer pessoa (ou assistente de IA)
> retomar o trabalho exatamente de onde parou, sem depender de uma conversa antiga.
> **Atualize a seção 2 a cada fase concluída e faça commit junto com o código.**

- **Dono do projeto:** Natan
- **Atualizado em:** outubro de 2026
- **Versão:** pré-1.0 (procedimento manual de backup implementado; faltam preparar o destino, validar a primeira coleta, marca `v1.0` e validação final)

---

## 1. O que é a Evy

A Evy é uma **assistente pessoal de um único usuário**, construída do zero em Python.
Ela conversa por uma página web própria (instalável no celular como app), lembra de
coisas sobre o dono, sabe que dia e hora são, percebe quanto tempo passou entre uma
conversa e outra, cria lembretes e avisa no celular na hora marcada.

**Objetivo de longo prazo:** uma agente pessoal autônoma e muito personalizada, com os
dados guardados no servidor dela (um notebook em casa) e um modelo de IA como
"mecanismo de raciocínio". O projeto também é, de propósito, uma forma de **aprender**
programação, Linux e arquitetura de sistemas, construindo tijolo por tijolo.

---

## 2. Estado atual

### Fases concluídas

| Fase | O que entregou |
| --- | --- |
| 0 | Notebook servidor com Linux, SSH com chave, sem suspender com a tampa fechada |
| 1 | Git, repositório privado, ambiente virtual, `.gitignore` protegendo segredos |
| 2 | Cérebro no terminal usando a API do Gemini (SDK `google-genai`) |
| 3 | Personalidade em arquivo de texto (`personalidade.txt`) |
| 4 | Memória: histórico da conversa + ficha de fatos sobre o dono |
| 5 | Servidor web (Flask + waitress) e página de chat |
| 6A | Tailscale (acesso privado, HTTPS) e serviço `systemd` que sobe sozinho |
| 6B | Página instalável como app (PWA: manifesto, ícones, service worker) |
| 7a | Noção de data, dia da semana, hora e tempo desde a última mensagem |
| 7b-1 | Ferramentas de memória: a Evy guarda e apaga fatos sozinha |
| 7b-2 | Painel "Memória" no site para ver e apagar o que ela guardou |
| 7c | Lembretes: a Evy cria e apaga por conversa; painel "Lembretes" no site |
| 7d | Notificações push no celular na hora do lembrete |

### Pendências para fechar a 1.0

1. **Validar o backup manual** de `dados/` e `.env` no armazenamento interno do servidor; a automação diária continua pendente.
2. **Marcar a versão no Git:** `git tag v1.0`.
3. **Teste do tempo:** contar à Evy um compromisso futuro, voltar depois da data com um simples "oi" e ver se ela retoma o assunto.
4. Limpar inscrições duplicadas de push, se houver (ver seção 11).

### Depois da 1.0

- **7e — Calendário:** leitura primeiro; escrita só com confirmação do dono (ver seção 13).
- Redesenho da página e afinamento do tom da personalidade (a cargo do dono).
- **Evy 2:** cérebro com memória estruturada em SQLite (ver seção 13).

---

## 3. Ambiente

| Peça | Detalhe |
| --- | --- |
| **YshBook** | Notebook principal. Linux Mint (XFCE). Usado para controlar o servidor por SSH e, no futuro, receber os backups. |
| **YhwBook** | Notebook servidor. Samsung, cerca de 4 GB de RAM (≈ 1,6 a 2,6 GiB livres), 2 CPUs, gráficos Intel UHD 610 (sem GPU dedicada), bastante armazenamento. Linux Mint (Cinnamon) em dual boot (300 GB Linux, 200 GB Windows). Fica sempre na tomada; o Mint é a primeira opção no boot. |
| **Celular** | Android (Redmi Note 13 4G). App da Evy instalado pelo Chrome. Tailscale instalado. |
| **Modelo de IA** | `gemini-3.5-flash-lite` pela API do Google (plano gratuito). |
| **Rede privada** | Tailscale; a Evy é publicada com `tailscale serve` (nunca `funnel`). |
| **Fuso** | `America/Sao_Paulo` |

O trabalho no servidor é feito **por SSH a partir do YshBook** (decisão do dono),
poupando a RAM do YhwBook.

---

## 4. Arquitetura

```
 Celular (app/PWA)                       YhwBook (servidor)
 ┌──────────────┐   HTTPS (Tailscale)   ┌────────────────────────────────────────┐
 │ web/         │ ────────────────────► │ servidor.py  (Flask + waitress,        │
 │ index.html   │                       │               127.0.0.1:5000)          │
 │ app.js       │ ◄──── push ────────── │   ├─ cerebro.py   monta contexto,      │
 │ sw.js        │   (serviço de push    │   │                chama o Gemini      │
 └──────────────┘    do Google)         │   ├─ ferramentas.py  (as "mãos")       │
                                        │   ├─ memoria.py / lembretes.py         │
                                        │   ├─ tempo.py  /  push.py              │
                                        │   └─ verificador de lembretes (20 s)   │
                                        │              │                         │
                                        │         dados/ (arquivos locais)       │
                                        └──────────────┼─────────────────────────┘
                                                       ▼
                                          API do Gemini (nuvem)
```

### Fluxo de uma mensagem

1. A página envia `POST /api/mensagem` com a senha no cabeçalho `X-Evy-Senha`.
2. O servidor valida a senha, pega a trava (`trava`) e chama `criar_conversa()`.
3. `criar_conversa()` **reconstrói a conversa a cada mensagem a partir do disco**:
   histórico salvo (até 30 mensagens) + instruções do sistema.
4. As instruções do sistema são: `personalidade.txt` + `REGRAS_DE_TEMPO` +
   `REGRAS_DE_MEMORIA` + `REGRAS_DE_LEMBRETES` + fatos numerados + lista de lembretes.
5. `responder()` prefixa a mensagem com uma linha `[Contexto: dia da semana, data,
   hora; tempo desde a última mensagem]` e envia ao Gemini.
6. O Gemini pode chamar ferramentas (`guardar_fato`, `esquecer_fato`,
   `criar_lembrete`, `apagar_lembrete`); o SDK executa a função Python e devolve o
   resultado ao modelo (chamada automática de funções).
7. Erros temporários (500, 503, 504) são tentados de novo após 3, 8 e 15 segundos.
8. Depois da resposta: salva o histórico (somente texto, sem os bastidores das
   ferramentas) e o horário da última mensagem.
9. O endpoint de histórico remove a linha `[Contexto: ...]` antes de exibir na página.

### Fluxo de um lembrete

1. A Evy chama `criar_lembrete(texto, "AAAA-MM-DD HH:MM")` e o lembrete vai para `dados/lembretes.json`.
2. Uma thread do servidor verifica a cada 20 s os lembretes vencidos e ainda não avisados.
3. Para cada um, `push.enviar()` manda o aviso (criptografado, prioridade alta, validade de 24 h) a todos os aparelhos inscritos.
4. Se ao menos um aparelho aceitou, o lembrete é marcado como `avisado`. Se estiver mais de 10 minutos atrasado, o título é "Lembrete atrasado".
5. Lembretes avisados há mais de 2 dias são removidos automaticamente.
6. Inscrições que o serviço de push informa como expiradas (404/410) são descartadas.

---

## 5. Estrutura de arquivos

```
evy/
├── servidor.py          # HTTP: rotas, autenticação, verificador de lembretes
├── cerebro.py           # monta instruções, cria a conversa, chama o Gemini, salva
├── ferramentas.py       # funções que o modelo pode chamar (as "mãos")
├── memoria.py           # histórico, fatos, estado (última mensagem)
├── lembretes.py         # CRUD e resumos dos lembretes
├── push.py              # inscrições e envio de notificações (Web Push / VAPID)
├── tempo.py             # fuso, dias da semana, linha [Contexto: ...]
├── terminal.py          # interface de terminal (debug); comandos /lembrar, /fatos...
├── backup_manual.py     # backup local criptografado e validação em diretório temporário
├── personalidade.txt    # quem a Evy é (identidade e jeito de falar)
├── requirements.txt
├── .gitignore
├── README.md
├── PROJETO.md
└── web/
    ├── index.html
    ├── estilo.css
    ├── app.js           # chat, painéis Memória e Lembretes, avisos
    ├── sw.js            # service worker: instalação, push, clique na notificação
    ├── manifest.json
    ├── icone-192.png
    └── icone-512.png
```

---

## 6. Dados e segredos

Tudo abaixo vive **só no servidor** e **fica fora do Git** (`.gitignore`).

| Caminho | Conteúdo |
| --- | --- |
| `.env` | `GEMINI_API_KEY`, `EVY_SENHA`, `VAPID_PUBLICA`, `VAPID_CONTATO` (permissão `600`) |
| `dados/historico.json` | últimas 30 mensagens (texto) |
| `dados/fatos.txt` | memória de longo prazo, um fato por linha |
| `dados/estado.json` | horário da última mensagem do dono |
| `dados/lembretes.json` | lembretes (`id`, `texto`, `quando`, `criado`, `avisado`) |
| `dados/inscricoes.json` | aparelhos inscritos para receber push |
| `dados/vapid/` | chaves VAPID (`private_key.pem`, `public_key.pem`) |
| `venv/` | ambiente virtual Python |

**Nunca** colar chaves, senha, endereço do Tailscale ou e-mails em conversas, issues
ou commits.

---

## 7. API HTTP

Todas as rotas `/api/*` exigem o cabeçalho `X-Evy-Senha`.

| Método e rota | Função |
| --- | --- |
| `GET /` | página do chat |
| `GET /web/<arquivo>` | arquivos estáticos |
| `GET /manifest.webmanifest` | manifesto do PWA |
| `GET /sw.js` | service worker (servido na raiz para ter escopo `/`) |
| `GET /api/historico` | mensagens (sem a linha `[Contexto: ...]`) |
| `POST /api/mensagem` | envia mensagem `{mensagem}`, devolve `{resposta}` |
| `GET /api/memoria` | lista os fatos |
| `POST /api/memoria/apagar` | apaga um fato pelo texto exato `{fato}` |
| `GET /api/lembretes` | lista lembretes para o painel |
| `POST /api/lembretes/apagar` | apaga lembrete por `{id}` |
| `GET /api/push/chave` | chave pública VAPID |
| `POST /api/push/inscrever` | registra a inscrição do aparelho |
| `POST /api/push/testar` | envia um aviso de teste |

---

## 8. Ferramentas da Evy

| Ferramenta | O que faz |
| --- | --- |
| `guardar_fato(fato)` | guarda um fato duradouro (ignora duplicados) |
| `esquecer_fato(numero)` | apaga um fato pelo número na lista numerada |
| `criar_lembrete(texto, quando)` | cria lembrete; recusa horários no passado |
| `apagar_lembrete(id_lembrete)` | cancela um lembrete |

Regras de comportamento (no código, em `cerebro.py`): só guardar o que é duradouro e
útil; nunca dados sensíveis sem pedido claro; eventos futuros com **data exata**;
avisar o que guardou, de forma natural; nunca afirmar que fez algo sem ter usado a
ferramenta; perguntar quando faltar dia ou hora de um lembrete.

---

## 9. Segurança

- O servidor escuta **só em `127.0.0.1`**; quem expõe é o `tailscale serve` (rede privada).
- **Nunca** usar `tailscale funnel`, abrir porta no roteador ou ligar `debug=True`.
- Autenticação por senha única (`EVY_SENHA`), comparada com `hmac.compare_digest`.
- Servidor de produção: `waitress`.
- `.env` com permissão `600`; `dados/` e as chaves VAPID nunca vão ao Git.
- O painel de memória dá ao dono **controle e visibilidade** sobre o que a Evy guarda sozinha.
- Ações com efeito no mundo (futuro: calendário) devem **propor e esperar confirmação**.

---

## 10. Operação (cola rápida)

No servidor (via SSH):

```
sudo systemctl restart evy                 # depois de mudar arquivos .py
systemctl status evy                       # deve mostrar active (running)
journalctl -u evy -n 40 --no-pager         # ver o que a Evy registrou
sudo systemctl stop evy                    # antes de usar o terminal.py
sudo systemctl start evy                   # depois de usar o terminal.py
tailscale serve status                     # endereço HTTPS da Evy
```

- Mudou algo em `web/`? Basta recarregar a página; se o app instalado não atualizar, fechar e abrir de novo (às vezes duas vezes).
- **Não** usar `terminal.py` e o servidor ao mesmo tempo: os dois gravam o mesmo histórico.
- Antes de cada commit: `git status` e conferir que `.env` e `dados/` **não** aparecem.
- Ambiente: `cd ~/evy && source venv/bin/activate`.

### Backup manual

O script `backup_manual.py` cria um arquivo `tar.zst` criptografado com GPG fora do
checkout, incluindo `.env`, `dados/`, as chaves VAPID e as inscrições push. Antes da
coleta, ele verifica o serviço `evy`, interrompe-o se estiver ativo, recusa a coleta se
encontrar `servidor.py` ou `terminal.py` concorrente e restaura o serviço ao terminar.

Pré-requisito: o diretório `/var/backups/evy/` deve existir, pertencer ao usuário da
Evy e ter permissão `700`. O script não cria esse diretório automaticamente.

```bash
python3 backup_manual.py criar
python3 backup_manual.py verificar /var/backups/evy/ARQUIVO.gpg
```

O primeiro comando solicita a senha do GPG interativamente, valida a descriptografia e
os hashes antes de publicar o arquivo definitivo. A senha deve ser guardada fora do
servidor. A primeira coleta real ainda não foi executada; a automação diária será
considerada somente depois da validação manual e do teste de restauração.

---

## 11. Problemas conhecidos e soluções

| Sintoma | Causa provável | O que fazer |
| --- | --- | --- |
| `404 NOT_FOUND ... model no longer available` | modelo aposentado pelo Google | trocar `MODELO` em `cerebro.py` (IDs usados: `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`) |
| `503 UNAVAILABLE ... high demand` | pico de demanda do Google | já há 3 novas tentativas; se persistir, esperar |
| `429` | cota do plano gratuito esgotada | esperar; ver limites atuais na página do Google (relatos indicam limites diários por modelo) |
| `Registration failed - push service error` | falha no cadastro com o serviço de push do Google | usar o Chrome em aba normal; atualizar Chrome e Google Play Services; liberar bateria e inicialização automática (Xiaomi); testar outra rede; desligar DNS privado; limpar dados do site |
| Dois avisos por lembrete | dois navegadores inscritos | `rm dados/inscricoes.json` no servidor e reativar os avisos só no aparelho desejado |
| Chrome trata os avisos como spam | filtro de notificações silenciosas | marcar como confiável |
| Botões novos não aparecem | página/app em cache | fechar e abrir o app mais de uma vez |
| A Evy comenta o tempo demais | instruções duplicadas | manter regras de tempo/memória/lembretes **só no código**; `personalidade.txt` deve falar de identidade e jeito de ser |

---

## 12. Decisões de projeto (e por quê)

- **Interface web própria, não Telegram/WhatsApp:** o dono não usa o Telegram; WhatsApp exigiria API oficial (burocracia) ou bibliotecas não oficiais (risco de banir o número).
- **Notebook como servidor, cérebro por API:** 4 GB de RAM não sustentam um modelo local bom; a API deixa o servidor leve.
- **Tailscale em vez de expor à internet:** a Evy guarda memória pessoal e terá acesso à agenda; exposição pública seria risco desnecessário. Os avisos **não** dependem do Tailscale (viajam pelo serviço de push do Google).
- **Linux Mint Cinnamon com dual boot:** escolha do dono; o Windows ficou como reserva.
- **Conversa reconstruída a cada mensagem a partir do disco:** o disco é a fonte da verdade, então apagar memória pelo painel vale já na mensagem seguinte.
- **Linha `[Contexto: ...]` em cada mensagem:** dá noção de tempo ao modelo sem estado extra.
- **Regras operacionais no código, personalidade no arquivo:** evita duas vozes mandando a mesma coisa.
- **Memória em texto simples por enquanto:** com poucas dezenas de fatos, mandar tudo é aceitável; SQLite entra quando a memória crescer.
- **Modelo `gemini-3.5-flash-lite` no desenvolvimento:** o `gemini-3.8-flash` tem, segundo relatos, limite diário muito baixo no plano gratuito.
- **Segurança de ações:** ferramentas que alteram o mundo devem propor e pedir confirmação.

---

## 13. Roadmap

### 13.1 Fechar a 1.0
Backup → `git tag v1.0` → teste do tempo (seção 2).

### 13.2 Fase 7e — Calendário (Google Calendar)
- Projeto no Google Cloud, tela de consentimento, OAuth.
- **Primeiro só leitura** (a Evy enxerga a agenda).
- Depois escrita, **sempre propondo e esperando o "sim"** do dono.
- Atenção à privacidade: o que a Evy ler da agenda vai ao Google junto com a conversa.

### 13.3 Evy 2 — cérebro com memória estruturada (direção proposta)

Ideia central: **o banco local é o arquivo da Evy; o modelo é o especialista que ela
consulta.** Em vez de mandar a memória inteira, o cérebro busca localmente o que é
relevante e envia só isso.

Ordem sugerida, **uma peça por vez, sem refatorar tudo de uma vez**:

1. **SQLite para a memória**, com tipos (identidade, preferências, pessoas, projetos, objetivos, eventos, decisões) e **atualização** de fatos (não só empilhar).
2. **Arquivo de conversas antigas** com busca por texto (SQLite FTS5), para a Evy achar "aquilo que falamos mês passado".
3. **Montador de contexto:** histórico recente + memórias relevantes + lembretes + estado.
4. **Laço de agente com confirmação:** hoje a chamada automática de funções do SDK já faz o ciclo "chamar ferramenta → observar → decidir"; um laço próprio só se justifica quando precisarmos de confirmação humana, planejamento em etapas ou ferramentas perigosas.
5. **Abstração de provedor de IA** (Gemini hoje; outros depois), mantendo o resto da Evy independente do modelo.
6. **Ollama, se algum dia, só para tarefas pequenas** (busca por significado, classificação, reserva offline), nunca como cérebro principal neste hardware.
7. Separar `personalidade.txt` de um arquivo de comportamento operacional, quando a Evy ganhar poder real.

### 13.4 Ideias adiadas ou descartadas
- Telegram e WhatsApp como interface.
- Ollama como cérebro principal (hardware insuficiente).
- Exposição pública do servidor.
- Autonomia total sem confirmação.
- Conversas proativas (a Evy puxar assunto sozinha): possível no futuro com verificador + push, mas só depois do backup e do calendário.

---

## 14. Privacidade (leitura honesta)

- Os **dados ficam no servidor**, mas **a cada mensagem** vão ao Google: as últimas 30 mensagens, os fatos guardados e os lembretes.
- No plano gratuito da API, o Google pode usar esse conteúdo para melhorar seus produtos (conferir os termos atuais). Um modelo na nuvem **não torna nada 100% privado**.
- Formas de reduzir a exposição: guardar só o necessário (a Evy já evita dados sensíveis), enviar apenas memórias relevantes (Evy 2), não contar à Evy o que não deve sair da máquina, e, se a privacidade passar a pesar mais, avaliar um plano pago com termos diferentes.
- O conteúdo das notificações viaja criptografado entre o servidor e o aparelho.

---

## 15. Como colaborar neste projeto (para assistentes de IA)

- Responder em português do Brasil, em tom caloroso e próximo, com analogias quando ajudarem.
- O dono está **aprendendo**: explicar o porquê, a menos que ele peça "passos exatos"; nesse caso, dar os passos e comandos exatos, na ordem.
- **Mudanças pequenas e testáveis**, uma fase por vez, cada uma com "pronto quando" e commit.
- Ao substituir um arquivo inteiro, avisar; preferir remendos pequenos quando possível, com `grep` para conferir.
- Nunca pedir nem aceitar colagem de chaves, senhas ou endereços privados.
- Conferir sempre que `.env` e `dados/` não aparecem no `git status`.
- Respostas enxutas: a cota do plano gratuito do assistente é limitada.
- Discordar com gentileza quando fizer sentido e apontar riscos (privacidade, segurança, custo).
- Verificar na documentação atual o que muda com frequência (nomes de modelos, limites de cota, comandos do Tailscale).
