<!-- source: https://en.wikipedia.org/wiki/Digital_elevation_model -->
# Digital elevation model

> Source: https://en.wikipedia.org/wiki/Digital_elevation_model
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
3D computer-generated imagery and measurements of terrain
3D rendering
of a DTM of
Tithonium Chasma
on
Mars
Adigital elevation model(DEM) ordigital surface model(DSM) is a3D computer graphicsrepresentation ofelevationdata to representterrainor overlaying objects, commonly of aplanet,moon, orasteroid. A "global DEM" refers to adiscrete global grid. DEMs are used often ingeographic information systems(GIS), and are the most common basis for digitally producedrelief maps.
Adigital terrain model(DTM) represents specifically the ground surface while DEM and DSM may represent tree topcanopyorbuildingroofs.

A
digital elevation model
(
DEM
) or
digital surface model
(
DSM
) is a
3D computer graphics
representation of
elevation
data to represent
terrain
or overlaying objects, commonly of a
planet
,
moon
, or
asteroid
. A "global DEM" refers to a
discrete global grid
. DEMs are used often in
geographic information systems
(GIS), and are the most common basis for digitally produced
relief maps
.
A
digital terrain model
(
DTM
) represents specifically the ground surface while DEM and DSM may represent tree top
canopy
or
building
roofs.
While a DSM may be useful forlandscape modeling,city modelingand visualization applications, a DTM is often required for flood or drainage modeling,land-use studies,[1]geological applications,[2]and other applications,[3]and inplanetary science.

While a DSM may be useful for
landscape modeling
,
city modeling
and visualization applications, a DTM is often required for flood or drainage modeling,
land-use studies
,
[
1
]
geological applications,
[
2
]
and other applications,
[
3
]
and in
planetary science
.

## Terminology

Terminology
[
edit
]
Surfaces represented by a Digital Surface Model include buildings and other objects. Digital Terrain Models represent the bare ground.
There is no universal usage of the termsdigital elevation model(DEM),digital terrain model(DTM) anddigital surface model(DSM) in scientific literature. In most cases the termdigital surface modelrepresents the earth's surface and includes all objects on it. In contrast to a DSM, thedigital terrain model(DTM) represents the bare ground surface without any objects like plants and buildings (see the figure on the right).[4][5]

There is no universal usage of the terms
digital elevation model
(DEM),
digital terrain model
(DTM) and
digital surface model
(DSM) in scientific literature. In most cases the term
digital surface model
represents the earth's surface and includes all objects on it. In contrast to a DSM, the
digital terrain model
(DTM) represents the bare ground surface without any objects like plants and buildings (see the figure on the right).
[
4
]
[
5
]
DEM is often used as a generic term for DSMs and DTMs,[6]only representing height information without any further definition about the surface.[7]Other definitions equalise the terms DEM and DTM,[8]equalise the terms DEM and DSM,[9]define the DEM as a subset of the DTM, which also represents other morphological elements,[10]or define a DEM as a rectangulargridand a DTM as a three-dimensional model (TIN).[11]Most of the data providers (USGS,ERSDAC,CGIAR,Spot Image) use the term DEM as a generic term for DSMs and DTMs. Some datasets such asSRTMor theASTER GDEMare originally DSMs, although in forested areas, SRTM reaches into the tree canopy giving readings somewhere between a DSM and a DTM). DTMs are created from high resolution DSM datasets using complex algorithms to filter out buildings and other objects, a process known as "bare-earth extraction".[5][12]In the following, the term DEM is used as a generic term for DSMs and DTMs.

DEM is often used as a generic term for DSMs and DTMs,
[
6
]
only representing height information without any further definition about the surface.
[
7
]
Other definitions equalise the terms DEM and DTM,
[
8
]
equalise the terms DEM and DSM,
[
9
]
define the DEM as a subset of the DTM, which also represents other morphological elements,
[
10
]
or define a DEM as a rectangular
grid
and a DTM as a three-dimensional model (
TIN
).
[
11
]
Most of the data providers (
USGS
,
ERSDAC
,
CGIAR
,
Spot Image
) use the term DEM as a generic term for DSMs and DTMs. Some datasets such as
SRTM
or the
ASTER GDEM
are originally DSMs, although in forested areas, SRTM reaches into the tree canopy giving readings somewhere between a DSM and a DTM). DTMs are created from high resolution DSM datasets using complex algorithms to filter out buildings and other objects, a process known as "bare-earth extraction".
[
5
]
[
12
]
In the following, the term DEM is used as a generic term for DSMs and DTMs.

## Types

Types
[
edit
]
Heightmap of Earth's surface (including water and ice), rendered as an
equirectangular projection
with elevations indicated as normalized 8-bit grayscale, where lighter values indicate higher elevation
A DEM can be represented as araster(a grid of squares, also known as aheightmapwhen representing elevation) or as a vector-basedtriangular irregular network(TIN).[13]The TIN DEM dataset is also referred to as a primary (measured) DEM, whereas the Raster DEM is referred to as a secondary (computed) DEM.[14]The DEM could be acquired through techniques such asphotogrammetry,lidar,IfSARorInSAR,land surveying, etc. (Li et al. 2005).

A DEM can be represented as a
raster
(a grid of squares, also known as a
heightmap
when representing elevation) or as a vector-based
triangular irregular network
(TIN).
[
13
]
The TIN DEM dataset is also referred to as a primary (measured) DEM, whereas the Raster DEM is referred to as a secondary (computed) DEM.
[
14
]
The DEM could be acquired through techniques such as
photogrammetry
,
lidar
,
IfSAR
or
InSAR
,
land surveying
, etc. (Li et al. 2005).
DEMs are commonly built using data collected using remote sensing techniques, but they may also be built from land surveying.

DEMs are commonly built using data collected using remote sensing techniques, but they may also be built from land surveying.

### Rendering

Rendering
[
edit
]
Relief map of Spain's Sierra Nevada, showing use of both shading and false color as visualization tools to indicate elevation
The digital elevation model itself consists of a matrix of numbers, but the data from a DEM is often rendered in visual form to make it understandable to humans.  This visualization may be in the form of a contouredtopographic map, or could use shading andfalse colorassignment (or "pseudo-color") to render elevations as colors (for example, using green for the lowest elevations, shading to red, with white for the highest elevation.).

