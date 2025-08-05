from shapely.geometry import Point, LineString
import numpy as np
import geopandas as gpd
from geopandas import GeoSeries
from typing import Optional, Tuple
from dask_geopandas import GeoDataFrame

intersected_count = 0
non_intersected_count = 0

def generate_3d_ray_latlon(
    origin: Point,
    heading: float,
    pitch: float,
    zoom: int = 1,
    camera_height_m: float = 2.5,
    scale_factor: float = 1.0,
    use_meters: bool = False,
) -> gpd.GeoSeries:
    """
    Generate a more realistic 3D camera ray projection in 2D map space.
    """
    heading_rad = np.deg2rad(heading)
    pitch_rad = np.deg2rad(pitch)

    # Reproject origin to meters if needed
    if use_meters:
        gdf = gpd.GeoDataFrame(geometry=[origin], crs="EPSG:4326").to_crs("EPSG:3857")
        origin_m = gdf.geometry.values[0]
    else:
        origin_m = origin

    # Zoom → base distance
    zoom_to_distance = {0: 100, 1: 60, 2: 40, 3: 25, 4: 15, 5: 10}
    zoom_distance = zoom_to_distance.get(zoom, 25)

    # Estimate ray length from pitch (steeper pitch → shorter ray)
    if abs(pitch_rad) > 0.01:
        distance = camera_height_m / abs(np.tan(pitch_rad))
    else:
        distance = zoom_distance  # fallback for horizontal pitch

    # Apply zoom scaling and optional override
    distance *= (zoom_distance / 25.0) * scale_factor

    # Direction vector
    dx = distance * np.sin(heading_rad)
    dy = distance * np.cos(heading_rad)

    x0, y0 = origin_m.x, origin_m.y
    x1, y1 = x0 + dx, y0 + dy

    ray_projected = LineString([(x0, y0), (x1, y1)])

    # Convert back to WGS84 if needed
    if use_meters:
        ray = gpd.GeoSeries([ray_projected], crs="EPSG:3857").to_crs("EPSG:4326")
    else:
        ray = gpd.GeoSeries([ray_projected], crs="EPSG:4326")

    return ray


def get_intersected_buildings(ray:GeoSeries, buildings_gdf:GeoDataFrame) -> GeoDataFrame:
    global intersected_count, non_intersected_count
    """
    Function to filter buildings that intersect with the given ray.

    Parameters:
    - buildings_gdf (gpd.GeoDataFrame): The GeoDataFrame containing the buildings.
    - ray (geopandas.GeoSeries): The ray as a GeoSeries to check intersections.

    Returns:
    - gpd.GeoDataFrame: A GeoDataFrame containing the buildings that intersect with the ray.
    """
    try:
        # Ensure both the ray and the buildings_gdf are in the same CRS:
        buildings_gdf = buildings_gdf.to_crs(ray.crs)
        # Ensure the spatial index is up-to-date
        sindex = buildings_gdf.sindex

        # Access the Shapely geometry from the GeoSeries
        ray_geometry = ray.geometry[0]

        # Find intersecting buildings
        intersected_indices = list(sindex.intersection(
            ray_geometry.bounds))  # Use ray_geometry.bounds
        intersected_buildings = buildings_gdf.iloc[
            [idx for idx in intersected_indices if buildings_gdf.iloc[idx].geometry.intersects(
                ray_geometry)]
        ]
        if not intersected_buildings.empty:
            intersected_count += 1
        else:
            non_intersected_count += 1
        # print(intersected_count, non_intersected_count)
       

        return intersected_buildings

    except Exception as e:
        print(f"Error in get_intersected_buildings: {e}")
        return gpd.GeoDataFrame()  # Return an empty GeoDataFrame in case of error


def get_closest_intersection_point(ray: GeoSeries, gdf:GeoDataFrame) -> Tuple[Optional[GeoSeries], Optional[Point]]:
    # Get intersected buildings
    intersected_buildings = get_intersected_buildings(ray, gdf)

    # Calculate intersection points and associate them with buildings
    intersections = []
    for idx, building in intersected_buildings.iterrows():
        intersection = ray.geometry[0].intersection(building.geometry)
        if not intersection.is_empty:
            # Store intersection and building
            intersections.append((intersection, building))

    # Extract points from intersections and associate them with buildings
    intersection_points_with_buildings = []
    for intersection, building in intersections:
        if intersection.geom_type == "MultiLineString":
            for line in intersection.geoms:
                for coord in line.coords:
                    intersection_points_with_buildings.append(
                        (Point(coord), building))
        elif intersection.geom_type == "LineString":
            for coord in intersection.coords:
                intersection_points_with_buildings.append(
                    (Point(coord), building))
        elif intersection.geom_type == "Point":
            intersection_points_with_buildings.append((intersection, building))
        elif intersection.geom_type == "MultiPoint":
            for point in intersection.geoms:
                intersection_points_with_buildings.append((point, building))

    # Find the closest intersection point and its associated building
    if intersection_points_with_buildings:
        ray_start_point = Point(ray.geometry[0].coords[0])

        # Find the closest intersection point and building
        closest_intersection_point, closest_building = min(
            intersection_points_with_buildings,
            key=lambda x: ray_start_point.distance(
                x[0])  # Compare distance to the point
        )
        
        return closest_building, closest_intersection_point

    return None, None  # Return None if no intersections are found


def get_intersection(ray: GeoSeries, gdf: GeoDataFrame):
    intersected_buildings = get_intersected_buildings(ray, gdf)
    return get_closest_intersection_point(ray, intersected_buildings)
