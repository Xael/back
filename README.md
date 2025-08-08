# Backend (FastAPI) — CRB Serviços (v4)

Pronto para EasyPanel (Docker), com:
- FastAPI + Uvicorn
- JWT Auth
- CRUD: Users (ADMIN), Locations, Records
- Upload de fotos em `/app/data/uploads` (servidas via `/uploads/...`)
- CORS configurável
- Banco SQLite por padrão (simples); Postgres via `DATABASE_URL`
- **Login aceita JSON _ou_ FormData** e e-mail como string (sem validar formato)

## Rotas
- `GET /healthz`
- `POST /api/auth/login`
- `GET/POST /api/users` (ADMIN)
- `GET/POST /api/locations`
- `GET/POST /api/records`
- `POST /api/records/{id}/photos` (multipart)

## Variáveis de ambiente
- `SECRET_KEY` (obrigatória)
- `ALLOWED_ORIGINS` (ex.: `https://seu-front.vercel.app`)
- `DATABASE_URL` (ex.: `sqlite:////app/data/app.db`)
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` (cria/atualiza admin no startup)

## Docker (EasyPanel)
- Porta: **8000**
- Volume: montar em **/app/data**
- Domínio: apontar host para a app (proxy HTTP → porta 8000), SSL Let’s Encrypt
- Healthcheck: `/healthz`

