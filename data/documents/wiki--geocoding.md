<!-- source: https://en.wikipedia.org/wiki/Geocoding -->
# Address geocoding

> Source: https://en.wikipedia.org/wiki/Geocoding
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
(Redirected from
Geocoding
)
Process of turning a place name/address to coordinates
Not to be confused with
Geocode
,
Geolocating
, or
Geotagging
.

<!-- table omitted -->

This article
needs
more citations
.
Please help
improve this article
by
adding citations to reliable sources
. Unsourced material may be challenged and removed.
Find sources:
"Address geocoding"
–
news
·
newspapers
·
books
·
scholar
·
JSTOR
(
January 2014
)
(
Learn how and when to remove this message
)
Address geocoding, or simplygeocoding, is the process of taking a text-based description of a location, such as anaddressor the name of aplace, and returninggeographic coordinates(typically the latitude/longitude pair) to identify a location on the Earth's surface.[1]Reverse geocodingon the other hand convertsgeographic coordinatesto the description of a location, usually the name of a place or an addressable location. Geocoding relies on a computer representation of address points, the street / road network, together with postal and administrative boundaries.

Address geocoding
, or simply
geocoding
, is the process of taking a text-based description of a location, such as an
address
or the name of a
place
, and returning
geographic coordinates
(typically the latitude/longitude pair) to identify a location on the Earth's surface.
[
1
]
Reverse geocoding
on the other hand converts
geographic coordinates
to the description of a location, usually the name of a place or an addressable location. Geocoding relies on a computer representation of address points, the street / road network, together with postal and administrative boundaries.
- Geocode (verb):[2]provide geographical coordinates corresponding to (a location).
Geocode (
verb
):
[
2
]
provide geographical coordinates corresponding to (a location).
- Geocode(noun):  is acodethat represents a geographic entity (locationorobject).In general is a  human-readable and short identifier; like a nominal-geocode asISO 3166-1 alpha-2, or a grid-geocode, asGeohashgeocode.
Geocode
(
noun
):  is a
code
that represents a geographic entity (
location
or
object
).
In general is a  human-readable and short identifier; like a nominal-geocode as
ISO 3166-1 alpha-2
, or a grid-geocode, as
Geohash
geocode.
- Geocoder (noun): a piece of software or a (web) service that implements a geocoding process i.e. a set of interrelated components in the form of operations,algorithms, and data sources that work together to produce a spatial representation for descriptive locational references.
Geocoder (
noun
): a piece of software or a (web) service that implements a geocoding process i.e. a set of interrelated components in the form of operations,
algorithms
, and data sources that work together to produce a spatial representation for descriptive locational references.
The geographic coordinates representing locations often vary greatly in positional accuracy. Examples include buildingcentroids,land parcelcentroids, interpolated locations based onthoroughfareranges, street segments centroids,postal code centroids(e.g.ZIP codes,CEDEX), andadministrative divisionCentroids.

The geographic coordinates representing locations often vary greatly in positional accuracy. Examples include building
centroids
,
land parcel
centroids, interpolated locations based on
thoroughfare
ranges, street segments centroids,
postal code centroids
(e.g.
ZIP codes
,
CEDEX
), and
administrative division
Centroids.

## History

History
[
edit
]
Geocoding – a subset ofGeographic Information System(GIS)spatial analysis– has been a subject of interest since the early 1960s.

Geocoding – a subset of
Geographic Information System
(GIS)
spatial analysis
– has been a subject of interest since the early 1960s.

### 1960s

1960s
[
edit
]
In 1960, the first operational GIS –  named theCanada Geographic Information System(CGIS) – was invented by Dr.Roger Tomlinson, who has since been acknowledged as the father of GIS. The CGIS was used to store and analyze data collected for theCanada Land Inventory, which mapped information aboutagriculture,wildlife, andforestryat a scale of 1:50,000, in order to regulate land capability forrural Canada. However, the CGIS lasted until the 1990s and was never available commercially.

In 1960, the first operational GIS –  named the
Canada Geographic Information System
(CGIS) – was invented by Dr.
Roger Tomlinson
, who has since been acknowledged as the father of GIS. The CGIS was used to store and analyze data collected for the
Canada Land Inventory
, which mapped information about
agriculture
,
wildlife
, and
forestry
at a scale of 1:50,000, in order to regulate land capability for
rural Canada
. However, the CGIS lasted until the 1990s and was never available commercially.
On 1 July 1963, five-digit ZIP codes were introduced nationwide by the United States Post Office Department (USPOD). In 1983, nine-digit ZIP+4 codes were brought about as an extra identifier in more accurately locating addresses.

On 1 July 1963, five-digit ZIP codes were introduced nationwide by the United States Post Office Department (USPOD). In 1983, nine-digit ZIP+4 codes were brought about as an extra identifier in more accurately locating addresses.
In 1964, theHarvard Laboratory for Computer Graphics and Spatial Analysisdeveloped groundbreaking software code – e.g. GRID, and SYMAP – all of which were sources for commercial development of GIS.

In 1964, the
Harvard Laboratory for Computer Graphics and Spatial Analysis
developed groundbreaking software code – e.g. GRID, and SYMAP – all of which were sources for commercial development of GIS.
In 1967, a team at the Census Bureau – including the mathematician James Corbett[3]and Donald Cooke[4]– inventedDual Independent Map Encoding(DIME) – the first modern vector mapping model – which ciphered address ranges into street network files and incorporated the "percent along" geocoding algorithm.[5]Still in use by platforms such asGoogle MapsandMapQuest, the "percent along" algorithm denotes where a matched address is located along a reference feature as a percentage of the reference feature's total length.DIMEwas intended for the use of the United States Census Bureau, and it involved accurately mapping block faces, digitizing nodes representing street intersections, and formingspatial relationships. New Haven, Connecticut, was the first city on Earth with a geocodable streets network database.

