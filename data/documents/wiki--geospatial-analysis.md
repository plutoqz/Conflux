<!-- source: https://en.wikipedia.org/wiki/Geospatial_analysis -->
# Spatial analysis

> Source: https://en.wikipedia.org/wiki/Geospatial_analysis
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
(Redirected from
Geospatial analysis
)
Techniques to study geometric data
Map by Dr.
John Snow
of
London
, showing
clusters
of cholera cases in the
1854 Broad Street cholera outbreak
. This was one of the first uses of map-based spatial analysis.
Spatial analysisis any of the formal techniques which study entities using theirtopological,geometric, orgeographicproperties, primarily used inurban design. Spatial analysis includes a variety of techniques using different analytic approaches, especiallyspatial statistics. It may be applied in fields as diverse asastronomy, with its studies of the placement of galaxies in thecosmos, or to chip fabrication engineering, with its use of "place and route"algorithmsto build complex wiring structures. In a more restricted sense, spatial analysis isgeospatial analysis, the technique applied to structures at the human scale, most notably in the analysis ofgeographic data. It may also applied to genomics, as intranscriptomics data, but is primarily for spatial data.

Spatial analysis
is any of the formal techniques which study entities using their
topological
,
geometric
, or
geographic
properties, primarily used in
urban design
. Spatial analysis includes a variety of techniques using different analytic approaches, especially
spatial statistics
. It may be applied in fields as diverse as
astronomy
, with its studies of the placement of galaxies in the
cosmos
, or to chip fabrication engineering, with its use of "place and route"
algorithms
to build complex wiring structures. In a more restricted sense, spatial analysis is
geospatial analysis
, the technique applied to structures at the human scale, most notably in the analysis of
geographic data
. It may also applied to genomics, as in
transcriptomics data
, but is primarily for spatial data.
Complex issues arise in spatial analysis, many of which are neither clearly defined nor completely resolved, but form the basis for current research. The most fundamental of these is the problem of defining the spatial location of the entities being studied. Classification of the techniques of spatial analysis is difficult because of the large number of different fields of research involved, the different fundamental approaches which can be chosen, and the many forms the data can take.

Complex issues arise in spatial analysis, many of which are neither clearly defined nor completely resolved, but form the basis for current research. The most fundamental of these is the problem of defining the spatial location of the entities being studied. Classification of the techniques of spatial analysis is difficult because of the large number of different fields of research involved, the different fundamental approaches which can be chosen, and the many forms the data can take.

## History

History
[
edit
]
Spatial analysis began with early attempts atcartographyandsurveying. Land surveying goes back to at least 1,400 B.C in Egypt: the dimensions of taxable land plots were measured with measuring ropes and plumb bobs.[1]Many fields have contributed to its rise in modern form.Biologycontributed throughbotanicalstudies of global plant distributions and local plant locations,ethologicalstudies of animal movement,landscape ecologicalstudies of vegetation blocks,ecologicalstudies of spatial population dynamics, and the study ofbiogeography.Epidemiologycontributed with early work on disease mapping, notablyJohn Snow's work of mapping an outbreak of cholera, with research on mapping the spread of disease and with location studies for health care delivery.Statisticshas contributed greatly through work in spatial statistics.Economicshas contributed notably throughspatial econometrics.Geographic information systemis currently a major contributor due to the importance of geographic software in the modern analytic toolbox.Remote sensinghas contributed extensively in morphometric and clustering analysis.Computer sciencehas contributed extensively through the study of algorithms, notably incomputational geometry.Mathematicscontinues to provide the fundamental tools for analysis and to reveal the complexity of the spatial realm, for example, with recent work onfractalsandscale invariance.Scientific modellingprovides a useful framework for new approaches.[citation needed]

Spatial analysis began with early attempts at
cartography
and
surveying
. Land surveying goes back to at least 1,400 B.C in Egypt: the dimensions of taxable land plots were measured with measuring ropes and plumb bobs.
[
1
]
Many fields have contributed to its rise in modern form.
Biology
contributed through
botanical
studies of global plant distributions and local plant locations,
ethological
studies of animal movement,
landscape ecological
studies of vegetation blocks,
ecological
studies of spatial population dynamics, and the study of
biogeography
.
Epidemiology
contributed with early work on disease mapping, notably
John Snow
's work of mapping an outbreak of cholera, with research on mapping the spread of disease and with location studies for health care delivery.
Statistics
has contributed greatly through work in spatial statistics.
Economics
has contributed notably through
spatial econometrics
.
Geographic information system
is currently a major contributor due to the importance of geographic software in the modern analytic toolbox.
Remote sensing
has contributed extensively in morphometric and clustering analysis.
Computer science
has contributed extensively through the study of algorithms, notably in
computational geometry
.
Mathematics
continues to provide the fundamental tools for analysis and to reveal the complexity of the spatial realm, for example, with recent work on
fractals
and
scale invariance
.
Scientific modelling
provides a useful framework for new approaches.
[
citation needed
]

## Fundamental issues

Fundamental issues
[
edit
]
Spatial analysis confronts many fundamental issues in the definition of its objects of study, in the construction of the analytic operations to be used, in the use of computers for analysis, in the limitations and particularities of the analyses which are known, and in the presentation of analytic results. Many of these issues are active subjects of modern research.[citation needed]

Spatial analysis confronts many fundamental issues in the definition of its objects of study, in the construction of the analytic operations to be used, in the use of computers for analysis, in the limitations and particularities of the analyses which are known, and in the presentation of analytic results. Many of these issues are active subjects of modern research.
[
citation needed
]
Common errors often arise in spatial analysis, some due to the mathematics of space, some due to the particular ways data are presented spatially, some due to the tools which are available. Census data, because it protects individual privacy by aggregating data into local units, raises a number of statistical issues. The fractal nature of coastline makes precise measurements of its length difficult if not impossible. A computer software fitting straight lines to the curve of a coastline, can easily calculate the lengths of the lines which it defines. However these straight lines may have no inherent meaning in the real world, as was shown for thecoastline of Britain.[citation needed]

Common errors often arise in spatial analysis, some due to the mathematics of space, some due to the particular ways data are presented spatially, some due to the tools which are available. Census data, because it protects individual privacy by aggregating data into local units, raises a number of statistical issues. The fractal nature of coastline makes precise measurements of its length difficult if not impossible. A computer software fitting straight lines to the curve of a coastline, can easily calculate the lengths of the lines which it defines. However these straight lines may have no inherent meaning in the real world, as was shown for the
coastline of Britain
.
[
citation needed
]
These problems represent a challenge in spatial analysis because of the power of maps as media of presentation. When results are presented as maps, the presentation combines spatial data which are generally accurate with analytic results which may be inaccurate, leading to an impression that analytic results are more accurate than the data would indicate.[2]

These problems represent a challenge in spatial analysis because of the power of maps as media of presentation. When results are presented as maps, the presentation combines spatial data which are generally accurate with analytic results which may be inaccurate, leading to an impression that analytic results are more accurate than the data would indicate.
[
2
]

### Formal Problems

Formal Problems
[
edit
]

#### Boundary problem

Boundary problem
[
edit
]
This section is an excerpt from
Boundary problem (spatial analysis)
.
[
edit
]
Aboundary problemin analysis is a phenomenon in which geographical patterns are differentiated by the shape and arrangement of boundaries that are drawn for administrative or measurement purposes. The boundary problem occurs because of the loss of neighbors in analyses that depend on the values of the neighbors. While geographic phenomena are measured and analyzed within a specific unit, identical spatial data can appear either dispersed or clustered depending on the boundary placed around the data. In analysis with point data, dispersion is evaluated as dependent of the boundary. In analysis with areal data, statistics should be interpreted based upon the boundary.

A
boundary problem
in analysis is a phenomenon in which geographical patterns are differentiated by the shape and arrangement of boundaries that are drawn for administrative or measurement purposes. The boundary problem occurs because of the loss of neighbors in analyses that depend on the values of the neighbors. While geographic phenomena are measured and analyzed within a specific unit, identical spatial data can appear either dispersed or clustered depending on the boundary placed around the data. In analysis with point data, dispersion is evaluated as dependent of the boundary. In analysis with areal data, statistics should be interpreted based upon the boundary.

#### Modifiable areal unit problem

Modifiable areal unit problem
[
edit
]
This section is an excerpt from
Modifiable areal unit problem
.
[
edit
]
An example of the modifiable areal unit problem and the distortion of rate calculations.
Themodifiable areal unit problem(MAUP) is a source ofstatistical biasthat can significantly impact the results ofstatistical hypothesis tests. The MAUP affects results when point-based measures of spatial phenomena areaggregatedinto spatial partitions orareal units(such asregionsordistricts) as in, for example,population densityorillness rates.[3][4]The resulting summary values (e.g., totals, rates, proportions, densities) are influenced by both the shape andscaleof the aggregation unit.[5]

The
modifiable areal unit problem
(MAUP) is a source of
statistical bias
that can significantly impact the results of
statistical hypothesis tests
. The MAUP affects results when point-based measures of spatial phenomena are
aggregated
into spatial partitions or
areal units
(such as
regions
or
districts
) as in, for example,
population density
or
illness rates
.
[
3
]
[
4
]
The resulting summary values (e.g., totals, rates, proportions, densities) are influenced by both the shape and
scale
of the aggregation unit.
[
5
]
For example, census data may be aggregated into county districts, census tracts, postcode areas, police precincts, or any other arbitrary spatial partition. Thus, the results of data aggregation are dependent on the mapmaker's choice of which "modifiable areal unit" to use in their analysis. A censuschoropleth mapcalculating population density using state boundaries will yield radically different results from a map that calculates density based on county boundaries. Furthermore, census district boundaries are also subject to change over time,[6]meaning the MAUP must be considered when comparing past to current data.

For example, census data may be aggregated into county districts, census tracts, postcode areas, police precincts, or any other arbitrary spatial partition. Thus, the results of data aggregation are dependent on the mapmaker's choice of which "modifiable areal unit" to use in their analysis. A census
choropleth map
calculating population density using state boundaries will yield radically different results from a map that calculates density based on county boundaries. Furthermore, census district boundaries are also subject to change over time,
[
6
]
meaning the MAUP must be considered when comparing past to current data.

#### Modifiable temporal unit problem

Modifiable temporal unit problem
[
edit
]
This section is an excerpt from
Modifiable temporal unit problem
.
[
edit
]
Flowchart illustrating selected units of time. The graphic also shows the three celestial objects that are related to the units of time.
TheModified Temporal Unit Problem(MTUP) is a source ofstatistical biasthat occurs in time series and spatial analysis when using temporal data that has beenaggregatedintotemporal units.[7][8]In such cases, choosing a temporal unit (e.g., days, months, years) can affect the analysis results and lead to inconsistencies or errors instatistical hypothesis testing.[9]

The
Modified Temporal Unit Problem
(MTUP) is a source of
statistical bias
that occurs in time series and spatial analysis when using temporal data that has been
aggregated
into
temporal units
.
[
7
]
[
8
]
In such cases, choosing a temporal unit (e.g., days, months, years) can affect the analysis results and lead to inconsistencies or errors in
statistical hypothesis testing
.
[
9
]

#### Neighborhood effect averaging problem

Neighborhood effect averaging problem
[
edit
]
This section is an excerpt from
Neighborhood effect averaging problem
.
[
edit
]

<!-- table omitted -->

This article
may incorporate text from a
large language model
, which is
prohibited in Wikipedia articles
.
It may include
hallucinated
information,
copyright violations
, claims not
verified
in cited sources,
original research
, or
fictitious references
. Any such material should be
removed
. The reason given is:
since initial 2023 version; note
WP:AISIGNS
in superficial analyses, vocab distribution typical of 2023 LLMs, etc. (Headers may be non-AI)
(
January 2026
)
(
Learn how and when to remove this message
)
Theneighborhood effect averaging problem(NEAP) is a source of statistical bias that can significantly impact the results of statistical hypothesis tests. It is caused by the influence of aggregating neighborhood-level phenomena on individuals whenmobility-dependent exposures influence the phenomena.[10][11][12]The problem confounds theneighbourhood effect, which suggests that a person's neighborhood impacts their individual characteristics, such as health.[13][14]It relates to theboundary problem, in that delineated neighborhoods used for analysis may not fully account for an individual's activity space if the borders are permeable, and individual mobility crosses the boundaries. The term was first coined byMei-Po Kwanin 2018.[10][11]

The
neighborhood effect averaging problem
(NEAP) is a source of statistical bias that can significantly impact the results of statistical hypothesis tests. It is caused by the influence of aggregating neighborhood-level phenomena on individuals when
mobility
-dependent exposures influence the phenomena.
[
10
]
[
11
]
[
12
]
The problem confounds the
neighbourhood effect
, which suggests that a person's neighborhood impacts their individual characteristics, such as health.
[
13
]
[
14
]
It relates to the
boundary problem
, in that delineated neighborhoods used for analysis may not fully account for an individual's activity space if the borders are permeable, and individual mobility crosses the boundaries. The term was first coined by
Mei-Po Kwan
in 2018.
[
10
]
[
11
]

#### Travelling salesman problem

Travelling salesman problem
[
edit
]
This section is an excerpt from
Travelling salesman problem
.
[
edit
]
The travelling salesman problem seeks to find the shortest possible loop that connects every red dot.
Solution of the above problem
In thetheory of computational complexity, thetravelling salesman problem(TSP) asks the following question: "Given a list of cities and the distances between each pair of cities, what is the shortest possible route that visits each city exactly once and returns to the origin city?" It is anNP-hardproblem incombinatorial optimization, important intheoretical computer scienceandoperations research.

In the
theory of computational complexity
, the
travelling salesman problem
(TSP) asks the following question: "Given a list of cities and the distances between each pair of cities, what is the shortest possible route that visits each city exactly once and returns to the origin city?" It is an
NP-hard
problem in
combinatorial optimization
, important in
theoretical computer science
and
operations research
.
Thetravelling purchaser problem, thevehicle routing problemand thering star problem[15]are three generalizations of TSP.

The
travelling purchaser problem
, the
vehicle routing problem
and the
ring star problem
[
15
]
are three generalizations of TSP.
The decision version of the TSP (where given a lengthL, the task is to decide whether the graph has a tour whose length is at mostL) belongs to the class ofNP-completeproblems. Thus, it is possible that theworst-caserunning timefor any algorithm for the TSP increasessuperpolynomially(but no more thanexponentially) with the number of cities.

The decision version of the TSP (where given a length
L
, the task is to decide whether the graph has a tour whose length is at most
L
) belongs to the class of
NP-complete
problems. Thus, it is possible that the
worst-case
running time
for any algorithm for the TSP increases
superpolynomially
(but no more than
exponentially
) with the number of cities.
The problem was first formulated in 1930 and is one of the most intensively studied problems in optimization. It is used as abenchmarkfor many optimization methods. Even though the problem is computationally difficult, manyheuristicsandexact algorithmsare known, so that some instances with tens of thousands of cities can be solved completely, and even problems with millions of cities can be approximated within a small fraction of 1%.[16]

The problem was first formulated in 1930 and is one of the most intensively studied problems in optimization. It is used as a
benchmark
for many optimization methods. Even though the problem is computationally difficult, many
heuristics
and
exact algorithms
are known, so that some instances with tens of thousands of cities can be solved completely, and even problems with millions of cities can be approximated within a small fraction of 1%.
[
16
]

#### Uncertain geographic context problem

Uncertain geographic context problem
[
edit
]
This section is an excerpt from
Uncertain geographic context problem
.
[
edit
]
Ingeography,public health, and other fields that study spatial relationships, theuncertain geographic context problem(UGCoP) is a methodological problem in which the geographic areas used in research to represent people's environments—such asneighborhoods,census tracts,administrative areas, oractivity spaces—may differ from the places and periods that actually shape the phenomena being studied, potentially leading to misleading conclusions.[17]

In
geography
,
public health
, and other fields that study spatial relationships, the
uncertain geographic context problem
(UGCoP) is a methodological problem in which the geographic areas used in research to represent people's environments—such as
neighborhoods
,
census tracts
,
administrative areas
, or
activity spaces
—may differ from the places and periods that actually shape the phenomena being studied, potentially leading to misleading conclusions.
[
17
]
For example, a study that measures the effect of a person's residential neighborhood on health outcomes may overlook environmental influences encountered while working, traveling, or engaging in activities elsewhere.[18]The term was coined by geographerMei-Po Kwanin 2012.[19][20]