The digital elevation model itself consists of a matrix of numbers, but the data from a DEM is often rendered in visual form to make it understandable to humans.  This visualization may be in the form of a contoured
topographic map
, or could use shading and
false color
assignment (or "pseudo-color") to render elevations as colors (for example, using green for the lowest elevations, shading to red, with white for the highest elevation.).
Visualizations are sometimes also done as oblique views, reconstructing a synthetic visual image of the terrain as it would appear looking down at an angle. In these oblique visualizations, elevations are sometimes scaled using "vertical exaggeration" in order to make subtle elevation differences more noticeable.[15]Some scientists,[16][17]however, object to vertical exaggeration as misleading the viewer about the true landscape.

Visualizations are sometimes also done as oblique views, reconstructing a synthetic visual image of the terrain as it would appear looking down at an angle. In these oblique visualizations, elevations are sometimes scaled using "
vertical exaggeration
" in order to make subtle elevation differences more noticeable.
[
15
]
Some scientists,
[
16
]
[
17
]
however, object to vertical exaggeration as misleading the viewer about the true landscape.

## Production

Production
[
edit
]
Mappers may prepare digital elevation models in a number of ways, but they frequently useremote sensingrather than directsurveydata.

Mappers may prepare digital elevation models in a number of ways, but they frequently use
remote sensing
rather than direct
survey
data.
Older methods of generating DEMs often involveinterpolatingdigital contour maps that may have been produced by direct survey of the land surface. This method is still used inmountainareas, whereinterferometryis not always satisfactory. Note thatcontour linedata or any other sampled elevation datasets (by GPS or ground survey) are not DEMs, but may be considered digital terrain models. A DEM implies that elevation is available continuously at each location in the study area.

Older methods of generating DEMs often involve
interpolating
digital contour maps that may have been produced by direct survey of the land surface. This method is still used in
mountain
areas, where
interferometry
is not always satisfactory. Note that
contour line
data or any other sampled elevation datasets (by GPS or ground survey) are not DEMs, but may be considered digital terrain models. A DEM implies that elevation is available continuously at each location in the study area.

### Satellite mapping

Satellite mapping
[
edit
]
One powerful technique for generating digital elevation models isinterferometric synthetic aperture radarwhere two passes of a radar satellite (such asRADARSAT-1orTerraSAR-XorCosmo SkyMed), or a single pass if the satellite is equipped with two antennas (like theSRTMinstrumentation), collect sufficient data to generate a digital elevation map tens of kilometers on a side with a resolution of around ten meters.[18]Other kinds ofstereoscopicpairs can be employed using thedigital image correlationmethod, where two optical images are acquired with different angles taken from the same pass of an airplane or anEarth Observation Satellite(such as the HRS instrument ofSPOT5or theVNIRband ofASTER).[19]

One powerful technique for generating digital elevation models is
interferometric synthetic aperture radar
where two passes of a radar satellite (such as
RADARSAT-1
or
TerraSAR-X
or
Cosmo SkyMed
), or a single pass if the satellite is equipped with two antennas (like the
SRTM
instrumentation), collect sufficient data to generate a digital elevation map tens of kilometers on a side with a resolution of around ten meters.
[
18
]
Other kinds of
stereoscopic
pairs can be employed using the
digital image correlation
method, where two optical images are acquired with different angles taken from the same pass of an airplane or an
Earth Observation Satellite
(such as the HRS instrument of
SPOT5
or the
VNIR
band of
ASTER
).
[
19
]
TheSPOT 1 satellite(1986) provided the first usable elevation data for a sizeable portion of the planet's landmass, using two-pass stereoscopic correlation. Later, further data were provided by theEuropean Remote-Sensing Satellite(ERS, 1991) using the same method, theShuttle Radar Topography Mission(SRTM, 2000) using single-pass SAR and theAdvanced Spaceborne Thermal Emission and Reflection Radiometer(ASTER, 2000) instrumentation on theTerra satelliteusing double-pass stereo pairs.[19]

The
SPOT 1 satellite
(1986) provided the first usable elevation data for a sizeable portion of the planet's landmass, using two-pass stereoscopic correlation. Later, further data were provided by the
European Remote-Sensing Satellite
(ERS, 1991) using the same method, the
Shuttle Radar Topography Mission
(SRTM, 2000) using single-pass SAR and the
Advanced Spaceborne Thermal Emission and Reflection Radiometer
(ASTER, 2000) instrumentation on the
Terra satellite
using double-pass stereo pairs.
[
19
]
The HRS instrument on SPOT 5 has acquired over 100 million square kilometers of stereo pairs.

The HRS instrument on SPOT 5 has acquired over 100 million square kilometers of stereo pairs.

### Planetary mapping

Planetary mapping
[
edit
]
MOLA digital elevation model showing the two hemispheres of Mars. This image appeared on the cover of
Science
magazine in May 1999.
A tool of increasing value inplanetary sciencehas been use of orbital altimetry used to make digital elevation map of planets.  A primary tool for this islaser altimetrybut radar altimetry is also used.[20]Planetary digital elevation maps made using laser altimetry include theMars Orbiter Laser Altimeter(MOLA) mapping of Mars,[21]theLunar Orbital Laser Altimeter(LOLA)[22]and Lunar Altimeter (LALT) mapping of the Moon, and the Mercury Laser Altimeter (MLA) mapping of Mercury.[23]In planetary mapping, each planetary body has a unique reference surface.[24]New Horizons'Long Range Reconnaissance Imager used stereo photogrammetry to produce partial surface elevation maps ofPlutoand486958 Arrokoth.[25][26]

A tool of increasing value in
planetary science
has been use of orbital altimetry used to make digital elevation map of planets.  A primary tool for this is
laser altimetry
but radar altimetry is also used.
[
20
]
Planetary digital elevation maps made using laser altimetry include the
Mars Orbiter Laser Altimeter
(MOLA) mapping of Mars,
[
21
]
the
Lunar Orbital Laser Altimeter
(LOLA)
[
22
]
and Lunar Altimeter (LALT) mapping of the Moon, and the Mercury Laser Altimeter (MLA) mapping of Mercury.
[
23
]
In planetary mapping, each planetary body has a unique reference surface.
[
24
]
New Horizons'
Long Range Reconnaissance Imager used stereo photogrammetry to produce partial surface elevation maps of
Pluto
and
486958 Arrokoth
.
[
25
]
[
26
]

### Methods for obtaining elevation data used to create DEMs