In 1967, a team at the Census Bureau – including the mathematician James Corbett
[
3
]
and Donald Cooke
[
4
]
– invented
Dual Independent Map Encoding
(DIME) – the first modern vector mapping model – which ciphered address ranges into street network files and incorporated the "percent along" geocoding algorithm.
[
5
]
Still in use by platforms such as
Google Maps
and
MapQuest
, the "percent along" algorithm denotes where a matched address is located along a reference feature as a percentage of the reference feature's total length.
DIME
was intended for the use of the United States Census Bureau, and it involved accurately mapping block faces, digitizing nodes representing street intersections, and forming
spatial relationships
. New Haven, Connecticut, was the first city on Earth with a geocodable streets network database.

### 1980s

1980s
[
edit
]
In the late 1970s, two mainpublic domaingeocoding platforms were in development:GRASS GISand MOSS. The early 1980s saw the rise of many more commercial vendors of geocoding software, namelyIntergraph,ESRI,CARIS,ERDAS, andMapInfo Corporation. These platforms merged the 1960s approach of separatingspatial informationwith the approach of organizing this spatial information into database structures.

In the late 1970s, two main
public domain
geocoding platforms were in development:
GRASS GIS
and MOSS. The early 1980s saw the rise of many more commercial vendors of geocoding software, namely
Intergraph
,
ESRI
,
CARIS
,
ERDAS
, and
MapInfo Corporation
. These platforms merged the 1960s approach of separating
spatial information
with the approach of organizing this spatial information into database structures.
In 1986, Mapping Display and Analysis System (MIDAS) became the first desktop geocoding software, designed forMS-DOS. Geocoding was elevated from the research department into the business world with the acquisition of MIDAS by MapInfo. MapInfo has since been acquired byPitney Bowes, and has pioneered in merging geocoding with business intelligence; allowing location intelligence to provide solutions for thepublicandprivate sectors.

In 1986, Mapping Display and Analysis System (MIDAS) became the first desktop geocoding software, designed for
MS-DOS
. Geocoding was elevated from the research department into the business world with the acquisition of MIDAS by MapInfo. MapInfo has since been acquired by
Pitney Bowes
, and has pioneered in merging geocoding with business intelligence; allowing location intelligence to provide solutions for the
public
and
private sectors
.

### 1990s

1990s
[
edit
]
The end of the 20th century had seen geocoding become more user-oriented, especially via open-source GIS software. Mapping applications andgeospatial datahad become more accessible over the Internet.

The end of the 20th century had seen geocoding become more user-oriented, especially via open-source GIS software. Mapping applications and
geospatial data
had become more accessible over the Internet.
Because the mail-out/mail-back technique was so successful in the1980 census, the U.S. Bureau of Census was able to put together a large geospatial database, usinginterpolatedstreet geocoding.[6]This database – along with the Census' nationwide coverage of households – allowed for the birth ofTopologically Integrated Geographic Encoding and Referencing(TIGER).

Because the mail-out/mail-back technique was so successful in the
1980 census
, the U.S. Bureau of Census was able to put together a large geospatial database, using
interpolated
street geocoding.
[
6
]
This database – along with the Census' nationwide coverage of households – allowed for the birth of
Topologically Integrated Geographic Encoding and Referencing
(TIGER).
Containing address ranges instead of individual addresses, TIGER has since been implemented in nearly all geocoding software platforms used today. By the end of the1990 census, TIGER "contained alatitude/longitude-coordinate for more than 30 million feature intersections and endpoints and nearly 145 million feature 'shape' points that defined the more than 42 million feature segments that outlined more than 12 million polygons."[7]

Containing address ranges instead of individual addresses, TIGER has since been implemented in nearly all geocoding software platforms used today. By the end of the
1990 census
, TIGER "contained a
latitude/longitude
-coordinate for more than 30 million feature intersections and endpoints and nearly 145 million feature 'shape' points that defined the more than 42 million feature segments that outlined more than 12 million polygons."
[
7
]
TIGER was the breakthrough for "big data" geospatial solutions.

TIGER was the breakthrough for "big data" geospatial solutions.

### 2000s

2000s
[
edit
]
The early 2000s saw the rise ofCoding Accuracy Support System(CASS) address standardization. The CASS certification is offered to all softwarevendorsand advertising mailers who want theUnited States Postal Service(USPS) to assess the quality of their address-standardizing software. The annually renewed CASS certification is based ondelivery pointcodes, ZIP codes, and ZIP+4 codes. Adoption of a CASS certified software by software vendors allows them to receive discounts inbulk mailingand shipping costs. They can benefit from increased accuracy and efficiency in those bulk mailings, after having a certified database. In the early 2000s, geocoding platforms were also able to support multiple datasets.

The early 2000s saw the rise of
Coding Accuracy Support System
(CASS) address standardization. The CASS certification is offered to all software
vendors
and advertising mailers who want the
United States Postal Service
(USPS) to assess the quality of their address-standardizing software. The annually renewed CASS certification is based on
delivery point
codes, ZIP codes, and ZIP+4 codes. Adoption of a CASS certified software by software vendors allows them to receive discounts in
bulk mailing
and shipping costs. They can benefit from increased accuracy and efficiency in those bulk mailings, after having a certified database. In the early 2000s, geocoding platforms were also able to support multiple datasets.
In 2003, geocoding platforms were capable of merging postal codes with street data, updated monthly. This process became known as "conflation".

In 2003, geocoding platforms were capable of merging postal codes with street data, updated monthly. This process became known as "conflation".
Beginning in 2005, geocoding platforms included parcel-centroid geocoding. Parcel-centroid geocoding allowed for a lot of precision in geocoding an address. For example, parcel-centroid allowed a geocoder to determine the centroid of a specific building or lot of land. Platforms were now also able to determine the elevation of specificparcels.

