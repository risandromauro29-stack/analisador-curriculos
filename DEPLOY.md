# Deploy do Auditor de Ponto (webapp)

A webapp (`webapp/`) é um site Flask com login multiusuário em cima do
`ponto_auditor`: cada usuário logado envia um PDF de Cartão Ponto, o site
processa e guarda o resultado (painel + resumo) pra consultar depois.

Testada localmente de ponta a ponta (login → upload → painel → gestão de
usuários) antes deste guia — ver `webapp/` e os prints trocados na conversa.

## Passo a passo (Render, grátis)

Render foi escolhido por ter o deploy mais simples: conecta no GitHub e
publica a cada push, sem mexer em servidor.

### 1. Banco de dados

O disco do Render Free é **efêmero** — some a cada deploy. Como o site
guarda usuários e o histórico de auditorias no banco, use um Postgres
gerenciado (fora do disco do serviço):

- **Neon** (neon.tech) — Postgres grátis "para sempre" no free tier, é o
  mais simples de começar.
- Ou o Postgres gerenciado do próprio Render (grátis, mas expira em 30
  dias — só use se for testar por pouco tempo).

Crie o banco, copie a *connection string* (algo como
`postgresql://usuario:senha@host/banco`).

### 2. Criar o Web Service no Render

1. [dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**.
2. Conecte a conta GitHub e selecione este repositório.
3. **Environment**: `Docker` (Render detecta o `Dockerfile` sozinho).
4. **Instance Type**: Free.
5. Em **Environment Variables**, adicione (ver `.env.example`):

   | Nome | Valor |
   |---|---|
   | `SECRET_KEY` | gere com `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `DATABASE_URL` | a connection string do Neon/Postgres |
   | `ADMIN_EMAIL` | seu e-mail (primeiro login) |
   | `ADMIN_SENHA` | uma senha forte (troque depois de logar) |
   | `ADMIN_NOME` | seu nome |

6. **Create Web Service**. O primeiro build demora alguns minutos.

### 3. Primeiro acesso

Abra a URL que o Render deu (`https://seu-app.onrender.com`), entre com
`ADMIN_EMAIL`/`ADMIN_SENHA`. Vá em **Usuários** (menu superior) pra criar
os logins de quem mais vai usar — a senha de cada um é gerada na hora e
mostrada só uma vez, então copie e envie por um canal seguro (WhatsApp
com auto-destruição, ou peça pra pessoa trocar no primeiro login em
**Minha conta**).

### Atualizações

Todo `git push` na branch conectada ao Render dispara um novo deploy
automaticamente — não precisa fazer mais nada.

## Alternativa: Railway

Fluxo quase idêntico: New Project → Deploy from GitHub repo → Railway
detecta o Dockerfile. A vantagem do Railway é oferecer **Volumes**
persistentes de fábrica — se preferir não configurar um Postgres externo,
dá pra montar um volume em `/app` e usar SQLite (`DATABASE_URL` fica em
branco, o padrão já é um arquivo local). Mesmas variáveis de ambiente do
passo 2 acima, em Project → Variables.

## Rodando localmente (antes de subir, ou uso interno sem internet)

```bash
pip install -r requirements.txt
export ADMIN_EMAIL="voce@empresa.com"
export ADMIN_SENHA="uma-senha-forte"
export SECRET_KEY="qualquer-coisa-em-dev"
python run.py
# abre em http://127.0.0.1:5000
```

## Segurança — antes de divulgar o link pra equipe

- **Nunca** deixe `SECRET_KEY`/`ADMIN_SENHA` sem definir em produção (o
  app avisa nos logs se isso acontecer).
- Os dados são de ponto/CLT de colaboradores — trate a URL como
  confidencial: não fica pública em nenhum lugar, só quem tem login
  acessa (o Auditor de Ponto já bloqueia isso via `@login_required` em
  toda página com dado).
- Desative um usuário (em **Usuários**) assim que a pessoa sair da
  empresa ou trocar de função.
