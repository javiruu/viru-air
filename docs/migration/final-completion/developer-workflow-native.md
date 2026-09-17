# Native Developer Workflow & Hosted Supabase Environments (No Containers)

**Authority:** iru-completion-no-docker/01_CONTAINER_ERADICATION.md  
**Host Environment:** Windows (PowerShell / CMD)  
**Database Authority:** Hosted Supabase PostgreSQL  
**Zero Container Policy:** No local Docker, no local Supabase CLI containers, no Docker Compose.

---

## 1. Native Developer Workflow

### Terminal A: Backend (FastAPI)
`powershell
cd C:\Users\javiru\Desktop\viru-tracker\backend
.\.venv\Scripts\activate

# Optional: set environment variables if not using .env
#  = "dev"
#  = "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require"

# Actual canonical FastAPI dev command:
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
`

### Terminal B: Frontend (Next.js)
`powershell
cd C:\Users\javiru\Desktop\viru-tracker\frontend
npm run dev
`

### Management Scripts (Native Windows):
- VIRU_PANEL.bat (Interactive CLI panel)
- iniciar_viru.ps1 (Automated local orchestrator)
- scripts\viru-local-status.ps1 (Checks port 3000 and 8000)
- scripts\viru-local-stop.ps1 (Clean process termination)

---

## 2. Hosted Supabase Environments

Viru defines three distinct hosted environments to guarantee complete safety during migrations:

| Environment | VIRU_SUPABASE_ENV | Purpose | Isolation Rules |
|-------------|---------------------|---------|-----------------|
| **Development** | dev | Local day-to-day feature development | Separate hosted project; schema mutations permitted |
| **Staging** | staging | Pre-release automated integration & RLS testing | Dedicated verification project; destroyed/recreated via migrations |
| **Production** | production | Live user traffic | Strictly protected; destructive migration tests forbidden |

### Canonical Environment Variables

The application and automated scripts use standard, non-overloaded variable names:

`ini
# Public / Client-Safe (Next.js & Frontend)
NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT-REF].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=[PUBLISHABLE-ANON-KEY]

# Backend / Server-Only (FastAPI & Server Actions)
VIRU_SUPABASE_ENV=dev
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_PUBLISHABLE_KEY=[PUBLISHABLE-ANON-KEY]
SUPABASE_SECRET_KEY=[SERVICE-ROLE-KEY]
SUPABASE_PROJECT_REF=[PROJECT-REF]

# Database Connection (SQLAlchemy / Psycopg3 Direct or Pooler)
# SSL mode require is strictly enforced on all remote Supabase connections.
DB_URL=postgresql://postgres:[DB-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require
`

### Security Guardrails:
1. SUPABASE_SECRET_KEY and DB_URL must **never** be prefixed with NEXT_PUBLIC_.
2. All secrets reside in untracked .env or environment secrets stores.
3. Test suites verify that destructive resets immediately abort if VIRU_SUPABASE_ENV=production.
