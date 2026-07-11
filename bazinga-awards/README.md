# Bazinga Awards — fundação

Fase 1: banco de dados + login real com Google e Discord. Ainda não tem
categorias/votação/admin — isso vem na próxima fase.

## Rodar local

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # depois edite o .env com suas credenciais
python run.py
```

Abre em `http://localhost:5000`. Sem credenciais no `.env`, os botões de
login mostram um aviso em vez de dar erro — dá pra ver o resto do site
numa boa.

## Credenciais Google (OAuth)

1. https://console.cloud.google.com/ → crie um projeto
2. **APIs e Serviços → Tela de consentimento OAuth** → configura tipo
   "Externo", nome do app, seu e-mail
3. **APIs e Serviços → Credenciais → Criar credenciais → ID do cliente OAuth**
   → tipo "Aplicativo da Web"
4. Em **URIs de redirecionamento autorizados**, adiciona:
   - `http://localhost:5000/auth/callback/google` (pra testar local)
   - `https://SEUDOMINIO.com/auth/callback/google` (quando for pra produção)
5. Copia o **Client ID** e **Client Secret** pro `.env`

## Credenciais Discord (OAuth)

1. https://discord.com/developers/applications → **New Application**
2. Aba **OAuth2** → copia **Client ID** e **Client Secret**
3. Em **Redirects**, adiciona:
   - `http://localhost:5000/auth/callback/discord`
   - `https://SEUDOMINIO.com/auth/callback/discord`
4. Copia os dois valores pro `.env`

## Virar admin

No `.env`, `ADMIN_EMAILS` (Gmail, separado por vírgula) e/ou
`ADMIN_DISCORD_IDS` (o ID numérico da conta Discord, não o username).
Quem logar com um desses vira admin automaticamente.

## Banco de dados

SQLite por padrão (`bazinga.db`, criado sozinho no primeiro run). Pra trocar
por Postgres, só muda `DATABASE_URL` no `.env` — o resto do código não
precisa mudar.

## Deploy no VPS

Precisa de domínio + HTTPS (Google e Discord não aceitam redirect HTTP em
produção). Rodar atrás de Nginx + Gunicorn + Let's Encrypt é o caminho mais
simples — se quiser, monto esse passo a passo quando chegar a hora.

## O que já tem

- Modelo completo do banco: pessoas, temporadas, categorias (template +
  por edição), indicações, votos, progresso do "story" de revelação
- Login funcionando com Google e Discord, foto/nome puxados automático no
  primeiro login
- Marcação de admin automática por e-mail/Discord ID

## Próxima fase

Painel admin (pessoas e categorias reutilizáveis, copiar/duplicar/editar) e
a tela de votação com os cards.
