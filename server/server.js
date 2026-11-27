import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";
import { initSQL, getAllProducts, getProductById, getProductCount } from "./database.js";

dotenv.config();
const staticDir = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "static");
const app = express().use(cors(), express.json()).use("/static", express.static(staticDir, { maxAge: "1d" }));
const PORT = process.env.PORT || 5000;

app.get("/api/products", (req, res) => {
  try { res.set("Cache-Control", "public, max-age=15").json(getAllProducts()); }
  catch (e) { res.status(500).json({ error: e.message }); }
});
app.get("/api/products/:id", (req, res) => {
  try { const x = getProductById(req.params.id); x ? res.json({ ...x, watch: null }) : res.status(404).json({ error: "Product not found" }); }
  catch (e) { res.status(500).json({ error: e.message }); }
});
app.get("/api/live-status", (_, res) => res.json({ status: "active", feed: "Live Real-Time Market Feed (Node + SQL)", stores: ["Amazon.in", "Flipkart", "Croma", "Reliance Digital"], tracked_count: getProductCount(), database: "SQLite (SQL)", last_sync: new Date().toISOString() }));
app.get("/api/status", (_, res) => res.json({ ok: true, database: "SQLite (SQL)", live: getProductCount() }));
app.get("*", (_, res) => res.sendFile(path.join(staticDir, "index.html")));

initSQL().then(() => app.listen(PORT, () => console.log(`[PriceLens] http://localhost:${PORT}`)));
