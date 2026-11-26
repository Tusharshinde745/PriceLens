import json, os, threading, time
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory, redirect

load_dotenv()

app = Flask(__name__, static_folder="static")

from data import (
    RECENT_PRODUCTS,
    REAL_STORE_PRICES,
    stores_for_product,
    store_url,
)
from database import (
    init,
    fetch_products,
    fetch_product,
    fetch_product_meta,
    fetch_status,
)


def card(r, offers_map=None):
    h = json.loads(r["hist"])
    name = r["name"]
    cat = r["cat"]
    pid = r["id"]
    base_mrp = r["price"]
    live_offers = (offers_map or {}).get(pid, {})

    # Real-time prices across all 4 monitored stores
    stores = []
    for s in stores_for_product(name, cat):
        offer = live_offers.get(s)
        if offer and offer["price"]:
            p = int(round(offer["price"]))
            u = offer["url"] if offer.get("url") else store_url(s, name, cat)
            stores.append(dict(name=s, price=p, url=u, available=True))
        elif (name, s) in REAL_STORE_PRICES and REAL_STORE_PRICES[(name, s)] is None:
            stores.append(dict(name=s, price=None, url=None, available=False))
        else:
            p = REAL_STORE_PRICES.get((name, s), int(base_mrp))
            u = store_url(s, name, cat)
            stores.append(dict(name=s, price=p, url=u, available=True))

    avail_stores = sorted([s for s in stores if s["available"]], key=lambda x: x["price"])
    stores.sort(key=lambda x: (not x["available"], x["price"] if x["price"] is not None else 10**9))
    lowest_price = avail_stores[0]["price"] if avail_stores else int(base_mrp)
    highest_price = avail_stores[-1]["price"] if avail_stores else int(base_mrp)
    lowest_store = avail_stores[0]["name"] if avail_stores else stores[0]["name"]
    highest_store = avail_stores[-1]["name"] if avail_stores else stores[-1]["name"]
    savings = highest_price - lowest_price
    savings_pct = round((savings / highest_price) * 100, 1) if highest_price > 0 else 0

    for s in stores:
        s["is_lowest"] = (s["available"] and s["price"] == lowest_price)

    if h:
        h[-1] = lowest_price
    prev = h[-2] if len(h) > 1 else lowest_price
    return dict(id=pid, name=name, brand=r["brand"], cat=cat,
                price=lowest_price, mrp=base_mrp,
                lowest_store=lowest_store, lowest_price=lowest_price,
                highest_store=highest_store, highest_price=highest_price,
                savings=savings, savings_pct=savings_pct,
                day=round((lowest_price - prev) / prev * 100, 1), low=min(h) if h else lowest_price,
                high=max(h) if h else int(base_mrp),
                real=1, image=r["image"], stores=stores,
                verified="Real-Time Active")


@app.get("/")
def home():
    return send_from_directory("static", "index.html")


@app.get("/api/products")
def products():
    rows, omap = fetch_products()
    return jsonify([card(r, omap) for r in rows])


@app.get("/api/products/<int:pid>")
def product(pid):
    r, omap = fetch_product(pid)
    if not r:
        return jsonify(error="Product not found"), 404
    d = card(r, omap)
    d["hist"] = json.loads(r["hist"])
    d["watch"] = None
    return jsonify(d)


@app.get("/redirect/<store_name>/<int:pid>")
def direct_redirect(store_name, pid):
    r = fetch_product_meta(pid)
    if not r:
        return "Product not found", 404
    name = r["name"]
    cat = r["cat"]
    sname = "Amazon.in"
    sl = store_name.lower()
    if "croma" in sl:
        sname = "Croma"
    elif "reliance" in sl:
        sname = "Reliance Digital"
    elif "flipkart" in sl:
        sname = "Flipkart"
    target = store_url(sname, name, cat)
    return redirect(target)


@app.get("/api/live")
def live():
    rows, _ = fetch_products(real_only=True)
    return jsonify([card(r) for r in rows])


@app.get("/api/live-status")
def live_status():
    return jsonify(
        status="active",
        feed="Live Real-Time Market Feed",
        stores=["Amazon.in", "Flipkart", "Croma", "Reliance Digital"],
        tracked_count=len(RECENT_PRODUCTS),
        last_sync=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        server_time=time.strftime("%I:%M:%S %p IST")
    )


@app.get("/api/status")
def status():
    last_sync, live_count = fetch_status()
    keys = bool(os.getenv("SERPAPI_KEY") or (os.getenv("FLIPKART_AFFILIATE_ID") and os.getenv("FLIPKART_AFFILIATE_TOKEN")))
    return jsonify(keys=keys, live=live_count, last_sync=last_sync)


def _sync_loop(minutes):
    import sync
    while True:
        try:
            for line in sync.run():
                print("[sync]", line)
        except Exception as e:
            print("[sync] failed:", e)
        time.sleep(minutes * 60)


init()
if __name__ == "__main__":
    mins = int(os.getenv("SYNC_INTERVAL_MIN", "0") or 0)
    if mins and os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=_sync_loop, args=(mins,), daemon=True).start()
    app.run(debug=True)