Beginning in 2005, geocoding platforms included parcel-centroid geocoding. Parcel-centroid geocoding allowed for a lot of precision in geocoding an address. For example, parcel-centroid allowed a geocoder to determine the centroid of a specific building or lot of land. Platforms were now also able to determine the elevation of specific
parcels
.
2005 also saw the introduction of theAssessor's Parcel Number(APN). A jurisdiction'stax assessorwas able to assign this number to parcels of real estate. This allowed for proper identification and record-keeping. An APN is important for geocoding an area which is covered by a gas or oil lease, and indexing property tax information provided to the public.

2005 also saw the introduction of the
Assessor's Parcel Number
(APN). A jurisdiction's
tax assessor
was able to assign this number to parcels of real estate. This allowed for proper identification and record-keeping. An APN is important for geocoding an area which is covered by a gas or oil lease, and indexing property tax information provided to the public.
In 2006, Reverse Geocoding and reverse APN lookup were introduced to geocoding platforms. This involved geocoding a numerical point location – with alongitude and latitude– to a textual, readable address.

In 2006, Reverse Geocoding and reverse APN lookup were introduced to geocoding platforms. This involved geocoding a numerical point location – with a
longitude and latitude
– to a textual, readable address.
2008 and 2009 saw the growth of interactive, user-oriented geocoding platforms – namely MapQuest, Google Maps, Bing Maps, and Global Positioning Systems (GPS). These platforms were made even more accessible to the public with the simultaneous growth of the mobile industry, specifically smartphones.

2008 and 2009 saw the growth of interactive, user-oriented geocoding platforms – namely MapQuest, Google Maps, Bing Maps, and Global Positioning Systems (GPS). These platforms were made even more accessible to the public with the simultaneous growth of the mobile industry, specifically smartphones.

### 2010s

2010s
[
edit
]
The 2010s saw vendors fully support geocoding and reverse geocoding globally. Cloud-based geocoding application programming interface (API) and on-premises geocoding have allowed for a greater match rate, greater precision, and greater speed. There is now a popularity in the idea of geocoding being able to influence business decisions. This is the integration between the geocoding process and business intelligence.

The 2010s saw vendors fully support geocoding and reverse geocoding globally. Cloud-based geocoding application programming interface (API) and on-premises geocoding have allowed for a greater match rate, greater precision, and greater speed. There is now a popularity in the idea of geocoding being able to influence business decisions. This is the integration between the geocoding process and business intelligence.
The future of geocoding also involves three-dimensional geocoding, indoor geocoding, and multiple language returns for the geocoding platforms.

The future of geocoding also involves three-dimensional geocoding, indoor geocoding, and multiple language returns for the geocoding platforms.

## Geocoding process

Geocoding process
[
edit
]
Geocoding is a task which involves multiple datasets and processes, all of which work together. Some of the components are provided by the user, while others are built into the geocoding software.

Geocoding is a task which involves multiple datasets and processes, all of which work together. Some of the components are provided by the user, while others are built into the geocoding software.

### Input dataset

Input dataset
[
edit
]
Input data are the descriptive, textual information (address or building name) which the user wants to turn into numerical, spatial data (latitude and longitude) through the process of geocoding. These are often included in a table with other attributes of the locations. Input data is classified into two categories:

Input data are the descriptive, textual information (address or building name) which the user wants to turn into numerical, spatial data (latitude and longitude) through the process of geocoding. These are often included in a table with other attributes of the locations. Input data is classified into two categories:
Relative input data
Relative input data are the textual descriptions of a location which, alone, cannot specify a spatial representation of that location, but is geographically dependent and geographically relative on other locations. An example of a relative geocode is "Across the street from the Empire State Building." The location being sought cannot be determined without identifying the Empire State Building. Geocoding platforms often do not support such relative locations, but advances are being made in this direction.
Absolute input data
Absolute input data are the textual descriptions of a location which, alone, can output a spatial representation of that location. This data type outputs an absolute known location independently of other locations. For example, USPS ZIP codes; USPS ZIP+4 codes; complete and partial postal addresses; USPS PO boxes; rural routes; cities; counties; intersections; and named places can all be referenced in a data source absolutely.
To achieve the greatest accuracy, the geocodes in the input dataset need to be as correct as possible, and formatted in standard ways. Thus, it is common to first go through a process ofdata cleansing, often called "address scrubbing," to find and correct any errors. This is especially important for databases in which participants enter their own location geocodes, frequently resulting in a variety of forms (e.g., "Pennsylvania," "PA," "Penn.") and misspellings.

To achieve the greatest accuracy, the geocodes in the input dataset need to be as correct as possible, and formatted in standard ways. Thus, it is common to first go through a process of
data cleansing
, often called "address scrubbing," to find and correct any errors. This is especially important for databases in which participants enter their own location geocodes, frequently resulting in a variety of forms (e.g., "Pennsylvania," "PA," "Penn.") and misspellings.

### Reference dataset

Reference dataset
[
edit
]
The second necessary dataset specifies the locations of geographic features in a commonspatial reference system, usually stored in aGIS file formatorspatial database. Examples include a point dataset of buildings, a line dataset of streets, or a polygon dataset of counties. The attributes of these features must include information that will match the geocodes in the input dataset, such as a name, unique id, or standard geocode such as the United StatesFIPS codesfor geographic features. It is common for the reference dataset to include multiple attribute columns of geocodes for flexibility or handling of complex geocodes. For example, a street dataset intended to be used for street address geocoding must include not only the street name, but any directional suffixes or prefixes and the range of address numbers found on each segment.

The second necessary dataset specifies the locations of geographic features in a common
spatial reference system
, usually stored in a
GIS file format
or
spatial database
. Examples include a point dataset of buildings, a line dataset of streets, or a polygon dataset of counties. The attributes of these features must include information that will match the geocodes in the input dataset, such as a name, unique id, or standard geocode such as the United States
FIPS codes
for geographic features. It is common for the reference dataset to include multiple attribute columns of geocodes for flexibility or handling of complex geocodes. For example, a street dataset intended to be used for street address geocoding must include not only the street name, but any directional suffixes or prefixes and the range of address numbers found on each segment.