Methods for obtaining elevation data used to create DEMs
[
edit
]
Gatewing X100
unmanned aerial vehicle
- Lidar[27]
Lidar
[
27
]
- Radar
Radar
- Stereo photogrammetryfromaerial surveysStructure from motion/ Multi-view stereo applied to aerial photography[28]
Stereo photogrammetry
from
aerial surveys
- Structure from motion/ Multi-view stereo applied to aerial photography[28]
Structure from motion
/ Multi-view stereo applied to aerial photography
[
28
]
- Block adjustment from optical satellite imagery
Block adjustment from optical satellite imagery
- Interferometry from radar data
Interferometry from radar data
- Real Time KinematicGPS
Real Time Kinematic
GPS
- Topographic maps
Topographic maps
- Theodoliteortotal station
Theodolite
or
total station
- Doppler radar
Doppler radar
- Focus variation
Focus variation
- Inertial surveys
Inertial surveys
- Surveying and mappingdrones
Surveying and mapping
drones
- Range imaging
Range imaging

### Accuracy

Accuracy
[
edit
]
The quality of a DEM is a measure of how accurate elevation is at each pixel (absolute accuracy) and how accurately is the morphology presented (relative accuracy). Quality assessment of DEM can be performed by comparison of DEMs from different sources.[29]Several factors play an important role for quality of DEM-derived products:

The quality of a DEM is a measure of how accurate elevation is at each pixel (absolute accuracy) and how accurately is the morphology presented (relative accuracy). Quality assessment of DEM can be performed by comparison of DEMs from different sources.
[
29
]
Several factors play an important role for quality of DEM-derived products:
- terrain roughness;
terrain roughness
;
- sampling density (elevation data collection method);
sampling density (elevation data collection method);
- grid resolution orpixelsize;
grid resolution or
pixel
size;
- interpolationalgorithm;
interpolation
algorithm;
- vertical resolution;
vertical resolution;
- terrain analysis algorithm;
terrain analysis algorithm;
- Reference 3D products include quality masks that give information on the coastline, lake, snow, clouds, correlation etc.
Reference 3D products include quality masks that give information on the coastline, lake, snow, clouds, correlation etc.

## Uses

Uses
[
edit
]
Digital Elevation Model – Red Rocks Amphitheater, Colorado obtained using a UAV
Bezmiechowa airfield 3D Digital Surface Model obtained using
Pteryx UAV
flying 200 m above hilltop
Digital Surface Model of
motorway
interchange
construction site
. Note that tunnels are closed.
Example DEM flown with the Gatewing X100 in Assenede
Digital Terrain Model Generator + Textures(Maps) + Vectors
Common uses of DEMs include:

Common uses of DEMs include:
- Extracting terrain parameters forgeomorphology
Extracting terrain parameters for
geomorphology
- Modelingwater flowforhydrologyor mass movement (for exampleavalanchesandlandslides)
Modeling
water flow
for
hydrology
or mass movement (for example
avalanches
and
landslides
)
- Modeling soils wetness with Cartographic Depth to Water Indexes (DTW-index)[27]
Modeling soils wetness with Cartographic Depth to Water Indexes (DTW-index)
[
27
]
- Creation of relief maps
Creation of relief maps
- Rendering of3D visualizations.
Rendering of
3D visualizations
.
- 3D flight planningandTERCOM
3D flight planning
and
TERCOM
- Creation of physical models (includingraised relief mapsand 3D printed terrain models)[30]
Creation of physical models (including
raised relief maps
and 3D printed terrain models)
[
30
]
- Rectification ofaerial photographyorsatellite imagery
Rectification of
aerial photography
or
satellite imagery
- Reduction (terrain correction) ofgravitymeasurements (gravimetry,physical geodesy)
Reduction (terrain correction) of
gravity
measurements (
gravimetry
,
physical geodesy
)
- Terrain analysis ingeomorphologyandphysical geography
Terrain analysis in
geomorphology
and
physical geography
- Geographic information systems(GIS)
Geographic information systems
(GIS)
- Engineeringandinfrastructuredesign
Engineering
and
infrastructure
design
- Satellite navigation(for exampleGPSandGLONASS)
Satellite navigation
(for example
GPS
and
GLONASS
)
- Line-of-sight analysis
Line-of-sight analysis
- Base mapping
Base mapping
- Flight simulation
Flight simulation
- Train simulation
Train simulation
- Precision farmingandforestry[31]
Precision farming
and
forestry
[
31
]
- Surface analysis
Surface analysis
- Intelligent transportation systems(ITS)
Intelligent transportation systems
(ITS)
- Auto safety /advanced driver-assistance systems(ADAS)
Auto safety /
advanced driver-assistance systems
(ADAS)
- Archaeology
Archaeology

## Sources

Sources
[
edit
]

### Global

Global
[
edit
]
Released at the beginning of 2022,FABDEMoffers a bare earth simulation of the Earth's surface at 1 arc-second resolution (about 30 meters). Adapted from GLO-30, the data removes all forests and buildings. The data is free to download non-commercially and through thedeveloper's websiteat a cost commercially.

Released at the beginning of 2022,
FABDEM
offers a bare earth simulation of the Earth's surface at 1 arc-second resolution (about 30 meters). Adapted from GLO-30, the data removes all forests and buildings. The data is free to download non-commercially and through the
developer's website
at a cost commercially.
An alternative free global DEM is calledGTOPO30(30arcsecondresolution, c. 1kmalong the equator) is available, but its quality is variable and in some areas it is very poor. A much higher quality DEM from the Advanced Spaceborne Thermal Emission and Reflection Radiometer (ASTER) instrument of theTerra satelliteis also freely available for 99% of the globe, and represents elevation at 30meterresolution. A similarly high resolution was previously only available for theUnited States territoryunder the Shuttle Radar Topography Mission (SRTM) data, while most of the rest of the planet was only covered in a 3 arc-second resolution (around 90 meters  along the equator). SRTM does not cover the polar regions and has mountain and desert no data (void) areas. SRTM data, being derived from radar, represents the elevation of the first-reflected surface—quite often tree tops.  So, the data are not necessarily representative of the ground surface, but the top of whatever is first encountered by the radar.

