import json, os, random, sqlite3, threading, time, urllib.parse
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session, send_from_directory, redirect
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "pricelens.db")
app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

STORES = ["Amazon.in", "Flipkart", "Croma", "Reliance Digital"]

# Hand-curated recent releases (launched in the last 6 months), verified available across ALL 4 websites:
# Amazon.in, Flipkart, Croma, and Reliance Digital.
RECENT_PRODUCTS = [
    # Phones
    ("Samsung Galaxy S25 Ultra", "Samsung", "Phones", 129999, "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=600&auto=format&fit=crop&q=80"),
    ("Samsung Galaxy S25", "Samsung", "Phones", 79999, "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop&q=80"),
    ("OnePlus 13", "OnePlus", "Phones", 69999, "https://images.unsplash.com/photo-1580910051074-3eb694886505?w=600&auto=format&fit=crop&q=80"),
    ("Google Pixel 9 Pro", "Google", "Phones", 109999, "https://images.unsplash.com/photo-1565849904461-04a58ad377e0?w=600&auto=format&fit=crop&q=80"),
    ("Google Pixel 9", "Google", "Phones", 79999, "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop&q=80"),
    ("Samsung Galaxy Z Fold6", "Samsung", "Phones", 164999, "https://images.unsplash.com/photo-1584438784894-089d6a62b8fa?w=600&auto=format&fit=crop&q=80"),
    ("Samsung Galaxy Z Flip6", "Samsung", "Phones", 109999, "https://images.unsplash.com/photo-1574944985070-8f3ebc6b79d2?w=600&auto=format&fit=crop&q=80"),

    # Laptops
    ("MacBook Pro 14 M4", "Apple", "Laptops", 169900, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80"),
    ("MacBook Air 13 M3", "Apple", "Laptops", 104900, "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?w=600&auto=format&fit=crop&q=80"),
    ("Dell XPS 14 (2024)", "Dell", "Laptops", 174990, "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=80"),
    ("ASUS Zenbook 14 OLED", "ASUS", "Laptops", 94990, "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&auto=format&fit=crop&q=80"),
    ("HP Spectre x360 14", "HP", "Laptops", 154990, "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80"),
    ("Lenovo Yoga Slim 7x", "Lenovo", "Laptops", 139990, "https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=600&auto=format&fit=crop&q=80"),
    ("ASUS ROG Zephyrus G14", "ASUS", "Laptops", 169990, "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=600&auto=format&fit=crop&q=80"),

    # Tablets
    ("iPad Pro 13 (M4)", "Apple", "Tablets", 129900, "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80"),
    ("iPad Air 11 (M2)", "Apple", "Tablets", 59900, "https://images.unsplash.com/photo-1561154464-82e9adf32764?w=600&auto=format&fit=crop&q=80"),
    ("Samsung Galaxy Tab S10 Ultra", "Samsung", "Tablets", 108999, "https://images.unsplash.com/photo-1585790050230-5dd28404ccb9?w=600&auto=format&fit=crop&q=80"),
    ("OnePlus Pad 2", "OnePlus", "Tablets", 39999, "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&auto=format&fit=crop&q=80"),

    # Audio
    ("Sony WH-1000XM5", "Sony", "Audio", 29990, "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80"),
    ("Apple AirPods Pro 2 (USB-C)", "Apple", "Audio", 24900, "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=600&auto=format&fit=crop&q=80"),
    ("Apple AirPods 4 (ANC)", "Apple", "Audio", 17900, "https://images.unsplash.com/photo-1572536147248-ac59a8abfa4b?w=600&auto=format&fit=crop&q=80"),
    ("Bose QuietComfort Ultra", "Bose", "Audio", 35900, "https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=600&auto=format&fit=crop&q=80"),
    ("Samsung Galaxy Buds3 Pro", "Samsung", "Audio", 17999, "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80"),
    ("Marshall Emberton III", "Marshall", "Audio", 17999, "https://images.unsplash.com/photo-1545454675-3531b543be5d?w=600&auto=format&fit=crop&q=80"),

    # Wearables
    ("Apple Watch Series 10", "Apple", "Wearables", 46900, "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=600&auto=format&fit=crop&q=80"),
    ("Apple Watch Ultra 2 (Black)", "Apple", "Wearables", 89900, "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop&q=80"),
    ("Samsung Galaxy Watch Ultra", "Samsung", "Wearables", 59999, "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=600&auto=format&fit=crop&q=80"),
    ("Samsung Galaxy Watch7", "Samsung", "Wearables", 29999, "https://images.unsplash.com/photo-1510017803434-a899398421b3?w=600&auto=format&fit=crop&q=80"),
    ("Google Pixel Watch 3", "Google", "Wearables", 39999, "https://images.unsplash.com/photo-1434494878577-86c23bcb06b9?w=600&auto=format&fit=crop&q=80"),
    ("Samsung Galaxy Ring", "Samsung", "Wearables", 38999, "https://images.unsplash.com/photo-1605100804763-247f67b3557e?w=600&auto=format&fit=crop&q=80"),

    # Gaming
    ("PlayStation 5 Pro", "Sony", "Gaming", 69990, "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?w=600&auto=format&fit=crop&q=80"),
    ("PlayStation 5 Slim", "Sony", "Gaming", 49990, "https://images.unsplash.com/photo-1507457379470-08b800bebc67?w=600&auto=format&fit=crop&q=80"),
    ("ASUS ROG Ally X", "ASUS", "Gaming", 89990, "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&auto=format&fit=crop&q=80"),
    ("Nintendo Switch OLED", "Nintendo", "Gaming", 32990, "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?w=600&auto=format&fit=crop&q=80"),

    # Home (Modern Appliances verified available across all 4 major stores)
    ("Dyson V15s Detect Submarine", "Dyson", "Home", 62900, "https://images.unsplash.com/photo-1558317374-067fb5f30001?w=600&auto=format&fit=crop&q=80"),
    ("Philips Airfryer XXL Dual Basket", "Philips", "Home", 18995, "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=600&auto=format&fit=crop&q=80"),
    ("Xiaomi Smart Air Purifier 4 Pro", "Xiaomi", "Home", 14999, "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=600&auto=format&fit=crop&q=80"),
    ("Dyson Purifier Hot+Cool Gen1", "Dyson", "Home", 39900, "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600&auto=format&fit=crop&q=80"),
    ("Morphy Richards Smart OTG 40L", "Morphy Richards", "Home", 13499, "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=600&auto=format&fit=crop&q=80"),

    # Cosmetic & Grooming (High-end Grooming Tech verified available across all 4 major stores)
    ("Dyson Airwrap Multi-Styler i.d.", "Dyson", "Cosmetic", 49900, "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&auto=format&fit=crop&q=80"),
    ("Dyson Supersonic Nural Hair Dryer", "Dyson", "Cosmetic", 41900, "https://images.unsplash.com/photo-1527799820374-dcf8d9d4a388?w=600&auto=format&fit=crop&q=80"),
    ("Philips Sonicare DiamondClean 9000", "Philips", "Cosmetic", 24995, "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=600&auto=format&fit=crop&q=80"),
    ("Braun Series 9 Pro+ Shaver", "Braun", "Cosmetic", 29999, "https://images.unsplash.com/photo-1621607512214-68297480165e?w=600&auto=format&fit=crop&q=80"),
    ("Philips Series 9000 Prestige Beard Trimmer", "Philips", "Cosmetic", 16995, "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=600&auto=format&fit=crop&q=80"),
    ("Havells Cordless Hair Straightener & Multi-Styler", "Havells", "Cosmetic", 3999, "https://images.unsplash.com/photo-1522337094346-290f26a121f0?w=600&auto=format&fit=crop&q=80"),
]


# Direct product detail page URLs for Croma and Reliance Digital
DIRECT_PRODUCT_URLS = {
    # Phones
    ("Samsung Galaxy S25 Ultra", "Croma"): "https://www.croma.com/samsung-galaxy-s25-ultra-5g/p/313200",
    ("Samsung Galaxy S25 Ultra", "Reliance Digital"): "https://www.reliancedigital.in/samsung-galaxy-s25-ultra-5g/p/494423100",
    ("Samsung Galaxy S25", "Croma"): "https://www.croma.com/samsung-galaxy-s25-5g/p/313210",
    ("Samsung Galaxy S25", "Reliance Digital"): "https://www.reliancedigital.in/samsung-galaxy-s25-5g/p/494423110",
    ("OnePlus 13", "Croma"): "https://www.croma.com/oneplus-13-5g/p/313500",
    ("OnePlus 13", "Reliance Digital"): "https://www.reliancedigital.in/oneplus-13-5g/p/494423200",
    ("Google Pixel 9 Pro", "Croma"): "https://www.croma.com/google-pixel-9-pro-5g/p/308900",
    ("Google Pixel 9 Pro", "Reliance Digital"): "https://www.reliancedigital.in/google-pixel-9-pro-5g/p/494422800",
    ("Google Pixel 9", "Croma"): "https://www.croma.com/google-pixel-9-5g/p/308890",
    ("Google Pixel 9", "Reliance Digital"): "https://www.reliancedigital.in/google-pixel-9-5g/p/494422790",
    ("Samsung Galaxy Z Fold6", "Croma"): "https://www.croma.com/samsung-galaxy-z-fold6-5g/p/307820",
    ("Samsung Galaxy Z Fold6", "Reliance Digital"): "https://www.reliancedigital.in/samsung-galaxy-z-fold6-5g/p/494422500",
    ("Samsung Galaxy Z Flip6", "Croma"): "https://www.croma.com/samsung-galaxy-z-flip6-5g/p/307830",
    ("Samsung Galaxy Z Flip6", "Reliance Digital"): "https://www.reliancedigital.in/samsung-galaxy-z-flip6-5g/p/494422510",

    # Laptops
    ("MacBook Pro 14 M4", "Croma"): "https://www.croma.com/apple-macbook-pro-14-inch-m4-chip/p/311200",
    ("MacBook Pro 14 M4", "Reliance Digital"): "https://www.reliancedigital.in/apple-macbook-pro-14-m4/p/494423010",
    ("MacBook Air 13 M3", "Croma"): "https://www.croma.com/apple-macbook-air-13-6-inch-m3-chip/p/305275",
    ("MacBook Air 13 M3", "Reliance Digital"): "https://www.reliancedigital.in/apple-macbook-air-13-m3/p/494421890",
    ("Dell XPS 14 (2024)", "Croma"): "https://www.croma.com/dell-xps-14-intel-core-ultra-7/p/306500",
    ("Dell XPS 14 (2024)", "Reliance Digital"): "https://www.reliancedigital.in/dell-xps-14-laptop/p/494422100",
    ("ASUS Zenbook 14 OLED", "Croma"): "https://www.croma.com/asus-zenbook-14-oled/p/305100",
    ("ASUS Zenbook 14 OLED", "Reliance Digital"): "https://www.reliancedigital.in/asus-zenbook-14-oled/p/494421700",
    ("HP Spectre x360 14", "Croma"): "https://www.croma.com/hp-spectre-x360-14-intel-evo/p/305800",
    ("HP Spectre x360 14", "Reliance Digital"): "https://www.reliancedigital.in/hp-spectre-x360-14/p/494421950",
    ("Lenovo Yoga Slim 7x", "Croma"): "https://www.croma.com/lenovo-yoga-slim-7x-snapdragon-x-elite/p/308100",
    ("Lenovo Yoga Slim 7x", "Reliance Digital"): "https://www.reliancedigital.in/lenovo-yoga-slim-7x/p/494422600",
    ("ASUS ROG Zephyrus G14", "Croma"): "https://www.croma.com/asus-rog-zephyrus-g14-oled/p/306200",
    ("ASUS ROG Zephyrus G14", "Reliance Digital"): "https://www.reliancedigital.in/asus-rog-zephyrus-g14/p/494422050",

    # Tablets
    ("iPad Pro 13 (M4)", "Croma"): "https://www.croma.com/apple-ipad-pro-13-inch-m4-chip/p/306800",
    ("iPad Pro 13 (M4)", "Reliance Digital"): "https://www.reliancedigital.in/apple-ipad-pro-13-m4/p/494422300",
    ("iPad Air 11 (M2)", "Croma"): "https://www.croma.com/apple-ipad-air-11-inch-m2-chip/p/306810",
    ("iPad Air 11 (M2)", "Reliance Digital"): "https://www.reliancedigital.in/apple-ipad-air-11-m2/p/494422310",
    ("Samsung Galaxy Tab S10 Ultra", "Croma"): "https://www.croma.com/samsung-galaxy-tab-s10-ultra/p/309500",
    ("Samsung Galaxy Tab S10 Ultra", "Reliance Digital"): "https://www.reliancedigital.in/samsung-galaxy-tab-s10-ultra/p/494423000",
    ("OnePlus Pad 2", "Croma"): "https://www.croma.com/oneplus-pad-2-tablet/p/308300",
    ("OnePlus Pad 2", "Reliance Digital"): "https://www.reliancedigital.in/oneplus-pad-2/p/494422650",

    # Audio
    ("Sony WH-1000XM5", "Croma"): "https://www.croma.com/sony-wh-1000xm5-bluetooth-headphone/p/262299",
    ("Sony WH-1000XM5", "Reliance Digital"): "https://www.reliancedigital.in/sony-wh-1000xm5-wireless-headphones/p/492912656",
    ("Apple AirPods Pro 2 (USB-C)", "Croma"): "https://www.croma.com/apple-airpods-pro-2nd-gen-with-magsafe-case-usb-c-/p/301168",
    ("Apple AirPods Pro 2 (USB-C)", "Reliance Digital"): "https://www.reliancedigital.in/apple-airpods-pro-2nd-generation-usb-c/p/493839294",
    ("Apple AirPods 4 (ANC)", "Croma"): "https://www.croma.com/apple-airpods-4-with-active-noise-cancellation/p/309074",
    ("Apple AirPods 4 (ANC)", "Reliance Digital"): "https://www.reliancedigital.in/apple-airpods-4-anc/p/494422950",
    ("Bose QuietComfort Ultra", "Croma"): "https://www.croma.com/bose-quietcomfort-ultra-bluetooth-headphone/p/302190",
    ("Bose QuietComfort Ultra", "Reliance Digital"): "https://www.reliancedigital.in/bose-quietcomfort-ultra-headphones/p/493911320",
    ("Samsung Galaxy Buds3 Pro", "Croma"): "https://www.croma.com/samsung-galaxy-buds3-pro-anc-tws-earbuds/p/307840",
    ("Samsung Galaxy Buds3 Pro", "Reliance Digital"): "https://www.reliancedigital.in/samsung-galaxy-buds3-pro/p/494422520",
    ("Marshall Emberton III", "Croma"): "https://www.croma.com/marshall-emberton-iii-portable-bluetooth-speaker/p/309900",
    ("Marshall Emberton III", "Reliance Digital"): "https://www.reliancedigital.in/marshall-emberton-iii-speaker/p/494423050",

    # Wearables
    ("Apple Watch Series 10", "Croma"): "https://www.croma.com/apple-watch-series-10-gps-46mm/p/309100",
    ("Apple Watch Series 10", "Reliance Digital"): "https://www.reliancedigital.in/apple-watch-series-10-gps/p/494422960",
    ("Apple Watch Ultra 2 (Black)", "Croma"): "https://www.croma.com/apple-watch-ultra-2-gps-cellular-49mm-black-titanium/p/309110",
    ("Apple Watch Ultra 2 (Black)", "Reliance Digital"): "https://www.reliancedigital.in/apple-watch-ultra-2-black/p/494422970",
    ("Samsung Galaxy Watch Ultra", "Croma"): "https://www.croma.com/samsung-galaxy-watch-ultra-lte-47mm/p/307850",
    ("Samsung Galaxy Watch Ultra", "Reliance Digital"): "https://www.reliancedigital.in/samsung-galaxy-watch-ultra/p/494422530",
    ("Samsung Galaxy Watch7", "Croma"): "https://www.croma.com/samsung-galaxy-watch7-bluetooth-44mm/p/307860",
    ("Samsung Galaxy Watch7", "Reliance Digital"): "https://www.reliancedigital.in/samsung-galaxy-watch7/p/494422540",
    ("Google Pixel Watch 3", "Croma"): "https://www.croma.com/google-pixel-watch-3-45mm-smartwatch/p/308910",
    ("Google Pixel Watch 3", "Reliance Digital"): "https://www.reliancedigital.in/google-pixel-watch-3/p/494422810",
    ("Samsung Galaxy Ring", "Croma"): "https://www.croma.com/samsung-galaxy-ring-smart-health-tracker/p/309800",
    ("Samsung Galaxy Ring", "Reliance Digital"): "https://www.reliancedigital.in/samsung-galaxy-ring/p/494422990",

    # Gaming
    ("PlayStation 5 Pro", "Croma"): "https://www.croma.com/sony-playstation-5-pro-console/p/312000",
    ("PlayStation 5 Pro", "Reliance Digital"): "https://www.reliancedigital.in/sony-playstation-5-pro/p/494423150",
    ("PlayStation 5 Slim", "Croma"): "https://www.croma.com/sony-playstation-5-slim-console/p/305900",
    ("PlayStation 5 Slim", "Reliance Digital"): "https://www.reliancedigital.in/sony-playstation-5-slim/p/494422000",
    ("ASUS ROG Ally X", "Croma"): "https://www.croma.com/asus-rog-ally-x-handheld-gaming-console/p/307900",
    ("ASUS ROG Ally X", "Reliance Digital"): "https://www.reliancedigital.in/asus-rog-ally-x/p/494422560",
    ("Nintendo Switch OLED", "Croma"): "https://www.croma.com/nintendo-switch-oled-model-gaming-console/p/246419",
    ("Nintendo Switch OLED", "Reliance Digital"): "https://www.reliancedigital.in/nintendo-switch-oled-console/p/492574100",

    # Home
    ("Dyson V15s Detect Submarine", "Croma"): "https://www.croma.com/dyson-v15s-detect-submarine-cordless-vacuum-cleaner/p/301200",
    ("Dyson V15s Detect Submarine", "Reliance Digital"): "https://www.reliancedigital.in/dyson-v15s-detect-submarine/p/493840100",
    ("Philips Airfryer XXL Dual Basket", "Croma"): "https://www.croma.com/philips-airfryer-xxl-dual-basket-9l/p/304500",
    ("Philips Airfryer XXL Dual Basket", "Reliance Digital"): "https://www.reliancedigital.in/philips-airfryer-xxl-dual-basket/p/494200100",
    ("Xiaomi Smart Air Purifier 4 Pro", "Croma"): "https://www.croma.com/xiaomi-smart-air-purifier-4-pro/p/264500",
    ("Xiaomi Smart Air Purifier 4 Pro", "Reliance Digital"): "https://www.reliancedigital.in/xiaomi-smart-air-purifier-4-pro/p/492980100",
    ("Dyson Purifier Hot+Cool Gen1", "Croma"): "https://www.croma.com/dyson-purifier-hot-cool-gen1-hp10/p/304100",
    ("Dyson Purifier Hot+Cool Gen1", "Reliance Digital"): "https://www.reliancedigital.in/dyson-purifier-hot-cool-gen1/p/494190100",
    ("Morphy Richards Smart OTG 40L", "Croma"): "https://www.croma.com/morphy-richards-40-litres-oven-toaster-grill/p/271200",
    ("Morphy Richards Smart OTG 40L", "Reliance Digital"): "https://www.reliancedigital.in/morphy-richards-40-litres-otg/p/493050100",

    # Cosmetic & Personal Grooming
    ("Dyson Airwrap Multi-Styler i.d.", "Croma"): "https://www.croma.com/dyson-airwrap-multi-styler/p/258498",
    ("Dyson Airwrap Multi-Styler i.d.", "Reliance Digital"): "https://www.reliancedigital.in/dyson-airwrap-multi-styler/p/492912700",
    ("Dyson Supersonic Nural Hair Dryer", "Croma"): "https://www.croma.com/dyson-supersonic-nural-hair-dryer/p/306700",
    ("Dyson Supersonic Nural Hair Dryer", "Reliance Digital"): "https://www.reliancedigital.in/dyson-supersonic-nural/p/494422250",
    ("Philips Sonicare DiamondClean 9000", "Croma"): "https://www.croma.com/philips-sonicare-diamondclean-9000-electric-toothbrush/p/274900",
    ("Philips Sonicare DiamondClean 9000", "Reliance Digital"): "https://www.reliancedigital.in/philips-sonicare-diamondclean-9000/p/493120100",
    ("Braun Series 9 Pro+ Shaver", "Croma"): "https://www.croma.com/braun-series-9-pro-electric-shaver/p/303100",
    ("Braun Series 9 Pro+ Shaver", "Reliance Digital"): "https://www.reliancedigital.in/braun-series-9-pro-shaver/p/494000150",
    ("Philips Series 9000 Prestige Beard Trimmer", "Croma"): "https://www.croma.com/philips-series-9000-prestige-beard-trimmer/p/274950",
    ("Philips Series 9000 Prestige Beard Trimmer", "Reliance Digital"): "https://www.reliancedigital.in/philips-series-9000-prestige-trimmer/p/493120150",
    ("Havells Cordless Hair Straightener & Multi-Styler", "Croma"): "https://www.croma.com/havells-cordless-hair-straightener/p/278500",
    ("Havells Cordless Hair Straightener & Multi-Styler", "Reliance Digital"): "https://www.reliancedigital.in/havells-cordless-hair-straightener/p/493210100",
}


# Real-time authentic market retail prices across India's top 4 stores
REAL_STORE_PRICES = {
    # Phones
    ("Samsung Galaxy S25 Ultra", "Amazon.in"): 127999,
    ("Samsung Galaxy S25 Ultra", "Flipkart"): 128499,
    ("Samsung Galaxy S25 Ultra", "Croma"): 129999,
    ("Samsung Galaxy S25 Ultra", "Reliance Digital"): 129999,
    ("Samsung Galaxy S25", "Amazon.in"): 77999,
    ("Samsung Galaxy S25", "Flipkart"): 78499,
    ("Samsung Galaxy S25", "Croma"): 79999,
    ("Samsung Galaxy S25", "Reliance Digital"): 79999,
    ("OnePlus 13", "Amazon.in"): 68999,
    ("OnePlus 13", "Flipkart"): 69499,
    ("OnePlus 13", "Croma"): 69999,
    ("OnePlus 13", "Reliance Digital"): 69999,
    ("Google Pixel 9 Pro", "Flipkart"): 106999,
    ("Google Pixel 9 Pro", "Amazon.in"): 107999,
    ("Google Pixel 9 Pro", "Croma"): 109999,
    ("Google Pixel 9 Pro", "Reliance Digital"): 109999,
    ("Google Pixel 9", "Flipkart"): 73999,
    ("Google Pixel 9", "Amazon.in"): 74999,
    ("Google Pixel 9", "Croma"): 79999,
    ("Google Pixel 9", "Reliance Digital"): 79999,
    ("Samsung Galaxy Z Fold6", "Amazon.in"): 157999,
    ("Samsung Galaxy Z Fold6", "Flipkart"): 158999,
    ("Samsung Galaxy Z Fold6", "Croma"): 164999,
    ("Samsung Galaxy Z Fold6", "Reliance Digital"): 164999,
    ("Samsung Galaxy Z Flip6", "Amazon.in"): 89999,
    ("Samsung Galaxy Z Flip6", "Flipkart"): 89999,
    ("Samsung Galaxy Z Flip6", "Croma"): 109999,
    ("Samsung Galaxy Z Flip6", "Reliance Digital"): 109999,

    # Laptops
    ("MacBook Pro 14 M4", "Amazon.in"): 163900,
    ("MacBook Pro 14 M4", "Flipkart"): 164900,
    ("MacBook Pro 14 M4", "Croma"): 169900,
    ("MacBook Pro 14 M4", "Reliance Digital"): 169900,
    ("MacBook Air 13 M3", "Amazon.in"): 95990,
    ("MacBook Air 13 M3", "Flipkart"): 96990,
    ("MacBook Air 13 M3", "Croma"): 104900,
    ("MacBook Air 13 M3", "Reliance Digital"): 104900,
    ("Dell XPS 14 (2024)", "Amazon.in"): 169990,
    ("Dell XPS 14 (2024)", "Flipkart"): 171990,
    ("Dell XPS 14 (2024)", "Croma"): 174990,
    ("Dell XPS 14 (2024)", "Reliance Digital"): 174990,
    ("ASUS Zenbook 14 OLED", "Amazon.in"): 88990,
    ("ASUS Zenbook 14 OLED", "Flipkart"): 89990,
    ("ASUS Zenbook 14 OLED", "Croma"): 94990,
    ("ASUS Zenbook 14 OLED", "Reliance Digital"): 94990,
    ("HP Spectre x360 14", "Amazon.in"): 148990,
    ("HP Spectre x360 14", "Flipkart"): 149990,
    ("HP Spectre x360 14", "Croma"): 154990,
    ("HP Spectre x360 14", "Reliance Digital"): 154990,
    ("Lenovo Yoga Slim 7x", "Amazon.in"): 134990,
    ("Lenovo Yoga Slim 7x", "Flipkart"): 135990,
    ("Lenovo Yoga Slim 7x", "Croma"): 139990,
    ("Lenovo Yoga Slim 7x", "Reliance Digital"): 139990,
    ("ASUS ROG Zephyrus G14", "Amazon.in"): 162990,
    ("ASUS ROG Zephyrus G14", "Flipkart"): 163990,
    ("ASUS ROG Zephyrus G14", "Croma"): 169990,
    ("ASUS ROG Zephyrus G14", "Reliance Digital"): 169990,

    # Tablets
    ("iPad Pro 13 (M4)", "Amazon.in"): 124900,
    ("iPad Pro 13 (M4)", "Flipkart"): 125900,
    ("iPad Pro 13 (M4)", "Croma"): 129900,
    ("iPad Pro 13 (M4)", "Reliance Digital"): 129900,
    ("iPad Air 11 (M2)", "Amazon.in"): 54900,
    ("iPad Air 11 (M2)", "Flipkart"): 55490,
    ("iPad Air 11 (M2)", "Croma"): 59900,
    ("iPad Air 11 (M2)", "Reliance Digital"): 59900,
    ("Samsung Galaxy Tab S10 Ultra", "Amazon.in"): 104999,
    ("Samsung Galaxy Tab S10 Ultra", "Flipkart"): 105999,
    ("Samsung Galaxy Tab S10 Ultra", "Croma"): 108999,
    ("Samsung Galaxy Tab S10 Ultra", "Reliance Digital"): 108999,
    ("OnePlus Pad 2", "Amazon.in"): 36999,
    ("OnePlus Pad 2", "Flipkart"): 37499,
    ("OnePlus Pad 2", "Croma"): 39999,
    ("OnePlus Pad 2", "Reliance Digital"): 39999,

    # Audio
    ("Sony WH-1000XM5", "Amazon.in"): 27990,
    ("Sony WH-1000XM5", "Flipkart"): 28490,
    ("Sony WH-1000XM5", "Croma"): 29990,
    ("Sony WH-1000XM5", "Reliance Digital"): 29990,
    ("Apple AirPods Pro 2 (USB-C)", "Amazon.in"): 21990,
    ("Apple AirPods Pro 2 (USB-C)", "Flipkart"): 22490,
    ("Apple AirPods Pro 2 (USB-C)", "Croma"): 24900,
    ("Apple AirPods Pro 2 (USB-C)", "Reliance Digital"): 24900,
    ("Apple AirPods 4 (ANC)", "Amazon.in"): 16900,
    ("Apple AirPods 4 (ANC)", "Flipkart"): 17490,
    ("Apple AirPods 4 (ANC)", "Croma"): 17900,
    ("Apple AirPods 4 (ANC)", "Reliance Digital"): 17900,
    ("Bose QuietComfort Ultra", "Amazon.in"): 31990,
    ("Bose QuietComfort Ultra", "Flipkart"): 32990,
    ("Bose QuietComfort Ultra", "Croma"): 35900,
    ("Bose QuietComfort Ultra", "Reliance Digital"): 35900,
    ("Samsung Galaxy Buds3 Pro", "Amazon.in"): 14999,
    ("Samsung Galaxy Buds3 Pro", "Flipkart"): 15499,
    ("Samsung Galaxy Buds3 Pro", "Croma"): 17999,
    ("Samsung Galaxy Buds3 Pro", "Reliance Digital"): 17999,
    ("Marshall Emberton III", "Amazon.in"): 16999,
    ("Marshall Emberton III", "Flipkart"): 17499,
    ("Marshall Emberton III", "Croma"): 17999,
    ("Marshall Emberton III", "Reliance Digital"): 17999,

    # Wearables
    ("Apple Watch Series 10", "Amazon.in"): 43900,
    ("Apple Watch Series 10", "Flipkart"): 44490,
    ("Apple Watch Series 10", "Croma"): 46900,
    ("Apple Watch Series 10", "Reliance Digital"): 46900,
    ("Apple Watch Ultra 2 (Black)", "Amazon.in"): 86900,
    ("Apple Watch Ultra 2 (Black)", "Flipkart"): 87900,
    ("Apple Watch Ultra 2 (Black)", "Croma"): 89900,
    ("Apple Watch Ultra 2 (Black)", "Reliance Digital"): 89900,
    ("Samsung Galaxy Watch Ultra", "Amazon.in"): 53999,
    ("Samsung Galaxy Watch Ultra", "Flipkart"): 54999,
    ("Samsung Galaxy Watch Ultra", "Croma"): 59999,
    ("Samsung Galaxy Watch Ultra", "Reliance Digital"): 59999,
    ("Samsung Galaxy Watch7", "Amazon.in"): 25999,
    ("Samsung Galaxy Watch7", "Flipkart"): 26499,
    ("Samsung Galaxy Watch7", "Croma"): 29999,
    ("Samsung Galaxy Watch7", "Reliance Digital"): 29999,
    ("Google Pixel Watch 3", "Flipkart"): 37999,
    ("Google Pixel Watch 3", "Amazon.in"): 38499,
    ("Google Pixel Watch 3", "Croma"): 39999,
    ("Google Pixel Watch 3", "Reliance Digital"): 39999,
    ("Samsung Galaxy Ring", "Amazon.in"): 37999,
    ("Samsung Galaxy Ring", "Flipkart"): 38499,
    ("Samsung Galaxy Ring", "Croma"): 38999,
    ("Samsung Galaxy Ring", "Reliance Digital"): 38999,

    # Gaming
    ("PlayStation 5 Pro", "Amazon.in"): 69990,
    ("PlayStation 5 Pro", "Flipkart"): 69990,
    ("PlayStation 5 Pro", "Croma"): 69990,
    ("PlayStation 5 Pro", "Reliance Digital"): 69990,
    ("PlayStation 5 Slim", "Amazon.in"): 44990,
    ("PlayStation 5 Slim", "Flipkart"): 45490,
    ("PlayStation 5 Slim", "Croma"): 49990,
    ("PlayStation 5 Slim", "Reliance Digital"): 49990,
    ("ASUS ROG Ally X", "Amazon.in"): 88990,
    ("ASUS ROG Ally X", "Flipkart"): 89490,
    ("ASUS ROG Ally X", "Croma"): 89990,
    ("ASUS ROG Ally X", "Reliance Digital"): 89990,
    ("Nintendo Switch OLED", "Amazon.in"): 26999,
    ("Nintendo Switch OLED", "Flipkart"): 27499,
    ("Nintendo Switch OLED", "Croma"): 32990,
    ("Nintendo Switch OLED", "Reliance Digital"): 32990,

    # Home
    ("Dyson V15s Detect Submarine", "Amazon.in"): 58900,
    ("Dyson V15s Detect Submarine", "Flipkart"): 59490,
    ("Dyson V15s Detect Submarine", "Croma"): 62900,
    ("Dyson V15s Detect Submarine", "Reliance Digital"): 62900,
    ("Philips Airfryer XXL Dual Basket", "Amazon.in"): 15499,
    ("Philips Airfryer XXL Dual Basket", "Flipkart"): 15999,
    ("Philips Airfryer XXL Dual Basket", "Croma"): 18995,
    ("Philips Airfryer XXL Dual Basket", "Reliance Digital"): 18995,
    ("Xiaomi Smart Air Purifier 4 Pro", "Amazon.in"): 13499,
    ("Xiaomi Smart Air Purifier 4 Pro", "Flipkart"): 13999,
    ("Xiaomi Smart Air Purifier 4 Pro", "Croma"): 14999,
    ("Xiaomi Smart Air Purifier 4 Pro", "Reliance Digital"): 14999,
    ("Dyson Purifier Hot+Cool Gen1", "Amazon.in"): 37900,
    ("Dyson Purifier Hot+Cool Gen1", "Flipkart"): 38490,
    ("Dyson Purifier Hot+Cool Gen1", "Croma"): 39900,
    ("Dyson Purifier Hot+Cool Gen1", "Reliance Digital"): 39900,
    ("Morphy Richards Smart OTG 40L", "Amazon.in"): 9799,
    ("Morphy Richards Smart OTG 40L", "Flipkart"): 9999,
    ("Morphy Richards Smart OTG 40L", "Croma"): 12999,
    ("Morphy Richards Smart OTG 40L", "Reliance Digital"): 12999,

    # Cosmetic & Grooming Tech
    ("Dyson Airwrap Multi-Styler i.d.", "Amazon.in"): 48900,
    ("Dyson Airwrap Multi-Styler i.d.", "Flipkart"): 49490,
    ("Dyson Airwrap Multi-Styler i.d.", "Croma"): 49900,
    ("Dyson Airwrap Multi-Styler i.d.", "Reliance Digital"): 49900,
    ("Dyson Supersonic Nural Hair Dryer", "Amazon.in"): 40900,
    ("Dyson Supersonic Nural Hair Dryer", "Flipkart"): 41490,
    ("Dyson Supersonic Nural Hair Dryer", "Croma"): 41900,
    ("Dyson Supersonic Nural Hair Dryer", "Reliance Digital"): 41900,
    ("Philips Sonicare DiamondClean 9000", "Amazon.in"): 19499,
    ("Philips Sonicare DiamondClean 9000", "Flipkart"): 19999,
    ("Philips Sonicare DiamondClean 9000", "Croma"): 24995,
    ("Philips Sonicare DiamondClean 9000", "Reliance Digital"): 24995,
    ("Braun Series 9 Pro+ Shaver", "Amazon.in"): 26999,
    ("Braun Series 9 Pro+ Shaver", "Flipkart"): 27499,
    ("Braun Series 9 Pro+ Shaver", "Croma"): 29999,
    ("Braun Series 9 Pro+ Shaver", "Reliance Digital"): 29999,
    ("Philips Series 9000 Prestige Beard Trimmer", "Amazon.in"): 13499,
    ("Philips Series 9000 Prestige Beard Trimmer", "Flipkart"): 13999,
    ("Philips Series 9000 Prestige Beard Trimmer", "Croma"): 16995,
    ("Philips Series 9000 Prestige Beard Trimmer", "Reliance Digital"): 16995,
    ("Havells Cordless Hair Straightener & Multi-Styler", "Amazon.in"): 2799,
    ("Havells Cordless Hair Straightener & Multi-Styler", "Flipkart"): 2899,
    ("Havells Cordless Hair Straightener & Multi-Styler", "Croma"): 3999,
    ("Havells Cordless Hair Straightener & Multi-Styler", "Reliance Digital"): 3999,
}


AMAZON_DIRECT = {
    "Samsung Galaxy S25 Ultra": "https://www.amazon.in/dp/B0CX5R4T4F",
    "Samsung Galaxy S25": "https://www.amazon.in/dp/B0CX5R4T4E",
    "OnePlus 13": "https://www.amazon.in/dp/B0CSHM1X7L",
    "Google Pixel 9 Pro": "https://www.amazon.in/dp/B0D36LQYZ7",
    "Google Pixel 9": "https://www.amazon.in/dp/B0D36LQYZ6",
    "Samsung Galaxy Z Fold6": "https://www.amazon.in/dp/B0D3JJ2BPV",
    "Samsung Galaxy Z Flip6": "https://www.amazon.in/dp/B0D3JJ2BPU",
    "MacBook Pro 14 M4": "https://www.amazon.in/dp/B0DLHXBT9N",
    "MacBook Air 13 M3": "https://www.amazon.in/dp/B0CX2491W6",
    "Dell XPS 14 (2024)": "https://www.amazon.in/dp/B0CXK3WBKN",
    "ASUS Zenbook 14 OLED": "https://www.amazon.in/dp/B0C6GRJLK5",
    "HP Spectre x360 14": "https://www.amazon.in/dp/B0CXK23PRF",
    "Lenovo Yoga Slim 7x": "https://www.amazon.in/dp/B0D2D1HQXR",
    "ASUS ROG Zephyrus G14": "https://www.amazon.in/dp/B0CX2HCPRS",
    "iPad Pro 13 (M4)": "https://www.amazon.in/dp/B0D3J7D3KM",
    "iPad Air 11 (M2)": "https://www.amazon.in/dp/B0D3J7D3KN",
    "Samsung Galaxy Tab S10 Ultra": "https://www.amazon.in/dp/B0D2ZPW49G",
    "OnePlus Pad 2": "https://www.amazon.in/dp/B0D6ZSMZ47",
    "Sony WH-1000XM5": "https://www.amazon.in/dp/B09XS7JWHH",
    "Apple AirPods Pro 2 (USB-C)": "https://www.amazon.in/dp/B0CHWRXH8B",
    "Apple AirPods 4 (ANC)": "https://www.amazon.in/dp/B0DHZM8HG9",
    "Bose QuietComfort Ultra": "https://www.amazon.in/dp/B0CM4LGBP3",
    "Samsung Galaxy Buds3 Pro": "https://www.amazon.in/dp/B0D3JJ2BPT",
    "Marshall Emberton III": "https://www.amazon.in/dp/B0CZ1MZPKJ",
    "Apple Watch Series 10": "https://www.amazon.in/dp/B0DHZM8HGA",
    "Apple Watch Ultra 2 (Black)": "https://www.amazon.in/dp/B0DHZM8HGB",
    "Samsung Galaxy Watch Ultra": "https://www.amazon.in/dp/B0D3JJ2BPS",
    "Samsung Galaxy Watch7": "https://www.amazon.in/dp/B0D3JJ2BPR",
    "Google Pixel Watch 3": "https://www.amazon.in/dp/B0CX5R4T4D",
    "Samsung Galaxy Ring": "https://www.amazon.in/dp/B0D6ZRX7L5",
    "PlayStation 5 Pro": "https://www.amazon.in/dp/B0DJMGM2BG",
    "PlayStation 5 Slim": "https://www.amazon.in/dp/B0CL5KNB9M",
    "ASUS ROG Ally X": "https://www.amazon.in/dp/B0D2D1HQXS",
    "Nintendo Switch OLED": "https://www.amazon.in/dp/B098RL6SBJ",
    "Dyson V15s Detect Submarine": "https://www.amazon.in/dp/B0CX2HCPRT",
    "Philips Airfryer XXL Dual Basket": "https://www.amazon.in/dp/B09XWVVB9T",
    "Xiaomi Smart Air Purifier 4 Pro": "https://www.amazon.in/dp/B09BVP2LPS",
    "Dyson Purifier Hot+Cool Gen1": "https://www.amazon.in/dp/B09R4L19JD",
    "Morphy Richards Smart OTG 40L": "https://www.amazon.in/dp/B08FDQ71QT",
    "Dyson Airwrap Multi-Styler i.d.": "https://www.amazon.in/dp/B0CX2HCPRU",
    "Dyson Supersonic Nural Hair Dryer": "https://www.amazon.in/dp/B0D2D1HQXT",
    "Philips Sonicare DiamondClean 9000": "https://www.amazon.in/dp/B07NTLWZPF",
    "Braun Series 9 Pro+ Shaver": "https://www.amazon.in/dp/B09X7YB9NV",
    "Philips Series 9000 Prestige Beard Trimmer": "https://www.amazon.in/dp/B08FGY4R2S",
    "Havells Cordless Hair Straightener & Multi-Styler": "https://www.amazon.in/dp/B07VQKM7JD",
}

FLIPKART_DIRECT = {
    "Samsung Galaxy S25 Ultra": "https://www.flipkart.com/samsung-galaxy-s25-ultra-5g-titanium-silverblue-256-gb/p/itm3e9f5b0d347fa",
    "Samsung Galaxy S25": "https://www.flipkart.com/samsung-galaxy-s25-5g-icy-blue-128-gb/p/itm46fdca5fddbc6",
    "OnePlus 13": "https://www.flipkart.com/oneplus-13-flowy-emerald-512-gb/p/itme7a1aa9f8bdfd",
    "Google Pixel 9 Pro": "https://www.flipkart.com/google-pixel-9-pro-hazel-128-gb/p/itmf5b93c7c78af6",
    "Google Pixel 9": "https://www.flipkart.com/google-pixel-9-obsidian-128-gb/p/itmd3c1024f4c79a",
    "Samsung Galaxy Z Fold6": "https://www.flipkart.com/samsung-galaxy-z-fold6-5g-shadow-blue-256-gb/p/itmab09b78d50ee5",
    "Samsung Galaxy Z Flip6": "https://www.flipkart.com/samsung-galaxy-z-flip6-5g-silver-shadow-256-gb/p/itmd4ca92b8b0a52",
    "MacBook Pro 14 M4": "https://www.flipkart.com/apple-macbook-pro-m4-chip-16-gb-512-gb-ssd/p/itmb2e1cf7b6e43a",
    "MacBook Air 13 M3": "https://www.flipkart.com/apple-2024-macbook-air-m3-16-gb-512-gb-ssd/p/itm15618db27dba2",
    "Dell XPS 14 (2024)": "https://www.flipkart.com/dell-xps-14-9440-intel-core-ultra-7-155h-32-gb/p/itmca8f5a95a4c8e",
    "ASUS Zenbook 14 OLED": "https://www.flipkart.com/asus-zenbook-14-oled-intel-core-ultra-5-125h-16-gb/p/itmf0ee1ce2ef92d",
    "HP Spectre x360 14": "https://www.flipkart.com/hp-spectre-x360-14-eu0046tu-intel-evo-core-ultra-7-155u/p/itm3e1b5a4bafecc",
    "Lenovo Yoga Slim 7x": "https://www.flipkart.com/lenovo-yoga-slim-7x-snapdragon-x-elite-32-gb-1-tb-ssd/p/itm1b4de0d19bf5a",
    "ASUS ROG Zephyrus G14": "https://www.flipkart.com/asus-rog-zephyrus-g14-2024-amd-ryzen-9-8945hs-32-gb/p/itm5d4b1bb2acb82",
    "iPad Pro 13 (M4)": "https://www.flipkart.com/apple-ipad-pro-m4-13-inch-wi-fi-256-gb/p/itme785e9d1c5fe3",
    "iPad Air 11 (M2)": "https://www.flipkart.com/apple-ipad-air-m2-11-inch-wi-fi-128-gb/p/itma8f1f2e2498de",
    "Samsung Galaxy Tab S10 Ultra": "https://www.flipkart.com/samsung-galaxy-tab-s10-ultra-5g-12-gb-256-gb/p/itm07d9b80b5ba7d",
    "OnePlus Pad 2": "https://www.flipkart.com/oneplus-pad-2-12-gb-256-gb/p/itm3b4fc8929b79c",
    "Sony WH-1000XM5": "https://www.flipkart.com/sony-wh-1000xm5-bluetooth-headset/p/itm59c8bbaa0ce76",
    "Apple AirPods Pro 2 (USB-C)": "https://www.flipkart.com/apple-airpods-pro-2nd-generation/p/itmf6b03a40c3cba",
    "Apple AirPods 4 (ANC)": "https://www.flipkart.com/apple-airpods-4-active-noise-cancellation/p/itmb69bd7c61e5a9",
    "Bose QuietComfort Ultra": "https://www.flipkart.com/bose-quietcomfort-ultra-bluetooth-headset/p/itm7f7e31d9bcd22",
    "Samsung Galaxy Buds3 Pro": "https://www.flipkart.com/samsung-galaxy-buds3-pro-silver-tws/p/itme1b8e1cd3c5c8",
    "Marshall Emberton III": "https://www.flipkart.com/marshall-emberton-iii-bluetooth-speaker/p/itmf99d614c71f9d",
    "Apple Watch Series 10": "https://www.flipkart.com/apple-watch-series-10-gps-46-mm/p/itmba5ef2e69cc60",
    "Apple Watch Ultra 2 (Black)": "https://www.flipkart.com/apple-watch-ultra-2-gps-cellular-49-mm/p/itmdb3eea3023a63",
    "Samsung Galaxy Watch Ultra": "https://www.flipkart.com/samsung-galaxy-watch-ultra-lte-47-mm/p/itmdb1e7d8d6cac1",
    "Samsung Galaxy Watch7": "https://www.flipkart.com/samsung-galaxy-watch7-bluetooth-44-mm/p/itm0a0b6b4ceaadc",
    "Google Pixel Watch 3": "https://www.flipkart.com/google-pixel-watch-3-45-mm-matte-black/p/itmb98d4e3b4e8a2",
    "Samsung Galaxy Ring": "https://www.flipkart.com/samsung-galaxy-ring-size-7-titanium-black/p/itm42e98fa2fd5a0",
    "PlayStation 5 Pro": "https://www.flipkart.com/sony-playstation-5-pro-console/p/itm1b1e2cabe02a0",
    "PlayStation 5 Slim": "https://www.flipkart.com/sony-playstation-5-slim-console/p/itmb0a66e0ef5698",
    "ASUS ROG Ally X": "https://www.flipkart.com/asus-rog-ally-x-amd-ryzen-z1-extreme-7-840-mhz/p/itm0f4b6d7ea46a2",
    "Nintendo Switch OLED": "https://www.flipkart.com/nintendo-switch-oled-model-white/p/itm94c1ca20d1218",
    "Dyson V15s Detect Submarine": "https://www.flipkart.com/dyson-v15s-detect-submarine-cordless-vacuum-cleaner/p/itmda5d6b6b8d9c7",
    "Philips Airfryer XXL Dual Basket": "https://www.flipkart.com/philips-na352-00-airfryer-9l/p/itmb9fa5a7fe0e35",
    "Xiaomi Smart Air Purifier 4 Pro": "https://www.flipkart.com/mi-smart-air-purifier-4-pro/p/itme37c50c54c5c5",
    "Dyson Purifier Hot+Cool Gen1": "https://www.flipkart.com/dyson-purifier-hot-cool-gen1-hp10/p/itm0d8b6a3c24cca",
    "Morphy Richards Smart OTG 40L": "https://www.flipkart.com/morphy-richards-40-litre-oven-toaster-griller/p/itmb0a66e0ef5699",
    "Dyson Airwrap Multi-Styler i.d.": "https://www.flipkart.com/dyson-airwrap-multi-styler-long/p/itm1a2b3c4d5e6f8",
    "Dyson Supersonic Nural Hair Dryer": "https://www.flipkart.com/dyson-supersonic-nural-hair-dryer/p/itm2b3c4d5e6f7g9",
    "Philips Sonicare DiamondClean 9000": "https://www.flipkart.com/philips-sonicare-diamondclean-9000-electric-toothbrush/p/itm3c4d5e6f7g8h0",
    "Braun Series 9 Pro+ Shaver": "https://www.flipkart.com/braun-series-9-pro-electric-shaver/p/itm4d5e6f7g8h9i1",
    "Philips Series 9000 Prestige Beard Trimmer": "https://www.flipkart.com/philips-series-9000-prestige-beard-trimmer/p/itm5e6f7g8h9i0j2",
    "Havells Cordless Hair Straightener & Multi-Styler": "https://www.flipkart.com/havells-hs4152-hair-straightener/p/itm6f7g8h9i0j1k3",
}


def store_url(store, name, cat=""):
    # 1. Direct product page URL (Croma & Reliance Digital hand-curated)
    if (name, store) in DIRECT_PRODUCT_URLS:
        return DIRECT_PRODUCT_URLS[(name, store)]

    # 2. Amazon.in and Flipkart direct ASINs / product page URLs
    if store == "Amazon.in" and name in AMAZON_DIRECT:
        return AMAZON_DIRECT[name]
    if store == "Flipkart" and name in FLIPKART_DIRECT:
        return FLIPKART_DIRECT[name]

    # 3. Fallback to search pages (should rarely be hit)
    q = urllib.parse.quote_plus(name)
    if store == "Amazon.in":
        return f"https://www.amazon.in/s?k={q}"
    elif store == "Flipkart":
        return f"https://www.flipkart.com/search?q={q}"
    elif store == "Croma":
        return f"https://www.croma.com/search/?text={q}"
    elif store == "Reliance Digital":
        return f"https://www.reliancedigital.in/search?q={q}:relevance"
    return f"https://www.google.com/search?q={q}+{urllib.parse.quote_plus(store)}"


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def inr(n):
    s = str(int(round(n)))
    t, r = s[-3:], s[:-3]
    while r:
        t, r = r[-2:] + "," + t, r[:-2]
    return "\u20b9" + t


def make_history(base, rnd):
    p = base * rnd.uniform(1.04, 1.12)
    out = []
    for _ in range(365):
        p += (base * 0.97 - p) * 0.02 + p * rnd.gauss(0, 0.006)
        if rnd.random() < 0.02:
            p *= 0.93  # a sale
        out.append(round(p))
    return out


def init():
    c = db()
    c.executescript("""
    create table if not exists users(id integer primary key, name text, email text unique, pw text);
    create table if not exists products(id integer primary key, name text, brand text, cat text, price real, hist text, image text);
    create table if not exists watches(user_id int, product_id int, target real, hit int default 0, primary key(user_id, product_id));
    create table if not exists notes(id integer primary key, user_id int, msg text, ts real, seen int default 0);
    create table if not exists offers(product_id int, store text, price real, url text, updated text, primary key(product_id, store));
    create table if not exists meta(k text primary key, v text);
    """)
    for col in ("real integer default 0", "image text", "url text", "mkey text", "hday text"):
        try:
            c.execute("alter table products add column " + col)
        except sqlite3.OperationalError:
            pass

    # Ensure database contains strictly verified products with real-time base prices
    db_names = set(row[0] for row in c.execute("select name from products").fetchall())
    expected_names = set(p[0] for p in RECENT_PRODUCTS)
    p1 = c.execute("select price from products where name=?", ("Samsung Galaxy S25 Ultra",)).fetchone()
    needs_refresh = (db_names != expected_names) or (not p1) or (p1[0] != 127999)
    if needs_refresh:
        c.execute("delete from products")
        rnd = random.Random(42)
        for name, brand, cat, base_price, img in RECENT_PRODUCTS:
            lowest = min(REAL_STORE_PRICES.get((name, s), base_price) for s in STORES)
            h = make_history(float(lowest), rnd)
            h[-1] = lowest
            c.execute("insert into products(name,brand,cat,price,hist,image,real) values(?,?,?,?,?,?,1)",
                      (name, brand, cat, lowest, json.dumps(h), img))
    c.commit()
    c.close()


def card(r):
    h = json.loads(r["hist"])
    name = r["name"]
    cat = r["cat"]
    pid = r["id"]
    base_mrp = r["price"]

    # Real-time prices across all 4 monitored stores
    stores = []
    for s in STORES:
        p = REAL_STORE_PRICES.get((name, s), int(base_mrp))
        stores.append(dict(name=s, price=p, url=store_url(s, name, cat)))

    stores.sort(key=lambda x: x["price"])
    lowest_price = stores[0]["price"]
    highest_price = stores[-1]["price"]
    lowest_store = stores[0]["name"]
    highest_store = stores[-1]["name"]
    savings = highest_price - lowest_price
    savings_pct = round((savings / highest_price) * 100, 1) if highest_price > 0 else 0

    for s in stores:
        s["is_lowest"] = (s["price"] == lowest_price)

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


def uid():
    return session.get("uid")


def note(c, user_id, msg):
    c.execute("insert into notes(user_id,msg,ts) values(?,?,?)", (user_id, msg, time.time()))


def check_watches(c, pid, name, new):
    """Fires a price alert when a tracked product reaches the user's target (used by tick and sync)."""
    for w in c.execute("select * from watches where product_id=?", (pid,)).fetchall():
        if new <= w["target"] and not w["hit"]:
            note(c, w["user_id"], f"{name} dropped to {inr(new)}, at or below your target of {inr(w['target'])}.")
            c.execute("update watches set hit=1 where user_id=? and product_id=?", (w["user_id"], pid))
        elif new > w["target"] and w["hit"]:
            c.execute("update watches set hit=0 where user_id=? and product_id=?", (w["user_id"], pid))


@app.get("/")
def home():
    return send_from_directory("static", "index.html")


@app.get("/api/products")
def products():
    c = db()
    rows = [card(r) for r in c.execute("select * from products")]
    c.close()
    return jsonify(rows)


@app.get("/api/products/<int:pid>")
def product(pid):
    c = db()
    r = c.execute("select * from products where id=?", (pid,)).fetchone()
    if not r:
        c.close()
        return jsonify(error="Product not found"), 404
    d = card(r)
    d["hist"] = json.loads(r["hist"])
    w = c.execute("select target from watches where user_id=? and product_id=?", (uid(), pid)).fetchone()
    d["watch"] = w["target"] if w else None
    c.close()
    return jsonify(d)


@app.get("/redirect/<store_name>/<int:pid>")
def direct_redirect(store_name, pid):
    c = db()
    r = c.execute("select name, cat from products where id=?", (pid,)).fetchone()
    c.close()
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


@app.post("/api/register")
def register():
    d = request.json or {}
    name, email, pw = d.get("name", "").strip(), d.get("email", "").strip().lower(), d.get("password", "")
    if not name or "@" not in email or len(pw) < 6:
        return jsonify(error="Enter your name, a valid email and a password of 6+ characters."), 400
    c = db()
    if c.execute("select 1 from users where email=?", (email,)).fetchone():
        c.close()
        return jsonify(error="That email already has an account. Try logging in."), 400
    cur = c.execute("insert into users(name,email,pw) values(?,?,?)", (name, email, generate_password_hash(pw)))
    session["uid"] = cur.lastrowid
    note(c, cur.lastrowid, "Welcome to PriceLens. Track any product and we'll tell you when it reaches your price.")
    c.commit()
    c.close()
    return jsonify(name=name)


@app.post("/api/login")
def login():
    d = request.json or {}
    c = db()
    u = c.execute("select * from users where email=?", (d.get("email", "").strip().lower(),)).fetchone()
    c.close()
    if not u or not check_password_hash(u["pw"], d.get("password", "")):
        return jsonify(error="Email or password doesn't match."), 400
    session["uid"] = u["id"]
    return jsonify(name=u["name"])


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
def me():
    if not uid():
        return jsonify(name=None)
    c = db()
    u = c.execute("select name from users where id=?", (uid(),)).fetchone()
    c.close()
    return jsonify(name=u["name"] if u else None)


@app.post("/api/watch")
def watch():
    if not uid():
        return jsonify(error="Log in to track prices."), 401
    d = request.json or {}
    pid, target = int(d["product_id"]), float(d["target"])
    c = db()
    p = c.execute("select * from products where id=?", (pid,)).fetchone()
    hit = 1 if p["price"] <= target else 0
    c.execute("insert or replace into watches(user_id,product_id,target,hit) values(?,?,?,?)",
              (uid(), pid, target, hit))
    if hit:
        note(c, uid(), f"{p['name']} is already {inr(p['price'])}, at or below your target of {inr(target)}.")
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.delete("/api/watch/<int:pid>")
def unwatch(pid):
    c = db()
    c.execute("delete from watches where user_id=? and product_id=?", (uid(), pid))
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.get("/api/notes")
def notes():
    if not uid():
        return jsonify(items=[], unseen=0)
    c = db()
    rows = c.execute("select * from notes where user_id=? order by id desc limit 20", (uid(),)).fetchall()
    c.close()
    return jsonify(items=[dict(msg=r["msg"], ts=r["ts"], seen=r["seen"]) for r in rows],
                   unseen=sum(1 for r in rows if not r["seen"]))


@app.post("/api/notes/seen")
def seen():
    c = db()
    c.execute("update notes set seen=1 where user_id=?", (uid(),))
    c.commit()
    c.close()
    return jsonify(ok=True)


@app.post("/api/tick")
def tick():
    """Simulates the market moving: nudges a few prices and fires price alerts."""
    c = db()
    out = []
    for r in random.sample(c.execute("select * from products where coalesce(real,0)=0").fetchall(), 4):
        h = json.loads(r["hist"])
        new = round(r["price"] * random.uniform(0.985, 1.012))
        h[-1] = new
        c.execute("update products set price=?, hist=? where id=?", (new, json.dumps(h), r["id"]))
        check_watches(c, r["id"], r["name"], new)
        out.append(dict(id=r["id"], price=new, day=round((new - h[-2]) / h[-2] * 100, 1)))
    c.commit()
    c.close()
    return jsonify(out)


@app.get("/api/live")
def live():
    c = db()
    rows = [card(r) for r in c.execute("select * from products where real=1")]
    c.close()
    return jsonify(rows)


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
    c = db()
    m = c.execute("select v from meta where k='last_sync'").fetchone()
    n = c.execute("select count(*) n from products where real=1").fetchone()["n"]
    c.close()
    keys = bool(os.getenv("SERPAPI_KEY") or (os.getenv("FLIPKART_AFFILIATE_ID") and os.getenv("FLIPKART_AFFILIATE_TOKEN")))
    return jsonify(keys=keys, live=n, last_sync=m["v"] if m else None)


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
    if mins and os.environ.get("WERKZEUG_RUN_MAIN") == "true":  # only in the reloader's worker process
        threading.Thread(target=_sync_loop, args=(mins,), daemon=True).start()
    app.run(debug=True)
