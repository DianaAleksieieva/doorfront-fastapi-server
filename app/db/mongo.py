from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables if in development mode
if os.getenv("ENV", "dev") == "dev":
    load_dotenv()

# Required Mongo URI
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("Missing MONGO_URI environment variable.")

# Default database names
MAIN_DB_NAME = os.getenv("MONGO_DB", "myFirstDatabase")
ADDRESS_DB_NAME = os.getenv("ADDRESS_DB", "address-db")

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # Force connection on startup, raises if failed
except Exception as e:
    # Log and handle error appropriately
    print(f"Failed to connect to MongoDB: {e}")
    raise


# Access databases
main_db = client[MAIN_DB_NAME]
address_db = client[ADDRESS_DB_NAME]

collect_panorama = main_db["collect_panorama"]
address_points = address_db["address-points"]
