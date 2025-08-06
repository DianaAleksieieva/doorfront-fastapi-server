import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox
from app.geo_helpers import generate_3d_ray_latlon, get_intersection
from app.db.mongo import collect_panorama
from typing import Optional, Dict, Any

FALLBACK_ZOOM = 1
RETRY_SCALE = 2.0

def find_label_coordinates_by_id(label_id: str) -> Optional[Dict[str, Any]]:
    """
    Given a label_id, find its exact coordinates by:
    - Querying the MongoDB for the document containing the label
    - Extracting camera location and label marker POV data
    - Generating a 3D ray from camera location and orientation
    - Intersecting the ray with nearby building footprints from OSM
    - Returning the WGS84 coordinates of the intersection point if found
    """

    # Step 1: Find the document containing this label
    doc = collect_panorama.find_one({
        "human_labels.labels.label_id": label_id
    })

    if not doc:
        return None

    image_id = str(doc["image_id"])
    location = doc.get("location", {})

    # Step 2: Search for the label inside human_labels
    for entry in doc.get("human_labels", []):
        for label in entry.get("labels", []):
            if label.get("label_id") == label_id:
                marker_pov = label.get("markerPov", {})
                lat = location.get("lat")
                lon = location.get("lng")
                print(f"Camera location: lat={lat}, lon={lon}")
                heading = marker_pov.get("heading")
                pitch = marker_pov.get("pitch")
                zoom = marker_pov.get("zoom", FALLBACK_ZOOM)

                if None in [lat, lon, heading, pitch]:
                    return None

                origin = Point(lon, lat)  # Note: Point(x=lon, y=lat)

                # Step 3: Download buildings nearby
                tags = {"building": True}
                buildings = ox.features_from_point((lat, lon), tags=tags, dist=100)
                buildings = buildings[buildings.is_valid & ~buildings.geometry.is_empty].copy()

                if buildings.empty:
                    return None

                # Step 4: Generate and project the ray
                ray = generate_3d_ray_latlon(origin, heading, pitch, zoom=zoom, use_meters=True)
                ray_proj = ray.to_crs("EPSG:3857")
                buildings_proj = buildings.to_crs("EPSG:3857")
 
 
                # Step 5: Find intersection
                building, intersection = get_intersection(ray_proj, buildings_proj)

                # Step 6: Retry with longer ray if needed
                if not intersection:
                    ray = generate_3d_ray_latlon(origin, heading, pitch, zoom=zoom, use_meters=True, scale_factor=RETRY_SCALE)
                    ray_proj = ray.to_crs("EPSG:3857")
                    building, intersection = get_intersection(ray_proj, buildings_proj)

                # Step 7: If intersection found, convert back and return
                if intersection:
                    point_wgs = gpd.GeoSeries([intersection], crs="EPSG:3857").to_crs("EPSG:4326").iloc[0]
                    return {
                        "label_id": label_id,
                        "image_id": image_id,
                        "geometry": {
                            "type": "Point",
                            "coordinates": [point_wgs.x, point_wgs.y]  # lon, lat order
                        }
                    }

    return None
