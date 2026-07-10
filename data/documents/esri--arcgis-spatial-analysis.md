<!-- source: https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/an-overview-of-the-spatial-analyst-toolbox.htm -->
# An overview of the Spatial Analyst toolbox | ArcGIS Pro documentation

> Source: https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/an-overview-of-the-spatial-analyst-toolbox.htm

##### Table of Contents

Table of Contents

# An overview of the Spatial Analyst toolbox

An overview of the Spatial Analyst toolbox
Available with Spatial Analyst license.

Available with Spatial Analyst license.
The Spatial Analyst toolbox provides a set of spatial analysis and modeling tools for raster (cell-based) and feature (vector) data.

The Spatial Analyst toolbox provides a set of spatial analysis and modeling tools for raster (cell-based) and feature (vector) data.
The capabilities of Spatial Analyst are broken down into categories or groups of related functionality. Knowing the categories will help you identify which particular tool to use. The table at the end of this section lists all the available toolsets with a description of the capabilities offered by the tools in each.

The capabilities of Spatial Analyst are broken down into categories or groups of related functionality. Knowing the categories will help you identify which particular tool to use. The table at the end of this section lists all the available toolsets with a description of the capabilities offered by the tools in each.
There are several ways to access Spatial Analyst functionality. With geoprocessing, operations in the Spatial Analyst toolbox can be performed through aTooldialog box,Python(either at an interactive command line interface or with a script), or aModel. Traditional operations and workflows usingmap algebracan also be performed in the Python environment. There is also aRaster Calculatoravailable for entering simple map algebra expressions that generate an output raster.

There are several ways to access Spatial Analyst functionality. With geoprocessing, operations in the Spatial Analyst toolbox can be performed through a
Tool
dialog box,
Python
(either at an interactive command line interface or with a script), or a
Model
. Traditional operations and workflows using
map algebra
can also be performed in the Python environment. There is also a
Raster Calculator
available for entering simple map algebra expressions that generate an output raster.
For most tools, when the output is a raster, the location and name you specify for the output raster determines the format in which it is created. When not saving to a geodatabase, specify.tiffor a TIFF file format,.crffor a CRF file format,.imgfor an ERDAS IMAGINE file format, or no extension for an Esri Grid raster format.  SeeOutput raster formats and namesfor more information.

For most tools, when the output is a raster, the location and name you specify for the output raster determines the format in which it is created. When not saving to a geodatabase, specify

```
.tif
```

.tif
for a TIFF file format,

```
.crf
```

.crf
for a CRF file format,

```
.img
```

.img
for an ERDAS IMAGINE file format, or no extension for an Esri Grid raster format.  See
Output raster formats and names
for more information.
See theSpatial Analyst extensionhelp to learn more about the product, its capabilities, and how to perform analysis with it.

See the
Spatial Analyst extension
help to learn more about the product, its capabilities, and how to perform analysis with it.

## Spatial Analyst toolsets

Spatial Analyst toolsets
The functional categories of Spatial Analyst are identified below.

The functional categories of Spatial Analyst are identified below.

<!-- table omitted -->

Toolset
Description
Conditional
The Conditional tools allow you to control the output values based on the conditions placed on the input values. The conditions that can be applied are of two types: queries on the attributes or a condition based on the position of the conditional statement in a list.

The Conditional tools allow you to control the output values based on the conditions placed on the input values. The conditions that can be applied are of two types: queries on the attributes or a condition based on the position of the conditional statement in a list.
Density
The Density toolset contains tools that calculate the density of input features within a neighborhood around each output raster cell.

The Density toolset contains tools that calculate the density of input features within a neighborhood around each output raster cell.
Distance
The Distance tools allow you to perform analysis that accounts for either straight-line (Euclidean) distance or weighted distance. Distance can be weighted by a simple cost (friction) surface or in ways that account for vertical and horizontal restrictions to movement.

