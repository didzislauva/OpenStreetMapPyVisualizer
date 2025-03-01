# OpenStreetMap Data Visualization with Python

## Overview
This project fetches OpenStreetMap (OSM) data for a **1 km × 1 km area** near Riga, Latvia (Salaspils area), processes it into geographic data, and generates a high-quality **JPG and PDF map**. The map includes:

✅ Roads (classified by type: highways, residential, service roads, etc.)  
✅ Buildings (displayed as polygons)  
✅ Forests (land use areas)  
✅ Scale bar and north arrow for reference  
✅ Proper aspect ratio correction to prevent distortion  

---

## Features
- **Fetches OSM Data**: Uses Overpass API to retrieve roads, buildings, and land use (forests).
- **Processes OSM Data**: Converts JSON data into GeoDataFrames with accurate geometries.
- **Improved Visualization**:
  - Roads classified by type and styled accordingly.
  - Buildings displayed as filled polygons.
  - Forests rendered with transparency for visibility.
- **Corrected Aspect Ratio**: Adjusts for **latitude compression** to ensure correct proportions.
- **Scale Bar & North Arrow**: Adds a **real-world distance reference** and orientation guide.
- **High-Quality Output**: Saves the map as **map.jpg** and **map.pdf**.

---

## Installation
### 1️⃣ Install Dependencies
Make sure you have Python installed, then run:
```bash
pip install requests geopandas matplotlib shapely numpy
```

---

## Usage
### 2️⃣ Run the Script
Execute the Python script to fetch OSM data and generate the map:
```bash
python script.py
```

### 3️⃣ View Output
- The generated map will be saved as:
  - **map.jpg** (for quick viewing)
  - **map.pdf** (for printing or detailed inspection)

---

## Adjusting the Map
- **Change the Location**: Modify the bounding box coordinates in the script:
  ```python
  south, west, north, east = 56.850, 24.300, 56.860, 24.310  # Salaspils area
  ```
- **Increase Coverage**: Expand the bounding box size (`bbox_size = 0.01` for 2 km²).
- **Modify Styling**: Change road colors, building transparency, or add more layers.

---

## Troubleshooting
- **Map appears stretched?** → Ensure aspect ratio correction is applied:
  ```python
  import numpy as np
  mean_lat = (south + north) / 2
  aspect_correction = np.cos(np.radians(mean_lat))
  ax.set_aspect(1 / aspect_correction)
  ```
- **No data in map?** → Increase bounding box size or select a more urban area.
- **OSM API errors?** → Try again later (Overpass API may throttle excessive requests).

---

## Future Enhancements
🚀 Add a background **basemap** (satellite, OpenStreetMap tiles) using `contextily`.  
🚀 Overlay **elevation contours** by fetching **DEM (Digital Elevation Model) data**.  

---

## Screenshot
![image](https://github.com/user-attachments/assets/63644593-d8b3-4459-aed1-0d00b6842fd6)


## License
This project is open-source under the **MIT License**.

---

📌 **Author:** Didzis Lauva   
📅 **Last Updated:** 2025-03-01  

