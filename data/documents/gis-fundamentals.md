<!-- source: synthetic -->
# GIS Fundamentals — A Technical Primer

> Source: Synthetic document for RAG evaluation
> Topics: GIS concepts, data models, spatial analysis

## Introduction to GIS

A Geographic Information System (GIS) is a framework for gathering, managing,
and analyzing data. Rooted in the science of geography, GIS integrates many
types of data. It analyzes spatial location and organizes layers of information
into visualizations using maps and 3D scenes.

## Data Models

### Vector Data Model

Vector data represents geographic features as discrete objects: points, lines,
and polygons. Each feature has attributes stored in a table.

- **Points**: Represent discrete locations (e.g., cities, wells, sensors)
- **Lines**: Represent linear features (e.g., roads, rivers, pipelines)
- **Polygons**: Represent area features (e.g., lakes, parcels, countries)

### Raster Data Model

Raster data represents the world as a grid of cells (pixels). Each cell stores
a single value representing information such as elevation, temperature, or land
cover classification.

Key characteristics:
- Cell size (spatial resolution)
- Number of rows and columns
- Single or multiple bands
- Continuous vs. discrete values

### TIN (Triangulated Irregular Network)

A TIN is a vector-based representation of a continuous surface, constructed
from a set of irregularly spaced points. TINs are commonly used for high-precision
terrain modeling.

## Coordinate Systems

### Geographic Coordinate Systems (GCS)

Uses a three-dimensional spherical surface to define locations on the Earth.
Locations are measured in angular units (degrees) of latitude and longitude.

Common GCS: WGS 84, NAD83, CGCS2000

### Projected Coordinate Systems (PCS)

A PCS projects the Earth's curved surface onto a flat, two-dimensional plane.
Locations are measured in linear units (meters, feet).

Common projections:
- **Mercator**: Preserves angles, distorts area
- **UTM (Universal Transverse Mercator)**: Divides Earth into 60 zones
- **Albers Equal Area**: Preserves area, good for regional mapping
- **Lambert Conformal Conic**: Preserves shape for mid-latitude regions

## Spatial Analysis Methods

### Buffer Analysis

Creates zones of a specified distance around features.

### Overlay Analysis

Combines multiple layers to identify relationships:
- **Intersect**: Areas common to all inputs
- **Union**: All areas from all inputs combined
- **Erase**: Removes areas of one input from another

### Network Analysis

Analyzes transportation networks:
- Shortest path
- Service area
- Location-allocation
- OD cost matrix

### Surface Analysis

Analyzes continuous surfaces (e.g., elevation):
- Slope, aspect, hillshade
- Viewshed analysis
- Contour generation
- Cut/fill calculations

### Statistical Analysis

- **Hot Spot Analysis (Getis-Ord Gi*)**: Identifies statistically significant
  clusters of high and low values
- **Spatial Autocorrelation (Moran's I)**: Measures how clustered or dispersed
  features are
- **Kriging**: Advanced geostatistical interpolation method

## Geodatabase Concepts

The geodatabase is the native data structure for ArcGIS and is the primary data
format used for editing and data management. It supports:

- **Feature classes**: Collections of geographic features with the same geometry type
- **Feature datasets**: Collections of feature classes that share a coordinate system
- **Topology**: Rules defining how features share geometry
- **Relationship classes**: Associations between feature classes or tables
- **Network datasets**: Connectivity models for transportation networks
- **Mosaic datasets**: Manage and serve large collections of raster data
