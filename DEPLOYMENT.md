# CheckFIFA deployment

This project requires the Node server. Static hosting alone cannot provide wallet
challenges, signed sessions, payment verification, or premium API protection.

## Render Blueprint

1. Push `render.yaml` to GitHub.
2. In Render, create a Blueprint from this repository.
3. Enter `API_FOOTBALL_KEY` when prompted.
4. Open the generated `checkfifa.onrender.com` URL.
5. Confirm `GET /api/health` returns JSON before testing wallet login.

The Blueprint starts the app with `npm start`, serves the frontend and `/api/*`
from the same origin, generates `SESSION_SECRET`, and configures the developer
wallet.

## Production payment storage

The current prototype stores confirmed payments in `data/payments.json`. Files on
an ephemeral web-service filesystem do not survive every deploy or instance
replacement. Move payment records to a persistent database before accepting
production payments.
