# hunar-assignment

## Overview

Monorepo starter for the Hunar assignment, with a FastAPI backend, a Next.js frontend, and a local PostgreSQL development service.

## Architecture

- `apps/api`: Python 3.11 FastAPI service. Configuration is loaded from environment variables using pydantic-settings.
- `apps/web`: Next.js App Router application using TypeScript, Tailwind CSS, and shadcn/ui.
- `postgres`: PostgreSQL 16 container used by the API during local development.

## Setup

1. Copy `apps/api/.env.example` to `apps/api/.env` and fill in the required values. Keep secrets local.
2. Start the API and database:

   ```bash
   docker compose up --build
   ```

3. Verify the API at [http://localhost:8000/health](http://localhost:8000/health).
4. Run the web app separately:

   ```bash
   cd apps/web
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

See `apps/api/.env.example` and `apps/web/.env.example` for every supported variable, descriptions, and placeholder values. `PEOPLE_SEARCH_PROVIDER=mock` is the default for local development; API keys must never be committed.

## Deployment

Build and deploy `apps/api` using its Dockerfile and provide production environment variables through the platform’s secret manager. Deploy `apps/web` as a standard Next.js application. Use a managed PostgreSQL instance and set `WEBHOOK_BASE_URL` to a publicly reachable HTTPS URL.

## Known Limitations

- The API currently exposes only a health check; business endpoints and database models are not implemented.
- Database migrations are not yet configured beyond the Alembic dependency.
- The web app is an uncustomized starter UI with the requested component primitives installed.
- Local webhook delivery requires a tunnel or publicly reachable development URL.