For example, a study that measures the effect of a person's residential neighborhood on health outcomes may overlook environmental influences encountered while working, traveling, or engaging in activities elsewhere.
[
18
]
The term was coined by geographer
Mei-Po Kwan
in 2012.
[
19
]
[
20
]

#### Weber problem

Weber problem
[
edit
]
This section is an excerpt from
Weber problem
.
[
edit
]
Ingeometry, theWeber problem, named afterAlfred Weber, is one of the most famous problems inlocation theory. It requires finding a point in the plane that minimizes the sum of the transportation costs from this point tondestination points, where different destination points are associated with different costs per unit distance.

In
geometry
, the
Weber problem
, named after
Alfred Weber
, is one of the most famous problems in
location theory
. It requires finding a point in the plane that minimizes the sum of the transportation costs from this point to
n
destination points, where different destination points are associated with different costs per unit distance.
The Weber problem generalizes thegeometric median, which assumes transportation costs per unit distance are the same for all destination points, and the problem of computing theFermat point, the geometric median of three points. For this reason it is sometimes called the Fermat–Weber problem, although the same name has also been used for the unweighted geometric median problem. The Weber problem is in turn generalized by theattraction–repulsion problem, which allows some of the costs to be negative, so that greater distance from some points is better.

The Weber problem generalizes the
geometric median
, which assumes transportation costs per unit distance are the same for all destination points, and the problem of computing the
Fermat point
, the geometric median of three points. For this reason it is sometimes called the Fermat–Weber problem, although the same name has also been used for the unweighted geometric median problem. The Weber problem is in turn generalized by the
attraction–repulsion problem
, which allows some of the costs to be negative, so that greater distance from some points is better.

### Spatial characterization

Spatial characterization
[
edit
]
Spread of bubonic plague in medieval Europe.
[
citation needed
]
The colors indicate the spatial distribution of plague outbreaks over time.
The definition of the spatial presence of an entity constrains the possible analysis which can be applied to that entity and influences the final conclusions that can be reached. While this property is fundamentally true of allanalysis, it is particularly important in spatial analysis because the tools to define and study entities favor specific characterizations of the entities being studied. Statistical techniques favor the spatial definition of objects as points because there are very few statistical techniques which operate directly on line, area, or volume elements. Computer tools favor the spatial definition of objects as homogeneous and separate elements because of the limited number ofdatabaseelements and computational structures available, and the ease with which these primitive structures can be created.[citation needed]

The definition of the spatial presence of an entity constrains the possible analysis which can be applied to that entity and influences the final conclusions that can be reached. While this property is fundamentally true of all
analysis
, it is particularly important in spatial analysis because the tools to define and study entities favor specific characterizations of the entities being studied. Statistical techniques favor the spatial definition of objects as points because there are very few statistical techniques which operate directly on line, area, or volume elements. Computer tools favor the spatial definition of objects as homogeneous and separate elements because of the limited number of
database
elements and computational structures available, and the ease with which these primitive structures can be created.
[
citation needed
]

### Spatial dependence

Spatial dependence
[
edit
]
Spatial dependenceis the spatial relationship of variable values (for themes defined over space, such asrainfall) or locations (for themes defined as objects, such as cities). Spatial dependence is measured as the existence ofstatistical dependencein a collection ofrandom variables, each of which is associated with a differentgeographical location. Spatial dependence is of importance in applications where it is reasonable to postulate the existence of corresponding set of random variables at locations that have not been included in a sample. Thusrainfallmay be measured at a set of rain gauge locations, and such measurements can be considered as outcomes of random variables, but rainfall clearly occurs at other locations and would again be random. Becauserainfallexhibits properties ofautocorrelation, spatial interpolation techniques can be used to estimaterainfallamounts at locations near measured locations.[21]

Spatial dependence
is the spatial relationship of variable values (for themes defined over space, such as
rainfall
) or locations (for themes defined as objects, such as cities). Spatial dependence is measured as the existence of
statistical dependence
in a collection of
random variables
, each of which is associated with a different
geographical location
. Spatial dependence is of importance in applications where it is reasonable to postulate the existence of corresponding set of random variables at locations that have not been included in a sample. Thus
rainfall
may be measured at a set of rain gauge locations, and such measurements can be considered as outcomes of random variables, but rainfall clearly occurs at other locations and would again be random. Because
rainfall
exhibits properties of
autocorrelation
, spatial interpolation techniques can be used to estimate
rainfall
amounts at locations near measured locations.
[
21
]
As with other types of statistical dependence, the presence of spatial dependence generally leads to estimates of an average value from a sample being less accurate than had the samples been independent, although if negative dependence exists a sample average can be better than in the independent case.  A different problem than that of estimating an overall average is that ofspatial interpolation: here the problem is to estimate the unobserved random outcomes of variables at locations intermediate to places where measurements are made, on that there is spatial dependence between the observed and unobserved random variables.[citation needed]

As with other types of statistical dependence, the presence of spatial dependence generally leads to estimates of an average value from a sample being less accurate than had the samples been independent, although if negative dependence exists a sample average can be better than in the independent case.  A different problem than that of estimating an overall average is that of
spatial interpolation
: here the problem is to estimate the unobserved random outcomes of variables at locations intermediate to places where measurements are made, on that there is spatial dependence between the observed and unobserved random variables.
[
citation needed
]
Tools for exploring spatial dependence include:spatial correlation,spatial covariance functionsandsemivariograms.
Methods for spatial interpolation includeKriging, which is a type ofbest linear unbiased prediction.
The topic of spatial dependence is of importance togeostatisticsand spatial analysis.[citation needed]

Tools for exploring spatial dependence include:
spatial correlation
,
spatial covariance functions
and
semivariograms
.
Methods for spatial interpolation include
Kriging
, which is a type of
best linear unbiased prediction
.
The topic of spatial dependence is of importance to
geostatistics
and spatial analysis.
[
citation needed
]

#### Spatial auto-correlation

Spatial auto-correlation
[
edit
]
Spatial Autocorrelation Report generated by ArcGIS Pro for 2022 U.S. county population.
Spatial dependency is the co-variation of properties within geographic space: characteristics at proximal locations appear to be correlated, either positively or negatively.[22]Spatial dependency leads to thespatialautocorrelationproblem in statistics since, like temporal autocorrelation, this violates standard statistical techniques that assume independence among observations. For example,regressionanalyses that do not compensate for spatial dependency can have unstable parameter estimates and yield unreliable significance tests. Spatial regression models (see below) capture these relationships and do not suffer from these weaknesses. It is also appropriate to view spatial dependency as a source of information rather than something to be corrected.[23]

Spatial dependency is the co-variation of properties within geographic space: characteristics at proximal locations appear to be correlated, either positively or negatively.
[
22
]
Spatial dependency leads to the
spatial
autocorrelation
problem in statistics since, like temporal autocorrelation, this violates standard statistical techniques that assume independence among observations. For example,
regression
analyses that do not compensate for spatial dependency can have unstable parameter estimates and yield unreliable significance tests. Spatial regression models (see below) capture these relationships and do not suffer from these weaknesses. It is also appropriate to view spatial dependency as a source of information rather than something to be corrected.
[
23
]
Locational effects also manifest as spatialheterogeneity, or the apparent variation in a process with respect to location in geographic space. Unless a space is uniform and boundless, every location will have some degree of uniqueness relative to the other locations. This affects the spatial dependency relations and therefore the spatial process. Spatial heterogeneity means that overall parameters estimated for the entire system may not adequately describe the process at any given location.[citation needed]

Locational effects also manifest as spatial
heterogeneity
, or the apparent variation in a process with respect to location in geographic space. Unless a space is uniform and boundless, every location will have some degree of uniqueness relative to the other locations. This affects the spatial dependency relations and therefore the spatial process. Spatial heterogeneity means that overall parameters estimated for the entire system may not adequately describe the process at any given location.
[
citation needed
]

### Spatial association

Spatial association
[
edit
]
Further information:
Indicators of spatial association
Spatial associationis the degree to which things are similarly arranged in space. Analysis of the distribution patterns of two phenomena is done by map overlay. If the distributions are similar, then the spatial association is strong, and vice versa.[24]In aGeographic Information System, the analysis can be done quantitatively. For example, a set of observations (as points or extracted from raster cells) at matching locations can be intersected and examined byregression analysis.

Spatial association
is the degree to which things are similarly arranged in space. Analysis of the distribution patterns of two phenomena is done by map overlay. If the distributions are similar, then the spatial association is strong, and vice versa.
[
24
]
In a
Geographic Information System
, the analysis can be done quantitatively. For example, a set of observations (as points or extracted from raster cells) at matching locations can be intersected and examined by
regression analysis
.
Likespatial autocorrelation, this can be a useful tool for spatial prediction. In spatial modeling, the concept of spatial association allows the use of covariates in a regression equation to predict the geographic field and thus produce a map.

Like
spatial autocorrelation
, this can be a useful tool for spatial prediction. In spatial modeling, the concept of spatial association allows the use of covariates in a regression equation to predict the geographic field and thus produce a map.

#### The second dimension of spatial association

The second dimension of spatial association
[
edit
]
The second dimension of spatial association (SDA) reveals the association between spatial variables through extracting geographical information at locations outside samples. SDA effectively uses the missing geographical information outside sample locations in methods of the first dimension of spatial association (FDA), which explore spatial association using observations at sample locations.[25]In the field of public health surveillance, spatial analysis techniques have investigated topics such as the correlation between literacy rates and health insurance enrollment gaps.[26]

The second dimension of spatial association (SDA) reveals the association between spatial variables through extracting geographical information at locations outside samples. SDA effectively uses the missing geographical information outside sample locations in methods of the first dimension of spatial association (FDA), which explore spatial association using observations at sample locations.
[
25
]
In the field of public health surveillance, spatial analysis techniques have investigated topics such as the correlation between literacy rates and health insurance enrollment gaps.
[
26
]

### Scaling

Scaling
[
edit
]
Spatialmeasurementscale is a persistent issue in spatial analysis; more detail is available at themodifiable areal unit problem(MAUP) topic entry. Landscape ecologists developed a series ofscale invariantmetrics for aspects of ecology that arefractalin nature.[27]In more general terms, no scale independent method ofanalysisis widely agreed upon for spatial statistics.[citation needed]

Spatial
measurement
scale is a persistent issue in spatial analysis; more detail is available at the
modifiable areal unit problem
(MAUP) topic entry. Landscape ecologists developed a series of
scale invariant
metrics for aspects of ecology that are
fractal
in nature.
[
27
]
In more general terms, no scale independent method of
analysis
is widely agreed upon for spatial statistics.
[
citation needed
]

### Sampling

Sampling
[
edit
]
Spatialsamplinginvolves determining a limited number of locations in geographic space for faithfully measuring phenomena that are subject to dependency and heterogeneity.[citation needed]Dependency suggests that since one location can predict the value of another location, we do not need observations in both places. But heterogeneity suggests that this relation can change across space, and therefore we cannot trust an observed degree of dependency beyond a region that may be small.  Basic spatial sampling schemes include random, clustered and systematic. These basic schemes can be applied at multiple levels in a designated spatial hierarchy (e.g., urban area, city, neighborhood). It is also possible to exploit ancillary data, for example, using property values as a guide in a spatial sampling scheme to measure educational attainment and income.  Spatial models such as autocorrelation statistics, regression and interpolation (see below) can also dictate sample design.[citation needed]

Spatial
sampling
involves determining a limited number of locations in geographic space for faithfully measuring phenomena that are subject to dependency and heterogeneity.
[
citation needed
]
Dependency suggests that since one location can predict the value of another location, we do not need observations in both places. But heterogeneity suggests that this relation can change across space, and therefore we cannot trust an observed degree of dependency beyond a region that may be small.  Basic spatial sampling schemes include random, clustered and systematic. These basic schemes can be applied at multiple levels in a designated spatial hierarchy (e.g., urban area, city, neighborhood). It is also possible to exploit ancillary data, for example, using property values as a guide in a spatial sampling scheme to measure educational attainment and income.  Spatial models such as autocorrelation statistics, regression and interpolation (see below) can also dictate sample design.
[
citation needed
]

### Common errors in spatial analysis

Common errors in spatial analysis
[
edit
]
The fundamental issues in spatial analysis lead to numerous problems in analysis including bias, distortion and outright errors in the conclusions reached. These issues are often interlinked but various attempts have been made to separate out particular issues from each other.[28]

The fundamental issues in spatial analysis lead to numerous problems in analysis including bias, distortion and outright errors in the conclusions reached. These issues are often interlinked but various attempts have been made to separate out particular issues from each other.
[
28
]

#### Length

Length
[
edit
]
In discussing thecoastline of Britain,Benoit Mandelbrotshowed that certain spatial concepts are inherently nonsensical despite presumption of their validity. Lengths in ecology depend directly on the scale at which they are measured and experienced. So while surveyors commonly measure the length of a river, this length only has meaning in the context of the relevance of the measuring technique to the question under study.[29]

In discussing the
coastline of Britain
,
Benoit Mandelbrot
showed that certain spatial concepts are inherently nonsensical despite presumption of their validity. Lengths in ecology depend directly on the scale at which they are measured and experienced. So while surveyors commonly measure the length of a river, this length only has meaning in the context of the relevance of the measuring technique to the question under study.
[
29
]
- Britain measured using a 200 km linear measurement
Britain measured using a 200 km linear measurement
- Britain measured using a 100 km linear measurement
Britain measured using a 100 km linear measurement
- Britain measured using a 50 km linear measurement
Britain measured using a 50 km linear measurement

#### Locational fallacy

Locational fallacy
[
edit
]
The locational fallacy refers to error due to the particular spatial characterization chosen for the elements of study, in particular choice of placement for the spatial presence of the element.[29]

The locational fallacy refers to error due to the particular spatial characterization chosen for the elements of study, in particular choice of placement for the spatial presence of the element.
[
29
]
Spatial characterizations may be simplistic or even wrong. Studies of humans often reduce the spatial existence of humans to a single point, for instance their home address. This can easily lead to poor analysis, for example, when considering disease transmission which can happen at work or at school and therefore far from the home.[29]

Spatial characterizations may be simplistic or even wrong. Studies of humans often reduce the spatial existence of humans to a single point, for instance their home address. This can easily lead to poor analysis, for example, when considering disease transmission which can happen at work or at school and therefore far from the home.
[
29
]
The spatial characterization may implicitly limit the subject of study. For example, the spatial analysis of crime data has recently become popular but these studies can only describe the particular kinds of crime which can be described spatially. This leads to many maps of assault but not to any maps of embezzlement with political consequences in the conceptualization of crime and the design of policies to address the issue.[29]

The spatial characterization may implicitly limit the subject of study. For example, the spatial analysis of crime data has recently become popular but these studies can only describe the particular kinds of crime which can be described spatially. This leads to many maps of assault but not to any maps of embezzlement with political consequences in the conceptualization of crime and the design of policies to address the issue.
[
29
]

#### Atomic fallacy

Atomic fallacy
[
edit
]
This describes errors due to treating elements as separate 'atoms' outside of their spatial context.[29]The fallacy is about transferring individual conclusions to spatial units.[30]

This describes errors due to treating elements as separate 'atoms' outside of their spatial context.
[
29
]
The fallacy is about transferring individual conclusions to spatial units.
[
30
]

#### Ecological fallacy

Ecological fallacy
[
edit
]
Theecological fallacydescribes errors due to performing analyses on aggregate data when trying to reach conclusions on the individual units.[29][31]Errors occur in part from spatial aggregation.  For example, apixelrepresents the average surface temperatures within an area.  Ecological fallacy would be to assume that all points within the area have the same temperature.

The
ecological fallacy
describes errors due to performing analyses on aggregate data when trying to reach conclusions on the individual units.
[
29
]
[
31
]
Errors occur in part from spatial aggregation.  For example, a
pixel
represents the average surface temperatures within an area.  Ecological fallacy would be to assume that all points within the area have the same temperature.

### Solutions to the fundamental issues

Solutions to the fundamental issues
[
edit
]

#### Geographic space

