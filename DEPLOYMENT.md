# CheckFIFA deployment

This project requires the Node server. Static hosting alone cannot provide wallet
challenges, signed sessions, payment verification, or premium API protection.

## Bonto

Bonto is the best fit for the current backend shape because it can run this app
as a normal Node.js service from `package.json`.

Deploy the repository as a Node.js app and use:

```text
npm install
npm start
```

Set these environment variables in Bonto:

```text
API_FOOTBALL_KEY=your_api_football_key
MY_SOLANA_WALLET=EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq
DEVELOPER_WALLETS=EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq
SESSION_SECRET=generate_a_long_random_secret
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
HOST=0.0.0.0
```

After deployment, verify:

```text
https://your-app.bonto.run/api/health
```

It must return JSON before wallet login can work.

## Render Blueprint

1. Push `render.yaml` to GitHub.
2. In Render, create a Blueprint from this repository.
3. Enter `API_FOOTBALL_KEY` when prompted.
4. Open the generated `checkfifa.onrender.com` URL.
5. Confirm `GET /api/health` returns JSON before testing wallet login.

The Blueprint starts the app with `npm start`, serves the frontend and `/api/*`
from the same origin, generates `SESSION_SECRET`, and configures the developer
wallet.

## Vercel

This repository now includes Vercel serverless entrypoints:

- `api/[...path].js` handles the backend `/api/*` routes.
- `api/protected.js` gates premium HTML pages.
- `vercel.json` rewrites protected pages through the backend before serving them.

Import the GitHub repository into Vercel and set these environment variables:

```text
API_FOOTBALL_KEY=your_api_football_key
MY_SOLANA_WALLET=EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq
DEVELOPER_WALLETS=EwAh2VbsbgG2xWsFsDYMjmCUqq48cSkms1HATZDi3Vgq
SESSION_SECRET=generate_a_long_random_secret
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
```

After deployment, verify:

```text
https://your-vercel-domain.vercel.app/api/health
```

It must return JSON before wallet login can work. GitHub Pages or other static
hosting will return HTML for `/api/*`, which prevents wallet signing from
starting.

## Production payment storage

The current prototype stores confirmed payments and predictions on the local
server filesystem. On Vercel this is redirected to `/tmp/fifa2026-data`, which is
enough for a runnable preview but is not durable across deployments or instance
replacement. Move payment and prediction records to Supabase before accepting
production payments.
