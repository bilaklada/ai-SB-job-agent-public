# Frontend

The frontend is a Next.js admin UI for operating and inspecting the backend system.

## Current Responsibilities

- discover database tables dynamically through the admin API
- inspect table schemas and paginated data
- edit selected configuration tables such as LLM providers/models
- submit manual job URLs tied to a selected profile
- expose runtime settings pages backed by the backend API

## Run Locally

```bash
cd frontend
npm install
npm run dev
```

By default the app expects the backend at `http://localhost:8000` and proxies requests through `next.config.ts`.

## Key Files

- `app/page.tsx`: database/admin landing page
- `app/new-task/page.tsx`: manual job URL submission flow
- `app/settings/page.tsx`: runtime settings UI
- `components/DataTable.tsx`: schema-driven table renderer/editor
- `lib/api.ts`: typed backend client

## Notes

- This UI is intentionally operational, not product-marketing focused.
- It reflects the live backend schema rather than a fixed front-end domain model.
