from database import users_collection, products_collection, orders_collection
import bcrypt
from datetime import datetime


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@sgarden.com",
        "password": hash_password("admin123"),
        "role": "admin",
        "lastActiveAt": datetime.utcnow(),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    },
    {
        "username": "user",
        "email": "user@sgarden.com",
        "password": hash_password("user1234"),
        "role": "user",
        "lastActiveAt": datetime.utcnow(),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    },
]

SEED_PRODUCTS = [
    {"name": "Wireless Mouse", "description": "Ergonomic wireless mouse with USB receiver", "category": "Electronics", "price": 29.99, "stock": 150},
    {"name": "Mechanical Keyboard", "description": "RGB mechanical keyboard with Cherry MX switches", "category": "Electronics", "price": 89.99, "stock": 75},
    {"name": "USB-C Hub", "description": "7-in-1 USB-C hub with HDMI and Ethernet", "category": "Electronics", "price": 45.99, "stock": 200},
    {"name": "Monitor Stand", "description": "Adjustable monitor stand with USB ports", "category": "Accessories", "price": 34.99, "stock": 120},
    {"name": "Webcam HD", "description": "1080p HD webcam with built-in microphone", "category": "Electronics", "price": 59.99, "stock": 90},
    {"name": "Desk Lamp", "description": "LED desk lamp with adjustable brightness", "category": "Accessories", "price": 24.99, "stock": 180},
    {"name": "Cable Organizer", "description": "Silicone cable management clips, pack of 10", "category": "Accessories", "price": 9.99, "stock": 500},
    {"name": "Laptop Sleeve", "description": "Neoprene laptop sleeve for 15-inch laptops", "category": "Accessories", "price": 19.99, "stock": 250},
    {"name": "External SSD", "description": "1TB portable external SSD, USB 3.2", "category": "Storage", "price": 79.99, "stock": 60},
    {"name": "USB Flash Drive", "description": "64GB USB 3.0 flash drive", "category": "Storage", "price": 12.99, "stock": 400},
    {"name": "Ethernet Cable", "description": "Cat6 ethernet cable, 10 meters", "category": "Networking", "price": 8.99, "stock": 300},
    {"name": "Wi-Fi Router", "description": "Dual-band Wi-Fi 6 router", "category": "Networking", "price": 129.99, "stock": 45},
    {"name": "Mouse Pad XL", "description": "Extended gaming mouse pad, 900x400mm", "category": "Accessories", "price": 15.99, "stock": 200},
    {"name": "Headphone Stand", "description": "Aluminum headphone stand", "category": "Accessories", "price": 22.99, "stock": 100},
    {"name": "Power Strip", "description": "6-outlet power strip with USB charging", "category": "Electronics", "price": 18.99, "stock": 350},
]


# Orders: (product name, quantity) pairs per order, with a fixed 2024 date
SEED_ORDER_TEMPLATES = [
    {"items": [("Wireless Mouse", 2), ("USB Flash Drive", 3)],         "date": datetime(2024, 1, 15)},
    {"items": [("Mechanical Keyboard", 1), ("Mouse Pad XL", 1)],       "date": datetime(2024, 2, 8)},
    {"items": [("USB-C Hub", 2), ("Cable Organizer", 5)],              "date": datetime(2024, 3, 22)},
    {"items": [("Webcam HD", 1), ("Monitor Stand", 1)],                "date": datetime(2024, 4, 10)},
    {"items": [("External SSD", 2)],                                   "date": datetime(2024, 5, 5)},
    {"items": [("Wi-Fi Router", 1), ("Ethernet Cable", 3)],            "date": datetime(2024, 6, 18)},
    {"items": [("Desk Lamp", 2), ("Headphone Stand", 1)],              "date": datetime(2024, 7, 30)},
    {"items": [("Wireless Mouse", 3), ("Laptop Sleeve", 2)],           "date": datetime(2024, 8, 14)},
    {"items": [("Power Strip", 2), ("USB-C Hub", 1)],                  "date": datetime(2024, 9, 25)},
    {"items": [("Mechanical Keyboard", 2), ("Webcam HD", 1)],          "date": datetime(2024, 10, 11)},
    {"items": [("External SSD", 1), ("USB Flash Drive", 5)],           "date": datetime(2024, 11, 7)},
    {"items": [("Wi-Fi Router", 2), ("Mouse Pad XL", 3)],              "date": datetime(2024, 12, 20)},
]


async def seed_orders():
    """Seed sample orders referencing seeded products, spread across 2024."""
    count = await orders_collection.count_documents({})
    if count > 0:
        return

    product_map = {}
    async for p in products_collection.find():
        product_map[p["name"]] = p

    if not product_map:
        return

    orders_to_insert = []
    for template in SEED_ORDER_TEMPLATES:
        items = []
        total = 0.0
        for product_name, quantity in template["items"]:
            product = product_map.get(product_name)
            if not product:
                continue
            item_total = product["price"] * quantity
            items.append({
                "productId": str(product["_id"]),
                "name": product["name"],
                "quantity": quantity,
                "price": product["price"],
            })
            total += item_total
        if items:
            orders_to_insert.append({
                "items": items,
                "total": round(total, 2),
                "status": "completed",
                "createdAt": template["date"],
                "updatedAt": template["date"],
            })

    if orders_to_insert:
        await orders_collection.insert_many(orders_to_insert)
        print(f"Seeded {len(orders_to_insert)} orders")


async def seed_data():
    """Seed test users, sample products, and sample orders if they don't exist."""
    # Seed users
    for user_data in SEED_USERS:
        existing = await users_collection.find_one({"username": user_data["username"]})
        if not existing:
            await users_collection.insert_one(user_data.copy())
            print(f"Seeded user: {user_data['username']}")

    # Seed products
    count = await products_collection.count_documents({})
    if count == 0:
        products_to_insert = []
        for p in SEED_PRODUCTS:
            product = {**p, "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()}
            products_to_insert.append(product)
        await products_collection.insert_many(products_to_insert)
        print(f"Seeded {len(products_to_insert)} products")

    await seed_orders()
