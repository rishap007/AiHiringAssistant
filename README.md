# AI Hiring Assistant

## Overview

Production-ready assignment submission with a FastAPI backend, a Next.js frontend, PostgreSQL persistence, Hunar voice screening/reachout, LLM job-description parsing, and configurable people search.

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

## Features

- Create jobs and parse job descriptions into searchable hiring criteria.
- Create Hunar screening agents, place real calls, and display statuses, recordings, duration, and structured results.
- Search candidates through Apollo when configured, with clearly labelled deterministic mock data for demo environments without a people-search key.
- Add missing candidate phone numbers, create a Hunar reachout agent, place outbound calls, and refresh the dashboard from Hunar or signed webhooks.
- Responsive recruiter UI built with Next.js, TypeScript, Tailwind CSS, and shadcn/ui primitives.

## Environment Variables

See `apps/api/.env.example` and `apps/web/.env.example` for every supported variable, descriptions, and placeholder values. `PEOPLE_SEARCH_PROVIDER=mock` is the default for local development; API keys must never be committed.

## Deployment

The reference deployment uses Render for the API, Neon for PostgreSQL, and Vercel for the web app. Configure production secrets only in the platform secret managers. Set `PEOPLE_SEARCH_PROVIDER=apollo` and provide `PEOPLE_SEARCH_API_KEY` to use live Apollo results; leave it as `mock` only for a clearly labelled demo environment. Set `WEBHOOK_BASE_URL` to the public API URL and `CORS_ORIGINS` to the public web URL.

Current reference URLs:

- Web: https://web-peach-two-2mhhh20clc.vercel.app
- API: https://aihiringassistant-api.onrender.com

## Attendance design

The no-smartphone attendance proposal is documented in [`docs/attendance-without-smartphones.md`](docs/attendance-without-smartphones.md). It uses IVR/missed calls, verified phone numbers, location-specific numbers, deterministic attendance rules, an auditable ledger, and supervisor exception review.

## Testing

Backend tests cover Hunar request formatting, trailing-slash call retrieval, signed webhook updates, and invalid webhook signatures. Frontend lint and production builds should be run from `apps/web`. The free Render instance may sleep between requests, and LLM parsing can take several seconds.
