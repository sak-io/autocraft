# Pantry Pal — technical plan

## Stack
- **Next.js** (React) with server-rendered pages, deployed on **Vercel**.
- **PostgreSQL** on **Supabase** for all data; row-level security per household.
- REST API routes inside the Next.js app.

## Accounts
Sign-in by **magic link sent to email** (no passwords). A household is created by the first user; others join by an invite link.

## Shared list freshness
The list page **polls the server every 30 seconds**; no websockets in v1.

## Barcode
Use the browser camera with a JavaScript barcode library, then look the product up in the **OpenFoodFacts** public API.

## Meal suggestions
The server sends the pantry contents to the **Claude API** and renders the suggested recipes.

## Notifications
Daily expiry reminder as a push notification.

## Testing and quality
To be added after the first release.
