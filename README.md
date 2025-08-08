# Backend (FastAPI) — CRB Serviços (MVP)

Backend mínimo para rodar no VPS (EasyPanel) com:
- FastAPI + Uvicorn
- JWT Auth (login)
- CRUD básico: Users (admin), Locations, Records
- Upload de fotos para volume persistente (`/app/data/uploads`), servidas em `/uploads/...`
- CORS configurável
- Banco: SQLite por padrão (simples para começar). Pode trocar para Postgres via `DATABASE_URL`.

## Endpoints principais
- `GET /healthz`
- `POST /api/auth/login` → JWT
- `GET /api/users` (ADMIN) — lista
- `POST /api/users` (ADMIN) — cria funcionário/admin
- `GET /api/locations` — lista
- `POST /api/locations` — cria
- `GET /api/records` — lista (filtros simples)
- `POST /api/records` — cria
- `POST /api/records/{id}/photos` — upload (múltiplos arquivos)

## Variáveis de ambiente
- `SECRET_KEY` (obrigatória) — chave aleatória (32+ chars)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (opcional, padrão 60)
- `DATABASE_URL` (opcional) — ex.: `sqlite:////app/data/app.db` (padrão) ou `postgresql+psycopg://user:pass@host:5432/db`
- `ALLOWED_ORIGINS` — lista separada por vírgula (ex.: `https://seu-front.vercel.app,https://app.seu-dominio.com`)
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` — se definidos, cria/atualiza admin no startup

## Docker (EasyPanel)
1. Crie um app Git apontando para este repositório e selecione o `Dockerfile`.
2. Volumes:
   - Monte um volume persistente em `/app/data` (para DB SQLite e uploads).
3. Porta de exposição: **8000**
4. Domínio: `api.seu-dominio.com` (habilite HTTPS no EasyPanel).
5. Variáveis de ambiente: conforme acima.
6. Healthcheck/Status: `GET /healthz`.

## Rodando localmente (opcional)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
