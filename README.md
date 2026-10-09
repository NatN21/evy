# Evy 1.0

Uma assistente pessoal feita do zero, para **um único usuário**, que roda num notebook em casa.
Ela conversa por uma página web própria (instalável no celular como app), lembra do que
importa, sabe que dia e hora são, percebe quanto tempo passou entre as conversas e avisa
no celular na hora dos lembretes.

> Projeto pessoal e de aprendizado. Não é um produto: foi pensado para um só dono, numa
> rede privada, e cresce uma peça por vez.

## O que a Evy faz hoje

- **Conversa** com personalidade definida em um arquivo de texto.
- **Memória de longo prazo:** guarda fatos duradouros por conta própria ou a pedido, e apaga quando solicitada. Um painel no site mostra tudo o que ela guardou e permite apagar.
- **Noção de tempo:** sabe a data, o dia da semana e a hora, e percebe o intervalo desde a última mensagem para retomar assuntos pendentes com naturalidade.
- **Lembretes:** cria, lista e cancela por conversa, com painel no site.
- **Notificações no celular** na hora marcada, mesmo com o app fechado.
- **App instalável (PWA)**, acessível só pela rede privada do dono.
- **Sobe sozinha** quando o servidor liga.

## Como funciona

```
 Celular (PWA)  ──HTTPS (Tailscale)──►  Servidor (notebook)
                                        ├─ Flask + waitress (só localhost)
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
- **Modelo:** família Gemini Flash-Lite pela API do Google
- **Web:** HTML, CSS e JavaScript puros, com PWA (manifesto e service worker) e Web Push
- **Infra:** Linux Mint, `systemd`, Tailscale, Git

## Estrutura

```
servidor.py        rotas HTTP, autenticação e verificador de lembretes
cerebro.py         instruções, conversa com o modelo e persistência do histórico
ferramentas.py     funções que o modelo pode chamar
memoria.py         histórico, fatos e estado
lembretes.py       lembretes
push.py            notificações Web Push
tempo.py           fuso horário e contexto temporal
terminal.py        interface de terminal (depuração)
personalidade.txt  identidade da assistente
web/               página, estilos, app.js, service worker e manifesto
```

Os dados (`dados/`) e os segredos (`.env`) ficam **fora do Git**.

## Configuração

Variáveis no arquivo `.env` (nunca versionado):

| Variável | Para quê |
| --- | --- |
| `GEMINI_API_KEY` | chave da API do Gemini |
| `EVY_SENHA` | senha de acesso à página e à API |
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
```

Em produção, o servidor roda como serviço `systemd` e é publicado na rede privada com
`tailscale serve`. **Nunca** exponha a porta diretamente à internet.

## Segurança e privacidade

- O servidor escuta só em `127.0.0.1`; o acesso externo é feito por uma rede privada (Tailscale).
- Autenticação por senha única, comparada em tempo constante.
- Os dados ficam no servidor, mas **o conteúdo de cada conversa é enviado à API do modelo**. Veja os termos do plano usado antes de contar algo sensível.
- Ferramentas que alteram o mundo devem **propor e esperar confirmação**.

## Roadmap

- [x] Conversa, personalidade, memória, tempo, lembretes, notificações, app instalável
- [ ] Backup automático dos dados e marca `v1.0`
- [ ] Integração com calendário (leitura primeiro; escrita com confirmação)
- [ ] Memória estruturada em SQLite, com busca e atualização de fatos
- [ ] Arquivo de conversas antigas com busca
- [ ] Abstração do provedor de IA

Veja [`PROJETO.md`](PROJETO.md) para o contexto completo: decisões, operação, problemas
conhecidos e próximos passos.

## Licença

Projeto pessoal, sem licença definida. Todos os direitos reservados ao autor.
