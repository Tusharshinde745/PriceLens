import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import mongoose from "mongoose";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import Product from "./models/Product.js";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 5000;
const MONGODB_URI = process.env.MONGODB_URI || "";
const DATA_PATH = path.join(__dirname, "data", "products.json");

let useMongo = false;
let memoryProducts = JSON.parse(fs.readFileSync(DATA_PATH, "utf-8"));

async function connectDB() {
  if (!MONGODB_URI) {
    console.log("[PriceLens] MONGODB_URI not set — running with JSON/in-memory store.");
    return;
  }
  try {
    await mongoose.connect(MONGODB_URI);
    useMongo = true;
    console.log("[PriceLens] Connected to MongoDB.");
    const count = await Product.countDocuments();
    if (count !== memoryProducts.length) {
      await Product.deleteMany({});
      await Product.insertMany(memoryProducts);
      console.log(`[PriceLens] Seeded ${memoryProducts.length} products into MongoDB.`);
    }
  } catch (err) {
    console.warn("[PriceLens] MongoDB connection failed, falling back to JSON store:", err.message);
  }
}

app.get("/api/products", async (req, res) => {
  try {
    const list = useMongo
      ? await Product.find({}, { hist: 0, _id: 0, __v: 0 }).sort({ id: 1 }).lean()
      : memoryProducts.map(({ hist, ...rest }) => rest);
    res.json(list);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/api/products/:id", async (req, res) => {
  try {
    const pid = Number(req.params.id);
    const item = useMongo
      ? await Product.findOne({ id: pid }, { _id: 0, __v: 0 }).lean()
      : memoryProducts.find((p) => p.id === pid);
    if (!item) return res.status(404).json({ error: "Product not found" });
    res.json({ ...item, watch: null });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/api/live-status", (req, res) => {
  res.json({
    status: "active",
    feed: "Live Real-Time Market Feed (MERN)",
    stores: ["Amazon.in", "Flipkart", "Croma", "Reliance Digital"],
    tracked_count: memoryProducts.length,
    database: useMongo ? "MongoDB" : "JSON Store",
    last_sync: new Date().toISOString(),
  });
});

app.get("/api/status", async (req, res) => {
  const count = useMongo ? await Product.countDocuments() : memoryProducts.length;
  res.json({ ok: true, database: useMongo ? "MongoDB" : "JSON Store", live: count });
});

// Serve standard HTML, CSS, JS frontend from static/
const staticDir = path.join(__dirname, "..", "static");
app.use(express.static(staticDir));
app.get("*", (req, res) => {
  res.sendFile(path.join(staticDir, "index.html"));
});

connectDB().then(() => {
  app.listen(PORT, () => {
    console.log(`[PriceLens MERN Server] listening on http://localhost:${PORT}`);
  });
});
