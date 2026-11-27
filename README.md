# PriceLens — Real-Time Multi-Store Price Comparison Portal

PriceLens compares live gadget, home, and cosmetic prices across India's top e-commerce and instant-delivery platforms (**Amazon.in**, **Flipkart**, **Croma**, **Reliance Digital**, **Nykaa**, **Tira**, **Blinkit**, **Zepto**, and **Instamart**) with 1-year price history charts and direct product links.

## Tech Stack
- **Frontend:** Standard HTML5, CSS3 (Light Theme), Vanilla JavaScript (`static/`)
- **Backend:** Node.js + Express.js (`server/server.js`)
- **Database:** SQLite via `sql.js` (`server/database.js`, auto-seeded from `server/data/products.json`)
- **Deployment:** Render Cloud (`render.yaml`, `package.json`)

## Project Structure
```text
├── package.json              # Root Node.js manifest & Render scripts
├── render.yaml               # Render deployment configuration
├── server/
│   ├── server.js             # Express REST API & static file server
│   ├── database.js           # SQLite (sql.js) schema & SQL queries
│   ├── data/products.json    # 49 curated products with store prices & URLs
│   └── package.json          # Server dependencies
├── static/
│   ├── index.html            # Main HTML UI
│   ├── css/styles.css        # Light-theme responsive styling
│   └── js/app.js             # API calls, filtering, sorting & SVG chart
└── client/                   # Optional React + Vite client
```

## API Endpoints
- `GET /api/products` — Returns all 49 products with live store prices
- `GET /api/products/:id` — Returns product details and 365-day price history
- `GET /api/live-status` — Returns live feed metadata and store list
- `GET /api/status` — Health check (`{ ok: true, database: "SQLite (SQL)", live: 49 }`)

## Run Locally
```bash
npm install
npm start
```
Open `http://localhost:5000` in your browser.

## Render Deployment
- **Runtime:** `Node`
- **Build Command:** `npm install`
- **Start Command:** `node server/server.js`
- **Environment Variable:** `NODE_ENV=production`