An alternative free global DEM is called
GTOPO30
(30
arcsecond
resolution
, c. 1
km
along the equator) is available, but its quality is variable and in some areas it is very poor. A much higher quality DEM from the Advanced Spaceborne Thermal Emission and Reflection Radiometer (ASTER) instrument of the
Terra satellite
is also freely available for 99% of the globe, and represents elevation at 30
meter
resolution. A similarly high resolution was previously only available for the
United States territory
under the Shuttle Radar Topography Mission (SRTM) data, while most of the rest of the planet was only covered in a 3 arc-second resolution (around 90 meters  along the equator). SRTM does not cover the polar regions and has mountain and desert no data (void) areas. SRTM data, being derived from radar, represents the elevation of the first-reflected surface—quite often tree tops.  So, the data are not necessarily representative of the ground surface, but the top of whatever is first encountered by the radar.
Submarine elevation (known asbathymetry) data is generated using ship-mounteddepth soundings. When land topography and bathymetry is combined, a trulyglobal relief modelis obtained.   The SRTM30Plus dataset (used inNASA World Wind) attempts to combine GTOPO30, SRTM and bathymetric data to produce a truly global elevation model.[32]The Earth2014 global topography and relief model[33]provides layered topography grids at 1 arc-minute resolution. Other than SRTM30plus, Earth2014 provides information on ice-sheet heights and bedrock (that is, topography below the ice) over Antarctica and Greenland. Another global model is Global Multi-resolution Terrain Elevation Data 2010 (GMTED2010) with 7.5 arc second resolution. It is based on SRTM data and combines other data outside SRTM coverage. A novel global DEM of postings lower than 12 m and a height accuracy of less than 2 m is expected from theTanDEM-Xsatellite mission which started in July 2010.

Submarine elevation (known as
bathymetry
) data is generated using ship-mounted
depth soundings
. When land topography and bathymetry is combined, a truly
global relief model
is obtained.   The SRTM30Plus dataset (used in
NASA World Wind
) attempts to combine GTOPO30, SRTM and bathymetric data to produce a truly global elevation model.
[
32
]
The Earth2014 global topography and relief model
[
33
]
provides layered topography grids at 1 arc-minute resolution. Other than SRTM30plus, Earth2014 provides information on ice-sheet heights and bedrock (that is, topography below the ice) over Antarctica and Greenland. Another global model is Global Multi-resolution Terrain Elevation Data 2010 (GMTED2010) with 7.5 arc second resolution. It is based on SRTM data and combines other data outside SRTM coverage. A novel global DEM of postings lower than 12 m and a height accuracy of less than 2 m is expected from the
TanDEM-X
satellite mission which started in July 2010.
The most common grid (raster) spacing is between 50 and 500 meters. In gravimetry e.g., the primary grid may be 50 m, but is switched to 100 or 500 meters in distances of about 5 or 10 kilometers.

The most common grid (raster) spacing is between 50 and 500 meters. In gravimetry e.g., the primary grid may be 50 m, but is switched to 100 or 500 meters in distances of about 5 or 10 kilometers.
Since 2002, the HRS instrument on SPOT 5 has acquired over 100 million square kilometers of stereo pairs used to produce a DTED2  format DEM (with a 30-meter posting) DEM format DTED2 over 50 million km2.[34]The radar satelliteRADARSAT-2has been used byMacDonald, Dettwiler and Associates Ltd.to provide DEMs for commercial and military customers.[35]

Since 2002, the HRS instrument on SPOT 5 has acquired over 100 million square kilometers of stereo pairs used to produce a DTED2  format DEM (with a 30-meter posting) DEM format DTED2 over 50 million km
2
.
[
34
]
The radar satellite
RADARSAT-2
has been used by
MacDonald, Dettwiler and Associates Ltd.
to provide DEMs for commercial and military customers.
[
35
]
In 2014, acquisitions from radar satellites TerraSAR-X and TanDEM-X will be available in the form of a uniform global coverage with a resolution of 12 meters.[36]

In 2014, acquisitions from radar satellites TerraSAR-X and TanDEM-X will be available in the form of a uniform global coverage with a resolution of 12 meters.
[
36
]
ALOS provides since 2016 a global 1-arc second DSM free of charge,[37]and a commercial 5 meter DSM/DTM.[38]

ALOS provides since 2016 a global 1-arc second DSM free of charge,
[
37
]
and a commercial 5 meter DSM/DTM.
[
38
]

### Local

Local
[
edit
]
Many national mapping agencies produce their own DEMs, often of a higher resolution and quality, but frequently these have to be purchased, and the cost is usually prohibitive to all except public authorities and large corporations. DEMs are often a product ofnational lidar datasetprograms.

Many national mapping agencies produce their own DEMs, often of a higher resolution and quality, but frequently these have to be purchased, and the cost is usually prohibitive to all except public authorities and large corporations. DEMs are often a product of
national lidar dataset
programs.
Free DEMs are also available forMars: the MEGDR, or Mission Experiment Gridded Data Record, from theMars Global Surveyor's Mars Orbiter Laser Altimeter (MOLA) instrument; and NASA's Mars Digital Terrain Model (DTM).[39]

Free DEMs are also available for
Mars
: the MEGDR, or Mission Experiment Gridded Data Record, from the
Mars Global Surveyor
's Mars Orbiter Laser Altimeter (MOLA) instrument; and NASA's Mars Digital Terrain Model (DTM).
[
39
]

### Websites

Websites
[
edit
]
OpenTopography[40]is a web based community resource for access to high-resolution, Earth science-oriented, topography data (lidar and DEM data), and processing tools running on commodity and high performance compute system along with educational resources.[41]OpenTopography is based at the San Diego Supercomputer Center[42]at the University of California San Diego and is operated in collaboration with colleagues in the School of Earth and Space Exploration at Arizona State University and UNAVCO.[43]Core operational support for OpenTopography comes from the National Science Foundation, Division of Earth Sciences.

OpenTopography
[
40
]
is a web based community resource for access to high-resolution, Earth science-oriented, topography data (lidar and DEM data), and processing tools running on commodity and high performance compute system along with educational resources.
[
41
]
OpenTopography is based at the San Diego Supercomputer Center
[
42
]
at the University of California San Diego and is operated in collaboration with colleagues in the School of Earth and Space Exploration at Arizona State University and UNAVCO.
[
43
]
Core operational support for OpenTopography comes from the National Science Foundation, Division of Earth Sciences.
The OpenDemSearcher is a Mapclient with a visualization of regions with free available middle and high resolution DEMs.[44]

The OpenDemSearcher is a Mapclient with a visualization of regions with free available middle and high resolution DEMs.
[
44
]
STL 3D model
of the
Moon
with 10× elevation exaggeration rendered with data from the
Lunar Orbiter Laser Altimeter
of the
Lunar Reconnaissance Orbiter
The R programming language comes with the volcano matrix of elevations.[45]