The Distance tools allow you to perform analysis that accounts for either straight-line (Euclidean) distance or weighted distance. Distance can be weighted by a simple cost (friction) surface or in ways that account for vertical and horizontal restrictions to movement.
Extraction
The Extraction tools allow you to extract a subset of cells from a raster by either the cells' attributes or their spatial location. You can also obtain the cell values for specific locations as an attribute in a point feature class or as a table.

The Extraction tools allow you to extract a subset of cells from a raster by either the cells' attributes or their spatial location. You can also obtain the cell values for specific locations as an attribute in a point feature class or as a table.
Generalization
The generalization analysis tools are used to either clean up small erroneous data in the raster or generalize the data to get rid of unnecessary detail for a more general analysis.

The generalization analysis tools are used to either clean up small erroneous data in the raster or generalize the data to get rid of unnecessary detail for a more general analysis.
Groundwater
The Groundwater tools can be used to perform rudimentary advection-dispersion modeling of constituents in groundwater flow. The following topics provide background information on the theoretical aspects of the tools as well as some examples of their implementation.

The Groundwater tools can be used to perform rudimentary advection-dispersion modeling of constituents in groundwater flow. The following topics provide background information on the theoretical aspects of the tools as well as some examples of their implementation.
The Groundwater tools can be applied individually or used in sequence to model and analyze groundwater flow.

The Groundwater tools can be applied individually or used in sequence to model and analyze groundwater flow.
Hydrology
The Hydrology tools are used to model the flow of water across a surface.

The Hydrology tools are used to model the flow of water across a surface.
The Hydrology tools can be applied individually or used in sequence to create a stream network or delineate watersheds.

The Hydrology tools can be applied individually or used in sequence to create a stream network or delineate watersheds.
Interpolation
The Interpolation tools create a continuous (or prediction) surface from sampled point values.

The Interpolation tools create a continuous (or prediction) surface from sampled point values.
The continuous surface representation of a raster dataset represents some measure, such as the height, concentration, or magnitude (for example, elevation, acidity, or noise level). Surface interpolation tools make predictions from sample measurements for all locations in an output raster dataset, whether or not a measurement has been taken at the location.

The continuous surface representation of a raster dataset represents some measure, such as the height, concentration, or magnitude (for example, elevation, acidity, or noise level). Surface interpolation tools make predictions from sample measurements for all locations in an output raster dataset, whether or not a measurement has been taken at the location.
Local
The Local tools are those where the value at each cell location on the output raster is a function of the values from all the inputs at that location.

The Local tools are those where the value at each cell location on the output raster is a function of the values from all the inputs at that location.
With the local tools, you can combine the input rasters, calculate a statistic on them, or evaluate a criterion for each cell on the output raster based on the values of each cell from multiple input rasters.

With the local tools, you can combine the input rasters, calculate a statistic on them, or evaluate a criterion for each cell on the output raster based on the values of each cell from multiple input rasters.
Map Algebra
Map algebra is a way to perform spatial analysis by creating expressions in an algebraic language. With theRaster Calculatortool, you can create and run map algebra expressions that output a raster dataset.

Map algebra is a way to perform spatial analysis by creating expressions in an algebraic language. With the
Raster Calculator
tool, you can create and run map algebra expressions that output a raster dataset.
Math (general)
The general Math tools apply a mathematical function to the input. These tools fall into several categories. The arithmetic tools perform basic mathematical operations, such as addition and multiplication. There are tools that perform various types of exponentiation operations, which includes exponentials and logarithms in addition to the basic power operations. The remaining tools are used either for sign conversion or for conversion between integer and floating point data types.

The general Math tools apply a mathematical function to the input. These tools fall into several categories. The arithmetic tools perform basic mathematical operations, such as addition and multiplication. There are tools that perform various types of exponentiation operations, which includes exponentials and logarithms in addition to the basic power operations. The remaining tools are used either for sign conversion or for conversion between integer and floating point data types.
Math Bitwise
The bitwise math tools compute on the binary representation of the input values.