Geographic space
[
edit
]
Manhattan distance versus Euclidean distance: The red, blue, and yellow lines have the same length (12) in both Euclidean and taxicab geometry. In Euclidean geometry, the green line has length 6×
√
2
≈ 8.48, and is the unique shortest path. In taxicab geometry, the green line's length is still 12, making it no shorter than any other path shown.
A mathematical space exists whenever we have a set of observations and quantitative measures of their attributes. For example, we can represent individuals' incomes or years of education within a coordinate system where the location of each individual can be specified with respect to both dimensions. The distance between individuals within this space is a quantitative measure of their differences with respect to income and education. However, in spatial analysis, we are concerned with specific types of mathematical spaces, namely, geographic space. In geographic space, the observations correspond to locations in a spatial measurement framework that capture their proximity in the real world. The locations in a spatial measurement framework often represent locations on the surface of the Earth, but this is not strictly necessary. A spatial measurement framework can also capture proximity with respect to, say, interstellar space or within a biological entity such as a liver. The fundamental tenet isTobler's First Law of Geography: if the interrelation between entities increases with proximity in the real world, then representation in geographic space and assessment using spatial analysis techniques are appropriate.

A mathematical space exists whenever we have a set of observations and quantitative measures of their attributes. For example, we can represent individuals' incomes or years of education within a coordinate system where the location of each individual can be specified with respect to both dimensions. The distance between individuals within this space is a quantitative measure of their differences with respect to income and education. However, in spatial analysis, we are concerned with specific types of mathematical spaces, namely, geographic space. In geographic space, the observations correspond to locations in a spatial measurement framework that capture their proximity in the real world. The locations in a spatial measurement framework often represent locations on the surface of the Earth, but this is not strictly necessary. A spatial measurement framework can also capture proximity with respect to, say, interstellar space or within a biological entity such as a liver. The fundamental tenet is
Tobler's First Law of Geography
: if the interrelation between entities increases with proximity in the real world, then representation in geographic space and assessment using spatial analysis techniques are appropriate.
TheEuclidean distancebetween locations often represents their proximity, although this is only one possibility. There are an infinite number of distances in addition to Euclidean that can support quantitative analysis. For example, "Manhattan" (or "Taxicab") distances where movement is restricted to paths parallel to the axes can be more meaningful than Euclidean distances in urban settings. In addition to distances, other geographic relationships such as connectivity(e.g., the existence or degree of shared borders) and directioncan also influence the relationships among entities. It is also possible to compute minimal cost paths across a cost surface; for example, this can represent proximity among locations when travel must occur across rugged terrain.