The R programming language comes with the volcano matrix of elevations.
[
45
]
The volcano dataset from the R programming environment is visualized, restructured, colored, and georeferenced.

## See also

See also
[
edit
]
- Ground slopeandaspect(groundspatial gradient)
Ground slope
and
aspect
(ground
spatial gradient
)
- Digital outcrop model
Digital outcrop model
- Global Relief Model
Global Relief Model
- Physical terrain model
Physical terrain model
- Terrain cartography
Terrain cartography
- Terrain rendering
Terrain rendering

### DEM file formats

DEM file formats
[
edit
]
- Bathymetric Attributed Grid(BAG)
Bathymetric Attributed Grid
(BAG)
- DTED
DTED
- DIMAP Sentinel 1 ESA data base
DIMAP Sentinel 1 ESA data base
- Geotiff
Geotiff
- SDTSDEM
SDTS
DEM
- USGS DEM
USGS DEM

## References

References
[
edit
]
- ^I. Balenovic, H. Marjanovic, D. Vuletic, etc. Quality assessment of high density digital surface model over different land cover classes. PERIODICUM BIOLOGORUM. VOL. 117, No 4, 459–470, 2015.
^
I. Balenovic, H. Marjanovic, D. Vuletic, etc. Quality assessment of high density digital surface model over different land cover classes. PERIODICUM BIOLOGORUM. VOL. 117, No 4, 459–470, 2015.
- ^"Analysis of a digital terrain model for solving geological problems by the example of Aktogai ore field".Mining Science and Technology (Russia).doi:10.17073/2500-0632-2025-06-422.
^
"Analysis of a digital terrain model for solving geological problems by the example of Aktogai ore field"
.
Mining Science and Technology (Russia)
.
doi
:
10.17073/2500-0632-2025-06-422
.
- ^"Appendix A – Glossary and Acronyms"(PDF).Severn Tidal Tributaries Catchment Flood Management Plan – Scoping Stage. UK:Environment Agency. Archived fromthe original(PDF)on 2007-07-10.
^
"Appendix A – Glossary and Acronyms"
(PDF)
.
Severn Tidal Tributaries Catchment Flood Management Plan – Scoping Stage
. UK:
Environment Agency
. Archived from
the original
(PDF)
on 2007-07-10.
- ^"Intermap Digital Surface Model: accurate, seamless, wide-area surface models". Archived fromthe originalon 2011-09-28.
^
"Intermap Digital Surface Model: accurate, seamless, wide-area surface models"
. Archived from
the original
on 2011-09-28.
- ^abLi, Z., Zhu, Q. and Gold, C. (2005),Digital terrain modeling: principles and methodology,CRC Press, Boca Raton, FL.
^
a
b
Li, Z., Zhu, Q. and Gold, C. (2005),
Digital terrain modeling: principles and methodology,
CRC Press, Boca Raton, FL.
- ^Hirt, C. (2014)."Digital Terrain Models"(PDF).Encyclopedia of Geodesy. pp.1–6.doi:10.1007/978-3-319-02370-0_31-1.ISBN978-3-319-01868-3. RetrievedOctober 14,2024.
^
Hirt, C. (2014).
"Digital Terrain Models"
(PDF)
.
Encyclopedia of Geodesy
. pp.
1–
6.
doi
:
10.1007/978-3-319-02370-0_31-1
.
ISBN
978-3-319-01868-3
. Retrieved
October 14,
2024
.
- ^Peckham, Robert Joseph; Jordan, Gyozo (Eds.)(2007):  Development and Applications in a Policy Support Environment Series: Lecture Notes in Geoinformation and Cartography.  Heidelberg.
^
Peckham, Robert Joseph; Jordan, Gyozo (Eds.)(2007):  Development and Applications in a Policy Support Environment Series: Lecture Notes in Geoinformation and Cartography.  Heidelberg.
- ^Podobnikar, Tomaz (2008)."Methods for visual quality assessment of a digital terrain model".S.A.P.I.EN.S.1(2).
^
Podobnikar, Tomaz (2008).
"Methods for visual quality assessment of a digital terrain model"
.
S.A.P.I.EN.S
.
1
(2).
- ^Adrian W. Graham, Nicholas C. Kirkman, Peter M. Paul (2007):Mobile radio network design in the VHF and UHF bands: a practical approach. West Sussex.
^
Adrian W. Graham, Nicholas C. Kirkman, Peter M. Paul (2007):
Mobile radio network design in the VHF and UHF bands: a practical approach
. West Sussex.
- ^"DIN Standard 18709-1". Archived fromthe originalon 2011-01-11.
^
"DIN Standard 18709-1"
. Archived from
the original
on 2011-01-11.
- ^"Landslide Glossary USGS". Archived fromthe originalon 2011-05-16.
^
"Landslide Glossary USGS"
. Archived from
the original
on 2011-05-16.
- ^"Understanding Digital Surface Models, Digital Terrain Models and Digital Elevation Models: A Comprehensive Guide to Digital Models of the Earth's Surface".FlyGuys. March 2023. Retrieved7 September2023.
^
"Understanding Digital Surface Models, Digital Terrain Models and Digital Elevation Models: A Comprehensive Guide to Digital Models of the Earth's Surface"
.
FlyGuys
. March 2023
. Retrieved
7 September
2023
.
- ^DeMers, Michael (2002).GIS Modeling in Raster. Wiley.ISBN978-0-471-31965-8.
^
DeMers, Michael (2002).
GIS Modeling in Raster
. Wiley.
ISBN
978-0-471-31965-8
.
- ^Ronald Toppe  (1987):Terrain models — A tool for natural hazard MappingArchived2020-07-29 at theWayback Machine. In: Avalanche Formation, Movement and Effects (Proceedings of the Davos Symposium, September 1986). IAHS Publ. no. 162,1987
^
Ronald Toppe  (1987):
Terrain models — A tool for natural hazard Mapping
Archived
2020-07-29 at the
Wayback Machine
. In: Avalanche Formation, Movement and Effects (Proceedings of the Davos Symposium, September 1986). IAHS Publ. no. 162,1987
- ^Making 3D Terrain Maps,Shaded Relief. Retrieved 11 March 2019.
^
Making 3D Terrain Maps
,
Shaded Relief
. Retrieved 11 March 2019.
- ^David Morrison, ""Flat-Venus Society" organizes",EOS, Volume 73, Issue 9, American Geophysical Union, 3 March 1992, p. 99.doi:10.1029/91EO00076. Retrieved 11 March 2019.
^
David Morrison, "
"Flat-Venus Society" organizes
",
EOS, Volume 73
, Issue 9, American Geophysical Union, 3 March 1992, p. 99.
doi
:
10.1029/91EO00076
. Retrieved 11 March 2019.
- ^Robert Simmon. "Elegant Figures What Not To Do: Vertical Exaggeration,"NASA Earth Observatory,November 5, 2010. Retrieved 11 March 2019.
^
Robert Simmon. "
Elegant Figures What Not To Do: Vertical Exaggeration
,"
NASA Earth Observatory,
November 5, 2010. Retrieved 11 March 2019.
- ^"WorldDEM(TM): Airbus Defence and Space".www.intelligence-airbusds.com. Archived fromthe originalon 2018-06-04. Retrieved2018-01-05.
^
"WorldDEM(TM): Airbus Defence and Space"
.
www.intelligence-airbusds.com
. Archived from
the original
on 2018-06-04
. Retrieved
2018-01-05
.
- ^abNikolakopoulos, K. G.; Kamaratakis, E. K; Chrysoulakis, N. (10 November 2006)."SRTM vs ASTER elevation products. Comparison for two regions in Crete, Greece"(PDF).International Journal of Remote Sensing.27(21):4819–4838.Bibcode:2006IJRS...27.4819N.doi:10.1080/01431160600835853.ISSN0143-1161.S2CID1939968. Archived fromthe original(PDF)on July 21, 2011. RetrievedJune 22,2010.
^
a
b
Nikolakopoulos, K. G.; Kamaratakis, E. K; Chrysoulakis, N. (10 November 2006).
"SRTM vs ASTER elevation products. Comparison for two regions in Crete, Greece"
(PDF)
.
International Journal of Remote Sensing
.
27
(21):
4819–
4838.
Bibcode
:
2006IJRS...27.4819N
.
doi
:
10.1080/01431160600835853
.
ISSN
0143-1161
.
S2CID
1939968
. Archived from
the original
(PDF)
on July 21, 2011
. Retrieved
June 22,
2010
.
- ^Hargitai, Henrik; Willner, Konrad; Buchroithner, Manfred (2019), "Methods in Planetary Topographic Mapping: A Review", in Hargitai, Henrik (ed.),Planetary Cartography and GIS, Lecture Notes in Geoinformation and Cartography, Springer International Publishing, pp.147–174,doi:10.1007/978-3-319-62849-3_6,ISBN978-3-319-62848-6,S2CID133855780
^
Hargitai, Henrik; Willner, Konrad; Buchroithner, Manfred (2019), "Methods in Planetary Topographic Mapping: A Review", in Hargitai, Henrik (ed.),
Planetary Cartography and GIS
, Lecture Notes in Geoinformation and Cartography, Springer International Publishing, pp.
147–
174,
doi
:
10.1007/978-3-319-62849-3_6
,
ISBN
978-3-319-62848-6
,
S2CID
133855780
- ^Bruce Banerdt,Orbital Laser Altimeter,The Martian Chronicle, Volume 1, No. 3, NASA.  Retrieved 11 March 2019.
^
Bruce Banerdt,
Orbital Laser Altimeter
,
The Martian Chronicle, Volume 1
, No. 3, NASA.  Retrieved 11 March 2019.
- ^NASA,LOLA.  Retrieved 11 March 2019.
^
NASA,
LOLA
.  Retrieved 11 March 2019.
- ^John F. Cavanaugh,et al.,"The Mercury Laser Altimeter Instrument for the MESSENGER Mission",Space Sci Rev,doi:10.1007/s11214-007-9273-4, 24 August 2007.  Retrieved 11 March 2019.
^
John F. Cavanaugh,
et al.,
"
The Mercury Laser Altimeter Instrument for the MESSENGER Mission
",
Space Sci Rev
,
doi
:
10.1007/s11214-007-9273-4
, 24 August 2007.  Retrieved 11 March 2019.
- ^Hargitai, Henrik; Willner, Konrad; Hare, Trent (2019), "Fundamental Frameworks in Planetary Mapping: A Review", in Hargitai, Henrik (ed.),Planetary Cartography and GIS, Lecture Notes in Geoinformation and Cartography, Springer International Publishing, pp.75–101,doi:10.1007/978-3-319-62849-3_4,ISBN978-3-319-62848-6,S2CID133867607
^
Hargitai, Henrik; Willner, Konrad; Hare, Trent (2019), "Fundamental Frameworks in Planetary Mapping: A Review", in Hargitai, Henrik (ed.),
Planetary Cartography and GIS
, Lecture Notes in Geoinformation and Cartography, Springer International Publishing, pp.
75–
101,
doi
:
10.1007/978-3-319-62849-3_4
,
ISBN
978-3-319-62848-6
,
S2CID
133867607
- ^"Astropedia – Pluto New Horizons LORRI – MVIC Global DEM 300m".astrogeology.usgs.gov.
^
"Astropedia – Pluto New Horizons LORRI – MVIC Global DEM 300m"
.
astrogeology.usgs.gov
.
- ^Schenk, Paul; Singer, Kelsi; Beyer, Ross; Beddingfield, Chloe; Robbins, Stuart J.; McKinnon, William B.; Lauer, Tod R.; Verbiscer, Anne J.; Keane, James. T.; Dhingra, Rajani D.; Moore, Jeffrey; Parker, Joel W.; Olkin, Cathy; Spencer, John; Weaver, Hal; Stern, S. Alan (1 March 2021)."Origins of pits and troughs and degradation on a small primitive planetesimal in the Kuiper Belt: high-resolution topography of (486958) Arrokoth (aka 2014 MU69) from New Horizons".Icarus.356113834.Bibcode:2021Icar..35613834S.doi:10.1016/j.icarus.2020.113834.ISSN0019-1035.
^
Schenk, Paul; Singer, Kelsi; Beyer, Ross; Beddingfield, Chloe; Robbins, Stuart J.; McKinnon, William B.; Lauer, Tod R.; Verbiscer, Anne J.; Keane, James. T.; Dhingra, Rajani D.; Moore, Jeffrey; Parker, Joel W.; Olkin, Cathy; Spencer, John; Weaver, Hal; Stern, S. Alan (1 March 2021).
"Origins of pits and troughs and degradation on a small primitive planetesimal in the Kuiper Belt: high-resolution topography of (486958) Arrokoth (aka 2014 MU69) from New Horizons"
.
Icarus
.
356
113834.
Bibcode
:
2021Icar..35613834S
.
doi
:
10.1016/j.icarus.2020.113834
.
ISSN
0019-1035
.
- ^abCampbell, D. M. H.; White, B.; Arp, P. A. (2013-11-01)."Modeling and mapping soil resistance to penetration and rutting using LiDAR-derived digital elevation data".Journal of Soil and Water Conservation.68(6):460–473.doi:10.2489/jswc.68.6.460.ISSN0022-4561.
^
a
b
Campbell, D. M. H.; White, B.; Arp, P. A. (2013-11-01).
"Modeling and mapping soil resistance to penetration and rutting using LiDAR-derived digital elevation data"
.
Journal of Soil and Water Conservation
.
68
(6):
460–
473.
doi
:
10.2489/jswc.68.6.460
.
ISSN
0022-4561
.
- ^James, M. R.; Robson, S. (2012)."Straightforward reconstruction of 3D surfaces and topography with a camera: Accuracy and geoscience application"(PDF).Journal of Geophysical Research: Earth Surface.117(F3): n/a.Bibcode:2012JGRF..117.3017J.doi:10.1029/2011JF002289.
^
James, M. R.; Robson, S. (2012).
"Straightforward reconstruction of 3D surfaces and topography with a camera: Accuracy and geoscience application"
(PDF)
.
Journal of Geophysical Research: Earth Surface
.
117
(F3): n/a.
Bibcode
:
2012JGRF..117.3017J
.
doi
:
10.1029/2011JF002289
.
- ^Szypuła, Bartłomiej (1 January 2019)."Quality assessment of DEM derived from topographic maps for geomorphometric purposes".Open Geosciences.11(1):843–865.Bibcode:2019OGeo...11...66S.doi:10.1515/geo-2019-0066.hdl:20.500.12128/11742.ISSN2391-5447.S2CID208868204.
^
Szypuła, Bartłomiej (1 January 2019).
"Quality assessment of DEM derived from topographic maps for geomorphometric purposes"
.
Open Geosciences
.
11
(1):
843–
865.
Bibcode
:
2019OGeo...11...66S
.
doi
:
10.1515/geo-2019-0066
.
hdl
:
20.500.12128/11742
.
ISSN
2391-5447
.
S2CID
208868204
.
- ^Adams, Aaron (2019).A Comparative Usability Assessment of Augmented Reality 3-D Printed Terrain Models and 2-D Topographic Maps. NMSU. Retrieved11 March2022.{{cite book}}:  CS1 maint: location missing publisher (link)
^
Adams, Aaron (2019).
A Comparative Usability Assessment of Augmented Reality 3-D Printed Terrain Models and 2-D Topographic Maps
. NMSU
. Retrieved
11 March
2022
.

