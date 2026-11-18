# PriceLens

A price tracker for the Indian market. Browse 100+ recent gadgets, compare prices across Amazon.in, Flipkart, Croma and Reliance Digital, see a year of price history, and get an alert when something reaches the price you set.

Built with Flask and SQLite, with a plain HTML/CSS/JS frontend (no build step).

## Features

- Product catalogue across phones, laptops, tablets, audio, wearables, gaming, home, cameras and accessories, with search, category filters and sorting
- Live price ticker, with product cards and the open product window updating as prices change
- 1-year price graph (1, 3, 6 or 12 months) with hover for any day's price
- Store-by-store price comparison with links to the stores
- Accounts (register, log in, log out) with hashed passwords
- Price tracking: set a target price and get an alert in the bell menu
- Live store data through API keys (Flipkart Affiliate API and SerpApi Google Shopping for India)

## Quick start

```bash
git clone https://github.com/<your-username>/pricelens.git
cd pricelens
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
python app.py
```

Open http://127.0.0.1:5000. The database is created and seeded on first run.

## Live store prices (optional)

The app works without any keys, using simulated sample data. To load real products and prices, add keys to `.env`:

| Variable | Where to get it | What it covers |
|---|---|---|
| `FLIPKART_AFFILIATE_ID`, `FLIPKART_AFFILIATE_TOKEN` | Flipkart affiliate account, API > API Token | Flipkart |
| `SERPAPI_KEY` | serpapi.com | Amazon.in, Croma, Reliance Digital and other Indian stores via Google Shopping |
| `SECRET_KEY` | generate one yourself | Signs login sessions |
| `SYNC_INTERVAL_MIN` | your choice | Refresh live prices every N minutes while the app runs (0 = off) |

Then run:

```bash
python sync.py                       # all categories
python sync.py --cats Phones,Laptops # only some, to save API quota
```

Keys are read on the server only and are never sent to the browser. Never commit `.env`; it is already in `.gitignore`.

### Things to know

- Sample products (the first 101) use simulated prices and history. Live products are marked "live price" and are never simulated.
- The store APIs return only the current price, so a live product's graph starts with one point and fills in each day the sync runs.
- The same product from different stores is matched by the first few words of its title. Expect an occasional duplicate or odd merge.
- Amazon's old Product Advertising API has been retired in favour of the Creators API. Amazon.in prices currently come through SerpApi. A direct Creators API provider is not included.
- Check the Flipkart search request against Flipkart's current affiliate API docs if it returns nothing.
- Each sync uses about 16 searches per provider, so watch your plan's quota.

## Project layout

```
pricelens/
  app.py            Flask app: API routes, SQLite setup, sample data, price alerts
  sync.py           Store API providers and the sync job
  static/index.html Frontend (HTML, CSS and JS in one file)
  .env.example      Template for your keys
  requirements.txt
```

## API

| Route | Purpose |
|---|---|
| `GET /api/products`, `GET /api/products/<id>` | Catalogue; detail with history and store prices |
| `GET /api/live`, `GET /api/status` | Live product prices; sync status |
| `POST /api/register`, `/api/login`, `/api/logout`, `GET /api/me` | Accounts |
| `POST /api/watch`, `DELETE /api/watch/<id>` | Start or stop tracking a price |
| `GET /api/notes`, `POST /api/notes/seen` | Alerts |
| `POST /api/tick` | Moves the simulated sample prices |

## Deploying

`app.py` runs with Flask's debug server, which is for development only. For a public site, set a real `SECRET_KEY`, turn debug off, and serve with a production server such as gunicorn.

## License

MIT. See `LICENSE` (replace the name in it with yours).