The
Euclidean distance
between locations often represents their proximity, although this is only one possibility. There are an infinite number of distances in addition to Euclidean that can support quantitative analysis. For example, "Manhattan" (or "
Taxicab
") distances where movement is restricted to paths parallel to the axes can be more meaningful than Euclidean distances in urban settings. In addition to distances, other geographic relationships such as connectivity
(e.g., the existence or degree of shared borders) and direction
can also influence the relationships among entities. It is also possible to compute minimal cost paths across a cost surface; for example, this can represent proximity among locations when travel must occur across rugged terrain.

## Types

Types
[
edit
]
Spatial data comes in many varieties and it is not easy to
 arrive at a system of classification that is simultaneously
 exclusive, exhaustive, imaginative, and satisfying.
                             -- G. Upton & B. Fingelton[32]

Spatial data comes in many varieties and it is not easy to
 arrive at a system of classification that is simultaneously
 exclusive, exhaustive, imaginative, and satisfying.
                             -- G. Upton & B. Fingelton
[
32
]

### Spatial data analysis

Spatial data analysis
[
edit
]
Urban and Regional Studies deal with large tables of spatial data obtained from censuses and surveys. It is necessary to simplify the huge amount of detailed information in order to extract the main trends. Multivariable analysis (orFactor analysis, FA) allows a change of variables, transforming the many variables of the census, usually correlated between themselves, into fewer independent "Factors" or "Principal Components" which are, actually, theeigenvectorsof the data correlation matrix weighted by the inverse of their eigenvalues. This change of variables has two main advantages:

Urban and Regional Studies deal with large tables of spatial data obtained from censuses and surveys. It is necessary to simplify the huge amount of detailed information in order to extract the main trends. Multivariable analysis (or
Factor analysis
, FA) allows a change of variables, transforming the many variables of the census, usually correlated between themselves, into fewer independent "Factors" or "Principal Components" which are, actually, the
eigenvectors
of the data correlation matrix weighted by the inverse of their eigenvalues. This change of variables has two main advantages:
- Since information is concentrated on the first new factors, it is possible to keep only a few of them while losing only a small amount of information; mapping them produces fewer and more significant maps
Since information is concentrated on the first new factors, it is possible to keep only a few of them while losing only a small amount of information; mapping them produces fewer and more significant maps
- The factors, actually the eigenvectors, are orthogonal by construction, i.e. not correlated. In most cases, the dominant factor (with the largest eigenvalue) is the Social Component, separating rich and poor in the city. Since factors are not-correlated, other smaller processes than social status, which would have remained hidden otherwise, appear on the second, third, ... factors.
The factors, actually the eigenvectors, are orthogonal by construction, i.e. not correlated. In most cases, the dominant factor (with the largest eigenvalue) is the Social Component, separating rich and poor in the city. Since factors are not-correlated, other smaller processes than social status, which would have remained hidden otherwise, appear on the second, third, ... factors.
Factor analysis depends on measuring distances between observations : the choice of a significant metric is crucial. The Euclidean metric (Principal Component Analysis), the Chi-Square distance (Correspondence Analysis) or the Generalized Mahalanobis distance (Discriminant Analysis) are among the more widely used.[33]More complicated models, using communalities or rotations have been proposed.[34]

Factor analysis depends on measuring distances between observations : the choice of a significant metric is crucial. The Euclidean metric (Principal Component Analysis), the Chi-Square distance (Correspondence Analysis) or the Generalized Mahalanobis distance (Discriminant Analysis) are among the more widely used.
[
33
]
More complicated models, using communalities or rotations have been proposed.
[
34
]
Using multivariate methods in spatial analysis began really in the 1950s (although some examples go back to the beginning of the century) and culminated in the 1970s, with the increasing power and accessibility of computers. Already in 1948, in a seminal publication, two sociologists,Wendell Belland Eshref Shevky,[35]had shown that most city populations in the US and in the world could be represented with three independent factors : 1- the « socio-economic status » opposing rich and poor districts and distributed in sectors running along highways from the city center, 2- the « life cycle », i.e. the age structure of households, distributed in concentric circles, and 3-  « race and ethnicity », identifying patches of migrants located within the city. In 1961, in a groundbreaking study, British geographers used FA to classify British towns.[36]Brian J Berry, at the University of Chicago, and his students made a wide use of the method,[37]applying it to most important cities in the world and exhibiting common social structures.[38]The use of Factor Analysis in Geography, made so easy by modern computers, has been very wide but not always very wise.[39]

Using multivariate methods in spatial analysis began really in the 1950s (although some examples go back to the beginning of the century) and culminated in the 1970s, with the increasing power and accessibility of computers. Already in 1948, in a seminal publication, two sociologists,
Wendell Bell
and Eshref Shevky,
[
35
]
had shown that most city populations in the US and in the world could be represented with three independent factors : 1- the « socio-economic status » opposing rich and poor districts and distributed in sectors running along highways from the city center, 2- the « life cycle », i.e. the age structure of households, distributed in concentric circles, and 3-  « race and ethnicity », identifying patches of migrants located within the city. In 1961, in a groundbreaking study, British geographers used FA to classify British towns.
[
36
]
Brian J Berry, at the University of Chicago, and his students made a wide use of the method,
[
37
]
applying it to most important cities in the world and exhibiting common social structures.
[
38
]
The use of Factor Analysis in Geography, made so easy by modern computers, has been very wide but not always very wise.
[
39
]
Since the vectors extracted are determined by the data matrix, it is not possible to compare factors obtained from different censuses. A solution consists in fusing together several census matrices in a unique table which, then, may be analyzed. This, however, assumes that the definition of the variables has not changed over time and produces very large tables, difficult to manage. A better solution, proposed by psychometricians,[40]groups the data in a « cubic matrix », with three entries (for instance, locations, variables, time periods). A Three-Way Factor Analysis produces then three groups of factors related by a small cubic « core matrix ».[41]This method, which exhibits data evolution over time, has not been widely used in geography.[42]In Los Angeles,[43]however, it has exhibited the role, traditionally ignored, of Downtown as an organizing center for the whole city during several decades.

Since the vectors extracted are determined by the data matrix, it is not possible to compare factors obtained from different censuses. A solution consists in fusing together several census matrices in a unique table which, then, may be analyzed. This, however, assumes that the definition of the variables has not changed over time and produces very large tables, difficult to manage. A better solution, proposed by psychometricians,
[
40
]
groups the data in a « cubic matrix », with three entries (for instance, locations, variables, time periods). A Three-Way Factor Analysis produces then three groups of factors related by a small cubic « core matrix ».
[
41
]
This method, which exhibits data evolution over time, has not been widely used in geography.
[
42
]
In Los Angeles,
[
43
]
however, it has exhibited the role, traditionally ignored, of Downtown as an organizing center for the whole city during several decades.

### Spatial autocorrelation

Spatial autocorrelation
[
edit
]
Further information:
Tobler's first law of geography
Clusters of the estimated percent of people in poverty by county in the contiguous United States in 2020 calculated using
Anselin's
Local
Moran's I
.
Spatialautocorrelationstatistics measure and analyze the degree of dependency among observations in a geographic space.  Classic spatial autocorrelation statistics includeMoran'sI{\displaystyle I},Geary'sC{\displaystyle C},Getis'sG{\displaystyle G}and thestandard deviational ellipse. These statistics require measuring aspatial weights matrixthat reflects the intensity of the geographic relationship between observations in a neighborhood, e.g., the distances between neighbors, the lengths of shared border, or whether they fall into a specified directional class such as "west". Classic spatial autocorrelation statistics compare the spatial weights to the covariance relationship at pairs of locations. Spatial autocorrelation that is more positive than expected from random indicate the clustering of similar values across geographic space, while significant negative spatial autocorrelation indicates that neighboring values are more dissimilar than expected by chance, suggesting a spatial pattern similar to a chess board.

Spatial
autocorrelation
statistics measure and analyze the degree of dependency among observations in a geographic space.  Classic spatial autocorrelation statistics include
Moran's
I
{\displaystyle I}
,
Geary's
C
{\displaystyle C}
,
Getis's
G
{\displaystyle G}
and the
standard deviational ellipse
. These statistics require measuring a
spatial weights matrix
that reflects the intensity of the geographic relationship between observations in a neighborhood, e.g., the distances between neighbors, the lengths of shared border, or whether they fall into a specified directional class such as "west". Classic spatial autocorrelation statistics compare the spatial weights to the covariance relationship at pairs of locations. Spatial autocorrelation that is more positive than expected from random indicate the clustering of similar values across geographic space, while significant negative spatial autocorrelation indicates that neighboring values are more dissimilar than expected by chance, suggesting a spatial pattern similar to a chess board.
Spatial autocorrelation statistics such as Moran'sI{\displaystyle I}and Geary'sC{\displaystyle C}are global in the sense that they estimate the overall degree of spatial autocorrelation for a dataset.  The possibility of spatial heterogeneity suggests that the estimated degree of autocorrelation may vary significantly across geographic space.Local spatial autocorrelation statisticsprovide estimates disaggregated to the level of the spatial analysis units, allowing assessment of the dependency relationships across space.G{\displaystyle G}statistics compare neighborhoods to a global average and identify local regions of strong autocorrelation.  Local versions of theI{\displaystyle I}andC{\displaystyle C}statistics are also available.

Spatial autocorrelation statistics such as Moran's
I
{\displaystyle I}
and Geary's
C
{\displaystyle C}
are global in the sense that they estimate the overall degree of spatial autocorrelation for a dataset.  The possibility of spatial heterogeneity suggests that the estimated degree of autocorrelation may vary significantly across geographic space.
Local spatial autocorrelation statistics
provide estimates disaggregated to the level of the spatial analysis units, allowing assessment of the dependency relationships across space.
G
{\displaystyle G}
statistics compare neighborhoods to a global average and identify local regions of strong autocorrelation.  Local versions of the
I
{\displaystyle I}
and
C
{\displaystyle C}
statistics are also available.

### Spatial heterogeneity

Spatial heterogeneity
[
edit
]
This section is an excerpt from
Spatial heterogeneity
.
[
edit
]
Land cover surrounding Madison, WI. Fields are colored yellow and brown, water is colored blue, and urban surfaces are colored red.
Spatial heterogeneityis a property generally ascribed to alandscapeor to apopulation. It refers to the uneven distribution of various concentrations of eachspecieswithin an area. A landscape with spatial heterogeneity has a mix of concentrations of multiple species of plants or animals (biological), or ofterrainformations (geological), or environmental characteristics (e.g. rainfall, temperature, wind) filling its area. A population showing spatial heterogeneity is one where various concentrations of individuals of this species are unevenly distributed across an area; nearly synonymous with "patchily distributed."

Spatial heterogeneity
is a property generally ascribed to a
landscape
or to a
population
. It refers to the uneven distribution of various concentrations of each
species
within an area. A landscape with spatial heterogeneity has a mix of concentrations of multiple species of plants or animals (biological), or of
terrain
formations (geological), or environmental characteristics (e.g. rainfall, temperature, wind) filling its area. A population showing spatial heterogeneity is one where various concentrations of individuals of this species are unevenly distributed across an area; nearly synonymous with "patchily distributed."

### Spatial interaction

Spatial interaction
[
edit
]
Spatial interaction or "gravity models" estimate the flow of people, material or information between locations in geographic space.  Factors can include origin propulsive variables such as the number of commuters in residential areas, destination attractiveness variables such as the amount of office space in employment areas, and proximity relationships between the locations measured in terms such as driving distance or travel time.  In addition, the topological, orconnective, relationships between areas must be identified, particularly considering the often conflicting relationship between distance and topology; for example, two spatially close neighborhoods may not display any significant interaction if they are separated by a highway. After specifying the functional forms of these relationships, the analyst can estimate model parameters using observed flow data and standard estimation techniques such as ordinary least squares or maximum likelihood. Competing destinations versions of spatial interaction models include the proximity among the destinations (or origins) in addition to the origin-destination proximity; this captures the effects of destination (origin) clustering on flows.

Spatial interaction or "
gravity models
" estimate the flow of people, material or information between locations in geographic space.  Factors can include origin propulsive variables such as the number of commuters in residential areas, destination attractiveness variables such as the amount of office space in employment areas, and proximity relationships between the locations measured in terms such as driving distance or travel time.  In addition, the topological, or
connective
, relationships between areas must be identified, particularly considering the often conflicting relationship between distance and topology; for example, two spatially close neighborhoods may not display any significant interaction if they are separated by a highway. After specifying the functional forms of these relationships, the analyst can estimate model parameters using observed flow data and standard estimation techniques such as ordinary least squares or maximum likelihood. Competing destinations versions of spatial interaction models include the proximity among the destinations (or origins) in addition to the origin-destination proximity; this captures the effects of destination (origin) clustering on flows.

### Spatial interpolation

Spatial interpolation
[
edit
]
Spatial interpolationmethods estimate the variables at unobserved locations in geographic space based on the values at observed locations.  Basic methods includeinverse distance weighting: this attenuates the variable with decreasing proximity from the observed location.Krigingis a more sophisticated method that interpolates across space according to a spatial lag relationship that has both systematic and random components.  This can accommodate a wide range of spatial relationships for the hidden values between observed locations.  Kriging provides optimal estimates given the hypothesized lag relationship, and error estimates can be mapped to determine if spatial patterns exist.

Spatial interpolation
methods estimate the variables at unobserved locations in geographic space based on the values at observed locations.  Basic methods include
inverse distance weighting
: this attenuates the variable with decreasing proximity from the observed location.
Kriging
is a more sophisticated method that interpolates across space according to a spatial lag relationship that has both systematic and random components.  This can accommodate a wide range of spatial relationships for the hidden values between observed locations.  Kriging provides optimal estimates given the hypothesized lag relationship, and error estimates can be mapped to determine if spatial patterns exist.

### Spatial regression

Spatial regression
[
edit
]
See also:
Local regression
and
Regression-Kriging
Spatial regression methods capture spatial dependency inregression analysis, avoiding statistical problems such as unstable parameters and unreliable significance tests, as well as providing information on spatial relationships among the variables involved. Depending on the specific technique, spatial dependency can enter the regression model as relationships between the independent variables and the dependent, between the dependent variables and a spatial lag of itself, or in the error terms.Geographically weighted regression(GWR) is a local version of spatial regression that generates parameters disaggregated by the spatial units of analysis.[44]This allows assessment of the spatial heterogeneity in the estimated relationships between the independent and dependent variables. The use ofBayesian hierarchical modeling[45]in conjunction withMarkov chain Monte Carlo(MCMC) methods have recently shown to be effective in modeling complex relationships using Poisson-Gamma-CAR, Poisson-lognormal-SAR, or Overdispersed logit models. Statistical packages for implementing such Bayesian models using MCMC includeWinBugs,CrimeStatand many packages available viaR programming language.[46]

Spatial regression methods capture spatial dependency in
regression analysis
, avoiding statistical problems such as unstable parameters and unreliable significance tests, as well as providing information on spatial relationships among the variables involved. Depending on the specific technique, spatial dependency can enter the regression model as relationships between the independent variables and the dependent, between the dependent variables and a spatial lag of itself, or in the error terms.
Geographically weighted regression
(GWR) is a local version of spatial regression that generates parameters disaggregated by the spatial units of analysis.
[
44
]
This allows assessment of the spatial heterogeneity in the estimated relationships between the independent and dependent variables. The use of
Bayesian hierarchical modeling
[
45
]
in conjunction with
Markov chain Monte Carlo
(MCMC) methods have recently shown to be effective in modeling complex relationships using Poisson-Gamma-CAR, Poisson-lognormal-SAR, or Overdispersed logit models. Statistical packages for implementing such Bayesian models using MCMC include
WinBugs
,
CrimeStat
and many packages available via
R programming language
.
[
46
]
Spatial stochastic processes, such asGaussian processesare also increasingly being deployed in spatial regression analysis. Model-based versions of GWR, known as spatially varying coefficient models have been applied to conduct Bayesian inference.[45]Spatial stochastic processes can become computationally effective using scalable Gaussian process models, such as Gaussian Predictive Processes[47]and Nearest Neighbor Gaussian Processes (NNGP).[48]

Spatial stochastic processes, such as
Gaussian processes
are also increasingly being deployed in spatial regression analysis. Model-based versions of GWR, known as spatially varying coefficient models have been applied to conduct Bayesian inference.
[
45
]
Spatial stochastic processes can become computationally effective using scalable Gaussian process models, such as Gaussian Predictive Processes
[
47
]
and Nearest Neighbor Gaussian Processes (NNGP).
[
48
]

### Spatial neural networks

Spatial neural networks
[
edit
]
This section is an excerpt from
Spatial neural network
.
[
edit
]
Spatial neural networks (SNNs) constitute a supercategory of tailored
neural networks (NNs)
for representing and predicting geographic phenomena. They generally improve both the statistical
accuracy
and
reliability
of the a-spatial/classic NNs whenever they handle
geo-spatial datasets
, and also of the other spatial
(statistical) models
(e.g. spatial regression models) whenever the geo-spatial
datasets
' variables depict
non-linear relations
.
[
49
]
[
50
]
[
51
]
Examples of SNNs are the OSFA spatial neural networks, SVANNs and GWNNs.

### Spatial volatility

Spatial volatility
[
edit
]
Spatial volatility models describe spatial or spatiotemporal dependence in the conditional variance of a process, extending the concept ofAutoregressive conditional heteroskedasticity(ARCH) from time series to spatial settings. Such models account for the fact that variability at one location may be related to variability at neighbouring locations, as defined by a spatial weights matrix. This is in keeping with one formulation ofArbia's law of geographywhich states that "everything is related to everything else, but things observed at a coarse spatial resolution are more related than things observed at a finer resolution."

Spatial volatility models describe spatial or spatiotemporal dependence in the conditional variance of a process, extending the concept of
Autoregressive conditional heteroskedasticity
(ARCH) from time series to spatial settings. Such models account for the fact that variability at one location may be related to variability at neighbouring locations, as defined by a spatial weights matrix. This is in keeping with one formulation of
Arbia's law of geography
which states that "everything is related to everything else, but things observed at a coarse spatial resolution are more related than things observed at a finer resolution."
A generalised spatial and spatiotemporal ARCH/GARCH framework was introduced by Otto, Schmid, and Garthoff (2018),[52]allowing the conditional variance at a location to depend on weighted past squared residuals from neighbouring locations and, in the spatiotemporal case, on its own past conditional variances. Sato and Matsuda (2017)[53]proposed a spatial log-ARCH model as an alternative formulation.

A generalised spatial and spatiotemporal ARCH/GARCH framework was introduced by Otto, Schmid, and Garthoff (2018),
[
52
]
allowing the conditional variance at a location to depend on weighted past squared residuals from neighbouring locations and, in the spatiotemporal case, on its own past conditional variances. Sato and Matsuda (2017)
[
53
]
proposed a spatial log-ARCH model as an alternative formulation.
Spatial volatility models find applications in disciplines where risk or uncertainty propagate over space, including regional economics, environmental risk assessment, and financial networks. A recent review summarises methodological developments, estimation strategies, and applications of spatial and spatiotemporal volatility models across disciplines.[54]

Spatial volatility models find applications in disciplines where risk or uncertainty propagate over space, including regional economics, environmental risk assessment, and financial networks. A recent review summarises methodological developments, estimation strategies, and applications of spatial and spatiotemporal volatility models across disciplines.
[
54
]

### Simulation and modeling

Simulation and modeling
[
edit
]
Spatial interaction models are aggregate and top-down: they specify an overall governing relationship for flow between locations.  This characteristic is also shared by urban models such as those based on mathematical programming, flows among economic sectors, or bid-rent theory.  An alternative modeling perspective is to represent the system at the highest possible level of disaggregation and study the bottom-up emergence of complex patterns and relationships from behavior and interactions at the individual level.[citation needed]

Spatial interaction models are aggregate and top-down: they specify an overall governing relationship for flow between locations.  This characteristic is also shared by urban models such as those based on mathematical programming, flows among economic sectors, or bid-rent theory.  An alternative modeling perspective is to represent the system at the highest possible level of disaggregation and study the bottom-up emergence of complex patterns and relationships from behavior and interactions at the individual level.
[
citation needed
]
Complex adaptive systemstheory as applied to spatial analysis suggests that simple interactions among proximal entities can lead to intricate, persistent and functional spatial entities at aggregate levels.  Two fundamentally spatial simulation methods are cellular automata and agent-based modeling.Cellular automatamodeling imposes a fixed spatial framework such as grid cells and specifies rules that dictate the state of a cell based on the states of its neighboring cells.  As time progresses, spatial patterns emerge as cells change states based on their neighbors; this alters the conditions for future time periods.  For example, cells can represent locations in an urban area and their states can be different types of land use.  Patterns that can emerge from the simple interactions of local land uses include office districts andurban sprawl.Agent-based modelinguses software entities (agents) that have purposeful behavior (goals) and can react, interact and modify their environment while seeking their objectives.  Unlike the cells in cellular automata, simulysts can allow agents to be mobile with respect to space.  For example, one could model traffic flow and dynamics using agents representing individual vehicles that try to minimize travel time between specified origins and destinations.  While pursuing minimal travel times, the agents must avoid collisions with other vehicles also seeking to minimize their travel times.  Cellular automata and agent-based modeling are complementary modeling strategies.  They can be integrated into a common geographic automata system where some agents are fixed while others are mobile.

Complex adaptive systems
theory as applied to spatial analysis suggests that simple interactions among proximal entities can lead to intricate, persistent and functional spatial entities at aggregate levels.  Two fundamentally spatial simulation methods are cellular automata and agent-based modeling.
Cellular automata
modeling imposes a fixed spatial framework such as grid cells and specifies rules that dictate the state of a cell based on the states of its neighboring cells.  As time progresses, spatial patterns emerge as cells change states based on their neighbors; this alters the conditions for future time periods.  For example, cells can represent locations in an urban area and their states can be different types of land use.  Patterns that can emerge from the simple interactions of local land uses include office districts and
urban sprawl
.
Agent-based modeling
uses software entities (agents) that have purposeful behavior (goals) and can react, interact and modify their environment while seeking their objectives.  Unlike the cells in cellular automata, simulysts can allow agents to be mobile with respect to space.  For example, one could model traffic flow and dynamics using agents representing individual vehicles that try to minimize travel time between specified origins and destinations.  While pursuing minimal travel times, the agents must avoid collisions with other vehicles also seeking to minimize their travel times.  Cellular automata and agent-based modeling are complementary modeling strategies.  They can be integrated into a common geographic automata system where some agents are fixed while others are mobile.
Calibration plays a pivotal role in both CA and ABM simulation and modelling approaches. Initial approaches to CA proposed robust calibration approaches based on stochastic, Monte Carlo methods.[55][56]ABM approaches rely on agents' decision rules (in many cases extracted from qualitative research base methods such as questionnaires).[57]Recent Machine Learning Algorithms calibrate using training sets, for instance in order to understand the qualities of the built environment.[58]

Calibration plays a pivotal role in both CA and ABM simulation and modelling approaches. Initial approaches to CA proposed robust calibration approaches based on stochastic, Monte Carlo methods.
[
55
]
[
56
]
ABM approaches rely on agents' decision rules (in many cases extracted from qualitative research base methods such as questionnaires).
[
57
]
Recent Machine Learning Algorithms calibrate using training sets, for instance in order to understand the qualities of the built environment.
[
58
]

### Multiple-point geostatistics (MPS)

Multiple-point geostatistics (MPS)
[
edit
]
Spatial analysis of a conceptual geological model is the main purpose of any MPS algorithm. The method analyzes the spatial statistics of the geological model, called the training image, and generates realizations of the phenomena that honor those input multiple-point statistics.

Spatial analysis of a conceptual geological model is the main purpose of any MPS algorithm. The method analyzes the spatial statistics of the geological model, called the training image, and generates realizations of the phenomena that honor those input multiple-point statistics.
A recent MPS algorithm used to accomplish this task is the pattern-based method by Honarkhah.[59]In this method, a distance-based approach is employed to analyze the patterns in the training image. This allows the reproduction of the multiple-point statistics, and the complex geometrical features of the training image. Each output of the MPS algorithm is a realization that represents a random field. Together, several realizations may be used to quantify spatial uncertainty.

A recent MPS algorithm used to accomplish this task is the pattern-based method by Honarkhah.
[
59
]
In this method, a distance-based approach is employed to analyze the patterns in the training image. This allows the reproduction of the multiple-point statistics, and the complex geometrical features of the training image. Each output of the MPS algorithm is a realization that represents a random field. Together, several realizations may be used to quantify spatial uncertainty.
One of the recent methods is presented by Tahmasebi et al.[60]uses a cross-correlation function to improve the spatial pattern reproduction. They call their MPS simulation method as the CCSIM algorithm. This method is able to quantify the spatial connectivity, variability and uncertainty. Furthermore, the method is not sensitive to any type of data and is able to simulate both categorical and continuous scenarios. CCSIM algorithm is able to be used for any stationary, non-stationary and multivariate systems and it can provide high quality visual appeal model.,[61][62]

One of the recent methods is presented by Tahmasebi et al.
[
60
]
uses a cross-correlation function to improve the spatial pattern reproduction. They call their MPS simulation method as the CCSIM algorithm. This method is able to quantify the spatial connectivity, variability and uncertainty. Furthermore, the method is not sensitive to any type of data and is able to simulate both categorical and continuous scenarios. CCSIM algorithm is able to be used for any stationary, non-stationary and multivariate systems and it can provide high quality visual appeal model.,
[
61
]
[
62
]

## Geospatial and hydrospatial analysis

Geospatial and hydrospatial analysis
[
edit
]

<!-- table omitted -->

This section
may need to be cleaned up.
It has been
merged
from
Geospatial analysis
.
Geospatial and hydrospatial analysis, or justspatial analysis,[63]is an approach to applyingstatistical analysisand other analytic techniques to data which has a geographical or spatial aspect. Such analysis would typically employ software capable of rendering maps processing spatial data, and applyinganalyticalmethods to terrestrial orgeographicdatasets, including the use ofgeographic information systemsandgeomatics.[64][65][66]

Geospatial and hydrospatial analysis
, or just
spatial analysis
,
[
63
]
is an approach to applying
statistical analysis
and other analytic techniques to data which has a geographical or spatial aspect. Such analysis would typically employ software capable of rendering maps processing spatial data, and applying
analytical
methods to terrestrial or
geographic
datasets, including the use of
geographic information systems
and
geomatics
.
[
64
]
[
65
]
[
66
]

### Geographical information system usage

Geographical information system usage
[
edit
]
Geographic information systems(GIS) — a large domain that provides a variety of capabilities designed to capture, store, manipulate, analyze, manage, and present all types of geographical data — utilizes geospatial and hydrospatial analysis in a variety of contexts, operations and applications.

Geographic information systems
(GIS) — a large domain that provides a variety of capabilities designed to capture, store, manipulate, analyze, manage, and present all types of geographical data — utilizes geospatial and hydrospatial analysis in a variety of contexts, operations and applications.

#### Basic applications

Basic applications
[
edit
]
Geospatial and Hydrospatial analysis, usingGIS, was developed for problems in the environmental and life sciences, in particularecology,geologyandepidemiology. It has extended to almost all industries including defense, intelligence, utilities, Natural Resources (i.e. Oil and Gas, Forestry ... etc.), social sciences, medicine andPublic Safety(i.e. emergency management and criminology), disaster risk reduction and management (DRRM), andclimate change adaptation(CCA). Spatial statistics typically result primarily from observation rather than experimentation.  Hydrospatial is particularly used for the aquatic side and the members related to the water surface, column, bottom, sub-bottom and the coastal zones.

Geospatial and Hydrospatial analysis, using
GIS
, was developed for problems in the environmental and life sciences, in particular
ecology
,
geology
and
epidemiology
. It has extended to almost all industries including defense, intelligence, utilities, Natural Resources (i.e. Oil and Gas, Forestry ... etc.), social sciences, medicine and
Public Safety
(i.e. emergency management and criminology), disaster risk reduction and management (DRRM), and
climate change adaptation
(CCA). Spatial statistics typically result primarily from observation rather than experimentation.  Hydrospatial is particularly used for the aquatic side and the members related to the water surface, column, bottom, sub-bottom and the coastal zones.

#### Basic operations

Basic operations
[
edit
]
Vector-basedGISis typically related to operations such as map overlay (combining two or more maps or map layers according to predefined rules), simple buffering (identifying regions of a map within a specified distance of one or more features, such as towns, roads or rivers) and similar basic operations. This reflects (and is reflected in) the use of the term spatial analysis within the Open Geospatial Consortium (OGC) "simple feature specifications". For raster-based GIS, widely used in the environmental sciences and remote sensing, this typically means a range of actions applied to the grid cells of one or more maps (or images) often involving filtering and/or algebraic operations (map algebra). These techniques involve processing one or more raster layers according to simple rules resulting in a new map layer, for example replacing each cell value with some combination of its neighbours' values, or computing the sum or difference of specific attribute values for each grid cell in two matching raster datasets. Descriptive statistics, such as cell counts, means, variances, maxima, minima, cumulative values, frequencies and a number of other measures and distance computations are also often included in this generic term spatial analysis. Spatial analysis includes a large variety of statistical techniques (descriptive,exploratory, and explanatorystatistics) that apply to data that vary spatially and which can vary over time. Some more advanced statistical techniques includeGetis-ordGi* or Anselin Local Moran's I which are used to determine clustering patterns of spatially referenced data.

Vector-based
GIS
is typically related to operations such as map overlay (combining two or more maps or map layers according to predefined rules), simple buffering (identifying regions of a map within a specified distance of one or more features, such as towns, roads or rivers) and similar basic operations. This reflects (and is reflected in) the use of the term spatial analysis within the Open Geospatial Consortium (
OGC
) "simple feature specifications". For raster-based GIS, widely used in the environmental sciences and remote sensing, this typically means a range of actions applied to the grid cells of one or more maps (or images) often involving filtering and/or algebraic operations (map algebra). These techniques involve processing one or more raster layers according to simple rules resulting in a new map layer, for example replacing each cell value with some combination of its neighbours' values, or computing the sum or difference of specific attribute values for each grid cell in two matching raster datasets. Descriptive statistics, such as cell counts, means, variances, maxima, minima, cumulative values, frequencies and a number of other measures and distance computations are also often included in this generic term spatial analysis. Spatial analysis includes a large variety of statistical techniques (descriptive,
exploratory
, and explanatory
statistics
) that apply to data that vary spatially and which can vary over time. Some more advanced statistical techniques include
Getis-ord
Gi* or Anselin Local Moran's I which are used to determine clustering patterns of spatially referenced data.

#### Advanced operations