### Geocoder algorithm

Geocoder algorithm
[
edit
]
The third component is software that matches each geocode in the input dataset to the attributes of a corresponding feature in the reference dataset. Once a match is made, the location of the reference feature can be attached to the input row. These algorithms are of two types:

The third component is software that matches each geocode in the input dataset to the attributes of a corresponding feature in the reference dataset. Once a match is made, the location of the reference feature can be attached to the input row. These algorithms are of two types:
Direct match
The geocoder expects each input item to directly correspond to a single entire feature in the reference dataset. For example, a country or zip code, or matching street addresses to building point reference data. This kind of match is similar to a relational
table join
, except that geocoder algorithms usually incorporate some kind of uncertainty handling to recognize approximate matches (e.g., different capitalization or slight misspellings).
Interpolated match
The geocode specifies not only a feature, but some location within that feature. The most common (and oldest) example is matching street addresses to street line data. First the geocoder parses the street address into its component parts (street name, number, directional prefix/suffix). The geocoder matches these components to a corresponding street segment with a number range that includes the input value. Then it calculates where the given number falls within the segment's range to estimate a location along the segment. As with the direct match, these algorithms usually have uncertainty handling to handle approximate matches (especially abbreviations such as "E" for "East" and "Dr" for "Drive").
The algorithm is rarely able to perfectly locate all of the input data; mismatches can occur due to misspelled or incomplete input data, imperfect (usually outdated) reference data, or unique regional geocoding systems that the algorithm does not recognize. Many geocoders provide a follow-up stage to manually review and correct suspect matches.

The algorithm is rarely able to perfectly locate all of the input data; mismatches can occur due to misspelled or incomplete input data, imperfect (usually outdated) reference data, or unique regional geocoding systems that the algorithm does not recognize. Many geocoders provide a follow-up stage to manually review and correct suspect matches.

## Address interpolation

Address interpolation
[
edit
]
A simple method of geocoding is addressinterpolation.  This method makes use of data from a streetgeographic information systemwhere the street network is already mapped within the geographic coordinate space.  Each street segment is attributed with address ranges (e.g. house numbers from one segment to the next).  Geocoding takes an address, matches it to a street and specific segment (such as ablock, in towns that use the "block" convention). Geocoding then interpolates the position of the address, within the range along the segment.

A simple method of geocoding is address
interpolation
.  This method makes use of data from a street
geographic information system
where the street network is already mapped within the geographic coordinate space.  Each street segment is attributed with address ranges (e.g. house numbers from one segment to the next).  Geocoding takes an address, matches it to a street and specific segment (such as a
block
, in towns that use the "block" convention). Geocoding then interpolates the position of the address, within the range along the segment.

### Example

Example
[
edit
]
Take for example:742 Evergreen Terrace

Take for example:
742 Evergreen Terrace
Let's say that this segment (for instance, a block) of Evergreen Terrace runs from 700 to 799.  Even-numbered addresses fall on the east side of Evergreen Terrace, with odd-numbered addresses on the west side of the street.  742 Evergreen Terrace would (probably) be located slightly less than halfway up the block, on the east side of the street.  A point would be mapped at that location along the street, perhaps offset a distance to the east of the street centerline.

Let's say that this segment (for instance, a block) of Evergreen Terrace runs from 700 to 799.  Even-numbered addresses fall on the east side of Evergreen Terrace, with odd-numbered addresses on the west side of the street.  742 Evergreen Terrace would (probably) be located slightly less than halfway up the block, on the east side of the street.  A point would be mapped at that location along the street, perhaps offset a distance to the east of the street centerline.

### Complicating factors

Complicating factors
[
edit
]

<!-- table omitted -->

This section
is written like a
personal reflection, personal essay, or argumentative essay
that states a Wikipedia editor's personal feelings or presents an original argument about a topic.
Please
help improve it
by rewriting it in an
encyclopedic style
.
(
December 2014
)
(
Learn how and when to remove this message
)
However, this process is not always as straightforward as in this example.
Difficulties arise when

However, this process is not always as straightforward as in this example.
Difficulties arise when
- distinguishing between ambiguous addresses such as 742 Evergreen Terrace and 742 W Evergreen Terrace.
distinguishing between ambiguous addresses such as 742 Evergreen Terrace and 742 W Evergreen Terrace.
- attempting to geocode new addresses for a street that is not yet added to the geographic information system database.
attempting to geocode new addresses for a street that is not yet added to the geographic information system database.
While there might be a 742 Evergreen Terrace in Springfield, there might also be a 742 Evergreen Terrace in Shelbyville.  Asking for the city name (and state, province, country, etc. as needed) can solve this problem.Boston,Massachusetts[8]has multiple "100 Washington Street" locations because several cities have been annexed without changing street names, thus requiring use of uniquepostal codesor district names for disambiguation.
Geocoding accuracy can be greatly improved by first utilizing goodaddress verificationpractices.  Address verification will confirm the existence of the address and will eliminate ambiguities.  Once the valid address is determined, it is very easy to geocode and determine the latitude/longitude coordinates.
Finally, several caveats on using interpolation:

