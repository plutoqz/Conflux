<!-- source: https://en.wikipedia.org/wiki/Spatial_reference_system -->
# Spatial reference system

> Source: https://en.wikipedia.org/wiki/Spatial_reference_system
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
System to specify locations on Earth

<!-- table omitted -->

Geodesy
Fundamentals
- Geodesy
Geodesy
- Geodynamics
Geodynamics
- Geomatics
Geomatics
- History
History
Concepts
- Geographical distance
Geographical distance
- Geoid
Geoid
- Figure of the Earth(radiusandcircumference)
Figure of the Earth
(
radius
and
circumference
)
- Geodetic coordinates
Geodetic coordinates
- Geodetic datum
Geodetic datum
- Geodesic
Geodesic
- Horizontal position representation
Horizontal position representation
- Latitude/Longitude
Latitude
/
Longitude
- Map projection
Map projection
- Reference ellipsoid
Reference ellipsoid
- Satellite geodesy
Satellite geodesy
- Spatial reference system
Spatial reference system
- Spatial relations
Spatial relations
- Vertical positions
Vertical positions
Technologies
- Global Nav. Sat. Systems (GNSSs)
Global Nav. Sat. Systems (GNSSs)
- Global Pos. System (GPS)
Global Pos. System (GPS)
- GLONASS(Russia)
GLONASS
(Russia)
- BeiDou (BDS)(China)
BeiDou (BDS)
(China)
- Galileo(Europe)
Galileo
(Europe)
- NAVIC(India)
NAVIC
(India)
- Quasi-Zenith Sat. Sys. (QZSS)(Japan)
Quasi-Zenith Sat. Sys. (QZSS)
(Japan)
- Discrete Global Grid and Geocoding
Discrete Global Grid and Geocoding
Standards (history)

<!-- table omitted -->

NGVD 29
Sea Level Datum 1929
OSGB36
Ordnance Survey Great Britain 1936
SK-42
Systema Koordinat 1942 goda
ED50
European Datum 1950
SAD69
South American Datum 1969
GRS 80
Geodetic Reference System 1980
ISO 6709
Geographic point coord. 1983
NAD 83
North American Datum 1983
WGS 84
World Geodetic System 1984
NAVD 88
N. American Vertical Datum 1988
ETRS89
European Terrestrial Ref. Sys. 1989
GCJ-02
Chinese obfuscated datum 2002
Geo URI
Internet link to a point  2010
- International Terrestrial Reference System
International Terrestrial Reference System
- Spatial Reference System Identifier (SRID)
Spatial Reference System Identifier (SRID)
- Universal Transverse Mercator (UTM)
Universal Transverse Mercator (UTM)
- v
v
- t
t
- e
e
Aspatial reference system(SRS) orcoordinate reference system(CRS) is a framework used to precisely measure locations on, or relative to, the surface of Earth as coordinates. It is thus the application of the abstract mathematics ofcoordinate systemsandanalytic geometryto geographic space. A particular SRS specification (for example, "Universal Transverse MercatorWGS 84Zone 16N") comprises a choice ofEarth ellipsoid,horizontal datum,map projection(except in thegeographic coordinate system), origin point, and unit of measure. Thousands of coordinate systems have been specified for use around the world or in specific regions and for various purposes, necessitatingtransformationsbetween different SRS.

