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
    ("iPhone 16 Pro Max", "Apple", "Phones", 144900, "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=600&auto=format&fit=crop&q=80"),
    ("iPhone 16 Pro", "Apple", "Phones", 119900, "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&auto=format&fit=crop&q=80"),
    ("iPhone 16", "Apple", "Phones", 79900, "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?w=600&auto=format&fit=crop&q=80"),
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
    ("iPhone 16 Pro Max", "Croma"): "https://www.croma.com/apple-iphone-16-pro-max-256gb-desert-titanium/p/309744",
    ("iPhone 16 Pro Max", "Reliance Digital"): "https://www.reliancedigital.in/apple-iphone-16-pro-max-256-gb-desert-titanium/p/494422945",
    ("iPhone 16 Pro", "Croma"): "https://www.croma.com/apple-iphone-16-pro-128gb-natural-titanium/p/309062",
    ("iPhone 16 Pro", "Reliance Digital"): "https://www.reliancedigital.in/apple-iphone-16-pro-128-gb-natural-titanium/p/494422941",
    ("iPhone 16", "Croma"): "https://www.croma.com/apple-iphone-16-128gb-black/p/309051",
    ("iPhone 16", "Reliance Digital"): "https://www.reliancedigital.in/apple-iphone-16-128-gb-black/p/494422931",
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


def store_url(store, name, cat=""):
    # 1. Direct product page URL
    if (name, store) in DIRECT_PRODUCT_URLS:
        return DIRECT_PRODUCT_URLS[(name, store)]

    # 2. Native direct store URLs (zero DuckDuckGo)
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

    # Ensure database contains strictly verified products available across all 4 stores
    db_names = set(row[0] for row in c.execute("select name from products").fetchall())
    expected_names = set(p[0] for p in RECENT_PRODUCTS)
    if db_names != expected_names:
        c.execute("delete from products")
        rnd = random.Random(42)
        for name, brand, cat, base_price, img in RECENT_PRODUCTS:
            h = make_history(float(base_price), rnd)
            c.execute("insert into products(name,brand,cat,price,hist,image) values(?,?,?,?,?,?)",
                      (name, brand, cat, h[-1], json.dumps(h), img))
    c.commit()
    c.close()


def card(r):
    h = json.loads(r["hist"])
    prev = h[-2] if len(h) > 1 else r["price"]
    name = r["name"]
    cat = r["cat"]
    return dict(id=r["id"], name=name, brand=r["brand"], cat=cat, price=r["price"],
                day=round((r["price"] - prev) / prev * 100, 1), low=min(h), high=max(h),
                real=r["real"] or 0, image=r["image"],
                stores=[dict(name=s, url=store_url(s, name, cat)) for s in STORES])


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
    offers = c.execute("select store,price,url from offers where product_id=?", (pid,)).fetchall()
    if offers:
        d["stores"] = sorted([dict(name=o["store"], price=o["price"], url=o["url"] or store_url(o["store"], r["name"], r["cat"])) for o in offers],
                             key=lambda x: x["price"])
    else:
        rnd = random.Random(pid)
        d["stores"] = sorted([dict(name=s, price=round(r["price"] * rnd.uniform(0.98, 1.05)), url=store_url(s, r["name"], r["cat"])) for s in STORES],
                             key=lambda x: x["price"])
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