While there might be a 742 Evergreen Terrace in Springfield, there might also be a 742 Evergreen Terrace in Shelbyville.  Asking for the city name (and state, province, country, etc. as needed) can solve this problem.
Boston
,
Massachusetts
[
8
]
has multiple "100 Washington Street" locations because several cities have been annexed without changing street names, thus requiring use of unique
postal codes
or district names for disambiguation.
Geocoding accuracy can be greatly improved by first utilizing good
address verification
practices.  Address verification will confirm the existence of the address and will eliminate ambiguities.  Once the valid address is determined, it is very easy to geocode and determine the latitude/longitude coordinates.
Finally, several caveats on using interpolation:
- The typical attribution of a street segment assumes that all even numbered parcels are on one side of the segment, and all odd numbered parcels are on the other. This is often not true in real life.
The typical attribution of a street segment assumes that all even numbered parcels are on one side of the segment, and all odd numbered parcels are on the other. This is often not true in real life.
- Interpolation assumes that the given parcels are evenly distributed along the length of the segment. This is almost never true in real life; it is not uncommon for a geocoded address to be off by several thousand feet.
Interpolation assumes that the given parcels are evenly distributed along the length of the segment. This is almost never true in real life; it is not uncommon for a geocoded address to be off by several thousand feet.
- Interpolation also assumes that the street is straight.  If a street is curved then the geocoded location will not necessarily fit the physical location of the address.
Interpolation also assumes that the street is straight.  If a street is curved then the geocoded location will not necessarily fit the physical location of the address.
- Segment Information (esp. from sources such asTIGER) includes a maximum upper bound for addresses and is interpolated as though the full address range is used.  For example, a segment (block) might have a listed range of 100–199, but the last address at the end of the block is 110.  In this case, address 110 would be geocoded to 10% of the distance down the segment rather than near the end.
Segment Information (esp. from sources such as
TIGER
) includes a maximum upper bound for addresses and is interpolated as though the full address range is used.  For example, a segment (block) might have a listed range of 100–199, but the last address at the end of the block is 110.  In this case, address 110 would be geocoded to 10% of the distance down the segment rather than near the end.
- Most interpolation implementations will produce a point as their resulting address location. In reality, the physical address is distributed along the length of the segment, i.e. consider geocoding the address of ashopping mall– the physical lot may run a distance along the street segment (or could be thought of as a two-dimensional space-filling polygon which may front on several different streets — or worse, for cities with multi-level streets, a three-dimensional shape that meets different streets at several different levels) but the interpolation treats it as a singularity.
Most interpolation implementations will produce a point as their resulting address location. In reality, the physical address is distributed along the length of the segment, i.e. consider geocoding the address of a
shopping mall
– the physical lot may run a distance along the street segment (or could be thought of as a two-dimensional space-filling polygon which may front on several different streets — or worse, for cities with multi-level streets, a three-dimensional shape that meets different streets at several different levels) but the interpolation treats it as a singularity.
A very common error is to believe the accuracy ratings of a given map's geocodable attributes.  Such accuracy as quoted by vendors has no bearing on an address being attributed to the correct segment or to the correct side of the segment, nor resulting in an accurate position along that correct segment.  With the geocoding process used forU.S. censusTIGER datasets, 5–7.5% of the addresses may be allocated to a differentcensus tract, while a study of Australia's TIGER-like system found that 50% of the geocoded points were mapped to the wrong property parcel.[9]The accuracy of geocoded data can also have a bearing on the quality of research that uses this data.  One study[10]by a group of Iowa researchers found that the common method of geocoding using TIGER datasets as described above, can cause a loss of as much as 40% of the power of a statistical analysis.  An alternative is to useorthophotoor image coded data such as the Address Point data fromOrdnance Surveyin the UK, but such datasets are generally expensive.

A very common error is to believe the accuracy ratings of a given map's geocodable attributes.  Such accuracy as quoted by vendors has no bearing on an address being attributed to the correct segment or to the correct side of the segment, nor resulting in an accurate position along that correct segment.  With the geocoding process used for
U.S. census
TIGER datasets, 5–7.5% of the addresses may be allocated to a different
census tract
, while a study of Australia's TIGER-like system found that 50% of the geocoded points were mapped to the wrong property parcel.
[
9
]
The accuracy of geocoded data can also have a bearing on the quality of research that uses this data.  One study
[
10
]
by a group of Iowa researchers found that the common method of geocoding using TIGER datasets as described above, can cause a loss of as much as 40% of the power of a statistical analysis.  An alternative is to use
orthophoto
or image coded data such as the Address Point data from
Ordnance Survey
in the UK, but such datasets are generally expensive.
Because of this, it is quite important to avoid using interpolated results except for non-critical applications.  Interpolated geocoding is usually not appropriate for making authoritative decisions, for example if life safety will be affected by that decision.  Emergency services, for example, do not make an authoritative decision based on their interpolations; an ambulance or fire truck will always be dispatched regardless of what the map says.[citation needed]

Because of this, it is quite important to avoid using interpolated results except for non-critical applications.  Interpolated geocoding is usually not appropriate for making authoritative decisions, for example if life safety will be affected by that decision.  Emergency services, for example, do not make an authoritative decision based on their interpolations; an ambulance or fire truck will always be dispatched regardless of what the map says.
[
citation needed
]

## Other techniques

Other techniques
[
edit
]
In rural areas or other places lacking high quality street network data and addressing,GPSis useful for mapping a location.  For traffic accidents, geocoding to a street intersection or midpoint along a street centerline is a suitable technique.  Most highways in developed countries havemile markersto aid in emergency response, maintenance, and navigation.  It is also possible to use a combination of these geocoding techniques — using a particular technique for certain cases and situations and other techniques for other cases.
In contrast to geocoding of structured postal address records,toponym resolutionmaps place names in unstructured document collections to their corresponding spatial footprints.