The bitwise math tools compute on the binary representation of the input values.
Math Logical
The Logical Math tools evaluate the values of the inputs and determine the output values based on Boolean logic. The tools are grouped into four main categories: Boolean, Combinatorial, Logical, and Relational.

The Logical Math tools evaluate the values of the inputs and determine the output values based on Boolean logic. The tools are grouped into four main categories: Boolean, Combinatorial, Logical, and Relational.
Math Trigonometric
Trigonometric Math tools perform various trigonometric calculations on the values in an input raster.

Trigonometric Math tools perform various trigonometric calculations on the values in an input raster.
Multidimensional Analysis

Multidimensional Analysis
The tools in the Multidimensional Analysis toolset allow you to perform analysis on scientific raster data across multiple variables and dimensions.

The tools in the Multidimensional Analysis toolset allow you to perform analysis on scientific raster data across multiple variables and dimensions.
Multivariate
Multivariate statistical analysis allows the exploration of relationships among many different types of attributes. There are two types of multivariate analysis available: Classification (both Supervised and Unsupervised) and Principal Component Analysis (PCA).

Multivariate statistical analysis allows the exploration of relationships among many different types of attributes. There are two types of multivariate analysis available: Classification (both Supervised and Unsupervised) and Principal Component Analysis (PCA).
Neighborhood
Neighborhood tools create output values for each cell location based on the location value and the values identified in a specified neighborhood. The neighborhood type can be either moving or search radius.

Neighborhood tools create output values for each cell location based on the location value and the values identified in a specified neighborhood. The neighborhood type can be either moving or search radius.
Overlay
Overlay analysis tools allow you to apply weights to several input layers, combine them into a single output, and subject to specifications of distribution and shape, identify preferred locations within that result. These tools are commonly used for suitability modeling.

Overlay analysis tools allow you to apply weights to several input layers, combine them into a single output, and subject to specifications of distribution and shape, identify preferred locations within that result. These tools are commonly used for suitability modeling.
Proximity
Proximity analysis allows you to partition space into distinct zones of influence by balancing proximity with feature specific weights.

Proximity analysis allows you to partition space into distinct zones of influence by balancing proximity with feature specific weights.
Raster Creation
The Raster Creation tools generate new rasters in which the output values are based on a constant or a statistical distribution.

The Raster Creation tools generate new rasters in which the output values are based on a constant or a statistical distribution.
Reclass
The Reclass tools provide a variety of methods that allow you to reclassify or change input cell values to alternative values.

The Reclass tools provide a variety of methods that allow you to reclassify or change input cell values to alternative values.
Segmentation and Classification

Segmentation and Classification
With the segmentation and classification tools, you can prepare segmented rasters to use in creating classified raster datasets.

With the segmentation and classification tools, you can prepare segmented rasters to use in creating classified raster datasets.
Solar Radiation
The solar radiation analysis tools allow you to map and analyze the effects of the sun over a geographic area for specific time periods.

The solar radiation analysis tools allow you to map and analyze the effects of the sun over a geographic area for specific time periods.
Surface
With the Surface tools, you can quantify and visualize a terrain landform represented by a digital elevation model.

With the Surface tools, you can quantify and visualize a terrain landform represented by a digital elevation model.
Zonal
The Zonal tools allow you to perform analysis when the output is a result of computations performed on all cells that belong to each input zone. A zone can be defined as a single area of a particular value, but it can also be composed of multiple disconnected elements, or regions, all having the same value. Zones can be defined by raster or feature datasets. Rasters must be of integer type, and features must have an integer or string attribute field.

The Zonal tools allow you to perform analysis when the output is a result of computations performed on all cells that belong to each input zone. A zone can be defined as a single area of a particular value, but it can also be composed of multiple disconnected elements, or regions, all having the same value. Zones can be defined by raster or feature datasets. Rasters must be of integer type, and features must have an integer or string attribute field.
Spatial Analyst geoprocessing toolsets

Spatial Analyst geoprocessing toolsets

## Related topics

Related topics
- A complete listing of the Spatial Analyst tools
A complete listing of the Spatial Analyst tools