A
spatial reference system
(
SRS
) or
coordinate reference system
(
CRS
) is a framework used to precisely measure locations on, or relative to, the surface of Earth as coordinates. It is thus the application of the abstract mathematics of
coordinate systems
and
analytic geometry
to geographic space. A particular SRS specification (for example, "
Universal Transverse Mercator
WGS 84
Zone 16N") comprises a choice of
Earth ellipsoid
,
horizontal datum
,
map projection
(except in the
geographic coordinate system
), origin point, and unit of measure. Thousands of coordinate systems have been specified for use around the world or in specific regions and for various purposes, necessitating
transformations
between different SRS.
Although they date to theHellenistic period, spatial reference systems are now a crucial basis for the sciences and technologies ofGeoinformatics, includingcartography,geographic information systems,surveying,remote sensing, andcivil engineering. This has led to their standardization in international specifications such as theEPSG codes[1]andISO 19111:2019 Geographic information—Spatial referencing by coordinates, prepared byISO/TC 211, also published by theOpen Geospatial ConsortiumasAbstract Specification, Topic 2: Spatial referencing by coordinate.[2]

Although they date to the
Hellenistic period
, spatial reference systems are now a crucial basis for the sciences and technologies of
Geoinformatics
, including
cartography
,
geographic information systems
,
surveying
,
remote sensing
, and
civil engineering
. This has led to their standardization in international specifications such as the
EPSG codes
[
1
]
and
ISO 19111:2019 Geographic information—Spatial referencing by coordinates
, prepared by
ISO/TC 211
, also published by the
Open Geospatial Consortium
as
Abstract Specification, Topic 2: Spatial referencing by coordinate
.
[
2
]
The above refers to locations directly on the surface of the earth. Information on elevation may also be specified, via a vertical reference frame, so-called vertical CRS, or an integrated 3D CRS. Terminology in this area is evolving in line with increasing technical sophistication in measurement.

The above refers to locations directly on the surface of the earth. Information on elevation may also be specified, via a vertical reference frame, so-called vertical CRS, or an integrated 3D CRS. Terminology in this area is evolving in line with increasing technical sophistication in measurement.

## Types of systems

Types of systems
[
edit
]
Earth centered, Earth fixed coordinates in relation to latitude and longitude.
The thousands of spatial reference systems used today are based on a few general strategies, which have been defined in the EPSG, ISO, and OGC standards:[1][2]

The thousands of spatial reference systems used today are based on a few general strategies, which have been defined in the EPSG, ISO, and OGC standards:
[
1
]
[
2
]
Geographic coordinate system
(or geodetic)
A
spherical coordinate system
measuring locations directly on the Earth (modeled as a
sphere
or
ellipsoid
) using
latitude
(degrees north or south of the
equator
) and
longitude
(degrees west or east of a
prime meridian
).
Geocentric coordinate system
(or Earth-centered Earth-fixed)
A three-dimensional
cartesian coordinate system
that models the Earth as a three-dimensional object, measuring locations from a center point, usually the
center of mass
of the Earth, along x, y, and z axes aligned with the
equator
and the
prime meridian
. This system is commonly used to track the orbits of
satellites
, because they are based on the center of mass. Thus, this is the internal coordinate system used by
Satellite navigation
systems such as
GPS
to compute locations using
multilateration
.
Projected coordinate system
(or planar, grid)
Layout of a UTM coordinate system
A standardized
cartesian coordinate system
that models the surface of Earth (or more commonly, a large region thereof) as a plane, measuring locations from an arbitrary origin point along x and y axes more or less aligned with the cardinal directions. Each of these systems is based on a particular
map projection
to create a planar surface from the curved Earth surface. Such SRSs are generally defined and used strategically in their target regions to minimize the distortions inherent to projections for specific use cases. Common examples include the
Universal transverse mercator
(UTM) and national systems such as the
British National Grid
, and
State Plane Coordinate System
(SPCS).
Engineering coordinate system (or local, custom)
A
cartesian coordinate system
(2-D or 3-D) that is created bespoke for a small area, often a single engineering project, over which the curvature of the Earth can be safely approximated as flat without significant distortion. Locations are typically measured directly from an arbitrary origin point using
surveying
techniques. These may or may not be aligned with a standard projected coordinate system.
Local tangent plane coordinates
are a type of local coordinate system used in aviation and marine vehicles.
Vertical reference frame
A standard reference system for measuring
elevation
using
vertical datums
, based on
levelling
, a
geoid
model, or a
chart datum
(considering
tides
). This does not carry information about localization of a point on the surface of the earth, but elevation relative to the surface of the earth, importantly including specification of what zero elevation is.
3D (compound) coordinate system
Combines a geographic or projected coordinate system with a vertical reference frame to provide a full parametrization of locations on or near the surface of the earth relative to a chosen zero elevation level.
These standards acknowledge that standard reference systems also exist fortime(e.g.ISO 8601). These may be combined with a spatial reference system to form acompound coordinate systemfor representing three-dimensional and/or spatio-temporal locations. There are also internal systems for measuring location within the context of an object, such as the rows and columns of pixels in araster image,Linear referencingmeasurements along linear features (e.g., highway mileposts), and systems for specifying location within moving objects such as ships. The latter two are often classified as subcategories of engineering coordinate systems.

These standards acknowledge that standard reference systems also exist for
time
(e.g.
ISO 8601
). These may be combined with a spatial reference system to form a
compound coordinate system
for representing three-dimensional and/or spatio-temporal locations. There are also internal systems for measuring location within the context of an object, such as the rows and columns of pixels in a
raster image
,
Linear referencing
measurements along linear features (e.g., highway mileposts), and systems for specifying location within moving objects such as ships. The latter two are often classified as subcategories of engineering coordinate systems.

## Components

Components
[
edit
]
The goal of any spatial reference system is to create a common reference frame in which locations can be measured precisely and consistently as coordinates, which can then be shared unambiguously, so that any recipient can identify the same location that was originally intended by the originator.[3]To accomplish this, any coordinate reference system definition needs to be composed of several specifications:

The goal of any spatial reference system is to create a common reference frame in which locations can be measured precisely and consistently as coordinates, which can then be shared unambiguously, so that any recipient can identify the same location that was originally intended by the originator.
[
3
]
To accomplish this, any coordinate reference system definition needs to be composed of several specifications:
- Acoordinate system, an abstract framework for measuring locations. Like any mathematical coordinate system, its definition consists of a measurable space (whether a plane, a three-dimension void, or the surface of an object such as the Earth), an origin point, a set of axis vectors emanating from the origin, and a unit of measure.
A
coordinate system
, an abstract framework for measuring locations. Like any mathematical coordinate system, its definition consists of a measurable space (whether a plane, a three-dimension void, or the surface of an object such as the Earth), an origin point, a set of axis vectors emanating from the origin, and a unit of measure.
- Ageodetic datum(horizontal, vertical, or three-dimensional) which binds the abstract coordinate system to the real space of the Earth. A horizontal datum can be defined as a precise reference framework for measuringgeographic coordinates(latitude and longitude). Examples include theWorld Geodetic Systemand the 1927 and 1983North American Datum. A datum generally consists of an estimate of the shape of the Earth (usually an ellipsoid), and one or moreanchor pointsorcontrol points, established locations (often marked by physical monuments) for which the measurement is documented.
A
geodetic datum
(horizontal, vertical, or three-dimensional) which binds the abstract coordinate system to the real space of the Earth. A horizontal datum can be defined as a precise reference framework for measuring
geographic coordinates
(latitude and longitude). Examples include the
World Geodetic System
and the 1927 and 1983
North American Datum
. A datum generally consists of an estimate of the shape of the Earth (usually an ellipsoid), and one or more
anchor points
or
control points
, established locations (often marked by physical monuments) for which the measurement is documented.
- A definition for a projected CRS must also include a choice ofmap projectionto convert the spherical coordinates specified by the datum into cartesian coordinates on a planar surface.
A definition for a projected CRS must also include a choice of
map projection
to convert the spherical coordinates specified by the datum into cartesian coordinates on a planar surface.
Thus, a CRS definition will typically consist of a "stack" of dependent specifications, as exemplified in the following table:

Thus, a CRS definition will typically consist of a "stack" of dependent specifications, as exemplified in the following table:

<!-- table omitted -->

EPSG code
Name
Ellipsoid
Horizontal datum
CS type
Projection
Origin
Axes
Unit of measure
4326
GCS
WGS 84
GRS 80
WGS 84
ellipsoidal (lat, lon)
—
N/a
equator/prime meridian
equator, prime meridian
degree of arc
26717
UTM
Zone 17N NAD 27
Clarke 1866
NAD 27
cartesian (x,y)
Transverse Mercator: central meridian 81°W, scaled 0.9996
500 km west of (81°W, 0°N)
equator, 81°W meridian
metre
6576
SPCS
Tennessee Zone NAD 83 (2011) ftUS
GRS 80
NAD 83
(2011 epoch)
cartesian (x,y)
Lambert Conformal Conic: center 86°W, 34°20'N, standard parallels 35°15'N, 36°25'N
600 km grid west of center point
grid east at center point, 86°W meridian
US survey foot

## Examples by continent

Examples by continent
[
edit
]
Examples of systems around the world are:

Examples of systems around the world are:

### Asia

Asia
[
edit
]
- Chinese Global Navigation Grid Code, China
Chinese Global Navigation Grid Code
, China
- Israeli Cassini Soldner, Israel
Israeli Cassini Soldner
, Israel
- Israeli Transverse Mercator, Israel
Israeli Transverse Mercator
, Israel
- Jordan Transverse Mercator, Jordan
Jordan Transverse Mercator
, Jordan

### Europe

Europe
[
edit
]
- British national grid reference system, Britain
British national grid reference system
, Britain
- Lambert-93(fr), the official projection inMetropolitan France
Lambert-93
(fr)
, the official projection in
Metropolitan France
- Hellenic Geodetic Reference System 1987, Greece
Hellenic Geodetic Reference System 1987
, Greece
- Irish grid reference system, Ireland
Irish grid reference system
, Ireland
- Irish Transverse Mercator, Ireland
Irish Transverse Mercator
, Ireland
- SWEREF 99(sv), Sweden
SWEREF 99
(sv)
, Sweden

### North America

North America
[
edit
]
- United States National GridandState Plane Coordinate System(SPCS), US
United States National Grid
and
State Plane Coordinate System
(SPCS), US
- Modified transverse Mercatorcoordinate system, Canada
Modified transverse Mercator
coordinate system, Canada

### Worldwide

Worldwide
[
edit
]
- Universal Transverse Mercator coordinate system
Universal Transverse Mercator coordinate system
- Lambert conformal conic projection
Lambert conformal conic projection
- International mapcode system
International mapcode system
- Military Grid Reference System
Military Grid Reference System

## Identifiers

Identifiers
[
edit
]
"SRID" redirects here. For the polyhedron, see
Rhombicosidodecahedron
.
ASpatial Reference System Identifier(SRID) is a unique value used to unambiguously identify projected, unprojected, and local spatial coordinate system definitions. These coordinate systems form the heart of allGISapplications.

A
Spatial Reference System Identifier
(
SRID
) is a unique value used to unambiguously identify projected, unprojected, and local spatial coordinate system definitions. These coordinate systems form the heart of all
GIS
applications.
Virtually all major spatial vendors have created their own SRID implementation or refer to those of an authority, such as theEPSG Geodetic Parameter Dataset.

Virtually all major spatial vendors have created their own SRID implementation or refer to those of an authority, such as the
EPSG Geodetic Parameter Dataset
.
SRIDs are the primary key for theOpen Geospatial Consortium (OGC)spatial_ref_sysmetadata table for theSimple Features for SQL Specification, Versions 1.1 and 1.2,  which is defined as follows:

SRIDs are the primary key for the
Open Geospatial Consortium (OGC)
spatial_ref_sys
metadata table for the
Simple Features for SQL Specification, Versions 1.1 and 1.2
,  which is defined as follows:

```
CREATE TABLE SPATIAL_REF_SYS
(
    SRID      INTEGER   NOT NULL PRIMARY KEY,
    AUTH_NAME CHARACTER VARYING(256),
    AUTH_SRID INTEGER,
    SRTEXT    CHARACTER VARYING(2048)
)
```

CREATE
TABLE
SPATIAL_REF_SYS
(
SRID
INTEGER
NOT
NULL
PRIMARY
KEY
,
AUTH_NAME
CHARACTER
VARYING
(
256
),
AUTH_SRID
INTEGER
,
SRTEXT
CHARACTER
VARYING
(
2048
)
)
In spatially enabled databases (such asIBM Db2,IBM Informix,Ingres,Microsoft SQL Server,MonetDB,MySQL,Oracle RDBMS,Teradata,PostGIS,SQL AnywhereandVertica), SRIDs are used to uniquely identify the coordinate systems used to define columns of spatial data or individual spatial objects in a spatial column (depending on the spatial implementation).  SRIDs are typically associated with awell-known text(WKT) string definition of the coordinate system (SRTEXT, above).
Here are two common coordinate systems with their EPSG SRID value followed by their WKT:

In spatially enabled databases (such as
IBM Db2
,
IBM Informix
,
Ingres
,
Microsoft SQL Server
,
MonetDB
,
MySQL
,
Oracle RDBMS
,
Teradata
,
PostGIS
,
SQL Anywhere
and
Vertica
), SRIDs are used to uniquely identify the coordinate systems used to define columns of spatial data or individual spatial objects in a spatial column (depending on the spatial implementation).  SRIDs are typically associated with a
well-known text
(WKT) string definition of the coordinate system (SRTEXT, above).
Here are two common coordinate systems with their EPSG SRID value followed by their WKT:
UTM, Zone 17N, NAD27 — SRID 2029:

UTM, Zone 17N, NAD27 — SRID 2029:

```
PROJCS["NAD27(76) / UTM zone 17N",
    GEOGCS["NAD27(76)",
        DATUM["North_American_Datum_1927_1976",
            SPHEROID["Clarke 1866",6378206.4,294.9786982138982,
                AUTHORITY["EPSG","7008"]],
            AUTHORITY["EPSG","6608"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.01745329251994328,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4608"]],
    UNIT["metre",1,
        AUTHORITY["EPSG","9001"]],
    PROJECTION["Transverse_Mercator"],
    PARAMETER["latitude_of_origin",0],
    PARAMETER["central_meridian",-81],
    PARAMETER["scale_factor",0.9996],
    PARAMETER["false_easting",500000],
    PARAMETER["false_northing",0],
    AUTHORITY["EPSG","2029"],
    AXIS["Easting",EAST],
    AXIS["Northing",NORTH]]
```

PROJCS
[
"NAD27(76) / UTM zone 17N"
,
GEOGCS
[
"NAD27(76)"
,
DATUM
[
"North_American_Datum_1927_1976"
,
SPHEROID
[
"Clarke 1866"
,
6378206.4
,
294.9786982138982
,
AUTHORITY
[
"EPSG"
,
"7008"
]],
AUTHORITY
[
"EPSG"
,
"6608"
]],
PRIMEM
[
"Greenwich"
,
0
,
AUTHORITY
[
"EPSG"
,
"8901"
]],
UNIT
[
"degree"
,
0.01745329251994328
,
AUTHORITY
[
"EPSG"
,
"9122"
]],
AUTHORITY
[
"EPSG"
,
"4608"
]],
UNIT
[
"metre"
,
1
,
AUTHORITY
[
"EPSG"
,
"9001"
]],
PROJECTION
[
"Transverse_Mercator"
],
PARAMETER
[
"latitude_of_origin"
,
0
],
PARAMETER
[
"central_meridian"
,
-
81
],
PARAMETER
[
"scale_factor"
,
0.9996
],
PARAMETER
[
"false_easting"
,
500000
],
PARAMETER
[
"false_northing"
,
0
],
AUTHORITY
[
"EPSG"
,
"2029"
],
AXIS
[
"Easting"
,
EAST
],
AXIS
[
"Northing"
,
NORTH
]]
WGS84
— SRID 4326

```
GEOGCS["WGS 84",
    DATUM["WGS_1984",
        SPHEROID["WGS 84",6378137,298.257223563,
            AUTHORITY["EPSG","7030"]],
        AUTHORITY["EPSG","6326"]],
    PRIMEM["Greenwich",0,
        AUTHORITY["EPSG","8901"]],
    UNIT["degree",0.01745329251994328,
        AUTHORITY["EPSG","9122"]],
    AUTHORITY["EPSG","4326"]]
```

GEOGCS
[
"WGS 84"
,
DATUM
[
"WGS_1984"
,
SPHEROID
[
"WGS 84"
,
6378137
,
298.257223563
,
AUTHORITY
[
"EPSG"
,
"7030"
]],
AUTHORITY
[
"EPSG"
,
"6326"
]],
PRIMEM
[
"Greenwich"
,
0
,
AUTHORITY
[
"EPSG"
,
"8901"
]],
UNIT
[
"degree"
,
0.01745329251994328
,
AUTHORITY
[
"EPSG"
,
"9122"
]],
AUTHORITY
[
"EPSG"
,
"4326"
]]
SRID values associated with spatial data can be used to constrain spatial operations — for instance, spatial operations cannot be performed between spatial objects with differing SRIDs in some systems, or trigger coordinate system transformations between spatial objects in others.

SRID values associated with spatial data can be used to constrain spatial operations — for instance, spatial operations cannot be performed between spatial objects with differing SRIDs in some systems, or trigger coordinate system transformations between spatial objects in others.

## See also

See also
[
edit
]
- Engineering datum
Engineering datum
- Geodesy
Geodesy
- Geodetic datum
Geodetic datum
- Georeferencing
Georeferencing
- Geographic coordinate systems
Geographic coordinate systems
- Geographic information system(GIS).
Geographic information system
(
GIS
).
- Grid reference
Grid reference
- Linear referencing
Linear referencing
- List of National Coordinate Reference Systems
List of National Coordinate Reference Systems
- Terms of orientation
Terms of orientation

## References

References
[
edit
]
- ^ab"Using the EPSG geodetic parameter dataset, Guidance Note 7-1".EPSG Geodetic Parameter Dataset. Geomatic Solutions.Archivedfrom the original on 15 December 2021. Retrieved15 December2021.
^
a
b
"Using the EPSG geodetic parameter dataset, Guidance Note 7-1"
.
EPSG Geodetic Parameter Dataset
. Geomatic Solutions.
Archived
from the original on 15 December 2021
. Retrieved
15 December
2021
.
- ^ab"OGC Abstract Specification Topic 2: Referencing by coordinates Corrigendum".Open Geospatial Consortium.Archivedfrom the original on 2021-07-30. Retrieved2018-12-25.
^
a
b
"OGC Abstract Specification Topic 2: Referencing by coordinates Corrigendum"
.
Open Geospatial Consortium
.
Archived
from the original on 2021-07-30
. Retrieved
2018-12-25
.
- ^A guide to coordinate systems in Great Britain(PDF), D00659 v2.3, Ordnance Survey, 2020, p. 11, archived fromthe original(PDF)on 24 September 2015, retrieved2021-12-16
^
A guide to coordinate systems in Great Britain
(PDF)
, D00659 v2.3, Ordnance Survey, 2020, p. 11, archived from
the original
(PDF)
on 24 September 2015
, retrieved
2021-12-16

## External links

External links
[
edit
]
Wikidata
has the property:
- spatial reference system (P3037)(seeuses)
spatial reference system (P3037)
(see
uses
)
- spatialreference.org– A website with more than 13000 spatial reference systems, in a variety of formats.
spatialreference.org
– A website with more than 13000 spatial reference systems, in a variety of formats.
- OpenGIS Specifications (Standards)Archived2004-12-13 at theWayback Machine
OpenGIS Specifications (Standards)
Archived
2004-12-13 at the
Wayback Machine
- OpenGIS Simple Features Specification for CORBA (99-054)
OpenGIS Simple Features Specification for CORBA (99-054)
- OpenGIS Simple Features Specification for OLE/COM (99-050)
OpenGIS Simple Features Specification for OLE/COM (99-050)
- OpenGIS Simple Features Specification for SQL (99-054, 05-134, 06-104r3)
OpenGIS Simple Features Specification for SQL (99-054, 05-134, 06-104r3)
- OGRArchived2006-04-22 at theWayback Machine— library implementing relevant OGC standards
OGR
Archived
2006-04-22 at the
Wayback Machine
— library implementing relevant OGC standards
- EPSG.org- Official EPSG Geodetic Parameter Dataset webpage. Search engine for EPSG defined reference systems.
EPSG.org
- Official EPSG Geodetic Parameter Dataset webpage. Search engine for EPSG defined reference systems.
- EPSG.io/- Full text search indexing over 6000 coordinate systems
EPSG.io/
- Full text search indexing over 6000 coordinate systems
- Galdos Systems INdicio CRS Registry
Galdos Systems INdicio CRS Registry

<!-- table omitted -->

- v
v
- t
t
- e
e
Standards of the
Open Geospatial Consortium
(OGC)
- CSW
CSW
- GeoPackage
GeoPackage
- GeoRSS
GeoRSS
- GeoSPARQL
GeoSPARQL
- GML
GML
- KML
KML
- O&M
O&M
- OGC Reference Model
OGC Reference Model
- SensorML
SensorML
- SOS
SOS
- SFA
SFA
- SLD
SLD
- SRID
SRID
- TransducerML
TransducerML
- TMS
TMS
- WaterML
WaterML
- WCS
WCS
- WFS
WFS
- WMS
WMS
- WMTS
WMTS
- WPS
WPS

<!-- table omitted -->

- v
v
- t
t
- e
e
International Organization for Standardization
(ISO) standards
List of
ISO standards
–
ISO romanizations
–
IEC standards
1–9999
- 1
1
- 2
2
- 3
3
- 4
4
- 6
6
- 7
7
- 9
9
- 16
16
- 17
17
- 31-0-1-3-4-5-6-7-8-9-10-11-12-13
31
- -0
-0
- -1
-1
- -3
-3
- -4
-4
- -5
-5
- -6
-6
- -7
-7
- -8
-8
- -9
-9
- -10
-10
- -11
-11
- -12
-12
- -13
-13
- 68-1
68-1
- 128
128
- 216
216
- 217
217
- 226
226
- 228
228
- 233
233
- 259
259
- 261
261
- 262
262
- 302
302
- 306
306
- 361
361
- 500
500
- 518
518
- 519
519
- 639-1-2-3-5-6
639
- -1
-1
- -2
-2
- -3
-3
- -5
-5
- -6
-6
- 646
646
- 657
657
- 668
668
- 690
690
- 704
704
- 732
732
- 764
764
- 838
838
- 843
843
- 860
860
- 898
898
- 965
965
- 999
999
- 1000
1000
- 1004
1004
- 1007
1007
- 1073-1
1073-1
- 1073-2
1073-2
- 1155
1155
- 1413
1413
- 1538
1538
- 1629
1629
- 1745
1745
- 1989
1989
- 2014
2014
- 2015
2015
- 2022
2022
- 2033
2033
- 2047
2047
- 2108
2108
- 2145
2145
- 2146
2146
- 2240
2240
- 2281
2281
- 2533
2533
- 2709
2709
- 2711
2711
- 2720
2720
- 2788
2788
- 2848
2848
- 2852
2852
- 2921
2921
- 3029
3029
- 3103
3103
- 3166-1-2-3
3166
- -1
-1
- -2
-2
- -3
-3
- 3297
3297
- 3307
3307
- 3601
3601
- 3602
3602
- 3864
3864
- 3901
3901
- 3950
3950
- 3977
3977
- 4031
4031
- 4157
4157
- 4165
4165
- 4217
4217
- 4909
4909
- 5218
5218
- 5426
5426
- 5427
5427
- 5428
5428
- 5725
5725
- 5775
5775
- 5776
5776
- 5800
5800
- 5807
5807
- 5964
5964
- 6166
6166
- 6344
6344
- 6346
6346
- 6373
6373
- 6385
6385
- 6425
6425
- 6429
6429
- 6438
6438
- 6523
6523
- 6709
6709
- 6943
6943
- 7001
7001
- 7002
7002
- 7010
7010
- 7027
7027
- 7064
7064
- 7098
7098
- 7185
7185
- 7200
7200
- 7498-1
7498
- -1
-1
- 7637
7637
- 7736
7736
- 7810
7810
- 7811
7811
- 7812
7812
- 7813
7813
- 7816
7816
- 7942
7942
- 8000
8000
- 8093
8093
- 8178
8178
- 8217
8217
- 8373
8373
- 8501-1
8501-1
- 8571
8571
- 8583
8583
- 8601
8601
- 8613
8613
- 8632
8632
- 8651
8651
- 8652
8652
- 8691
8691
- 8805/8806
8805/8806
- 8807
8807
- 8820-5
8820-5
- 8859-1-2-3-4-5-6-7-8-8-I-9-10-11-12-13-14-15-16
8859
- -1
-1
- -2
-2
- -3
-3
- -4
-4
- -5
-5
- -6
-6
- -7
-7
- -8
-8
- -8-I
-8-I
- -9
-9
- -10
-10
- -11
-11
- -12
-12
- -13
-13
- -14
-14
- -15
-15
- -16
-16
- 8879
8879
- 9000/9001
9000/9001
- 9036
9036
- 9075
9075
- 9126
9126
- 9141
9141
- 9227
9227
- 9241
9241
- 9293
9293
- 9314
9314
- 9362
9362
- 9407
9407
- 9496
9496
- 9506
9506
- 9529
9529
- 9564
9564
- 9592/9593
9592/9593
- 9594
9594
- 9660
9660
- 9797-1
9797-1
- 9897
9897
- 9899
9899
- 9945
9945
- 9984
9984
- 9985
9985
- 9995
9995
10000–19999
- 10006
10006
- 10007
10007
- 10116
10116
- 10118-3
10118-3
- 10160
10160
- 10161
10161
- 10165
10165
- 10179
10179
- 10206
10206
- 10218
10218
- 10279
10279
- 10303-11-21-22-28-238
10303
- -11
-11
- -21
-21
- -22
-22
- -28
-28
- -238
-238
- 10383
10383
- 10585
10585
- 10589
10589
- 10628
10628
- 10646
10646
- 10664
10664
- 10746
10746
- 10861
10861
- 10957
10957
- 10962
10962
- 10967
10967
- 11073
11073
- 11170
11170
- 11172
11172
- 11179
11179
- 11404
11404
- 11544
11544
- 11783
11783
- 11784
11784
- 11785
11785
- 11801
11801
- 11889
11889
- 11898
11898
- 11940(-2)
11940
(
-2
)
- 11941
11941
- 11941 (TR)
11941 (TR)
- 11992
11992
- 12006
12006
- 12052
12052
- 12182
12182
- 12207
12207
- 12234-2
12234-2
- 12620
12620
- 13211-1-2
13211
- -1
-1
- -2
-2
- 13216
13216
- 13250
13250
- 13399
13399
- 13406-2
13406-2
- 13450
13450
- 13485
13485
- 13490
13490
- 13567
13567
- 13568
13568
- 13584
13584
- 13616
13616
- 13816
13816
- 13818
13818
- 14000
14000
- 14031
14031
- 14224
14224
- 14289
14289
- 14396
14396
- 14443
14443
- 14496-2-3-6-10-11-12-14-17-20
14496
- -2
-2
- -3
-3
- -6
-6
- -10
-10
- -11
-11
- -12
-12
- -14
-14
- -17
-17
- -20
-20
- 14617
14617
- 14644
14644
- 14649
14649
- 14651
14651
- 14698
14698
- 14764
14764
- 14882
14882
- 14971
14971
- 15022
15022
- 15118
15118
- 15189
15189
- 15288
15288
- 15291
15291
- 15398
15398
- 15408
15408
- 15444-3-9
15444
- -3
-3
- -9
-9
- 15445
15445
- 15438
15438
- 15504
15504
- 15511
15511
- 15686
15686
- 15693
15693
- 15706-2
15706
- -2
-2
- 15707
15707
- 15897
15897
- 15919
15919
- 15924
15924
- 15926
15926
- 15926 WIP
15926 WIP
- 15930
15930
- 15938
15938
- 16023
16023
- 16262
16262
- 16355-1
16355-1
- 16485
16485
- 16612-2
16612-2
- 16750
16750
- 16949 (TS)
16949 (TS)
- 17024
17024
- 17025
17025
- 17100
17100
- 17203
17203
- 17369
17369
- 17442
17442
- 17506
17506
- 17799
17799
- 18004
18004
- 18014
18014
- 18181
18181
- 18245
18245
- 18629
18629
- 18760
18760
- 18916
18916
- 19005
19005
- 19011
19011
- 19092-1-2
19092
- -1
-1
- -2
-2
- 19114
19114
- 19115
19115
- 19125
19125
- 19136
19136
- 19407
19407
- 19439
19439
- 19500
19500
- 19501
19501
- 19502
19502
- 19503
19503
- 19505
19505
- 19506
19506
- 19507
19507
- 19508
19508
- 19509
19509
- 19510
19510
- 19600
19600
- 19650
19650
- 19752
19752
- 19757
19757
- 19770
19770
- 19775-1
19775-1
- 19794-5
19794-5
- 19831
19831
20000–29999
- 20000
20000
- 20022
20022
- 20121
20121
- 20400
20400
- 20802
20802
- 20830
20830
- 21000
21000
- 21001
21001
- 21047
21047
- 21122
21122
- 21500
21500
- 21778
21778
- 21827
21827
- 22000
22000
- 22275
22275
- 22300
22300
- 22301
22301
- 22395
22395
- 22537
22537
- 23000
23000
- 23003
23003
- 23008
23008
- 23009
23009
- 23090-3
23090-3
- 23092
23092
- 23094-1
23094-1
- 23094-2
23094-2
- 23270
23270
- 23271
23271
- 23360
23360
- 23941
23941
- 24517
24517
- 24613
24613
- 24617
24617
- 24707
24707
- 24728
24728
- 25178
25178
- 25964
25964
- 26000
26000
- 26262
26262
- 26300
26300
- 26324
26324
- 27000 series
27000 series
- 27000
27000
- 27001
27001
- 27002
27002
- 27005
27005
- 27006
27006
- 27729
27729
- 28000
28000
- 29110
29110
- 29148
29148
- 29199-2
29199-2
- 29500
29500
30000+
- 30170
30170
- 31000
31000
- 32000
32000
- 37001
37001
- 38500
38500
- 39075
39075
- 40230
40230
- 40240
40240
- 40250
40250
- 40260
40260
- 40314
40314
- 40500
40500
- 42010
42010
- 45001
45001
- 50001
50001
- 55000
55000
- 56000
56000
- 80000
80000
- Category
Category
NewPP limit report
Parsed by mw‐web.codfw.main‐7c6c8bdf8c‐76j6x
Cached time: 20260611180758
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, prevent‐selective‐update, show‐toc]
CPU time usage: 0.208 seconds
Real time usage: 0.414 seconds
Preprocessor visited node count: 927/1000000
Revision size: 16332/2097152 bytes
Post‐expand include size: 87107/2097152 bytes
Template argument size: 1970/2097152 bytes
Highest expansion depth: 11/100
Expensive parser function count: 6/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 50151/5000000 bytes
Lua time usage: 0.112/10.000 seconds
Lua memory usage: 5427804/52428800 bytes
Number of Wikibase entities loaded: 0/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  332.680      1 -total
 19.33%   64.307      1 Template:Geodesy
 18.87%   62.793      1 Template:Sidebar_with_collapsible_lists
 17.21%   57.245      1 Template:Reflist
 13.98%   46.499      2 Template:Cite_web
 12.24%   40.725      1 Template:Short_description
  7.40%   24.605      2 Template:Pagetype
  6.78%   22.546      2 Template:Navbox
  5.58%   18.572      1 Template:Wikidata_property
  5.34%   17.755      1 Template:OGC
Render ID 79fdd612-65c0-11f1-a6bb-a9c2172a8bd2
Saved in parser cache with key enwiki:pcache:2961833:|#|:idhash:canonical and timestamp 20260611180758 and revision id 1336385139. Rendering was triggered because: page_view
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Spatial_reference_system&oldid=1336385139
"
Categories
:
- Geographic coordinate systems
Geographic coordinate systems
- Geographic information systems
Geographic information systems
- Geodesy
Geodesy
- ISO/TC 211
ISO/TC 211
- Open Geospatial Consortium
Open Geospatial Consortium
- GIS file formats
GIS file formats
Hidden categories:
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata
- Webarchive template wayback links
Webarchive template wayback links