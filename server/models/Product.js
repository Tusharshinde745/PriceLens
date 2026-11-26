import mongoose from "mongoose";

const storeSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    price: { type: Number, default: null },
    url: { type: String, default: null },
    available: { type: Boolean, default: true },
    is_lowest: { type: Boolean, default: false },
  },
  { _id: false }
);

const productSchema = new mongoose.Schema(
  {
    id: { type: Number, required: true, unique: true },
    name: { type: String, required: true },
    brand: { type: String, required: true },
    cat: { type: String, required: true },
    price: { type: Number, required: true },
    mrp: { type: Number, required: true },
    lowest_store: { type: String, required: true },
    lowest_price: { type: Number, required: true },
    highest_store: { type: String, required: true },
    highest_price: { type: Number, required: true },
    savings: { type: Number, default: 0 },
    savings_pct: { type: Number, default: 0 },
    day: { type: Number, default: 0 },
    low: { type: Number, required: true },
    high: { type: Number, required: true },
    real: { type: Number, default: 1 },
    image: { type: String, required: true },
    verified: { type: String, default: "Real-Time Active" },
    stores: [storeSchema],
    hist: [Number],
  },
  { timestamps: true }
);

export default mongoose.model("Product", productSchema);