In rural areas or other places lacking high quality street network data and addressing,
GPS
is useful for mapping a location.  For traffic accidents, geocoding to a street intersection or midpoint along a street centerline is a suitable technique.  Most highways in developed countries have
mile markers
to aid in emergency response, maintenance, and navigation.  It is also possible to use a combination of these geocoding techniques — using a particular technique for certain cases and situations and other techniques for other cases.
In contrast to geocoding of structured postal address records,
toponym resolution
maps place names in unstructured document collections to their corresponding spatial footprints.
- Place codesoffer a way to create digitally generated addresses where no information exists using satellite imagery and machine learning, e.g.,Robocodes
Place codes
offer a way to create digitally generated addresses where no information exists using satellite imagery and machine learning, e.g.,
Robocodes
- Natural Address Codes[11]are a proprietary geocode system that can address an area anywhere on the Earth, or a volume of space anywhere around the Earth. The use of  alphanumeric characters instead of only ten digits makes a NAC shorter than its numerical latitude/longitude equivalent.
Natural Address Codes
[
11
]
are a proprietary geocode system that can address an area anywhere on the Earth, or a volume of space anywhere around the Earth. The use of  alphanumeric characters instead of only ten digits makes a NAC shorter than its numerical latitude/longitude equivalent.
- Military Grid Reference Systemis the geocoordinate standard used by NATO militaries for locating points on Earth.
Military Grid Reference System
is the geocoordinate standard used by NATO militaries for locating points on Earth.
- Universal Transverse Mercator coordinate systemis a map projection system for assigning coordinates to locations on the surface of the Earth.
Universal Transverse Mercator coordinate system
is a map projection system for assigning coordinates to locations on the surface of the Earth.
- theMaidenhead Locator System, popular with radio operators.
the
Maidenhead Locator System
, popular with radio operators.
- theWorld Geographic Reference System(GEOREF), developed for global military operations, replaced by the currentGlobal Area Reference System(GARS).
the
World Geographic Reference System
(GEOREF), developed for global military operations, replaced by the current
Global Area Reference System
(GARS).
- Open Location Codeor "Plus Codes," developed by Google and released into the public domain.
Open Location Code
or "Plus Codes," developed by Google and released into the public domain.
- Geohash, a public domain system based on the MortonZ-order curve.
Geohash
, a public domain system based on the Morton
Z-order curve
.
- What3words, a proprietary system that encodesgeographic coordinate system(GCS) coordinates as pseudorandom sets of words by dividing the coordinates into three numbers and looking up words in an indexed dictionary.
What3words
, a proprietary system that encodes
geographic coordinate system
(GCS) coordinates as pseudorandom sets of words by dividing the coordinates into three numbers and looking up words in an indexed dictionary.
- FullerCode, an open and free system developed to facilitate the transmission of geographic positions by voice (e.g., over radio or telephone).
FullerCode
, an open and free system developed to facilitate the transmission of geographic positions by voice (e.g., over radio or telephone).

## Research

Research
[
edit
]
Research has introduced a new approach to the control and knowledge aspects of geocoding, by using an agent-based paradigm.[12]In addition to the new paradigm for geocoding, additional correction techniques and control algorithms have been developed.[13]The approach represents the geographic elements commonly found in addresses as individual agents. This provides a commonality and duality to control and geographic representation. In addition to scientific publication, the new approach and subsequent prototype gained national media coverage in Australia.[14]The research was conducted at Curtin University in Perth, Western Australia.[15]

Research has introduced a new approach to the control and knowledge aspects of geocoding, by using an agent-based paradigm.
[
12
]
In addition to the new paradigm for geocoding, additional correction techniques and control algorithms have been developed.
[
13
]
The approach represents the geographic elements commonly found in addresses as individual agents. This provides a commonality and duality to control and geographic representation. In addition to scientific publication, the new approach and subsequent prototype gained national media coverage in Australia.
[
14
]
The research was conducted at Curtin University in Perth, Western Australia.
[
15
]
With the recent advance in Deep Learning and Computer Vision, a new geocoding workflow, which leverages Object Detection techniques to directly extract the centroid of the building rooftops as geocoding output, has been proposed.[16]

With the recent advance in Deep Learning and Computer Vision, a new geocoding workflow, which leverages Object Detection techniques to directly extract the centroid of the building rooftops as geocoding output, has been proposed.
[
16
]

## Uses

Uses
[
edit
]
Geocoded locations are useful in many GIS analysis, cartography, decision making workflow, transaction mash-up, or injected into larger business processes. On the web, geocoding is used in services like routing andlocal search. Geocoding, along withGPSprovides location data forgeotaggingmedia, such as photographs orRSSitems.

Geocoded locations are useful in many GIS analysis, cartography, decision making workflow, transaction mash-up, or injected into larger business processes. On the web, geocoding is used in services like routing and
local search
. Geocoding, along with
GPS
provides location data for
geotagging
media, such as photographs or
RSS
items.

## Privacy concerns

Privacy concerns
[
edit
]
The proliferation and ease of access to geocoding (andreverse geocoding) services raises privacy concerns.  For example, in mapping crime incidents, law enforcement agencies aim to balance the privacy rights of victims and offenders, with the public's right to know.  Law enforcement agencies have experimented with alternative geocoding techniques that allow them to mask a portion of the locational detail (e.g., address specifics that would lead to identifying a victim or offender).  As well, in providing onlinecrime mappingto the public, they also place disclaimers regarding the locational accuracy of points on the map, acknowledging these location masking techniques, and impose terms of use for the information.

The proliferation and ease of access to geocoding (and
reverse geocoding
) services raises privacy concerns.  For example, in mapping crime incidents, law enforcement agencies aim to balance the privacy rights of victims and offenders, with the public's right to know.  Law enforcement agencies have experimented with alternative geocoding techniques that allow them to mask a portion of the locational detail (e.g., address specifics that would lead to identifying a victim or offender).  As well, in providing online
crime mapping
to the public, they also place disclaimers regarding the locational accuracy of points on the map, acknowledging these location masking techniques, and impose terms of use for the information.

## See also

See also
[
edit
]
- Azure Maps, a leading commercial geocoding service
Azure Maps
, a leading commercial geocoding service
- Geocode
Geocode
- Gazetteer
Gazetteer
- Geocoded photo, which includes methods of geocoding images
Geocoded photo
, which includes methods of geocoding images
- Geographic information system(GIS)
Geographic information system
(GIS)
- Geolocation
Geolocation
- Geoparsing
Geoparsing
- Georeference
Georeference
- Geotagging
Geotagging
- Linear referencing
Linear referencing
- Reverse geocoding
Reverse geocoding
- Toponym resolution
Toponym resolution

