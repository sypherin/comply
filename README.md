# Compliance Dashboard (Python + Streamlit on Azure App Service)

A secure, internal **Compliance Dashboard** to track learning completion status and send email reminders via **Microsoft Graph**.
Built with **Python 3.11**, **Streamlit**, optional **Azure SQL** persistence, and **Microsoft Entra ID** (Azure AD) SSO.

## Features
- Upload CSV containing PII (learner completion data) — validated & normalized.
- KPIs (overall completion), per-course completion chart (Plotly), rich filters, individual lookup.
- Email reminders to learners for **incomplete** courses, with **manager CC** via Microsoft Graph.
- **Auth modes**:
  1. **Easy Auth** (Azure App Service built-in auth) — production-friendly.
  2. **MSAL Auth Code + PKCE** — local dev.
- **Security**: HTTPS/TLS-only, RBAC via allowed domains, secrets from **Key Vault** or env, least-privilege Graph scopes, parameterized SQL, logging/audit, retention controls.
- **Optional persistence**: Azure SQL via SQLAlchemy; default is **in‑memory only**.
- **Observability**: Console logging by default; optional Azure Monitor / OpenTelemetry exporter.

## Quickstart (Local Dev)
1. **Python 3.11** and **Node/Chrome** (for Streamlit) installed.
2. `python -m venv .venv && . .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill values for local dev:
   - `APP_ENV=local`
   - `AUTH_MODE=msal`
   - `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and **(local only)** `AZURE_CLIENT_SECRET` if using confidential client; or rely on public client + PKCE.
   - `GRAPH_SCOPES="User.Read Mail.Send Directory.Read.All"`
5. Run: `streamlit run app/app.py`

> **Note**: Local dev uses **MSAL**. For manager lookup/Graph calls, ensure your app registration has delegated permissions consented.

## Deploy to Azure App Service (Linux)
1. Create resources (see **IaC** bicep in `infra/` or do manually):
   - Azure App Service (Linux) + Managed Identity
   - Azure Key Vault
   - (Optional) Azure SQL
   - Log Analytics / Azure Monitor (optional)
2. Configure **App Service Authentication** (Easy Auth) with your **Entra ID** app registration.
3. Set environment variables in App Service Configuration (never commit secrets):
   - `APP_ENV=prod`
   - `AUTH_MODE=easy_auth`
   - `ALLOWED_EMAIL_DOMAINS=contoso.com,example.org`
   - `GRAPH_SCOPES=https://graph.microsoft.com/.default` (app permissions path)
   - `MAIL_SENDER_USER_ID=<sender UPN or GUID>`
   - Key Vault references (if using): `@Microsoft.KeyVault(SecretUri=...)`
4. Deploy via GitHub Actions (see `.github/workflows/ci.yml`) or container (see `Dockerfile`).

## Entra ID App Registration (both modes)
- **Redirect URI (web)** for local: `http://localhost:8501`
- **API permissions**:
  - **Delegated** (local dev): `User.Read`, `Mail.Send`, `Directory.Read.All` (for manager lookup). Grant admin consent as needed.
  - **Application** (prod w/ Easy Auth + client credentials): `Mail.Send`, `Directory.Read.All` as required. Use **least privilege**.
- **Certificates/Secrets**: For prod, prefer **Managed Identity** + Key Vault. Avoid client secrets in app settings unless necessary.
- **Easy Auth**: Enable in App Service → Authentication. Set allowed token audiences to your app registration's Application ID URI/client ID.

## Graph Permissions & Least Privilege
- **Mail.Send** — send reminders. Use `/me/sendMail` (delegated) or `/users/{id}/sendMail` (app).
- **User.Read** — basic profile when using delegated mode.
- **Directory.Read.All** — only if you must lookup managers across the directory. Consider caching to reduce calls.
- Scope via `GRAPH_SCOPES`. In prod with app perms use `.default` and consent at tenant level.

## Security Notes
- **PII**: CSV contains PII; enforce **HTTPS only**, set `ALLOWED_EMAIL_DOMAINS`, never log raw PII or email bodies.
- **Secrets**: Use **Key Vault** and **Managed Identity** in Azure; local `.env` only for dev.
- **SQL**: Parameterized queries via SQLAlchemy. Optional retention purge job (see config `RETENTION_DAYS`).
- **Logging**: Default logs to console; set `AZURE_MONITOR_CONNECTION_STRING` for Azure Monitor.
- **Data Retention**: Default in-memory only. When using SQL, no files persisted; scheduled purge deletes rows older than N days.

## Optional Azure SQL
- Set `USE_AZURE_SQL=true` and configure `SQL_SERVER`, `SQL_DATABASE`, and either `SQL_USERNAME`/`SQL_PASSWORD` **or** use AAD (Managed Identity).
- Initial tables auto-created on first run via SQLAlchemy models in `app/services/data_store.py`.
- To run purge: the app exposes a manual button and background call; for scheduled purge use Azure WebJobs/Functions or a cron CI.

## Limitations
- This is an internal tool; not for internet-exposed anonymous traffic.
- Streamlit CSRF is not applicable, but we still sanitize inputs and headers.
- Graph throttling may apply — exponential backoff is implemented.

## License
MIT (adjust as required by your enterprise).
