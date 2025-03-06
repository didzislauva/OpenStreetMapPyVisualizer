import requests
import json
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon, Point, box  # Fixed Missing Import
import pyproj
from pathlib import Path
import logging
import time
from typing import Dict, List, Tuple, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class OSMMapGenerator:
    """Class to fetch and visualize OpenStreetMap data for a specified area, including water bodies."""
    
    def __init__(self, center_lat: float, center_lon: float, radius_meters: float = 500):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_meters = radius_meters
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Coordinate transformations
        self.wgs84_to_lks92 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:25884", always_xy=True)
        self.lks92_to_wgs84 = pyproj.Transformer.from_crs("EPSG:25884", "EPSG:4326", always_xy=True)
        
        # Calculate bounding box
        self.bbox = self._calculate_bbox()
        
        # Define feature styles
        self.styles = {
            "forests": {"color": "darkgreen", "alpha": 0.5, "label": "Forests"},
            "buildings": {"color": "firebrick", "alpha": 0.7, "edgecolor": "black", "linewidth": 0.5, "label": "Buildings"},
            "water": {"color": "lightblue", "alpha": 0.5, "label": "Water Bodies"},
            "rivers": {"color": "blue", "linewidth": 1.5, "label": "Rivers"},
            "lakes": {"color": "deepskyblue", "alpha": 0.7, "label": "Lakes"},
            "channels": {"color": "lightblue", "linewidth": 1.2, "label": "Channels"},
            "roads": {
                "motorway": {"color": "orangered", "linewidth": 2.5},
                "trunk": {"color": "orangered", "linewidth": 2.5},
                "primary": {"color": "orangered", "linewidth": 2.5},
                "secondary": {"color": "orange", "linewidth": 1.8},
                "tertiary": {"color": "orange", "linewidth": 1.8},
                "residential": {"color": "gray", "linewidth": 1.2},
                "service": {"color": "gray", "linewidth": 1.2},
                "default": {"color": "black", "linewidth": 0.8, "linestyle": "--"}
            }
        }
    
    def _calculate_bbox(self) -> Tuple[float, float, float, float]:
        """Calculate bounding box in WGS 84 based on center point and radius."""
        center_x, center_y = self.wgs84_to_lks92.transform(self.center_lon, self.center_lat)
        xmin, xmax = center_x - self.radius_meters, center_x + self.radius_meters
        ymin, ymax = center_y - self.radius_meters, center_y + self.radius_meters
        
        bbox_wgs84 = [self.lks92_to_wgs84.transform(x, y) for x, y in [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]]
        south, west = bbox_wgs84[0][1], bbox_wgs84[0][0]
        north, east = bbox_wgs84[2][1], bbox_wgs84[2][0]
        
        return south, west, north, east

    def fetch_osm_data(self, feature_type: str) -> Optional[dict]:
        """Fetch OSM data for a specific feature type."""
        query = self._get_overpass_query(feature_type)
        if not query:
            logger.error(f"No query found for {feature_type}")
            return None

        logger.info(f"Fetching {feature_type} data from Overpass...")

        for attempt in range(3):
            try:
                response = requests.get(self.overpass_url, params={"data": query}, timeout=30)
                response.raise_for_status()
                data = response.json()

                num_elements = len(data.get("elements", []))
                logger.info(f"✅ Retrieved {num_elements} {feature_type} elements.")

                return data
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                logger.warning(f"Attempt {attempt+1}/3 failed: {str(e)}")
                time.sleep(5)

        logger.error(f"❌ Failed to fetch {feature_type} data.")
        return None


    def _get_overpass_query(self, feature_type: str) -> str:
        """Generate Overpass API query for a specific feature type."""
        bbox_str = f"{self.bbox[0]},{self.bbox[1]},{self.bbox[2]},{self.bbox[3]}"

        queries = {
            "roads": f"""[out:json];(way["highway"]({bbox_str}););out geom;""",
            "buildings": f"""[out:json];(way["building"]({bbox_str}););out geom;""",
            "forests": f"""[out:json];(way["landuse"="forest"]({bbox_str});way["natural"="wood"]({bbox_str}););out geom;""",
            "water": f"""[out:json];(way["natural"="water"]({bbox_str});way["waterway"]({bbox_str});relation["natural"="water"]({bbox_str});relation["waterway"]({bbox_str}););out geom;""",
            "rivers": f"""[out:json];(way["waterway"="river"]({bbox_str}););out geom;""",
            "lakes": f"""[out:json];(way["natural"="water"]({bbox_str});relation["natural"="water"]({bbox_str}););out geom;""",
            "channels": f"""[out:json];(way["waterway"="canal"]({bbox_str});way["waterway"="ditch"]({bbox_str});way["waterway"="stream"]({bbox_str}););out geom;"""
        }

        return queries.get(feature_type, "")


    def process_osm_data(self, data: Optional[dict], feature_type: str) -> gpd.GeoDataFrame:
        """Process OSM data into a GeoDataFrame and clip to bounding box."""
        if not data or "elements" not in data:
            logger.warning(f"⚠️ No data found for {feature_type}")
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

        geometries = []
        properties = []
        geometry_type = "polygon" if feature_type in ["buildings", "forests", "lakes"] else "line"

        for element in data.get("elements", []):
            if element["type"] == "way" and "geometry" in element:
                coords = [(node["lon"], node["lat"]) for node in element["geometry"]]
                if len(coords) < 2:
                    continue
                geo = Polygon(coords) if geometry_type == "polygon" and len(coords) >= 3 else LineString(coords)
                geometries.append(geo)
                properties.append(element.get("tags", {}))

        gdf = gpd.GeoDataFrame(properties, geometry=geometries, crs="EPSG:4326")

        # Clip to bounding box
        bbox_polygon = box(self.bbox[1], self.bbox[0], self.bbox[3], self.bbox[2])  # west, south, east, north
        gdf_clipped = gdf.clip(bbox_polygon)

        logger.info(f"✅ {feature_type.capitalize()} before clipping: {len(gdf)} elements.")
        logger.info(f"🔪 {feature_type.capitalize()} after clipping: {len(gdf_clipped)} elements.")

        if gdf_clipped.empty:
            logger.warning(f"⚠️ {feature_type} is empty after clipping!")

        return gdf_clipped


    
    def generate_map(self):
        """Generate and save the map."""
        feature_types = ["roads", "buildings", "forests", "rivers", "lakes", "channels", "water"]
        gdfs = {ft: self.process_osm_data(self.fetch_osm_data(ft), ft) for ft in feature_types}

        # Log the number of elements for each feature
        for feature, gdf in gdfs.items():
            logger.info(f"📌 {feature.capitalize()} - {len(gdf)} elements.")

        fig, ax = plt.subplots(figsize=(12, 12))
        ax.set_aspect("equal")

        # Plot features in correct order
        plot_order = ["water", "lakes", "forests", "rivers", "channels", "roads", "buildings"]

        for feature in plot_order:
            if feature in gdfs:
                gdf = gdfs[feature]
                if gdf is not None and not gdf.empty:
                    logger.info(f"🟢 Plotting {feature} ({len(gdf)} elements)")

                    try:
                        # Special handling for roads
                        if feature == "roads":
                            if "highway" in gdf.columns:
                                for road_type in gdf["highway"].unique():
                                    subset = gdf[gdf["highway"] == road_type]

                                    if subset.empty:
                                        logger.warning(f"⚠️ No roads found for type: {road_type}")
                                        continue

                                    style = self.styles["roads"].get(road_type, self.styles["roads"]["default"])
                                    subset.plot(ax=ax, label=f"{road_type} road", **style)
                            else:
                                logger.warning("⚠️ No 'highway' column in roads data")
                                gdf.plot(ax=ax, color="black", linewidth=1.5, label="Roads")
                        else:
                            # Default for all other layers
                            gdf.plot(ax=ax, **self.styles.get(feature, {"color": "black"}))

                    except Exception as e:
                        logger.error(f"❌ Error plotting {feature}: {str(e)}")

        ax.set_title("OSM Map with Roads, Water, and Buildings")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        plt.savefig(self.output_dir / "osm_map.jpg", dpi=300, bbox_inches="tight")
        plt.show()



def main():
    map_gen = OSMMapGenerator(56.9198, 23.8714, 500)
    map_gen.generate_map()

main()
