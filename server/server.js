import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";
import { initSQL, getAllProducts, getProductById, getProductCount } from "./database.js";

dotenv.config();
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 5000;
const staticDir = path.join(__dirname, "..", "static");

app.use(cors());
app.use(express.json());
app.use("/static", express.static(staticDir, { maxAge: "1d" }));

app.get("/api/products", (req, res) => {
  try {
    res.set("Cache-Control", "public, max-age=15").json(getAllProducts());
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get("/api/products/:id", (req, res) => {
  try {
    const item = getProductById(req.params.id);
    if (!item) return res.status(404).json({ error: "Product not found" });
    res.json({ ...item, watch: null });
  } catch (err) { res.status(500).json({ error: err.message }); }
});

app.get("/api/live-status", (req, res) => res.json({
  status: "active", feed: "Live Real-Time Market Feed (Node + SQL)",
  stores: ["Amazon.in", "Flipkart", "Croma", "Reliance Digital"],
  tracked_count: getProductCount(), database: "SQLite (SQL)", last_sync: new Date().toISOString(),
}));

app.get("/api/status", (req, res) => res.json({ ok: true, database: "SQLite (SQL)", live: getProductCount() }));
app.get("*", (req, res) => res.sendFile(path.join(staticDir, "index.html")));

initSQL().then(() => app.listen(PORT, () => console.log(`[PriceLens] http://localhost:${PORT}`)));