Advanced operations
[
edit
]
Geospatial and Hydrospatial analysis goes beyond 2D and 3D mapping operations and spatial statistics. It is multi-dimensional and also temporal and includes:

Geospatial and Hydrospatial analysis goes beyond 2D and 3D mapping operations and spatial statistics. It is multi-dimensional and also temporal and includes:
- Surface analysis — in particular analysing the properties of physical surfaces, such asgradient,aspectandvisibility, and analysing surface-like data "fields";
Surface analysis — in particular analysing the properties of physical surfaces, such as
gradient
,
aspect
and
visibility
, and analysing surface-like data "fields";
- Network analysis — examining the properties of natural and man-made networks in order to understand the behaviour of flows within and around such networks; and locational analysis. GIS-based network analysis may be used to address a wide range of practical problems such as route selection and facility location (core topics in the field ofoperations research), and problems involving flows such as those found in Hydrospatial andhydrologyand transportation research. In many instances location problems relate to networks and as such are addressed with tools designed for this purpose, but in others existing networks may have little or no relevance or may be impractical to incorporate within the modeling process. Problems that are not specifically network constrained, such as new road or pipeline routing, regional warehouse location, mobile phone mast positioning or the selection of rural community health care sites, may be effectively analysed (at least initially) without reference to existing physical networks. Locational analysis "in the plane" is also applicable where suitable network datasets are not available, or are too large or expensive to be utilised, or where the location algorithm is very complex or involves the examination or simulation of a very large number of alternative configurations.
Network analysis — examining the properties of natural and man-made networks in order to understand the behaviour of flows within and around such networks; and locational analysis. GIS-based network analysis may be used to address a wide range of practical problems such as route selection and facility location (core topics in the field of
operations research
), and problems involving flows such as those found in Hydrospatial and
hydrology
and transportation research. In many instances location problems relate to networks and as such are addressed with tools designed for this purpose, but in others existing networks may have little or no relevance or may be impractical to incorporate within the modeling process. Problems that are not specifically network constrained, such as new road or pipeline routing, regional warehouse location, mobile phone mast positioning or the selection of rural community health care sites, may be effectively analysed (at least initially) without reference to existing physical networks. Locational analysis "in the plane" is also applicable where suitable network datasets are not available, or are too large or expensive to be utilised, or where the location algorithm is very complex or involves the examination or simulation of a very large number of alternative configurations.
- Geovisualization— the creation and manipulation of images, maps, diagrams, charts, 3D views and their associated tabular datasets. GIS packages increasingly provide a range of such tools, providing static or rotating views, draping images over 2.5D surface representations, providing animations and fly-throughs, dynamic linking and brushing and spatio-temporal visualisations. This latter class of tools is the least developed, reflecting in part the limited range of suitable compatible datasets and the limited set of analytical methods available, although this picture is changing rapidly. All these facilities augment the core tools utilised in spatial analysis throughout the analytical process (exploration of data, identification of patterns and relationships, construction of models, and communication of results)
Geovisualization
— the creation and manipulation of images, maps, diagrams, charts, 3D views and their associated tabular datasets. GIS packages increasingly provide a range of such tools, providing static or rotating views, draping images over 2.5D surface representations, providing animations and fly-throughs, dynamic linking and brushing and spatio-temporal visualisations. This latter class of tools is the least developed, reflecting in part the limited range of suitable compatible datasets and the limited set of analytical methods available, although this picture is changing rapidly. All these facilities augment the core tools utilised in spatial analysis throughout the analytical process (exploration of data, identification of patterns and relationships, construction of models, and communication of results)

#### Mobile geospatial and hydrospatial Computing

Mobile geospatial and hydrospatial Computing
[
edit
]
Traditionally geospatial and hydrospatial computing has been performed primarily on personal computers (PCs) or servers. Due to the increasing capabilities of mobile devices, however, geospatial computing in mobile devices is a fast-growing trend.[67]The portable nature of these devices, as well as the presence of useful sensors, such as Global Navigation Satellite System (GNSS) receivers and barometric pressure sensors, make them useful for capturing and processing geospatial and hydrospatial information in the field. In addition to the local processing of geospatial information on mobile devices, another growing trend is cloud-based geospatial computing. In this architecture, data can be collected in the field using mobile devices and then transmitted to cloud-based servers for further processing and ultimate storage. In a similar manner, geospatial and hydrospatial information can be made available to connected mobile devices via the cloud, allowing access to vast databases of geospatial and hydrospatial information anywhere where a wireless data connection is available.

Traditionally geospatial and hydrospatial computing has been performed primarily on personal computers (PCs) or servers. Due to the increasing capabilities of mobile devices, however, geospatial computing in mobile devices is a fast-growing trend.
[
67
]
The portable nature of these devices, as well as the presence of useful sensors, such as Global Navigation Satellite System (GNSS) receivers and barometric pressure sensors, make them useful for capturing and processing geospatial and hydrospatial information in the field. In addition to the local processing of geospatial information on mobile devices, another growing trend is cloud-based geospatial computing. In this architecture, data can be collected in the field using mobile devices and then transmitted to cloud-based servers for further processing and ultimate storage. In a similar manner, geospatial and hydrospatial information can be made available to connected mobile devices via the cloud, allowing access to vast databases of geospatial and hydrospatial information anywhere where a wireless data connection is available.

### Geographic information science and spatial analysis

Geographic information science and spatial analysis
[
edit
]
Further information:
Geographic information systems § Spatial analysis
This flow map of Napoleon's ill-fated march on Moscow is an early and celebrated example of geovisualization. It shows the army's direction as it traveled, the places the troops passed through, the size of the army as troops died from hunger and wounds, and the freezing temperatures they experienced.
Geographic information systems(GIS) and the underlyinggeographic information sciencethat advances these technologies have a strong influence on spatial analysis.  The increasing ability to capture and handle geographic data means that spatial analysis is occurring within increasingly data-rich environments.  Geographic data capture systems include remotely sensed imagery,environmental monitoringsystems such as intelligent transportation systems, and location-aware technologies such as mobile devices that can report location in near-real time.  GIS provide platforms for managing these data, computing spatial relationships such as distance, connectivity and directional relationships between spatial units, and visualizing both the raw data and spatial analytic results within a cartographic context. Subtypes include:

Geographic information systems
(GIS) and the underlying
geographic information science
that advances these technologies have a strong influence on spatial analysis.  The increasing ability to capture and handle geographic data means that spatial analysis is occurring within increasingly data-rich environments.  Geographic data capture systems include remotely sensed imagery,
environmental monitoring
systems such as intelligent transportation systems, and location-aware technologies such as mobile devices that can report location in near-real time.  GIS provide platforms for managing these data, computing spatial relationships such as distance, connectivity and directional relationships between spatial units, and visualizing both the raw data and spatial analytic results within a cartographic context. Subtypes include:
- Geovisualization(GVis) combines scientific visualization withdigital cartographyto support the exploration and analysis of geographic data and information, including the results of spatial analysis or simulation. GVis leverages the human orientation towards visual information processing in the exploration, analysis and communication of geographic data and information.  In contrast with traditional cartography, GVis is typically three- or four-dimensional (the latter including time) and user-interactive.
Geovisualization
(GVis) combines scientific visualization with
digital cartography
to support the exploration and analysis of geographic data and information, including the results of spatial analysis or simulation. GVis leverages the human orientation towards visual information processing in the exploration, analysis and communication of geographic data and information.  In contrast with traditional cartography, GVis is typically three- or four-dimensional (the latter including time) and user-interactive.
- Geographic knowledge discovery (GKD) is the human-centered process of applying efficient computational tools for exploring massivespatial databases. GKD includes geographicdata mining, but also encompasses related activities such as data selection, data cleaning and pre-processing, and interpretation of results. GVis can also serve a central role in the GKD process.  GKD is based on the premise that massive databases contain interesting (valid, novel, useful and understandable) patterns that standard analytical techniques cannot find.  GKD can serve as a hypothesis-generating process for spatial analysis, producing tentative patterns and relationships that should be confirmed using spatial analytical techniques.
Geographic knowledge discovery (GKD) is the human-centered process of applying efficient computational tools for exploring massive
spatial databases
. GKD includes geographic
data mining
, but also encompasses related activities such as data selection, data cleaning and pre-processing, and interpretation of results. GVis can also serve a central role in the GKD process.  GKD is based on the premise that massive databases contain interesting (valid, novel, useful and understandable) patterns that standard analytical techniques cannot find.  GKD can serve as a hypothesis-generating process for spatial analysis, producing tentative patterns and relationships that should be confirmed using spatial analytical techniques.
- Spatial decision support systems(SDSS) take existing spatial data and use a variety of mathematical models to make projections into the future. This allows urban and regional planners to test intervention decisions prior to implementation.[68]
Spatial decision support systems
(SDSS) take existing spatial data and use a variety of mathematical models to make projections into the future. This allows urban and regional planners to test intervention decisions prior to implementation.
[
68
]

## See also

See also
[
edit
]
General topics
- Buffer analysis
Buffer analysis
- Cartography
Cartography
- Complete spatial randomness
Complete spatial randomness
- Concepts and Techniques in Modern Geography
Concepts and Techniques in Modern Geography
- Cost distance analysis
Cost distance analysis
- Four traditions of geography
Four traditions of geography
- GeoComputation
GeoComputation
- Geospatial intelligence
Geospatial intelligence
- Geospatial predictive modeling
Geospatial predictive modeling
- Dimensionally Extended nine-Intersection Model(DE-9IM)
Dimensionally Extended nine-Intersection Model
(DE-9IM)
- Geographic information science
Geographic information science
- Mathematical statistics
Mathematical statistics
- Modifiable areal unit problem
Modifiable areal unit problem
- Modifiable temporal unit problem
Modifiable temporal unit problem
- Neighborhood effect averaging problem
Neighborhood effect averaging problem
- Point process
Point process
- Proximity analysis
Proximity analysis
- Spatial descriptive statistics
Spatial descriptive statistics
- Spatial relation
Spatial relation
- Technical geography
Technical geography
- Terrain analysis
Terrain analysis
- Tobler's first law of geography
Tobler's first law of geography
- Tobler's second law of geography
Tobler's second law of geography
- List of spatial analysis software
List of spatial analysis software
Specific applications
- Boundary problem (in spatial analysis)
Boundary problem (in spatial analysis)
- Extrapolation domain analysis
Extrapolation domain analysis
- Fuzzy architectural spatial analysis
Fuzzy architectural spatial analysis
- Geodemographic segmentation
Geodemographic segmentation
- Geographic information systems
Geographic information systems
- Geoinformatics
Geoinformatics
- Geostatistics
Geostatistics
- Permeability (spatial and transport planning)
Permeability (spatial and transport planning)
- Spatial econometrics
Spatial econometrics
- Spatial epidemiology
Spatial epidemiology
- Suitability analysis
Suitability analysis
- Viewshed analysis
Viewshed analysis

## References

