# Buddy's Brain web app

React and Vite frontend with a bundled demo that needs no backend or API keys.

```sh
npm ci
npm run dev
```

For live mode, copy `.env.example` to `.env` and set `VITE_ENABLE_LIVE=true`.
Use `VITE_API_BASE_URL=http://localhost:8000` for a standalone local API or
`VITE_API_BASE_URL=/api` for the combined Vercel deployment. These values are
public and compiled into the frontend; never put secrets in `VITE_*` variables.

```sh
npm test
npm run lint
npm run build
```

The root `vercel.json` deploys web and API together. This directory's
`vercel.json` also supports a standalone frontend-only deployment.
See the [root README](../README.md) for both options.
