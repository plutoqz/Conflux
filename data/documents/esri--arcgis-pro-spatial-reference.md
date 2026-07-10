<!-- source: https://pro.arcgis.com/en/pro-app/latest/help/mapping/properties/coordinate-systems-and-projections.htm -->
# Coordinate systems, map projections, and transformations | ArcGIS Pro documentation

> Source: https://pro.arcgis.com/en/pro-app/latest/help/mapping/properties/coordinate-systems-and-projections.htm

##### Table of Contents

Table of Contents

# Coordinate systems, map projections, and transformations

Coordinate systems, map projections, and transformations
Data usually comprises an array of numbers. Spatial data is similar, but it also includes numerical information that allows you to position it on earth. These numbers are part of acoordinate systemthat provides a frame of reference for your data to locate features on the surface of the earth, to align your data relative to other data, to perform spatially accurate analysis, to add to and edit the data, and to create maps.

Data usually comprises an array of numbers. Spatial data is similar, but it also includes numerical information that allows you to position it on earth. These numbers are part of a
coordinate system
that provides a frame of reference for your data to locate features on the surface of the earth, to align your data relative to other data, to perform spatially accurate analysis, to add to and edit the data, and to create maps.
All spatial data is created in a coordinate system, whether it is points, lines, polygons, rasters, or annotation. The coordinates can be specified in many units, such as decimal degrees, feet, meters, or kilometers; any form of measurement can be used as a coordinate system. Identifying this measurement system is the first step to choosing a coordinate system that displays your data in its correct position in ArcGIS Pro, in relation to your other data.

All spatial data is created in a coordinate system, whether it is points, lines, polygons, rasters, or annotation. The coordinates can be specified in many units, such as decimal degrees, feet, meters, or kilometers; any form of measurement can be used as a coordinate system. Identifying this measurement system is the first step to choosing a coordinate system that displays your data in its correct position in ArcGIS Pro, in relation to your other data.
Maps and scenes in ArcGIS Pro must have a horizontal coordinate system and can optionally have a vertical coordinate system. In some specific workflows, a map may have anunknown coordinate system. To learn more, seeWork with coordinate systems.

Maps and scenes in ArcGIS Pro must have a horizontal coordinate system and can optionally have a vertical coordinate system. In some specific workflows, a map may have an
unknown coordinate system
. To learn more, see
Work with coordinate systems
.

## Coordinate systems

Coordinate systems
Data is defined in both horizontal and vertical coordinate systems. Horizontal coordinate systems locate data across the surface of the earth, and vertical coordinate systems locate the relative height or depth of data.

Data is defined in both horizontal and vertical coordinate systems. Horizontal coordinate systems locate data across the surface of the earth, and vertical coordinate systems locate the relative height or depth of data.

### Horizontal coordinate systems

Horizontal coordinate systems
Horizontal coordinate systems can be of three types: geographic, projected, or local. You can determine which type of coordinate system your data uses by examining the layer's properties.

Horizontal coordinate systems can be of three types: geographic, projected, or local. You can determine which type of coordinate system your data uses by examining the layer's properties.
Geographic coordinate systems are based on a three-dimensional ellipsoidal or spherical surface, and locations are defined using angular measurements, usually in decimal degrees, measuring degrees of longitude (x-coordinates) and degrees of latitude (y-coordinates). The location of data is expressed as positive or negative numbers: positive x- and y-values for north of the equator and east of the prime meridian and negative values for south of the equator and west of the prime meridian.

Geographic coordinate systems are based on a three-dimensional ellipsoidal or spherical surface, and locations are defined using angular measurements, usually in decimal degrees, measuring degrees of longitude (x-coordinates) and degrees of latitude (y-coordinates). The location of data is expressed as positive or negative numbers: positive x- and y-values for north of the equator and east of the prime meridian and negative values for south of the equator and west of the prime meridian.
Download thelist of supported geographic and vertical coordinate systems.

Download the
list of supported geographic and vertical coordinate systems
.
Projected coordinate systems are planar systems that use linear measurements for the coordinates rather than angular units. A projected coordinate system is composed of a geographic coordinate system and amap projectiontogether. A map projection contains the mathematical calculations that convert the angular geodetic coordinates of the geographic coordinate system to Cartesian coordinates of the planar projected coordinate system.