References
[
edit
]
- ^The History of Land Surveying. Accessed Dec 17 2020.https://info.courthousedirect.com/blog/history-of-land-surveying
^
The History of Land Surveying. Accessed Dec 17 2020.
https://info.courthousedirect.com/blog/history-of-land-surveying
- ^Mark MonmonierHow to Lie with MapsUniversity of Chicago Press, 1996.
^
Mark Monmonier
How to Lie with Maps
University of Chicago Press, 1996.
- ^Openshaw, Stan (1983).The Modifiable Areal Unit Problem(PDF). Geo Books.ISBN0-86094-134-5.
^
Openshaw, Stan (1983).
The Modifiable Areal Unit Problem
(PDF)
. Geo Books.
ISBN
0-86094-134-5
.
- ^Chen, Xiang; Ye, Xinyue; Widener, Michael J.; Delmelle, Eric; Kwan, Mei-Po; Shannon, Jerry; Racine, Racine F.; Adams, Aaron; Liang, Lu; Peng, Jia (27 December 2022)."A systematic review of the modifiable areal unit problem (MAUP) in community food environmental research".Urban Informatics.1(1): 22.Bibcode:2022UrbIn...1...22C.doi:10.1007/s44212-022-00021-1.S2CID255206315.
^
Chen, Xiang; Ye, Xinyue; Widener, Michael J.; Delmelle, Eric; Kwan, Mei-Po; Shannon, Jerry; Racine, Racine F.; Adams, Aaron; Liang, Lu; Peng, Jia (27 December 2022).
"A systematic review of the modifiable areal unit problem (MAUP) in community food environmental research"
.
Urban Informatics
.
1
(1): 22.
Bibcode
:
2022UrbIn...1...22C
.
doi
:
10.1007/s44212-022-00021-1
.
S2CID
255206315
.
- ^"MAUP | Definition – Esri Support GIS Dictionary".support.esri.com. Retrieved2017-03-09.
^
"MAUP | Definition – Esri Support GIS Dictionary"
.
support.esri.com
. Retrieved
2017-03-09
.
- ^Geography, US Census Bureau."Geographic Boundary Change Notes".www.census.gov. Retrieved2017-02-24.
^
Geography, US Census Bureau.
"Geographic Boundary Change Notes"
.
www.census.gov
. Retrieved
2017-02-24
.
- ^Cheng, Tao; Adepeju, Monsuru; Preis, Tobias (27 June 2014)."Modifiable Temporal Unit Problem (MTUP) and Its Effect on Space-Time Cluster Detection".PLOS ONE.9(6) e100465.Bibcode:2014PLoSO...9j0465C.doi:10.1371/journal.pone.0100465.PMC4074055.PMID24971885.
^
Cheng, Tao; Adepeju, Monsuru; Preis, Tobias (27 June 2014).
"Modifiable Temporal Unit Problem (MTUP) and Its Effect on Space-Time Cluster Detection"
.
PLOS ONE
.
9
(6) e100465.
Bibcode
:
2014PLoSO...9j0465C
.
doi
:
10.1371/journal.pone.0100465
.
PMC
4074055
.
PMID
24971885
.
- ^Jong, R. de; Bruin, S. de (5 January 2012)."Linear trends in seasonal vegetation time series and the modifiable temporal unit problem".Biogeosciences.9(1):71–77.Bibcode:2012BGeo....9...71D.doi:10.5194/bg-9-71-2012.
^
Jong, R. de; Bruin, S. de (5 January 2012).
"Linear trends in seasonal vegetation time series and the modifiable temporal unit problem"
.
Biogeosciences
.
9
(1):
71–
77.
Bibcode
:
2012BGeo....9...71D
.
doi
:
10.5194/bg-9-71-2012
.
- ^Deckard, Mica; Schnell, Cory (22 October 2022). "The Temporal (In)Stability of Violent Crime Hot Spots Between Months and The Modifiable Temporal Unit Problem".Crime & Delinquency.69(6–7):1312–1335.doi:10.1177/00111287221128483.
^
Deckard, Mica; Schnell, Cory (22 October 2022). "The Temporal (In)Stability of Violent Crime Hot Spots Between Months and The Modifiable Temporal Unit Problem".
Crime & Delinquency
.
69
(
6–
7):
1312–
1335.
doi
:
10.1177/00111287221128483
.
- ^abKwan, Mei-Po (2018)."The Neighborhood Effect Averaging Problem (NEAP): An Elusive Confounder of the Neighborhood Effect".Int J Environ Res Public Health.15(9): 1841.doi:10.3390/ijerph15091841.PMC6163400.PMID30150510.
^
a
b
Kwan, Mei-Po (2018).
"The Neighborhood Effect Averaging Problem (NEAP): An Elusive Confounder of the Neighborhood Effect"
.
Int J Environ Res Public Health
.
15
(9): 1841.
doi
:
10.3390/ijerph15091841
.
PMC
6163400
.
PMID
30150510
.
- ^abKwan, Mei-Po(2023)."Human Mobility and the Neighborhood Effect Averaging Problem (NEAP)". In Li, Bin; Xun, Shi; A-Xing, Zhu; Wang, Cuizhen; Lin, Hui (eds.).New Thinking in GIScience. Springer. pp.95–101.doi:10.1007/978-981-19-3816-0_11.ISBN978-981-19-3818-4. Retrieved7 October2023.
^
a
b
Kwan, Mei-Po
(2023).
"Human Mobility and the Neighborhood Effect Averaging Problem (NEAP)"
. In Li, Bin; Xun, Shi; A-Xing, Zhu; Wang, Cuizhen; Lin, Hui (eds.).
New Thinking in GIScience
. Springer. pp.
95–
101.
doi
:
10.1007/978-981-19-3816-0_11
.
ISBN
978-981-19-3818-4
. Retrieved
7 October
2023
.
- ^Xu, Tiantian; Wang, Shiyi; Liu, Qing; Kim, Junghwan; Zhang, Jingyi; Ren, Yiwen; Ta, Na; Wang, Xiaoliang; Wu, Jiayu (August 2023). "Vegetation color exposure differences at the community and individual levels: An explanatory framework based on the neighborhood effect averaging problem".Urban Forestry & Urban Greening.86.Bibcode:2023UFUG...8628001X.doi:10.1016/j.ufug.2023.128001.
^
Xu, Tiantian; Wang, Shiyi; Liu, Qing; Kim, Junghwan; Zhang, Jingyi; Ren, Yiwen; Ta, Na; Wang, Xiaoliang; Wu, Jiayu (August 2023). "Vegetation color exposure differences at the community and individual levels: An explanatory framework based on the neighborhood effect averaging problem".
Urban Forestry & Urban Greening
.
86
.
Bibcode
:
2023UFUG...8628001X
.
doi
:
10.1016/j.ufug.2023.128001
.
- ^Ham, Maarten van; Manley, David (2012). "Neighbourhood Effects Research at a Crossroads. Ten Challenges for Future Research Introduction".Environment and Planning A: Economy and Space.44(12):2787–2793.doi:10.1068/a4543.
^
Ham, Maarten van; Manley, David (2012). "Neighbourhood Effects Research at a Crossroads. Ten Challenges for Future Research Introduction".
Environment and Planning A: Economy and Space
.
44
(12):
2787–
2793.
doi
:
10.1068/a4543
.
- ^Parry, Marc (5 November 2012)."The Neighborhood Effect". THE CHRONICLE REVIEW. The Chronicle of Higher Education. Retrieved7 October2023.
^
Parry, Marc (5 November 2012).
"The Neighborhood Effect"
. THE CHRONICLE REVIEW. The Chronicle of Higher Education
. Retrieved
7 October
2023
.
- ^Labbé, Martine; Laporte, Gilbert; Rodríguez Martín, Inmaculada; Salazar González, Juan José (May 2004). "The Ring Star Problem: Polyhedral analysis and exact algorithm".Networks.43(3):177–189.doi:10.1002/net.10114.ISSN0028-3045.
^
Labbé, Martine; Laporte, Gilbert; Rodríguez Martín, Inmaculada; Salazar González, Juan José (May 2004). "The Ring Star Problem: Polyhedral analysis and exact algorithm".
Networks
.
43
(3):
177–
189.
doi
:
10.1002/net.10114
.
ISSN
0028-3045
.
- ^See the TSP world tour problem which has already been solved to within 0.05% of the optimal solution.[1]
^
See the TSP world tour problem which has already been solved to within 0.05% of the optimal solution.
[1]
- ^Matthews, Stephen A. (2017).International Encyclopedia of Geography: People, the Earth, Environment and Technology: Uncertain Geographic Context Problem. Wiley.doi:10.1002/9781118786352.wbieg0599.
^
Matthews, Stephen A. (2017).
International Encyclopedia of Geography: People, the Earth, Environment and Technology: Uncertain Geographic Context Problem
. Wiley.
doi
:
10.1002/9781118786352.wbieg0599
.
- ^Park, Yoo Min; Kwan, Mei-Po (19 March 2025). "Revisiting the Uncertain Geographic Context Problem: Expanding Its Scope to Include Indoor Geographic Contexts and Dynamics in Environmental Health and Social Science Research".Annals of the American Association of Geographers.115(5):1055–1070.doi:10.1080/24694452.2025.2472974.
^
Park, Yoo Min; Kwan, Mei-Po (19 March 2025). "Revisiting the Uncertain Geographic Context Problem: Expanding Its Scope to Include Indoor Geographic Contexts and Dynamics in Environmental Health and Social Science Research".
Annals of the American Association of Geographers
.
115
(5):
1055–
1070.
doi
:
10.1080/24694452.2025.2472974
.
- ^Kwan, Mei-Po (2012). "The Uncertain Geographic Context Problem".Annals of the Association of American Geographers.102(5):958–968.doi:10.1080/00045608.2012.687349.S2CID52024592.
^
Kwan, Mei-Po (2012). "The Uncertain Geographic Context Problem".
Annals of the Association of American Geographers
.
102
(5):
958–
968.
doi
:
10.1080/00045608.2012.687349
.
S2CID
52024592
.
- ^Kwan, Mei-Po (2012)."How GIS can help address the uncertain geographic context problem in social science research".Annals of GIS.18(4):245–255.Bibcode:2012AnGIS..18..245K.doi:10.1080/19475683.2012.727867.S2CID13215965. Retrieved4 January2023.
^
Kwan, Mei-Po (2012).
"How GIS can help address the uncertain geographic context problem in social science research"
.
Annals of GIS
.
18
(4):
245–
255.
Bibcode
:
2012AnGIS..18..245K
.
doi
:
10.1080/19475683.2012.727867
.
S2CID
13215965
. Retrieved
4 January
2023
.
- ^Journel, A G and Huijbregts, C J,Mining Geostatistics,Academic PressInc, London.
^
Journel, A G and Huijbregts, C J,
Mining Geostatistics
,
Academic Press
Inc, London.
- ^von Csefalvay, Chris (2023),"Spatial dynamics of epidemics",Computational Modeling of Infectious Disease, Elsevier, pp.257–303,doi:10.1016/b978-0-32-395389-4.00017-7,ISBN978-0-323-95389-4, retrieved2023-03-05
^
von Csefalvay, Chris (2023),
"Spatial dynamics of epidemics"
,
Computational Modeling of Infectious Disease
, Elsevier, pp.
257–
303,
doi
:
10.1016/b978-0-32-395389-4.00017-7
,
ISBN
978-0-323-95389-4
, retrieved
2023-03-05
- ^Knegt, De; Coughenour, M.B.; Skidmore, A.K.; Heitkönig, I.M.A.; Knox, N.M.; Slotow, R.; Prins, H.H.T. (2010)."Spatial autocorrelation and the scaling of species–environment relationships".Ecology.91(8):2455–2465.Bibcode:2010Ecol...91.2455D.doi:10.1890/09-1359.1.PMID20836467.
^
Knegt, De; Coughenour, M.B.; Skidmore, A.K.; Heitkönig, I.M.A.; Knox, N.M.; Slotow, R.; Prins, H.H.T. (2010).
"Spatial autocorrelation and the scaling of species–environment relationships"
.
Ecology
.
91
(8):
2455–
2465.
Bibcode
:
2010Ecol...91.2455D
.
doi
:
10.1890/09-1359.1
.
PMID
20836467
.
- ^"Spatial Association"(PDF). Geography Teachers' Association of Victoria. Retrieved17 November2014.
^
"Spatial Association"
(PDF)
. Geography Teachers' Association of Victoria
. Retrieved
17 November
2014
.
- ^Song, Yongze (July 2022)."The second dimension of spatial association".International Journal of Applied Earth Observation and Geoinformation.111102834.doi:10.1016/j.jag.2022.102834.hdl:20.500.11937/88649.S2CID249166886.
^
Song, Yongze (July 2022).
"The second dimension of spatial association"
.
International Journal of Applied Earth Observation and Geoinformation
.
111
102834.
doi
:
10.1016/j.jag.2022.102834
.
hdl
:
20.500.11937/88649
.
S2CID
249166886
.
- ^Ghanem, V. G. (2026)."Spatial and Machine Learning Analysis of District-Level Health Insurance Inequities in Ghana".Cureus.18(1) e101984.doi:10.7759/cureus.101984.
^
Ghanem, V. G. (2026).
"Spatial and Machine Learning Analysis of District-Level Health Insurance Inequities in Ghana"
.
Cureus
.
18
(1) e101984.
doi
:
10.7759/cureus.101984
.
- ^Halley, J. M.; Hartley, S.; Kallimanis, A. S.; Kunin, W. E.; Lennon, J. J.; Sgardelis, S. P. (2004-03-01). "Uses and abuses of fractal methodology in ecology".Ecology Letters.7(3):254–271.Bibcode:2004EcolL...7..254H.doi:10.1111/j.1461-0248.2004.00568.x.ISSN1461-0248.
^
Halley, J. M.; Hartley, S.; Kallimanis, A. S.; Kunin, W. E.; Lennon, J. J.; Sgardelis, S. P. (2004-03-01). "Uses and abuses of fractal methodology in ecology".
Ecology Letters
.
7
(3):
254–
271.
Bibcode
:
2004EcolL...7..254H
.
doi
:
10.1111/j.1461-0248.2004.00568.x
.
ISSN
1461-0248
.
- ^Ocaña-Riola, R (2010)."Common errors in disease mapping".Geospatial Health.4(2):139–154.doi:10.4081/gh.2010.196.PMID20503184.
^
Ocaña-Riola, R (2010).
"Common errors in disease mapping"
.
Geospatial Health
.
4
(2):
139–
154.
doi
:
10.4081/gh.2010.196
.
PMID
20503184
.
- ^abcdef"Understanding Spatial Fallacies".The Learner's Guide to Geospatial Analysis. Penn State Department of Geography. Retrieved27 April2018.
^
a
b
c
d
e
f
"Understanding Spatial Fallacies"
.
The Learner's Guide to Geospatial Analysis
. Penn State Department of Geography
. Retrieved
27 April
2018
.
- ^Quattrochi, Dale A (2016-02-01).Integrating scale in remote sensing and GIS. Taylor & Francis.ISBN978-1-4822-1826-8.OCLC973767077.
^
Quattrochi, Dale A (2016-02-01).
Integrating scale in remote sensing and GIS
. Taylor & Francis.
ISBN
978-1-4822-1826-8
.
OCLC
973767077
.
- ^Robinson, Ws (April 2009)."Ecological Correlations and the Behavior of Individuals*".International Journal of Epidemiology.38(2):337–341.doi:10.1093/ije/dyn357.PMID19179346.
^
Robinson, Ws (April 2009).
"Ecological Correlations and the Behavior of Individuals*"
.
International Journal of Epidemiology
.
38
(2):
337–
341.
doi
:
10.1093/ije/dyn357
.
PMID
19179346
.
- ^Graham J. Upton & Bernard Fingelton:Spatial Data Analysis by Example Volume 1: Point Pattern and Quantitative DataJohn Wiley & Sons, New York. 1985.
^
Graham J. Upton & Bernard Fingelton:
Spatial Data Analysis by Example Volume 1: Point Pattern and Quantitative Data
John Wiley & Sons, New York. 1985.
- ^Harman H H (1960)Modern Factor Analysis, University of Chicago Press
^
Harman H H (1960)
Modern Factor Analysis
, University of Chicago Press
- ^Rummel R J (1970)Applied Factor Analysis. Evanston, ILL: Northwestern University Press.
^
Rummel R J (1970)
Applied Factor Analysis
. Evanston, ILL: Northwestern University Press.
- ^Bell W & E Shevky (1955)Social Area Analysis, Stanford University Press
^
Bell W & E Shevky (1955)
Social Area Analysis
, Stanford University Press
- ^Moser C A & W Scott (1961)British Towns; A Statistical Study of their Social and Economic Differences, Oliver & Boyd, London.
^
Moser C A & W Scott (1961)
British Towns; A Statistical Study of their Social and Economic Differences
, Oliver & Boyd, London.
- ^Berry B J & F Horton (1971)Geographic Perspectives on Urban Systems, John Wiley, N-Y.
^
Berry B J & F Horton (1971)
Geographic Perspectives on Urban Systems
, John Wiley, N-Y.
- ^Berry B J & K B Smith eds (1972)City Classification Handbook : Methods and Applications, John Wiley, N-Y.
^
Berry B J & K B Smith eds (1972)
City Classification Handbook : Methods and Applications
, John Wiley, N-Y.
- ^Ciceri M-F (1974)Méthodes d'analyse multivariée dans la géographie anglo-saxonne, Université de Paris-1; free download onhttp://www-ohp.univ-paris1.fr
^
Ciceri M-F (1974)
Méthodes d'analyse multivariée dans la géographie anglo-saxonne
, Université de Paris-1; free download on
http://www-ohp.univ-paris1.fr
- ^Tucker L R (1964) « The extension of Factor Analysis to three-dimensional matrices », in  Frederiksen N & H Gulliksen eds,Contributions to Mathematical Psychology, Holt, Rinehart and Winston, NY.
^
Tucker L R (1964) « The extension of Factor Analysis to three-dimensional matrices », in  Frederiksen N & H Gulliksen eds,
Contributions to Mathematical Psychology
, Holt, Rinehart and Winston, NY.
- ^R. Coppi & S. Bolasco, eds. (1989),Multiway data analysis, Elsevier, Amsterdam.
^
R. Coppi & S. Bolasco, eds. (1989),
Multiway data analysis
, Elsevier, Amsterdam.
- ^Cant, R.G. (1971). "Changes in the location of manufacturing in New Zealand 1957-1968: An application of three-mode factor analysis".New Zealand Geographer.27(1):38–55.Bibcode:1971NZGeo..27...38C.doi:10.1111/j.1745-7939.1971.tb00636.x.
^
Cant, R.G. (1971). "Changes in the location of manufacturing in New Zealand 1957-1968: An application of three-mode factor analysis".
New Zealand Geographer
.
27
(1):
38–
55.
Bibcode
:
1971NZGeo..27...38C
.
doi
:
10.1111/j.1745-7939.1971.tb00636.x
.
- ^Marchand B (1986)The Emergence of Los Angeles, 1940-1970, Pion Ltd, London
^
Marchand B (1986)
The Emergence of Los Angeles, 1940-1970
, Pion Ltd, London
- ^Brunsdon, C.; Fotheringham, A.S.; Charlton, M.E. (1996)."Geographically Weighted Regression: A Method for Exploring Spatial Nonstationarity".Geographical Analysis.28(4):281–298.Bibcode:1996GeoAn..28..281B.doi:10.1111/j.1538-4632.1996.tb00936.x.
^
Brunsdon, C.; Fotheringham, A.S.; Charlton, M.E. (1996).
"Geographically Weighted Regression: A Method for Exploring Spatial Nonstationarity"
.
Geographical Analysis
.
28
(4):
281–
298.
Bibcode
:
1996GeoAn..28..281B
.
doi
:
10.1111/j.1538-4632.1996.tb00936.x
.
- ^abBanerjee, Sudipto; Carlin, Bradley P.; Gelfand, Alan E. (2014),Hierarchical Modeling and Analysis for Spatial Data, Second Edition, Monographs on Statistics and Applied Probability (2nd ed.), Chapman and Hall/CRC,ISBN978-1-4398-1917-3
^
a
b
Banerjee, Sudipto; Carlin, Bradley P.; Gelfand, Alan E. (2014),
Hierarchical Modeling and Analysis for Spatial Data, Second Edition
, Monographs on Statistics and Applied Probability (2nd ed.), Chapman and Hall/CRC,
ISBN
978-1-4398-1917-3
- ^Bivand, Roger (20 January 2021)."CRAN Task View: Analysis of Spatial Data". Retrieved21 January2021.
^
Bivand, Roger (20 January 2021).
"CRAN Task View: Analysis of Spatial Data"
. Retrieved
21 January
2021
.
- ^Banerjee, Sudipto;Gelfand, Alan E.; Finley, Andrew O.;Sang, Huiyan(2008)."Gaussian predictive process models for large spatial datasets".Journal of the Royal Statistical Society, Series B.70(4):825–848.doi:10.1111/j.1467-9868.2008.00663.x.PMC2741335.PMID19750209.
^
Banerjee, Sudipto
;
Gelfand, Alan E.
; Finley, Andrew O.;
Sang, Huiyan
(2008).
"Gaussian predictive process models for large spatial datasets"
.
Journal of the Royal Statistical Society, Series B
.
70
(4):
825–
848.
doi
:
10.1111/j.1467-9868.2008.00663.x
.
PMC
2741335
.
PMID
19750209
.
- ^Datta, Abhirup; Banerjee, Sudipto; Finley, Andrew O.; Gelfand, Alan E. (2016)."Hierarchical Nearest Neighbor Gaussian Process Models for Large Geostatistical Datasets".Journal of the American Statistical Association.111(514):800–812.arXiv:1406.7343.doi:10.1080/01621459.2015.1044091.PMC5927603.PMID29720777.
^
Datta, Abhirup; Banerjee, Sudipto; Finley, Andrew O.; Gelfand, Alan E. (2016).
"Hierarchical Nearest Neighbor Gaussian Process Models for Large Geostatistical Datasets"
.
Journal of the American Statistical Association
.
111
(514):
800–
812.
arXiv
:
1406.7343
.
doi
:
10.1080/01621459.2015.1044091
.
PMC
5927603
.
PMID
29720777
.
- ^Morer I, Cardillo A, Díaz-Guilera A, Prignano L, Lozano S (2020). "Comparing spatial networks: a one-size-fits-all efficiency-driven approach".Physical Review.101(4) 042301.arXiv:1807.00565.Bibcode:2020PhRvE.101d2301M.doi:10.1103/PhysRevE.101.042301.hdl:2445/161417.PMID32422764.S2CID49564277.
^
Morer I, Cardillo A, Díaz-Guilera A, Prignano L, Lozano S (2020). "Comparing spatial networks: a one-size-fits-all efficiency-driven approach".
Physical Review
.
101
(4) 042301.
arXiv
:
1807.00565
.
Bibcode
:
2020PhRvE.101d2301M
.
doi
:
10.1103/PhysRevE.101.042301
.
hdl
:
2445/161417
.
PMID
32422764
.
S2CID
49564277
.
- ^Gupta J, Molnar C, Xie Y, Knight J, Shekhar S (2021). "Spatial variability aware deep neural networks (SVANN): a general approach".ACM Transactions on Intelligent Systems and Technology.12(6):1–21.doi:10.1145/3466688.S2CID244786699.
^
Gupta J, Molnar C, Xie Y, Knight J, Shekhar S (2021). "Spatial variability aware deep neural networks (SVANN): a general approach".
ACM Transactions on Intelligent Systems and Technology
.
12
(6):
1–
21.
doi
:
10.1145/3466688
.
S2CID
244786699
.
- ^Hagenauer J, Helbich M (2022)."A geographically weighted artificial neural network".International Journal of Geographical Information Science.36(2):215–235.Bibcode:2022IJGIS..36..215H.doi:10.1080/13658816.2021.1871618.S2CID233883395.
^
Hagenauer J, Helbich M (2022).
"A geographically weighted artificial neural network"
.
International Journal of Geographical Information Science
.
36
(2):
215–
235.
Bibcode
:
2022IJGIS..36..215H
.
doi
:
10.1080/13658816.2021.1871618
.
S2CID
233883395
.
- ^Otto, P.; Schmid, W.; Garthoff, R. (2018). "Generalised spatial and spatiotemporal autoregressive conditional heteroscedasticity".Spatial Statistics.26:125–145.arXiv:1609.00711.Bibcode:2018SpaSt..26..125O.doi:10.1016/j.spasta.2018.07.005.
^
Otto, P.; Schmid, W.; Garthoff, R. (2018). "Generalised spatial and spatiotemporal autoregressive conditional heteroscedasticity".
Spatial Statistics
.
26
:
125–
145.
arXiv
:
1609.00711
.
Bibcode
:
2018SpaSt..26..125O
.
doi
:
10.1016/j.spasta.2018.07.005
.
- ^Sato, T.; Matsuda, Y. (2017)."Spatial autoregressive conditional heteroskedasticity models".Journal of the Japan Statistical Society.47(2):221–236.doi:10.14490/jjss.47.221.
^
Sato, T.; Matsuda, Y. (2017).
"Spatial autoregressive conditional heteroskedasticity models"
.
Journal of the Japan Statistical Society
.
47
(2):
221–
236.
doi
:
10.14490/jjss.47.221
.
- ^Otto, P.; Dogan, O.; Taspinar, S.; Schmid, W.; Bera, A. K. (2025)."Spatial and spatiotemporal volatility models: A review".Journal of Economic Surveys.39(3):1037–1091.doi:10.1111/joes.12643.
^
Otto, P.; Dogan, O.; Taspinar, S.; Schmid, W.; Bera, A. K. (2025).
"Spatial and spatiotemporal volatility models: A review"
.
Journal of Economic Surveys
.
39
(3):
1037–
1091.
doi
:
10.1111/joes.12643
.
- ^Silva, E. A.; Clarke, K.C. (2002). "Calibration of the SLEUTH urban growth model for Lisbon and Porto, Portugal".Computers, Environment and Urban Systems.26(6):525–552.Bibcode:2002CEUS...26..525S.doi:10.1016/S0198-9715(01)00014-X.
^
Silva, E. A.; Clarke, K.C. (2002). "Calibration of the SLEUTH urban growth model for Lisbon and Porto, Portugal".
Computers, Environment and Urban Systems
.
26
(6):
525–
552.
Bibcode
:
2002CEUS...26..525S
.
doi
:
10.1016/S0198-9715(01)00014-X
.
- ^Silva, E A (2003). "Complexity, emergence and cellular urban models: lessons learned from applying SLEUTH to two Portuguese metropolitan areas".European Planning Studies.13(1):93–115.doi:10.1080/0965431042000312424.S2CID197257.
^
Silva, E A (2003). "Complexity, emergence and cellular urban models: lessons learned from applying SLEUTH to two Portuguese metropolitan areas".
European Planning Studies
.
13
(1):
93–
115.
doi
:
10.1080/0965431042000312424
.
S2CID
197257
.
- ^Liu and Silva (2017)."Examining the dynamics of the interaction between the development of creative industries and urban spatial structure by agent-based modelling: A case study of Nanjing, China".Urban Studies.65(5):113–125.doi:10.1177/0042098016686493.S2CID157318972.
^
Liu and Silva (2017).
"Examining the dynamics of the interaction between the development of creative industries and urban spatial structure by agent-based modelling: A case study of Nanjing, China"
.
Urban Studies
.
65
(5):
113–
125.
doi
:
10.1177/0042098016686493
.
S2CID
157318972
.
- ^Liu, Lun; Silva, Elisabete A.; Wu, Chunyang; Wang, Hui (2017)."A machine learning-based method for the large-scale evaluation of the qualities of the urban environment"(PDF).Computers Environment and Urban Systems.65:113–125.Bibcode:2017CEUS...65..113L.doi:10.1016/j.compenvurbsys.2017.06.003.
^
Liu, Lun; Silva, Elisabete A.; Wu, Chunyang; Wang, Hui (2017).
"A machine learning-based method for the large-scale evaluation of the qualities of the urban environment"
(PDF)
.
Computers Environment and Urban Systems
.
65
:
113–
125.
Bibcode
:
2017CEUS...65..113L
.
doi
:
10.1016/j.compenvurbsys.2017.06.003
.
- ^Honarkhah, M; Caers, J (2010). "Stochastic Simulation of Patterns Using Distance-Based Pattern Modeling".Mathematical Geosciences.42(5):487–517.Bibcode:2010MatGe..42..487H.doi:10.1007/s11004-010-9276-7.S2CID73657847.
^
Honarkhah, M; Caers, J (2010). "Stochastic Simulation of Patterns Using Distance-Based Pattern Modeling".
Mathematical Geosciences
.
42
(5):
487–
517.
Bibcode
:
2010MatGe..42..487H
.
doi
:
10.1007/s11004-010-9276-7
.
S2CID
73657847
.
- ^Tahmasebi, P.; Hezarkhani, A.; Sahimi, M. (2012). "Multiple-point geostatistical modeling based on the cross-correlation functions".Computational Geosciences.16(3):779–79742.Bibcode:2012CmpGe..16..779T.doi:10.1007/s10596-012-9287-1.S2CID62710397.
^
Tahmasebi, P.; Hezarkhani, A.; Sahimi, M. (2012). "Multiple-point geostatistical modeling based on the cross-correlation functions".
Computational Geosciences
.
16
(3):
779–
79742.
Bibcode
:
2012CmpGe..16..779T
.
doi
:
10.1007/s10596-012-9287-1
.
S2CID
62710397
.
- ^Tahmasebi, P.; Sahimi, M. (2015)."Reconstruction of nonstationary disordered materials and media: Watershed transform and cross-correlation function".Physical Review E.91(3) 032401.Bibcode:2015PhRvE..91c2401T.doi:10.1103/PhysRevE.91.032401.PMID25871117.
^
Tahmasebi, P.; Sahimi, M. (2015).
"Reconstruction of nonstationary disordered materials and media: Watershed transform and cross-correlation function"
.
Physical Review E
.
91
(3) 032401.
Bibcode
:
2015PhRvE..91c2401T
.
doi
:
10.1103/PhysRevE.91.032401
.
PMID
25871117
.
- ^Tahmasebi, P.; Sahimi, M. (2015). "Geostatistical Simulation and Reconstruction of Porous Media by a Cross-Correlation Function and Integration of Hard and Soft Data".Transport in Porous Media.107(3):871–905.Bibcode:2015TPMed.107..871T.doi:10.1007/s11242-015-0471-3.S2CID123432975.
^
Tahmasebi, P.; Sahimi, M. (2015). "Geostatistical Simulation and Reconstruction of Porous Media by a Cross-Correlation Function and Integration of Hard and Soft Data".
Transport in Porous Media
.
107
(3):
871–
905.
Bibcode
:
2015TPMed.107..871T
.
doi
:
10.1007/s11242-015-0471-3
.
S2CID
123432975
.
- ^"Graduate Program in Spatial Analysis".Ryerson University. Retrieved17 December2015.
^
"Graduate Program in Spatial Analysis"
.
Ryerson University
. Retrieved
17 December
2015
.
- ^geospatial. Collins English Dictionary - Complete & Unabridged 11th Edition. Retrieved 5tth August 2012 from CollinsDictionary.com website:http://www.collinsdictionary.com/dictionary/english/geospatial
^
geospatial. Collins English Dictionary - Complete & Unabridged 11th Edition. Retrieved 5tth August 2012 from CollinsDictionary.com website:
http://www.collinsdictionary.com/dictionary/english/geospatial
- ^Dictionary.com's 21st Century Lexicon Copyright © 2003-2010 Dictionary.com, LLChttp://dictionary.reference.com/browse/geospatial
^
Dictionary.com's 21st Century Lexicon Copyright © 2003-2010 Dictionary.com, LLC
http://dictionary.reference.com/browse/geospatial
- ^The geospatial web – blending physical and virtual spaces.Archived2011-10-02 at theWayback Machine, Arno Scharl in receiver magazine, Autumn 2008
^
The geospatial web – blending physical and virtual spaces.
Archived
2011-10-02 at the
Wayback Machine
, Arno Scharl in receiver magazine, Autumn 2008
- ^Chen, Ruizhi; Guinness, Robert E. (2014).Geospatial Computing in Mobile Devices(1st ed.). Norwood, MA: Artech House. p. 228.ISBN978-1-60807-565-2. Retrieved1 July2014.
^
Chen, Ruizhi; Guinness, Robert E. (2014).
Geospatial Computing in Mobile Devices
(1st ed.). Norwood, MA: Artech House. p. 228.
ISBN
978-1-60807-565-2
. Retrieved
1 July
2014
.
- ^González, Ainhoa; Donnelly, Alison; Jones, Mike; Chrysoulakis, Nektarios; Lopes, Myriam (2012). "A decision-support system for sustainable urban metabolism in Europe".Environmental Impact Assessment Review.38:109–119.doi:10.1016/j.eiar.2012.06.007.
^
González, Ainhoa; Donnelly, Alison; Jones, Mike; Chrysoulakis, Nektarios; Lopes, Myriam (2012). "A decision-support system for sustainable urban metabolism in Europe".
Environmental Impact Assessment Review
.
38
:
109–
119.
doi
:
10.1016/j.eiar.2012.06.007
.

