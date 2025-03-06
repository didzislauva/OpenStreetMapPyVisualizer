import numpy as np
import requests
import json
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon

# Define Overpass API URL
overpass_url = "http://overpass-api.de/api/interpreter"

# Define a properly proportioned bounding box near Riga, Latvia
# At this latitude, longitude degrees are more stretched than latitude degrees
# Longitude: 1 degree ≈ 66.4 km
# Latitude: 1 degree ≈ 111.3 km
# To make a square 1km x 1km area, we need different deltas for lat/lon

# Define center point
center_lat, center_lon = 56.855, 24.305  # Salaspils area near Riga

# Define size in km
size_km = 1.0

# Calculate deltas (converting km to degrees)
delta_lat = size_km / 111.3  # approximately 0.009 degrees
delta_lon = size_km / (111.3 * np.cos(np.radians(center_lat)))  # approximately 0.015 degrees

# Calculate bounding box
south = center_lat - delta_lat/2
north = center_lat + delta_lat/2
west = center_lon - delta_lon/2
east = center_lon + delta_lon/2

print(f"Using bounding box: S={south}, W={west}, N={north}, E={east}")
bbox = f"{south},{west},{north},{east}"  # Overpass format: south, west, north, east

# Define Overpass API queries for roads, buildings, and forests
queries = {
    "roads": f"""
    [out:json];
    (
      way["highway"]({bbox});
    );
    out geom;
    """,
    "buildings": f"""
    [out:json];
    (
      way["building"]({bbox});
    );
    out geom;
    """,
    "forests": f"""
    [out:json];
    (
      way["landuse"="forest"]({bbox});
    );
    out geom;
    """
}

# Function to fetch and save OSM data
def fetch_osm_data(query, filename):
    print(f"Fetching {filename}...")
    response = requests.get(overpass_url, params={"data": query})
    if response.status_code == 200:
        data = response.json()
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Successfully fetched {filename}")
        return data
    else:
        print(f"❌ Failed to fetch {filename}: Status code {response.status_code}")
        print(response.text)
        return None

# Function to process OSM data into GeoDataFrame
def process_osm_data(data, feature_type="line"):
    if not data or "elements" not in data:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    
    geometries = []
    properties = []
    
    for element in data.get("elements", []):
        if element["type"] == "way" and "geometry" in element:
            # Extract coordinates directly from the geometry field
            coords = [(node["lon"], node["lat"]) for node in element["geometry"]]
            
            if len(coords) < 2:
                continue
                
            # Create the appropriate geometry type
            if feature_type == "polygon" and len(coords) >= 3:
                # Close the polygon if needed
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                geo = Polygon(coords)
            else:
                geo = LineString(coords)
                
            geometries.append(geo)
            
            # Extract properties
            props = {k: v for k, v in element.get("tags", {}).items()}
            properties.append(props)
    
    # Create GeoDataFrame with properties
    if geometries:
        gdf = gpd.GeoDataFrame(properties, geometry=geometries, crs="EPSG:4326")
        return gdf
    else:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

# Main process: fetch and process data
print("Starting data fetch and map generation...")

# Fetch OSM data
roads_data = fetch_osm_data(queries["roads"], "roads.json")
buildings_data = fetch_osm_data(queries["buildings"], "buildings.json")
forests_data = fetch_osm_data(queries["forests"], "forests.json")

# Process into GeoDataFrames
roads_gdf = process_osm_data(roads_data, "line")
buildings_gdf = process_osm_data(buildings_data, "polygon")
forests_gdf = process_osm_data(forests_data, "polygon")

# Debug: Check if data exists
print("✅ Roads found:", len(roads_gdf))
print("✅ Buildings found:", len(buildings_gdf))
print("✅ Forests found:", len(forests_gdf))

# Create a square figure
fig, ax = plt.subplots(figsize=(10, 10))

# Set equal aspect ratio to ensure proper proportions
ax.set_aspect('equal')

# Plot features with better styling
if not forests_gdf.empty:
    forests_gdf.plot(ax=ax, color="darkgreen", alpha=0.5, label="Forests")

if not buildings_gdf.empty:
    buildings_gdf.plot(ax=ax, color="firebrick", alpha=0.7, edgecolor="black", linewidth=0.5, label="Buildings")

if not roads_gdf.empty:
    # Style roads by type if available
    highway_types = roads_gdf["highway"].unique() if "highway" in roads_gdf.columns else []
    
    if len(highway_types) > 1:
        # Plot different road types with different styles
        for road_type in highway_types:
            subset = roads_gdf[roads_gdf["highway"] == road_type]
            if road_type in ["motorway", "trunk", "primary"]:
                subset.plot(ax=ax, color="orangered", linewidth=2.5, label=f"{road_type} road")
            elif road_type in ["secondary", "tertiary"]:
                subset.plot(ax=ax, color="orange", linewidth=1.8, label=f"{road_type} road")
            elif road_type in ["residential", "service"]:
                subset.plot(ax=ax, color="gray", linewidth=1.2, label=f"{road_type} road")
            else:
                subset.plot(ax=ax, color="black", linewidth=0.8, linestyle="--", label=f"{road_type}")
    else:
        # Simple road styling if types not available
        roads_gdf.plot(ax=ax, color="black", linewidth=1.5, label="Roads")

# Add map details
ax.set_title("OpenStreetMap Visualization - Salaspils area near Riga, Latvia")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")

# Set extent to match our bounding box exactly
ax.set_xlim(west, east)
ax.set_ylim(south, north)

# Remove duplicates in legend
handles, labels = ax.get_legend_handles_labels()
by_label = dict(zip(labels, handles))
if by_label:
    ax.legend(by_label.values(), by_label.keys(), loc='best', frameon=True, framealpha=0.8)

# Add scale bar (approximate)
def add_scale_bar(ax, length_km=0.25):
    # Convert length to coordinates
    x_start, y_start = 0.05, 0.05  # Position in axis coordinates
    
    # Convert km to degrees (approximate at this latitude)
    length_deg_lon = length_km / (111.3 * np.cos(np.radians(center_lat)))
    
    # Convert to axis coordinates
    x_end = x_start + length_deg_lon / (east - west)
    
    # Add scale bar
    ax.plot([west + x_start * (east - west), west + x_end * (east - west)], 
            [south + y_start * (north - south), south + y_start * (north - south)], 
            'k-', linewidth=3, transform=ax.transData)
    
    # Add text
    ax.text(west + ((x_start + x_end) / 2) * (east - west),
            south + (y_start - 0.02) * (north - south),
            f"{length_km} km", ha='center', transform=ax.transData)

add_scale_bar(ax)

# Add north arrow
ax.annotate('N', xy=(0.95, 0.95), xycoords='axes fraction',
            xytext=(0.95, 0.85), textcoords='axes fraction',
            arrowprops=dict(facecolor='black', width=5, headwidth=15),
            ha='center', va='center', fontsize=12, fontweight='bold')

# Save map as JPG and PDF
plt.savefig("map.jpg", dpi=300, bbox_inches="tight")
plt.savefig("map.pdf", dpi=300, bbox_inches="tight")

# Show the plot
plt.tight_layout()
plt.show()

print("✅ Map successfully generated: 'map.jpg' and 'map.pdf' 🎉")
