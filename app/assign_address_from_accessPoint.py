# assignAddressUsingAdressPoints.py

import math
import numpy as np
from sklearn.neighbors import BallTree
from pymongo import MongoClient
from app.db.mongo import address_points

EARTH_RADIUS = 6371000  # meters
MAX_DISTANCE_M = 25     # Only consider matches within 25 meters

# Cached global variables
_address_coords = []
_address_meta = []
_tree = None

def _load_address_points():
    """Load address points from MongoDB and build BallTree for spatial search."""
    global _address_coords, _address_meta, _tree

    if _tree is not None:
        return  # Already loaded

    cursor = address_points.find({
        "geometry.coordinates": {"$type": "array"},
        "google_address": {"$exists": True}
    })

    for doc in cursor:
        try:
            lon, lat = doc["geometry"]["coordinates"]
            google_address = doc["google_address"]
            _address_coords.append([math.radians(lat), math.radians(lon)])
            _address_meta.append({
                "mongo_id": str(doc["_id"]),
                "google_address": google_address
            })
        except Exception as e:
            print(f"⚠️ Skipping address doc: {e}")

    if _address_coords:
        tree_coords = np.array(_address_coords)
        _tree = BallTree(tree_coords, metric='haversine')

def assign_closest_address(lat: float, lon: float):
    """
    Find the closest address from MongoDB within MAX_DISTANCE_M of (lat, lon).
    Returns:
        - dict with 'google_address' and 'mongo_id' if a close match is found
        - None if no address is within MAX_DISTANCE_M
    """
    _load_address_points()
    
    if _tree is None or not _address_coords:
        print("⚠️ No address points available")
        return None

    point_rad = np.radians([[lat, lon]])
    dist_rad, idx = _tree.query(point_rad, k=1)
    dist_m = dist_rad[0][0] * EARTH_RADIUS

    if dist_m <= MAX_DISTANCE_M:
        return {
            "mongo_id": _address_meta[idx[0][0]]["mongo_id"],
            "google_address": _address_meta[idx[0][0]]["google_address"],
            "distance_m": round(dist_m, 2)
        }
    return None