## Further reading

Further reading
[
edit
]

<!-- table omitted -->

This "
further reading
" section
may need cleanup
.
Please read the
editing guide
and help improve the section.
(
June 2014
)
(
Learn how and when to remove this message
)
- Abler, R., J. Adams, and P. Gould (1971)Spatial Organization–The Geographer's View of the World, Englewood Cliffs, NJ: Prentice-Hall.
Abler, R., J. Adams, and P. Gould (1971)
Spatial Organization–The Geographer's View of the World
, Englewood Cliffs, NJ: Prentice-Hall.
- Anselin, L. (1995) "Local indicators of spatial association – LISA".Geographical Analysis, 27, 93–115.
Anselin, L. (1995) "Local indicators of spatial association – LISA".
Geographical Analysis
, 27, 93–115
.
- Awange, Joseph; Paláncz, Béla (2016).Geospatial Algebraic Computations, Theory and Applications, Third Edition. New York: Springer.ISBN978-3-319-25463-0.
Awange, Joseph; Paláncz, Béla (2016).
Geospatial Algebraic Computations, Theory and Applications, Third Edition
. New York: Springer.
ISBN
978-3-319-25463-0
.
- Banerjee, Sudipto; Carlin, Bradley P.; Gelfand, Alan E. (2014),Hierarchical Modeling and Analysis for Spatial Data, Second Edition, Monographs on Statistics and Applied Probability (2nd ed.), Chapman and Hall/CRC,ISBN978-1-4398-1917-3
Banerjee, Sudipto; Carlin, Bradley P.; Gelfand, Alan E. (2014),
Hierarchical Modeling and Analysis for Spatial Data, Second Edition
, Monographs on Statistics and Applied Probability (2nd ed.), Chapman and Hall/CRC,
ISBN
978-1-4398-1917-3
- Benenson, I. and P. M. Torrens. (2004).Geosimulation: Automata-Based Modeling of Urban Phenomena.Wiley.
Benenson, I. and P. M. Torrens. (2004).
Geosimulation: Automata-Based Modeling of Urban Phenomena.
Wiley.
- Fotheringham, A. S., C. Brunsdon and M. Charlton (2000)Quantitative Geography: Perspectives on Spatial Data Analysis, Sage.
Fotheringham, A. S., C. Brunsdon and M. Charlton (2000)
Quantitative Geography: Perspectives on Spatial Data Analysis
, Sage.
- Fotheringham, A. S. and M. E. O'Kelly (1989)Spatial Interaction Models: Formulations and Applications, Kluwer Academic
Fotheringham, A. S. and M. E. O'Kelly (1989)
Spatial Interaction Models: Formulations and Applications
, Kluwer Academic
- Fotheringham, A. S.; Rogerson, P. A. (1993). "GIS and spatial analytical problems".International Journal of Geographical Information Systems.7:3–19.doi:10.1080/02693799308901936.
Fotheringham, A. S.; Rogerson, P. A. (1993). "GIS and spatial analytical problems".
International Journal of Geographical Information Systems
.
7
:
3–
19.
doi
:
10.1080/02693799308901936
.
- Goodchild, M. F. (1987). "A spatial analytical perspective on geographical information systems".International Journal of Geographical Information Systems.1(4):327–44.doi:10.1080/02693798708927820.
Goodchild, M. F. (1987). "A spatial analytical perspective on geographical information systems".
International Journal of Geographical Information Systems
.
1
(4):
327–
44.
doi
:
10.1080/02693798708927820
.
- MacEachren, A. M.and D. R. F. Taylor (eds.) (1994)Visualization in Modern Cartography, Pergamon.
MacEachren, A. M.
and D. R. F. Taylor (eds.) (1994)
Visualization in Modern Cartography
, Pergamon.
- Levine, N. (2010).CrimeStat: A Spatial Statistics Program for the Analysis of Crime Incident Locations. Version 3.3. Ned Levine & Associates, Houston, TX and the National Institute of Justice, Washington, DC. Ch. 1-17 + 2 update chapters
Levine, N. (2010).
CrimeStat: A Spatial Statistics Program for the Analysis of Crime Incident Locations
. Version 3.3. Ned Levine & Associates, Houston, TX and the National Institute of Justice, Washington, DC. Ch. 1-17 + 2 update chapters
- Miller, H. J. (2004). "Tobler's First Law and spatial analysis".Annals of the Association of American Geographers.94(2):284–289.Bibcode:2004AAAG...94..284M.doi:10.1111/j.1467-8306.2004.09402005.x.S2CID19172678.
Miller, H. J. (2004). "Tobler's First Law and spatial analysis".
Annals of the Association of American Geographers
.
94
(2):
284–
289.
Bibcode
:
2004AAAG...94..284M
.
doi
:
10.1111/j.1467-8306.2004.09402005.x
.
S2CID
19172678
.
- Miller, H. J. and J. Han (eds.) (2001)Geographic Data Mining and Knowledge Discovery, Taylor and Francis.
Miller, H. J. and J. Han (eds.) (2001)
Geographic Data Mining and Knowledge Discovery
, Taylor and Francis.
- O'Sullivan, D. and D. Unwin (2002)Geographic Information Analysis, Wiley.
O'Sullivan, D. and D. Unwin (2002)
Geographic Information Analysis
, Wiley.
- Parker, D. C.; Manson, S. M.;Janssen, M.A.; Hoffmann, M. J.; Deadman, P. (2003). "Multi-agent systems for the simulation of land-use and land-cover change: A review".Annals of the Association of American Geographers.93(2):314–337.Bibcode:2003AAAG...93..314P.CiteSeerX10.1.1.109.1825.doi:10.1111/1467-8306.9302004.S2CID130096094.
Parker, D. C.; Manson, S. M.;
Janssen, M.A.
; Hoffmann, M. J.; Deadman, P. (2003). "Multi-agent systems for the simulation of land-use and land-cover change: A review".
Annals of the Association of American Geographers
.
93
(2):
314–
337.
Bibcode
:
2003AAAG...93..314P
.
CiteSeerX
10.1.1.109.1825
.
doi
:
10.1111/1467-8306.9302004
.
S2CID
130096094
.
- White, R.; Engelen, G. (1997). "Cellular automata as the basis of integrated dynamic regional modelling".Environment and Planning B: Planning and Design.24(2):235–246.Bibcode:1997EnPlB..24..235W.doi:10.1068/b240235.S2CID62516646.
White, R.; Engelen, G. (1997). "Cellular automata as the basis of integrated dynamic regional modelling".
Environment and Planning B: Planning and Design
.
24
(2):
235–
246.
Bibcode
:
1997EnPlB..24..235W
.
doi
:
10.1068/b240235
.
S2CID
62516646
.
- Scheldeman, X. & van Zonneveld, M. (2010).Training Manual on Spatial Analysis of Plant Diversity and Distribution. Bioversity International.
Scheldeman, X. & van Zonneveld, M. (2010).
Training Manual on Spatial Analysis of Plant Diversity and Distribution
. Bioversity International.
- Fisher MM, Leung Y (2001) Geocomputational Modelling: techniques and applications. Springer Verlag, Berlin
Fisher MM, Leung Y (2001) Geocomputational Modelling: techniques and applications. Springer Verlag, Berlin
- Fotheringham, S; Clarke, G; Abrahart, B (1997). "Geocomputation and GIS".Transactions in GIS.2(3):199–200.doi:10.1111/j.1467-9671.1997.tb00010.x.S2CID205576122.
Fotheringham, S; Clarke, G; Abrahart, B (1997). "Geocomputation and GIS".
Transactions in GIS
.
2
(3):
199–
200.
doi
:
10.1111/j.1467-9671.1997.tb00010.x
.
S2CID
205576122
.
- Openshaw S and Abrahart RJ (2000) GeoComputation. CRC Press
Openshaw S and Abrahart RJ (2000) GeoComputation. CRC Press
- Diappi Lidia (2004) Evolving Cities: Geocomputation in Territorial Planning. Ashgate, England
Diappi Lidia (2004) Evolving Cities: Geocomputation in Territorial Planning. Ashgate, England
- Longley PA, Brooks SM, McDonnell R, Macmillan B (1998), Geocomputation, a primer. John Wiley and Sons, Chichester
Longley PA, Brooks SM, McDonnell R, Macmillan B (1998), Geocomputation, a primer. John Wiley and Sons, Chichester
- Ehlen, J; Caldwell, DR; Harding, S (2002). "GeoComputation: what is it?".Comput Environ and Urban Syst.26(4):257–265.Bibcode:2002CEUS...26..257E.doi:10.1016/s0198-9715(01)00047-3.
Ehlen, J; Caldwell, DR; Harding, S (2002). "GeoComputation: what is it?".
Comput Environ and Urban Syst
.
26
(4):
257–
265.
Bibcode
:
2002CEUS...26..257E
.
doi
:
10.1016/s0198-9715(01)00047-3
.
- Gahegan, M (1999). "What is Geocomputation?".Transactions in GIS.3(3):203–206.doi:10.1111/1467-9671.00017.hdl:2292/7257.S2CID44656909.
Gahegan, M (1999). "What is Geocomputation?".
Transactions in GIS
.
3
(3):
203–
206.
doi
:
10.1111/1467-9671.00017
.
hdl
:
2292/7257
.
S2CID
44656909
.
- Murgante B., Borruso G., Lapucci A. (2009) "Geocomputation and Urban Planning"Studies in Computational Intelligence, Vol. 176. Springer-Verlag, Berlin.
Murgante B., Borruso G., Lapucci A. (2009) "Geocomputation and Urban Planning"
Studies in Computational Intelligence
, Vol. 176. Springer-Verlag, Berlin.
- Reis, José P.; Silva, Elisabete A.; Pinho, Paulo (2016)."Spatial metrics to study urban patterns in growing and shrinking cities".Urban Geography.37(2):246–271.doi:10.1080/02723638.2015.1096118.S2CID62886095.
Reis, José P.; Silva, Elisabete A.; Pinho, Paulo (2016).
"Spatial metrics to study urban patterns in growing and shrinking cities"
.
Urban Geography
.
37
(2):
246–
271.
doi
:
10.1080/02723638.2015.1096118
.
S2CID
62886095
.
- Papadimitriou, F. (2002). "Modelling indicators and indices of landscape complexity: An approach using G.I.S".Ecological Indicators.2(1–2):17–25.Bibcode:2002EcInd...2...17P.doi:10.1016/S1470-160X(02)00052-3.
Papadimitriou, F. (2002). "Modelling indicators and indices of landscape complexity: An approach using G.I.S".
Ecological Indicators
.
2
(
1–
2):
17–
25.
Bibcode
:
2002EcInd...2...17P
.
doi
:
10.1016/S1470-160X(02)00052-3
.
- Fischer M., Leung Y. (2010) "GeoComputational Modelling: Techniques and Applications" Advances in Spatial Science. Springer-Verlag, Berlin.
Fischer M., Leung Y. (2010) "GeoComputational Modelling: Techniques and Applications" Advances in Spatial Science. Springer-Verlag, Berlin.
- Murgante B., Borruso G., Lapucci A. (2011) "Geocomputation, Sustainability and Environmental Planning"Studies in Computational Intelligence, Vol. 348. Springer-Verlag, Berlin.
Murgante B., Borruso G., Lapucci A. (2011) "Geocomputation, Sustainability and Environmental Planning"
Studies in Computational Intelligence
, Vol. 348. Springer-Verlag, Berlin.
- Tahmasebi, P.; Hezarkhani, A.; Sahimi, M. (2012). "Multiple-point geostatistical modeling based on the cross-correlation functions".Computational Geosciences.16(3):779–79742.Bibcode:2012CmpGe..16..779T.doi:10.1007/s10596-012-9287-1.S2CID62710397.
Tahmasebi, P.; Hezarkhani, A.; Sahimi, M. (2012). "Multiple-point geostatistical modeling based on the cross-correlation functions".
Computational Geosciences
.
16
(3):
779–
79742.
Bibcode
:
2012CmpGe..16..779T
.
doi
:
10.1007/s10596-012-9287-1
.
S2CID
62710397
.
- Geza, Tóth; Áron, Kincses; Zoltán, Nagy (2014).European Spatial Structure. LAP LAMBERT Academic Publishing.doi:10.13140/2.1.1560.2247.
Geza, Tóth; Áron, Kincses; Zoltán, Nagy (2014).
European Spatial Structure
. LAP LAMBERT Academic Publishing.
doi
:
10.13140/2.1.1560.2247
.