## References

References
[
edit
]
- ^Leidner, J.L. (2017). "Georeferencing: From Texts to Maps".International Encyclopedia of Geography. Vol. vi. pp.2897–2907.doi:10.1002/9781118786352.wbieg0160.ISBN9780470659632.
^
Leidner, J.L. (2017). "Georeferencing: From Texts to Maps".
International Encyclopedia of Geography
. Vol. vi. pp.
2897–
2907.
doi
:
10.1002/9781118786352.wbieg0160
.
ISBN
9780470659632
.
- ^"Geocode" term as a verb, as defined by Oxford English Dictionary athttps://en.oxforddictionaries.com/definition/geocodeArchived26 April 2018 at theWayback Machine
^
"Geocode" term as a verb, as defined by Oxford English Dictionary at
https://en.oxforddictionaries.com/definition/geocode
Archived
26 April 2018 at the
Wayback Machine
- ^Corbett, James P. Topological principles in cartography. Vol. 48. US Department of Commerce, Bureau of the Census, 1979.
^
Corbett, James P. Topological principles in cartography. Vol. 48. US Department of Commerce, Bureau of the Census, 1979.
- ^"Short CV"(PDF). Retrieved9 April2023.
^
"Short CV"
(PDF)
. Retrieved
9 April
2023
.
- ^Olivares, Miriam."Geographic Information Systems at Yale: Geocoding Resources".guides.library.yale.edu. Retrieved22 June2016.
^
Olivares, Miriam.
"Geographic Information Systems at Yale: Geocoding Resources"
.
guides.library.yale.edu
. Retrieved
22 June
2016
.
- ^"Spatially enabling the data: What is geocoding?".National Criminal Justice Reference Service. Retrieved22 June2016.
^
"Spatially enabling the data: What is geocoding?"
.
National Criminal Justice Reference Service
. Retrieved
22 June
2016
.
- ^"25th Anniversary of TIGER".census.maps.arcgis.com. Retrieved22 June2016.
^
"25th Anniversary of TIGER"
.
census.maps.arcgis.com
. Retrieved
22 June
2016
.
- ^"Google Maps".Google Maps. Retrieved9 April2023.
^
"Google Maps"
.
Google Maps
. Retrieved
9 April
2023
.
- ^Ratcliffe, Jerry H. (2001)."On the accuracy of TIGER-type geocoded address data in relation to cadastral and census areal units"(PDF).International Journal of Geographical Information Science.15(5):473–485.Bibcode:2001IJGIS..15..473R.doi:10.1080/13658810110047221.S2CID14061774. Archived fromthe original(PDF)on 23 June 2006.
^
Ratcliffe, Jerry H. (2001).
"On the accuracy of TIGER-type geocoded address data in relation to cadastral and census areal units"
(PDF)
.
International Journal of Geographical Information Science
.
15
(5):
473–
485.
Bibcode
:
2001IJGIS..15..473R
.
doi
:
10.1080/13658810110047221
.
S2CID
14061774
. Archived from
the original
(PDF)
on 23 June 2006.
- ^Mazumdar S, Rushton G, Smith B, et al. (2008)."Geocoding accuracy and the recovery of relationships between environmental exposures and health".International Journal of Health Geographics.7(1):1–13.Bibcode:2008IJHGg...7...13M.doi:10.1186/1476-072X-7-13.PMC2359739.PMID18387189.
^
Mazumdar S, Rushton G, Smith B, et al. (2008).
"Geocoding accuracy and the recovery of relationships between environmental exposures and health"
.
International Journal of Health Geographics
.
7
(1):
1–
13.
Bibcode
:
2008IJHGg...7...13M
.
doi
:
10.1186/1476-072X-7-13
.
PMC
2359739
.
PMID
18387189
.
- ^Rwerekane, Valentin; Ndashimye, Maurice (2017)."Natural Area Coding Based Postcode Scheme"(PDF).International Journal of Computer and Communication Engineering.6(3):161–172.doi:10.17706/IJCCE.2017.6.3.161-172. Retrieved25 August2022.
^
Rwerekane, Valentin; Ndashimye, Maurice (2017).
"Natural Area Coding Based Postcode Scheme"
(PDF)
.
International Journal of Computer and Communication Engineering
.
6
(3):
161–
172.
doi
:
10.17706/IJCCE.2017.6.3.161-172
. Retrieved
25 August
2022
.
- ^Hutchinson, Matthew J (2010).Developing an Agent-Based Framework for Intelligent Geocoding(PhD thesis). Curtin University.
^
Hutchinson, Matthew J (2010).
Developing an Agent-Based Framework for Intelligent Geocoding
(PhD thesis). Curtin University.
- ^An Agent-Based Framework to Enable Intelligent Geocoding Services
^
An Agent-Based Framework to Enable Intelligent Geocoding Services
- ^Jennifer Foreshew (24 November 2009)."Difficult addresses no problem for IntelliGeoLocator".The Australian. Retrieved9 May2011.
^
Jennifer Foreshew (24 November 2009).
"Difficult addresses no problem for IntelliGeoLocator"
.
The Australian
. Retrieved
9 May
2011
.
- ^Department of Education, Western Australia (April 2011)."X marks the spot".School Matters. Retrieved9 May2011.
^
Department of Education, Western Australia (April 2011).
"X marks the spot"
.
School Matters
. Retrieved
9 May
2011
.
- ^Yin, Zhengcong; et al. (2019)."A deep learning approach for rooftop geocoding".Transactions in GIS.23(3):495–514.Bibcode:2019TrGIS..23..495Y.doi:10.1111/tgis.12536.S2CID195804197.
^
Yin, Zhengcong; et al. (2019).
"A deep learning approach for rooftop geocoding"
.
Transactions in GIS
.
23
(3):
495–
514.
Bibcode
:
2019TrGIS..23..495Y
.
doi
:
10.1111/tgis.12536
.
S2CID
195804197
.