```
{{cite book}}
```

{{
cite book
}}
:  CS1 maint: location missing publisher (
link
)
- ^"I. Balenović, A. Seletković, R. Pernar, A. Jazbec. Estimation of the mean tree height of forest stands by photogrammetric measurement using digital aerial images of high spatial resolution. ANNALS OF FOREST RESEARCH. 58(1), P. 125-143, 2015".
^
"I. Balenović, A. Seletković, R. Pernar, A. Jazbec. Estimation of the mean tree height of forest stands by photogrammetric measurement using digital aerial images of high spatial resolution. ANNALS OF FOREST RESEARCH. 58(1), P. 125-143, 2015"
.
- ^"Martin Gamache's paper on free sources of global data"(PDF).
^
"Martin Gamache's paper on free sources of global data"
(PDF)
.
- ^Hirt, C.; Rexer, M. (2015)."Earth2014: 1 arc-min shape, topography, bedrock and ice-sheet models - available as gridded data and degree-10,800 spherical harmonics"(PDF).International Journal of Applied Earth Observation and Geoinformation.39:103–112.Bibcode:2015IJAEO..39..103H.doi:10.1016/j.jag.2015.03.001.hdl:20.500.11937/25468. RetrievedFebruary 20,2016.
^
Hirt, C.; Rexer, M. (2015).
"Earth2014: 1 arc-min shape, topography, bedrock and ice-sheet models - available as gridded data and degree-10,800 spherical harmonics"
(PDF)
.
International Journal of Applied Earth Observation and Geoinformation
.
39
:
103–
112.
Bibcode
:
2015IJAEO..39..103H
.
doi
:
10.1016/j.jag.2015.03.001
.
hdl
:
20.500.11937/25468
. Retrieved
February 20,
2016
.
- ^"GEO Elevation Services : Airbus Defence and Space".www.astrium-geo.com. Archived fromthe originalon 2014-06-26. Retrieved2012-01-11.
^
"GEO Elevation Services : Airbus Defence and Space"
.
www.astrium-geo.com
. Archived from
the original
on 2014-06-26
. Retrieved
2012-01-11
.
- ^"International – Geospatial".gs.mdacorporation.com. Archived fromthe originalon 2016-03-04. Retrieved2012-02-02.
^
"International – Geospatial"
.
gs.mdacorporation.com
. Archived from
the original
on 2016-03-04
. Retrieved
2012-02-02
.
- ^"TerraSAR-X : Airbus Defence and Space".www.astrium-geo.com. Archived fromthe originalon 2014-08-12. Retrieved2012-01-11.
^
"TerraSAR-X : Airbus Defence and Space"
.
www.astrium-geo.com
. Archived from
the original
on 2014-08-12
. Retrieved
2012-01-11
.
- ^"ALOS World 3D – 30m".www.eorc.jaxa.jp. Archived fromthe originalon 2020-05-04. Retrieved2017-09-09.
^
"ALOS World 3D – 30m"
.
www.eorc.jaxa.jp
. Archived from
the original
on 2020-05-04
. Retrieved
2017-09-09
.
- ^"ALOS World 3D".www.aw3d.jp.
^
"ALOS World 3D"
.
www.aw3d.jp
.
- ^"A basic guide for using Digital Elevation Models with Terragen". Archived fromthe originalon 2007-05-19.
^
"A basic guide for using Digital Elevation Models with Terragen"
. Archived from
the original
on 2007-05-19.
- ^"OpenTopography".www.opentopography.org.
^
"OpenTopography"
.
www.opentopography.org
.
- ^"About OpenTopography".
^
"About OpenTopography"
.
- ^"San Diego Supercomputer Center".www.sdsc.edu. Retrieved2018-08-16.
^
"San Diego Supercomputer Center"
.
www.sdsc.edu
. Retrieved
2018-08-16
.
- ^"Home | UNAVCO".www.unavco.org. Retrieved2018-08-16.
^
"Home | UNAVCO"
.
www.unavco.org
. Retrieved
2018-08-16
.
- ^OpenDemSearcher
^
OpenDemSearcher
- ^Crawley, Michael J. (2007).The R book. Chichester England: Wiley.ISBN978-0-470-51024-7.
^
Crawley, Michael J. (2007).
The R book
. Chichester England: Wiley.
ISBN
978-0-470-51024-7
.