Projected coordinate systems are planar systems that use linear measurements for the coordinates rather than angular units. A projected coordinate system is composed of a geographic coordinate system and a
map projection
together. A map projection contains the mathematical calculations that convert the angular geodetic coordinates of the geographic coordinate system to Cartesian coordinates of the planar projected coordinate system.
Download thelist of supported projected coordinate systems.

Download the
list of supported projected coordinate systems
.
A geographic coordinate system (left) measured in angular units is compared to a projected coordinate system (right) measured in linear units (meters) for the same location in the Atlantic Ocean.
A local coordinate system uses a false origin (0, 0 or other values) in an arbitrary location anywhere on earth. Local coordinate systems are often used for large-scale (small area) mapping. The false origin may or may not be aligned to a known real-world coordinate, but for the purpose of data capture, bearings and distances can be measured using the local coordinate system rather than global coordinates. Local coordinate systems are usually expressed in meters or feet.

A local coordinate system uses a false origin (0, 0 or other values) in an arbitrary location anywhere on earth. Local coordinate systems are often used for large-scale (small area) mapping. The false origin may or may not be aligned to a known real-world coordinate, but for the purpose of data capture, bearings and distances can be measured using the local coordinate system rather than global coordinates. Local coordinate systems are usually expressed in meters or feet.

### Vertical coordinate systems

Vertical coordinate systems
Vertical coordinate systemsprovide a reference for z-coordinates, which are measurements of the height or depth of features. They are always measured in linear units such as meters or feet. Using a vertical coordinate system improves locational accuracy in analysis and editing but they are not applied by default to new maps and scenes; you must explicitly choose one.

Vertical coordinate systems
provide a reference for z-coordinates, which are measurements of the height or depth of features. They are always measured in linear units such as meters or feet. Using a vertical coordinate system improves locational accuracy in analysis and editing but they are not applied by default to new maps and scenes; you must explicitly choose one.
Vertical coordinate systems are either gravity based or ellipsoidal. Gravity-based vertical coordinate systems are more commonly used. They reference a mean sea level calculation (or in some cases, derived from the level of a single point). Ellipsoidal coordinate systems reference a mathematically derived spheroidal or ellipsoidal surface. Since they are calculated on a mathematical model, ellipsoidal coordinate systems are simpler than gravity-based vertical coordinate systems, but they may lack significant accuracy, especially in large-scale applications. For example, a stream in a large-scale map may appear to flow in a different direction using an ellipsoidal vertical coordinate system. When you use an ellipsoidal vertical coordinate system, you must ensure that it matches the horizontal geographic coordinate system. For example, if z-value height is defined in NAD 1983, the geographic coordinate system or the geographic coordinate system within a projected coordinate system must also be defined in NAD 1983 and not in WGS 1984.

Vertical coordinate systems are either gravity based or ellipsoidal. Gravity-based vertical coordinate systems are more commonly used. They reference a mean sea level calculation (or in some cases, derived from the level of a single point). Ellipsoidal coordinate systems reference a mathematically derived spheroidal or ellipsoidal surface. Since they are calculated on a mathematical model, ellipsoidal coordinate systems are simpler than gravity-based vertical coordinate systems, but they may lack significant accuracy, especially in large-scale applications. For example, a stream in a large-scale map may appear to flow in a different direction using an ellipsoidal vertical coordinate system. When you use an ellipsoidal vertical coordinate system, you must ensure that it matches the horizontal geographic coordinate system. For example, if z-value height is defined in NAD 1983, the geographic coordinate system or the geographic coordinate system within a projected coordinate system must also be defined in NAD 1983 and not in WGS 1984.
Vertical coordinate systems in a global scene must be ellipsoidal, with one exception. They can be gravity based only if they cover a full-world extent. EGM2008 Geoid and EGM96 Geoid are examples of global gravity-based vertical coordinate systems.

Vertical coordinate systems in a global scene must be ellipsoidal, with one exception. They can be gravity based only if they cover a full-world extent. EGM2008 Geoid and EGM96 Geoid are examples of global gravity-based vertical coordinate systems.

##### Caution:

Caution:
Be aware that the ellipsoidal vertical coordinate system is not taken into account when a scene draws. This may be noticeable if youextrudefeatures.

Be aware that the ellipsoidal vertical coordinate system is not taken into account when a scene draws. This may be noticeable if you
extrude
features.
Download thelist of supported geographic and vertical coordinate systems.

Download the
list of supported geographic and vertical coordinate systems
.

## Map projections

Map projections
A map projection is the means by which you display the coordinate system and your data on a flat surface, such as a piece of paper or a digital screen. Mathematical calculations in the map projection are used to convert the coordinate system used on the curved surface of earth to one used on a flat surface. Since there is no perfect way to transpose a curved surface to a flat surface without some distortion, various map projections exist to satisfy different compromises. Some map projections preserve area, while others preserve local angles. Some preserve specific distances or directions. The extent, location, and property (area, distance, or shape) you want to preserve must inform your choice of map projection for your projected coordinate system. There are approximately 6,000 coordinate systems in ArcGIS, so it is likely you'll find one to match your data. If not, you can create a custom projected coordinate system from more than 100map projectionsto display the data.

A map projection is the means by which you display the coordinate system and your data on a flat surface, such as a piece of paper or a digital screen. Mathematical calculations in the map projection are used to convert the coordinate system used on the curved surface of earth to one used on a flat surface. Since there is no perfect way to transpose a curved surface to a flat surface without some distortion, various map projections exist to satisfy different compromises. Some map projections preserve area, while others preserve local angles. Some preserve specific distances or directions. The extent, location, and property (area, distance, or shape) you want to preserve must inform your choice of map projection for your projected coordinate system. There are approximately 6,000 coordinate systems in ArcGIS, so it is likely you'll find one to match your data. If not, you can create a custom projected coordinate system from more than 100
map projections
to display the data.
ArcGIS Pro reprojects data on the fly so any data you add to a map adopts the coordinate system definition of the first layer added. As long as the first layer added has its coordinate system correctly defined, all other data with correct coordinate system information reprojects on the fly to the coordinate system of the map. This approach facilitates exploring and mapping data, but it should not be used for analysis or editing, because it can lead to inaccuracies from misaligned data among layers. Data is also slower to draw when it is projected on the fly. If you intend to perform analysis or edit the data, firstproject it into a consistent coordinate systemshared by all your layers. This creates a new version of your data.

ArcGIS Pro reprojects data on the fly so any data you add to a map adopts the coordinate system definition of the first layer added. As long as the first layer added has its coordinate system correctly defined, all other data with correct coordinate system information reprojects on the fly to the coordinate system of the map. This approach facilitates exploring and mapping data, but it should not be used for analysis or editing, because it can lead to inaccuracies from misaligned data among layers. Data is also slower to draw when it is projected on the fly. If you intend to perform analysis or edit the data, first
project it into a consistent coordinate system
shared by all your layers. This creates a new version of your data.
See a list of all themap projectionssupported in ArcGIS Pro.

See a list of all the
map projections
supported in ArcGIS Pro.
Download aposter that compares all the map projections.

Download a
poster that compares all the map projections
.

## Transformations

Transformations
After defining the coordinate system that matches your data, you may still want to use data in a different coordinate system. This is whentransformationsare useful. Transformations convert data between different geographic coordinate systems or between different vertical coordinate systems. Unless your data lines up, you'll encounter difficulties and inaccuracies in any analysis and mapping you perform on the mismatched data.

After defining the coordinate system that matches your data, you may still want to use data in a different coordinate system. This is when
transformations
are useful. Transformations convert data between different geographic coordinate systems or between different vertical coordinate systems. Unless your data lines up, you'll encounter difficulties and inaccuracies in any analysis and mapping you perform on the mismatched data.
Download thelist of supported geographic and vertical transformations.

Download the
list of supported geographic and vertical transformations
.

## Related topics

Related topics
- Work with coordinate systems
Work with coordinate systems

Work with coordinate systems
- Geographic datum transformations
Geographic datum transformations

Geographic datum transformations
- Vertical coordinate systems
Vertical coordinate systems

Vertical coordinate systems
- Define a new coordinate system
Define a new coordinate system

Define a new coordinate system