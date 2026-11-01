# Evy 1.1

Uma assistente pessoal feita do zero, para **um único usuário**, que roda num notebook em casa.
Ela conversa por uma página web própria (instalável no celular como app), lembra do que
importa, sabe que dia e hora são, percebe quanto tempo passou entre as conversas e avisa
no celular na hora dos lembretes.

> Projeto pessoal e de aprendizado. Não é um produto: foi pensado para um só dono e cresce uma peça por vez.

## O que a Evy faz hoje

- **Conversa** com personalidade definida em um arquivo de texto.
- **Memória de longo prazo:** guarda fatos duradouros por conta própria ou a pedido, e apaga quando solicitada. Um painel no site mostra tudo o que ela guardou e permite apagar.
- **Noção de tempo:** sabe a data, o dia da semana e a hora, e percebe o intervalo desde a última mensagem para retomar assuntos pendentes com naturalidade.
- **Lembretes:** cria, lista e cancela por conversa, com painel no site.
- **Notificações no celular** na hora marcada, mesmo com o app fechado.
- **App instalável (PWA)**, publicado pelo Tailscale Funnel e protegido por pareamento de aparelho (cookie revogável).
- **Pareamento de aparelhos:** código de uso único gerado no servidor; painel para ver e revogar aparelhos.
- **Reserva automática entre modelos** do Gemini quando um deles falha ou atinge a cota.
- **Sobe sozinha** quando o servidor liga.

## Como funciona

```
 Celular (PWA)  ──HTTPS (Funnel)─────►  Servidor (notebook)
                                        ├─ Flask + waitress (só localhost)
                                        ├─ pareamento de aparelhos (cookie)
                                        ├─ cérebro: contexto + chamada do modelo
                                        ├─ ferramentas: memória e lembretes
                                        ├─ dados locais (arquivos)
                                        └─ verificador de lembretes ──► push
                                                      │
                                              API do Gemini (nuvem)
```

O servidor reconstrói a conversa a cada mensagem a partir dos arquivos locais, envia ao
modelo o histórico recente, as memórias e os lembretes, e permite que o modelo chame
ferramentas (guardar/esquecer fatos, criar/apagar lembretes) por chamada de funções.

## Tecnologias

- **Python 3** — Flask, waitress, `google-genai`, `pywebpush`, `python-dotenv`
- **Modelo:** família Gemini (Flash-Lite e Flash, com reserva automática) pela API do Google
- **Web:** HTML, CSS e JavaScript puros, com PWA (manifesto e service worker) e Web Push
- **Infra:** Linux Mint, `systemd`, Tailscale Funnel, Git

## Estrutura

```
servidor.py        rotas HTTP, autenticação e verificador de lembretes
cerebro.py         instruções, conversa com o modelo e persistência do histórico
ferramentas.py     funções que o modelo pode chamar
memoria.py         histórico, fatos e estado
lembretes.py       lembretes
dispositivos.py    pareamento de aparelhos (códigos, tokens, revogação)
parear.py          gera o código de pareamento (rodar no servidor)
push.py            notificações Web Push
tempo.py           fuso horário e contexto temporal
terminal.py        interface de terminal (depuração)
backup_manual.py   backup manual criptografado e validação da restauração
personalidade.txt  identidade da assistente
web/               página, tela de pareamento, estilos, app.js, service worker e manifesto
```

Os dados (`dados/`) e os segredos (`.env`) ficam **fora do Git**.

## Configuração

Variáveis no arquivo `.env` (nunca versionado):

| Variável | Para quê |
| --- | --- |
| `GEMINI_API_KEY` | chave da API do Gemini |
| `VAPID_PUBLICA` | chave pública para notificações push |
| `VAPID_CONTATO` | contato (`mailto:`) exigido pelo serviço de push |

A chave privada VAPID fica em `dados/vapid/private_key.pem`.

## Executando

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python terminal.py     # conversar pelo terminal
python servidor.py     # subir o servidor (porta 5000, somente localhost)
python parear.py       # gerar o código para parear um aparelho
python backup_manual.py criar  # backup manual; requer /var/backups/evy preparado
```

Em produção, o servidor roda como serviço `systemd` e é publicado com
`tailscale funnel`. **Nunca** abra a porta 5000 diretamente na internet: o acesso passa sempre pelo Funnel e pelo pareamento.

## Segurança e privacidade

- O servidor escuta só em `127.0.0.1`; o acesso externo passa pelo Tailscale Funnel. Com o Funnel, a página e a tela de pareamento são públicas; a API só responde a aparelhos pareados.
- Autenticação por pareamento: código de uso único (5 minutos) gerado no servidor, token revogável guardado só como hash e cookie `HttpOnly`, `Secure`, `SameSite=Strict`.
- O limite de tentativas de pareamento é global e só em memória (limitação conhecida; veja `PROJETO.md`).
- Os dados ficam no servidor, mas **o conteúdo de cada conversa é enviado à API do modelo**. Veja os termos do plano usado antes de contar algo sensível.
- Ferramentas que alteram o mundo devem **propor e esperar confirmação**.

## Roadmap

- [x] Conversa, personalidade, memória, tempo, lembretes, notificações, app instalável
- [x] Validar a coleta manual do backup e marcar `v1.0`
- [x] Acesso externo pelo Funnel, pareamento de aparelhos e reserva entre modelos (1.1)
- [ ] Automatizar o backup (cron)
- [ ] Integração com calendário (leitura primeiro; escrita com confirmação)
- [ ] Memória estruturada em SQLite, com busca e atualização de fatos
- [ ] Arquivo de conversas antigas com busca
- [ ] Abstração do provedor de IA

Veja [`PROJETO.md`](PROJETO.md) para o contexto completo: decisões, operação, problemas
conhecidos e próximos passos.

## Licença

Projeto pessoal, sem licença definida. Todos os direitos reservados ao autor.