## Further reading

Further reading
[
edit
]
- Wilson, J.P.; Gallant, J.C. (2000)."Chapter 1"(PDF). In Wilson, J.P.; Gallant, J.C. (eds.).Terrain Analysis: Principles and Applications. New York: Wiley. pp.1–27.ISBN978-0-471-32188-0. Retrieved2007-02-16.
Wilson, J.P.; Gallant, J.C. (2000).
"Chapter 1"
(PDF)
. In Wilson, J.P.; Gallant, J.C. (eds.).
Terrain Analysis: Principles and Applications
. New York: Wiley. pp.
1–
27.
ISBN
978-0-471-32188-0
. Retrieved
2007-02-16
.
- Hirt, C.; Filmer, M.S.; Featherstone, W.E. (2010)."Comparison and validation of recent freely-available ASTER-GDEM ver1, SRTM ver4.1 and GEODATA DEM-9S ver3 digital elevation models over Australia".Australian Journal of Earth Sciences.57(3):337–347.Bibcode:2010AuJES..57..337H.doi:10.1080/08120091003677553.hdl:20.500.11937/43846.S2CID140651372. RetrievedMay 5,2012.
Hirt, C.; Filmer, M.S.; Featherstone, W.E. (2010).
"Comparison and validation of recent freely-available ASTER-GDEM ver1, SRTM ver4.1 and GEODATA DEM-9S ver3 digital elevation models over Australia"
.
Australian Journal of Earth Sciences
.
57
(3):
337–
347.
Bibcode
:
2010AuJES..57..337H
.
doi
:
10.1080/08120091003677553
.
hdl
:
20.500.11937/43846
.
S2CID
140651372
. Retrieved
May 5,
2012
.
- Rexer, M.; Hirt, C. (2014)."Comparison of free high-resolution digital elevation data sets (ASTER GDEM2, SRTM v2.1/v4.1) and validation against accurate heights from the Australian National Gravity Database"(PDF).Australian Journal of Earth Sciences.61(2):213–226.Bibcode:2014AuJES..61..213R.doi:10.1080/08120099.2014.884983.hdl:20.500.11937/38264.S2CID3783826. Archived fromthe original(PDF)on June 7, 2016. RetrievedApril 24,2014.
Rexer, M.; Hirt, C. (2014).
"Comparison of free high-resolution digital elevation data sets (ASTER GDEM2, SRTM v2.1/v4.1) and validation against accurate heights from the Australian National Gravity Database"
(PDF)
.
Australian Journal of Earth Sciences
.
61
(2):
213–
226.
Bibcode
:
2014AuJES..61..213R
.
doi
:
10.1080/08120099.2014.884983
.
hdl
:
20.500.11937/38264
.
S2CID
3783826
. Archived from
the original
(PDF)
on June 7, 2016
. Retrieved
April 24,
2014
.