## External links

External links
[
edit
]
Library resources
about
Spatial analysis
- Resources in your library
Resources in your library
- Resources in other libraries
Resources in other libraries
Wikimedia Commons has media related to
Spatial data analysis
.

<!-- table omitted -->

- v
v
- t
t
- e
e
Visualization
of technical information
Fields
- Biological data visualization
Biological data visualization
- Chemical imaging
Chemical imaging
- Crime mapping
Crime mapping
- Data visualization
Data visualization
- Educational visualization
Educational visualization
- Flow visualization
Flow visualization
- Geovisualization
Geovisualization
- Information visualization
Information visualization
- Mathematical visualization
Mathematical visualization
- Medical imaging
Medical imaging
- Molecular graphics
Molecular graphics
- Product visualization
Product visualization
- Scientific visualization
Scientific visualization
- Social visualization
Social visualization
- Software visualization
Software visualization
- Technical drawing
Technical drawing
- User interface design
User interface design
- Visual analytics
Visual analytics
- Visual culture
Visual culture
- Volume visualization
Volume visualization
Image
types
- Chart
Chart
- Diagram
Diagram
- Engineering drawing
Engineering drawing
- Graph of a function
Graph of a function
- Ideogram
Ideogram
- Map
Map
- Photograph
Photograph
- Pictogram
Pictogram
- Plot
Plot
- Sankey diagram
Sankey diagram
- Schematic
Schematic
- Skeletal formula
Skeletal formula
- Statistical graphics
Statistical graphics
- Table
Table
- Technical drawings
Technical drawings
- Technical illustration
Technical illustration
People

<!-- table omitted -->

Pre-19th century
- Edmond Halley
Edmond Halley
- Charles-René de Fourcroy
Charles-René de Fourcroy
- Joseph Priestley
Joseph Priestley
- Gaspard Monge
Gaspard Monge
19th century
- Charles Dupin
Charles Dupin
- Adolphe Quetelet
Adolphe Quetelet
- André-Michel Guerry
André-Michel Guerry
- William Playfair
William Playfair
- August Kekulé
August Kekulé
- Charles Joseph Minard
Charles Joseph Minard
- Francis Amasa Walker
Francis Amasa Walker
- John Venn
John Venn
- Oliver Byrne
Oliver Byrne
- Matthew Sankey
Matthew Sankey
- Charles Booth
Charles Booth
- John Snow
John Snow
- Florence Nightingale
Florence Nightingale
- Karl Wilhelm Pohlke
Karl Wilhelm Pohlke
- Toussaint Loua
Toussaint Loua
- Francis Galton
Francis Galton
Early 20th century
- Edward Walter Maunder
Edward Walter Maunder
- Otto Neurath
Otto Neurath
- W. E. B. Du Bois
W. E. B. Du Bois
- Henry Gantt
Henry Gantt
- Arthur Lyon Bowley
Arthur Lyon Bowley
- Howard G. Funkhouser
Howard G. Funkhouser
- John B. Peddle
John B. Peddle
- Ejnar Hertzsprung
Ejnar Hertzsprung
- Henry Norris Russell
Henry Norris Russell
- Max O. Lorenz
Max O. Lorenz
- Fritz Kahn
Fritz Kahn
- Harry Beck
Harry Beck
- Erwin Raisz
Erwin Raisz
Mid 20th century
- Jacques Bertin
Jacques Bertin
- Rudolf Modley
Rudolf Modley
- Arthur H. Robinson
Arthur H. Robinson
- John Tukey
John Tukey
- Mary Eleanor Spear
Mary Eleanor Spear
- Edgar Anderson
Edgar Anderson
- Howard T. Fisher
Howard T. Fisher
Late 20th century
- Borden Dent
Borden Dent
- Nigel Holmes
Nigel Holmes
- William S. Cleveland
William S. Cleveland
- George G. Robertson
George G. Robertson
- Bruce H. McCormick
Bruce H. McCormick
- Catherine Plaisant
Catherine Plaisant
- Stuart Card
Stuart Card
- Pat Hanrahan
Pat Hanrahan
- Edward Tufte
Edward Tufte
- Ben Shneiderman
Ben Shneiderman
- Michael Friendly
Michael Friendly
- Howard Wainer
Howard Wainer
- Clifford A. Pickover
Clifford A. Pickover
- Lawrence J. Rosenblum
Lawrence J. Rosenblum
- Thomas A. DeFanti
Thomas A. DeFanti
- George Furnas
George Furnas
- Sheelagh Carpendale
Sheelagh Carpendale
- Cynthia Brewer
Cynthia Brewer
- Jock D. Mackinlay
Jock D. Mackinlay
- Alan MacEachren
Alan MacEachren
- David Goodsell
David Goodsell
- Kwan-Liu Ma
Kwan-Liu Ma
- Michael Maltz
Michael Maltz
- Leland Wilkinson
Leland Wilkinson
- Alfred Inselberg
Alfred Inselberg
Early 21st century
- Ben Fry
Ben Fry
- Jeffrey Heer
Jeffrey Heer
- Jessica Hullman
Jessica Hullman
- Daniel A. Keim
Daniel A. Keim
- Gordon Kindlmann
Gordon Kindlmann
- Aaron Koblin
Aaron Koblin
- Christopher R. Johnson
Christopher R. Johnson
- Manuel Lima
Manuel Lima
- David McCandless
David McCandless
- Mauro Martino
Mauro Martino
- John Maeda
John Maeda
- Miriah Meyer
Miriah Meyer
- Tamara Munzner
Tamara Munzner
- Ade Olufeko
Ade Olufeko
- Hanspeter Pfister
Hanspeter Pfister
- Hans Rosling
Hans Rosling
- Claudio Silva
Claudio Silva
- Moritz Stefaner
Moritz Stefaner
- Fernanda Viégas
Fernanda Viégas
- Martin Wattenberg
Martin Wattenberg
- Bang Wong
Bang Wong
- Hadley Wickham
Hadley Wickham
Related
topics
- Cartography
Cartography
- Chartjunk
Chartjunk
- Color coding
Color coding
- Computer graphicsin computer science
Computer graphics
- in computer science
in computer science
- CPK coloring
CPK coloring
- Graph drawing
Graph drawing
- Graphic design
Graphic design
- Graphic organizer
Graphic organizer
- Imaging
Imaging
- Information art
Information art
- Information graphics
Information graphics
- Information science
Information science
- Misleading graph
Misleading graph
- Neuroimaging
Neuroimaging
- Patent drawing
Patent drawing
- Scientific modelling
Scientific modelling
- Spatial analysis
Spatial analysis
- Visual perception
Visual perception
- Virtual unfolding
Virtual unfolding
- Volume rendering
Volume rendering

<!-- table omitted -->

Authority control databases
National
- United States
United States
- France
France
- BnF data
BnF data
- Czech Republic
Czech Republic
- Israel
Israel
Other
- Yale LUX
Yale LUX
NewPP limit report
Parsed by mw‐web.codfw.main‐7c9cbc57bf‐mwq9x
Cached time: 20260624134232
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, prevent‐selective‐update, show‐toc]
CPU time usage: 0.859 seconds
Real time usage: 0.984 seconds
Preprocessor visited node count: 7266/1000000
Revision size: 66264/2097152 bytes
Post‐expand include size: 270536/2097152 bytes
Template argument size: 10430/2097152 bytes
Highest expansion depth: 14/100
Expensive parser function count: 16/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 276674/5000000 bytes
Lua time usage: 0.550/10.000 seconds
Lua memory usage: 7313009/52428800 bytes
Number of Wikibase entities loaded: 1/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  780.960      1 -total
 38.67%  302.010      1 Template:Reflist
 26.83%  209.497     47 Template:Cite_journal
 17.88%  139.609      9 Template:Excerpt
  9.39%   73.351     12 Template:Citation_needed
  9.19%   71.786      8 Template:Cite_book
  7.38%   57.597     12 Template:Fix
  5.55%   43.335      1 Template:Short_description
  5.19%   40.503      1 Template:Authority_control
  5.06%   39.527      2 Template:Side_box
Render ID 8cb9e53a-6fd2-11f1-a516-61e7f0efb22e
Saved in parser cache with key enwiki:pcache:3190431:|#|:idhash:canonical and timestamp 20260624134232 and revision id 1360738385. Rendering was triggered because: unknown
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Spatial_analysis&oldid=1360738385#Geospatial_and_Hydrospatial_analysis
"
Category
:
- Spatial analysis
Spatial analysis
Hidden categories:
- Webarchive template wayback links
Webarchive template wayback links
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata
- All articles with unsourced statements
All articles with unsourced statements
- Articles with unsourced statements from July 2021
Articles with unsourced statements from July 2021
- Articles with excerpts
Articles with excerpts
- Articles with unsourced statements from February 2013
Articles with unsourced statements from February 2013
- Articles with unsourced statements from December 2010
Articles with unsourced statements from December 2010
- Wikipedia spam cleanup from June 2014
Wikipedia spam cleanup from June 2014
- Wikipedia further reading cleanup
Wikipedia further reading cleanup
- Commons category link is locally defined
Commons category link is locally defined