## External links

External links
[
edit
]
- Three Standard Geocoding Methods(in North America) – article
Three Standard Geocoding Methods
(in North America) – article
- The Evolution of Geocoding: Moving Away from Conflation Confliction to Best Match– article
The Evolution of Geocoding: Moving Away from Conflation Confliction to Best Match
– article
- A Flexible Addressing System for Approximate Geocoding– paper presented at Geoinfo 2003
A Flexible Addressing System for Approximate Geocoding
– paper presented at Geoinfo 2003
- The UCDP and AidData codebook on geo-referencing aid– guide for geocoding development aid projects
The UCDP and AidData codebook on geo-referencing aid
– guide for geocoding development aid projects

<!-- table omitted -->

- v
v
- t
t
- e
e
Geocode systems
Country codes
- IANA country code
IANA country code
- ISO 3166-1alpha-2alpha-3numeric
ISO 3166-1
- alpha-2
alpha-2
- alpha-3
alpha-3
- numeric
numeric
- Aircraft prefixes
Aircraft prefixes
- IOC country code
IOC country code
- FIFA country code
FIFA country code
- Vehicle country codes
Vehicle country codes
- FIPS country code(FIPS 10-4)
FIPS country code
(FIPS 10-4)
- FIPS 6-4
FIPS 6-4
Administrative codes
and country subdivisions
- ISO 3166-2
ISO 3166-2
- FIPS place code(FIPS 55)
FIPS place code
(FIPS 55)
- FIPS state code(FIPS 5-2)
FIPS state code
(FIPS 5-2)
- NUTS(EU)
NUTS
(EU)
- GSS codes(United Kingdom)
GSS codes
(United Kingdom)
- SGC codes(Canada)
SGC codes
(Canada)
- UN M.49(UN)
UN M.49
(UN)
Airport codes
- IATA airport code
IATA airport code
- ICAO airport code
ICAO airport code
Geodesic
place codes

<!-- table omitted -->

Global
- C-squares
C-squares
- Geohash
Geohash
- Geohash-36
Geohash-36
- GEOREF
GEOREF
- International Map of the Worldindexing system
International Map of the World
indexing system
- Mapcode
Mapcode
- Marsden square
Marsden square
- Military Grid Reference System
Military Grid Reference System
- Natural Area Code
Natural Area Code
- Open Location Code
Open Location Code
- QDGC
QDGC
- UN/LOCODE
UN/LOCODE
- UTM
UTM
- WMO squares
WMO squares
Regional
- ICES Statistical Rectangles(north-east Atlantic region)
ICES Statistical Rectangles
(north-east Atlantic region)
- Irish grid reference system
Irish grid reference system
- National Topographic System(Canada)
National Topographic System
(Canada)
- Ordnance Survey National Grid(UK)
Ordnance Survey National Grid
(UK)
- National Level Addressing Grid(India)
National Level Addressing Grid
(India)
Postal codes
- Australian post codes
Australian post codes
- CEP(Brazil)
CEP
(Brazil)
- Eircodes(Republic of Ireland)
Eircodes
(Republic of Ireland)
- New Zealand post codes
New Zealand post codes
- Postal Index Number(India)
Postal Index Number
(India)
- United Kingdom post codes
United Kingdom post codes
- ZIP Code(United States)
ZIP Code
(United States)
Telephony
- ITU-R country codes
ITU-R country codes
- ITU-T telephone country codes
ITU-T telephone country codes
- ITU-T mobile country codes
ITU-T mobile country codes
Amateur radio
- Maidenhead Locator System
Maidenhead Locator System
- Historical :QRA locator
Historical :
QRA locator
NewPP limit report
Parsed by mw‐web.codfw.main‐8b57965b8‐7znf5
Cached time: 20260629182646
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, prevent‐selective‐update, show‐toc]
CPU time usage: 0.379 seconds
Real time usage: 0.479 seconds
Preprocessor visited node count: 1395/1000000
Revision size: 29936/2097152 bytes
Post‐expand include size: 66731/2097152 bytes
Template argument size: 1803/2097152 bytes
Highest expansion depth: 12/100
Expensive parser function count: 8/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 66739/5000000 bytes
Lua time usage: 0.243/10.000 seconds
Lua memory usage: 7333232/52428800 bytes
Number of Wikibase entities loaded: 0/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  415.612      1 -total
 39.46%  164.001      1 Template:Reflist
 17.56%   73.001      1 Template:Cite_book
 17.33%   72.039      1 Template:Geocoding-systems
 17.11%   71.111      2 Template:Navbox
 13.97%   58.065      1 Template:More_citations_needed
 13.85%   57.567      1 Template:Short_description
 12.97%   53.905      2 Template:Ambox
  8.51%   35.358      2 Template:Pagetype
  5.53%   23.002      1 Template:Distinguish
Render ID 15c48221-73e8-11f1-ac12-53d8ef463def
Saved in parser cache with key enwiki:pcache:1876018:|#|:idhash:canonical and timestamp 20260629182646 and revision id 1349909418. Rendering was triggered because: page_view
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Address_geocoding&oldid=1349909418
"
Categories
:
- Geocodes
Geocodes
- Geographic information systems
Geographic information systems
Hidden categories:
- Webarchive template wayback links
Webarchive template wayback links
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata
- Articles needing additional references from January 2014
Articles needing additional references from January 2014
- All articles needing additional references
All articles needing additional references
- Use dmy dates from January 2020
Use dmy dates from January 2020
- Wikipedia articles with style issues from December 2014
Wikipedia articles with style issues from December 2014
- All articles with style issues
All articles with style issues
- All articles with unsourced statements
All articles with unsourced statements
- Articles with unsourced statements from December 2014
Articles with unsourced statements from December 2014