## External links

External links
[
edit
]
- DEM Quality Comparison
DEM Quality Comparison
- Terrainmap.com
Terrainmap.com
- Maps-for-free.com
Maps-for-free.com
- Geo-Spatial Data AcquisitionArchived2013-08-22 at theWayback Machine
Geo-Spatial Data Acquisition
Archived
2013-08-22 at the
Wayback Machine
- Elevation Mapper, Create geo-referenced elevation maps
Elevation Mapper, Create geo-referenced elevation maps
Data products
- Satellite GeodesybyScripps Institution of Oceanography
Satellite Geodesy
by
Scripps Institution of Oceanography
- Shuttle Radar Topography Missionby NASA/JPL
Shuttle Radar Topography Mission
by NASA/JPL
- Global 30 Arc-Second Elevation (GTOPO30)by the U.S. Geological Survey
Global 30 Arc-Second Elevation (GTOPO30)
by the U.S. Geological Survey
- Global Multi-resolution Terrain Elevation Data 2010 (GMTED2010)by the U.S. Geological Survey
Global Multi-resolution Terrain Elevation Data 2010 (GMTED2010)
by the U.S. Geological Survey
- Earth2014byTechnische Universität München
Earth2014
by
Technische Universität München
- Sonny's LiDAR Digital Terrain Models of Europe
Sonny's LiDAR Digital Terrain Models of Europe
NewPP limit report
Parsed by mw‐web.codfw.main‐5595d54fdf‐29rrg
Cached time: 20260622193804
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, prevent‐selective‐update, show‐toc]
CPU time usage: 0.339 seconds
Real time usage: 0.408 seconds
Preprocessor visited node count: 1845/1000000
Revision size: 33063/2097152 bytes
Post‐expand include size: 74585/2097152 bytes
Template argument size: 698/2097152 bytes
Highest expansion depth: 10/100
Expensive parser function count: 1/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 139181/5000000 bytes
Lua time usage: 0.193/10.000 seconds
Lua memory usage: 5976139/52428800 bytes
Number of Wikibase entities loaded: 0/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  311.455      1 -total
 73.96%  230.349      1 Template:Reflist
 37.07%  115.463     10 Template:Cite_journal
 16.47%   51.307      1 Template:Short_description
 16.01%   49.870     18 Template:Cite_web
  9.76%   30.407      2 Template:Pagetype
  8.93%   27.825      6 Template:Cite_book
  3.48%   10.848      3 Template:Main_other
  3.43%   10.674      2 Template:Citation
  2.90%    9.046      1 Template:SDcat
Render ID e2c33890-6e71-11f1-a22b-4b1128c579cb
Saved in parser cache with key enwiki:pcache:78442:|#|:idhash:canonical and timestamp 20260622193804 and revision id 1360648790. Rendering was triggered because: page_view
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Digital_elevation_model&oldid=1360648790
"
Categories
:
- Digital elevation models
Digital elevation models
- Surveying
Surveying
- Planetary science
Planetary science
- Geographic data and information
Geographic data and information
- Geodesy
Geodesy
Hidden categories:
- Webarchive template wayback links
Webarchive template wayback links
- CS1 maint: location missing publisher
CS1 maint: location missing publisher
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata