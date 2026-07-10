<!-- source: https://pro.arcgis.com/en/pro-app/latest/help/mapping/layer-properties/layers.htm -->
# Layers | ArcGIS Pro documentation

> Source: https://pro.arcgis.com/en/pro-app/latest/help/mapping/layer-properties/layers.htm

##### Table of Contents

Table of Contents

# Layers

Layers
In ArcGIS, layers are collections of geographic data. Layers reference a data source, and if ArcGIS Pro interprets data as spatial, the data's properties and attributes specify how the layer draws on a map, scene, or layout. Data gathered in a layer is represented with points, lines, shapes (polygons), or surfaces. You then use symbols, text, graphics, and images to visualize the layer's data.

In ArcGIS, layers are collections of geographic data. Layers reference a data source, and if ArcGIS Pro interprets data as spatial, the data's properties and attributes specify how the layer draws on a map, scene, or layout. Data gathered in a layer is represented with points, lines, shapes (polygons), or surfaces. You then use symbols, text, graphics, and images to visualize the layer's data.
Some layers are automatically added to maps when you create the map. Most of the time, however, you manually add layers to a map. Most maps, scenes, and layouts are assembled with multiple layers. The layers are displayed in a particular order, called the drawing order, which is shown in the map'sContentspane. Layers listed at the bottom appear first but always draw below the layers above them.

Some layers are automatically added to maps when you create the map. Most of the time, however, you manually add layers to a map. Most maps, scenes, and layouts are assembled with multiple layers. The layers are displayed in a particular order, called the drawing order, which is shown in the map's
Contents
pane
. Layers listed at the bottom appear first but always draw below the layers above them.
Oncelayers are addedto a map or scene, you can change how a layer issymbolized,labeled,scaled, and arranged. You can usespatial analysis toolson layers to study the data's characteristics,filter layers using queriesordisplay filters, andextrude layer features into 3D.

Once
layers are added
to a map or scene, you can change how a layer is
symbolized
,
labeled
,
scaled
, and arranged. You can use
spatial analysis tools
on layers to study the data's characteristics,
filter layers using queries
or
display filters
, and
extrude layer features into 3D
.
Layers are reusable and flexible. For example, you can use the same imagery layer in every map you create. If the location of the data changes, however, thedata source path must be updated.

Layers are reusable and flexible. For example, you can use the same imagery layer in every map you create. If the location of the data changes, however, the
data source path must be updated
.

## Types of layers

Types of layers
There are many differenttypes of datathat are represented in ArcGIS Pro as layers. Layers typically comprise vector (feature), raster, or 3D data. The type of layer depends on the type of data you have, its underlying structure, and some other variables.

There are many different
types of data
that are represented in ArcGIS Pro as layers. Layers typically comprise vector (feature), raster, or 3D data. The type of layer depends on the type of data you have, its underlying structure, and some other variables.
To determine the layer type, click it in theContentspane. The layer type contextual tab set appearson the ribbon.

To determine the layer type, click it in the
Contents
pane. The layer type contextual tab set appears
on the ribbon
.

### Feature layers

Feature layers
Feature layersrepresent geographic objects as vectors and can be symbolized in a variety of ways depending on their attribution. Feature layer data referencesfeature classes, which are stored ingeodatabases.

Feature layers
represent geographic objects as vectors and can be symbolized in a variety of ways depending on their attribution. Feature layer data references
feature classes
, which are stored in
geodatabases
.
Because they comprise vectors, the features can besymbolized with the same symbolor withunique symbols based on valuesfrom one or more attribute fields. In the case of quantitative data, commonly used for thematic mapping, a layer can be represented withdefined classification ranges. Further symbology options include representing features asproportional symbols,charts, ordot densitymaps.

Because they comprise vectors, the features can be
symbolized with the same symbol
or with
unique symbols based on values
from one or more attribute fields. In the case of quantitative data, commonly used for thematic mapping, a layer can be represented with
defined classification ranges
. Further symbology options include representing features as
proportional symbols
,
charts
, or
dot density
maps.
There are other types of feature layers, such asstream layers,map notes layers, andaggregated feature layers, that bin or cluster features and map the results based on their attributes.

There are other types of feature layers, such as
stream layers
,
map notes layers
, and
aggregated feature layers
, that bin or cluster features and map the results based on their attributes.

### Raster layers

Raster layers
Raster layersreference rasters or images as their data source. They can be visualized as a single raster dataset or as amosaic layerthat references a mosaic dataset that manages large collections of raster data.A variety of display typesare available for visualizing raster data, depending on the raster band count, the presence of a color map, and whether the raster represents unique value data. As with vector layers, rasters can be classified using a variety of standard classification techniques. A variety ofimage analysis capabilitiesare available for performing visual analysis of rasters, including processing functions.

Raster layers
reference rasters or images as their data source. They can be visualized as a single raster dataset or as a
mosaic layer
that references a mosaic dataset that manages large collections of raster data.
A variety of display types
are available for visualizing raster data, depending on the raster band count, the presence of a color map, and whether the raster represents unique value data. As with vector layers, rasters can be classified using a variety of standard classification techniques. A variety of
image analysis capabilities
are available for performing visual analysis of rasters, including processing functions.

### Scene layers

Scene layers
If the layer has a three-dimensional aspect, it may be used to create ascene layer. Scene layers are cached to optimize the display of 3D data, and the cache is created as part of a scene layer package. For example, a building scene layer may reference data from feature classes to render the model of a building. Depending on the type of data, scene layers can be queried, symbolized, labeled and edited.

If the layer has a three-dimensional aspect, it may be used to create a
scene layer
. Scene layers are cached to optimize the display of 3D data, and the cache is created as part of a scene layer package. For example, a building scene layer may reference data from feature classes to render the model of a building. Depending on the type of data, scene layers can be queried, symbolized, labeled and edited.

### Service layers

Service layers
Maps and scenes can contain layers that reference map, feature, tile, vector tile, and OGC services. The majority of service types either have prerendered content or render the content on the server side, which allows for additional capabilities. For example, map image layers can be enabled to support dynamic server-side updates. Feature services allow vector features to be drawn on the client side with the full set of ArcGIS symbology.

Maps and scenes can contain layers that reference map, feature, tile, vector tile, and OGC services. The majority of service types either have prerendered content or render the content on the server side, which allows for additional capabilities. For example, map image layers can be enabled to support dynamic server-side updates. Feature services allow vector features to be drawn on the client side with the full set of ArcGIS symbology.
Common types of service layers include:

Common types of service layers include:
- Map image layers
Map image layers
- Web feature layers
Web feature layers
- Web tile layers
Web tile layers
- Web scene layers
Web scene layers
- Vector tile layers
Vector tile layers
- OGC service layers
OGC service layers

### Other layer types

Other layer types
Most layers are one of the above types. Because GIS data varies in organization and complexity, there are many more types. For example, agroup layerrefers to a collection of layers. Some other common types of layers include:

Most layers are one of the above types. Because GIS data varies in organization and complexity, there are many more types. For example, a
group layer
refers to a collection of layers. Some other common types of layers include:
- Query layer—Uses SQL queries to access and reference spatial and nonspatial database tables
Query layer—Uses SQL queries to access and reference spatial and nonspatial database tables

Query layer
—Uses SQL queries to access and reference spatial and nonspatial database tables
- Selection layer—References a subset of features from an existing layer
Selection layer—References a subset of features from an existing layer

Selection layer
—References a subset of features from an existing layer
- Subtype layer—Symbolizes a subtype in a feature class or feature service, as part of a subtype group layer
Subtype layer—Symbolizes a subtype in a feature class or feature service, as part of a subtype group layer

Subtype layer
—Symbolizes a subtype in a feature class or feature service, as part of a subtype group layer
- Voxel layer—A type of 3D grid-based layer for displaying spatiotemporal data
Voxel layer—A type of 3D grid-based layer for displaying spatiotemporal data

Voxel layer
—A type of 3D grid-based layer for displaying spatiotemporal data
- Graphics layer—Represents geographic objects but does not reference a dataset
Graphics layer—Represents geographic objects but does not reference a dataset

Graphics layer
—Represents geographic objects but does not reference a dataset
- Catalog layer—A collection (catalog) of references to multiple layers, datasets, and services
Catalog layer—A collection (catalog) of references to multiple layers, datasets, and services

Catalog layer
—A collection (catalog) of references to multiple layers, datasets, and services
- Stream layer—References real-time observations and draws the changes
Stream layer—References real-time observations and draws the changes

Stream layer
—References real-time observations and draws the changes

## Manage layers

Manage layers
Layers are managed from theContentspane. You can turn layer drawing on and off from there, reorder them, andgroupthem as needed.

Layers are managed from the
Contents
pane
. You can turn layer drawing on and off from there, reorder them, and
group
them as needed.

### Manage layers in scenes

Manage layers in scenes
Maps draw layers in 2D.Scenesdraw both 2D and 3D layers and are organized into 2D and 3D layers in theContentspane. To move a layer from one category to another, click the layer name in theContentspane and drag it into the other category. If the scene includesKML data, a KML category is also listed.

Maps draw layers in 2D.
Scenes
draw both 2D and 3D layers and are organized into 2D and 3D layers in the
Contents
pane. To move a layer from one category to another, click the layer name in the
Contents
pane and drag it into the other category. If the scene includes
KML data
, a KML category is also listed.
In scenes, the layers in the2D Layerscategory are drawn as though draped over a surface. Symbols in 2D layers are drawn and configured in a two-dimensional context.

In scenes, the layers in the
2D Layers
category are drawn as though draped over a surface. Symbols in 2D layers are drawn and configured in a two-dimensional context.
Layers in the3D Layerscategory have additional capabilities, such as vertical extrusion. Symbols in 3D layers are drawn and configured with three-dimensional properties. When a layer is in 3D, it renders its geometry separately from the rest of the scene. This means that polygons can flicker or stitch with other content in the scene. This display conflict is especially common with ground surface meshes, which are always changing to reflect the best level of detail for the current view location.

Layers in the
3D Layers
category have additional capabilities, such as vertical extrusion. Symbols in 3D layers are drawn and configured with three-dimensional properties. When a layer is in 3D, it renders its geometry separately from the rest of the scene. This means that polygons can flicker or stitch with other content in the scene. This display conflict is especially common with ground surface meshes, which are always changing to reflect the best level of detail for the current view location.
You can improve the display of the polygons byextruding the layerto create volumes orchanging the depth priorityto separate (vertically) the polygons from other content.

You can improve the display of the polygons by
extruding the layer
to create volumes or
changing the depth priority
to separate (vertically) the polygons from other content.

### Navigate and interact with layers

Navigate and interact with layers
Explore layers in a map by panning around them to see different areas and zooming in and out to see those areas at different scales. To learn how to navigate a map, seeKeyboard shortcuts for navigation. If comparing two or more maps, you canlink two or more open maps togetherso they stay in sync as you navigate. You can also explore layers bymeasuringdistances and areas or by viewing the data throughtimeor othervariable ranges.

Explore layers in a map by panning around them to see different areas and zooming in and out to see those areas at different scales. To learn how to navigate a map, see
Keyboard shortcuts for navigation
. If comparing two or more maps, you can
link two or more open maps together
so they stay in sync as you navigate. You can also explore layers by
measuring
distances and areas or by viewing the data through
time
or other
variable ranges
.
To view the ways you can interact with a layer, right-click its name in theContentspane. The context menu includes a variety of tools and options for your layer. For example, you can create aselection layerfrom a selection of features to work on only those features in a separate layer. You can also click the tabs in theContentspane to list layers according to various properties, and check or uncheck the check boxes to control their properties.

To view the ways you can interact with a layer, right-click its name in the
Contents
pane. The context menu includes a variety of tools and options for your layer. For example, you can create a
selection layer
from a selection of features to work on only those features in a separate layer. You can also click the tabs in the
Contents
pane to list layers according to various properties, and check or uncheck the check boxes to control their properties.

### Set layer properties

Set layer properties
In addition to interacting with the layer, layer management involvessetting layer properties. For example, if the layer's dataset contains information about the time the data was recorded, the layer can be enabled to use time-based data, which allows you to change the way the layer draws. Right-click a layer in theContentspane and clickPropertiesto view theLayer Propertiesdialog box.

In addition to interacting with the layer, layer management involves
setting layer properties
. For example, if the layer's dataset contains information about the time the data was recorded, the layer can be enabled to use time-based data, which allows you to change the way the layer draws. Right-click a layer in the
Contents
pane and click
Properties
to view the
Layer Properties
dialog box.

##### Legacy:

Legacy:
Some properties in ArcMap, such assymbologyand labeling, are set in theLayer Propertiesdialog box. In ArcGIS Pro, depending on the type of layer, you can find these and other properties from the ribbon.

Some properties in ArcMap, such as
symbology
and labeling, are set in the
Layer Properties
dialog box. In ArcGIS Pro, depending on the type of layer, you can find these and other properties from the ribbon.
Other properties, such asspecifying the coordinate systemandlayer clipping, are properties of the map, not of layers. To access these properties, right-click the map in theContentspane and clickProperties.

Other properties, such as
specifying the coordinate system
and
layer clipping
, are properties of the map, not of layers. To access these properties, right-click the map in the
Contents
pane and click
Properties
.

### Work with layer attributes

Work with layer attributes
Layers may reference spatial and nonspatial information in tables, called attributes. For those layer types, you can view and work with attributes in the layer'sattribute table. To open the attribute table, on the layer's contextualDatatab, in theTablegroup, clickAttribute Table.

Layers may reference spatial and nonspatial information in tables, called attributes. For those layer types, you can view and work with attributes in the layer's
attribute table
. To open the attribute table, on the layer's contextual
Data
tab, in the
Table
group, click
Attribute Table
.
In the attribute table, you can select and review data, find features on the map, and edit attribute values. Click the table window's options menu to search records, add joins or relates, and export the table. When you select one or more records in the table they are selected on the map and vice versa.

In the attribute table, you can select and review data, find features on the map, and edit attribute values. Click the table window's options menu to search records, add joins or relates, and export the table. When you select one or more records in the table they are selected on the map and vice versa.
Not all information in the layer can be visualized through labels and symbology at one time. To discover additional attribution, you canconfigure pop-upsto display information about features as they are interactively queried. ArcGIS Pro uses the same pop-up style as other ArcGIS applications, so maps can be designed for presenting information before sharing and publishing them.

Not all information in the layer can be visualized through labels and symbology at one time. To discover additional attribution, you can
configure pop-ups
to display information about features as they are interactively queried. ArcGIS Pro uses the same pop-up style as other ArcGIS applications, so maps can be designed for presenting information before sharing and publishing them.

### Share layers

Share layers
A layer can be saved as a layer file(.lyrx)or saved with its data as a layer package(.lpkx)and shared with other members of your organization. To save a layer file, on theSharetab, in theSave Asgroup, clickLayer File. To save a layer package, in thePackagegroup, clickLayer. When you add the layer file or package to another map, it draws exactly as it was saved.

A layer can be saved as a layer file

```
(.lyrx)
```

(.lyrx)
or saved with its data as a layer package

```
(.lpkx)
```

(.lpkx)
and shared with other members of your organization. To save a layer file, on the
Share
tab, in the
Save As
group, click
Layer File
. To save a layer package, in the
Package
group, click
Layer
. When you add the layer file or package to another map, it draws exactly as it was saved.
When layers are shared to the web, they are called web layers. If the data source is accessible, you can publish and share most layer types to your organization's portal as web layers. To share your data as a web layer, in theShare Asgroup, clickWeb Layer. To learn more about web layers, seeIntroduction to sharing web layers.

When layers are shared to the web, they are called web layers. If the data source is accessible, you can publish and share most layer types to your organization's portal as web layers. To share your data as a web layer, in the
Share As
group, click
Web Layer
. To learn more about web layers, see
Introduction to sharing web layers
.

##### Note:

Note:
Layer files and packages created in ArcGIS Desktop have.lyrand.lpkextensions, respectively. These files can be read in ArcGIS Pro, but you cannot save the layer with the.lyror.lpkextension.

Layer files and packages created in ArcGIS Desktop have

```
.lyr
```

.lyr
and

```
.lpk
```

.lpk
extensions, respectively. These files can be read in ArcGIS Pro, but you cannot save the layer with the

```
.lyr
```

.lyr
or

```
.lpk
```

.lpk
extension.

## Common layer tasks

Common layer tasks
The following table lists common operations for using layers in ArcGIS Pro:

The following table lists common operations for using layers in ArcGIS Pro:

<!-- table omitted -->

Common task
Additional information

Additional information
Add a layer to ArcGIS Pro

Add a layer to ArcGIS Pro
- Add data to a project
Add data to a project

Add data to a project
- Add layers to a map or scene
Add layers to a map or scene

Add layers to a map or scene
- Add x,y coordinate data as a layer
Add x,y coordinate data as a layer

Add x,y coordinate data as a layer
Reference other data to a layer

Reference other data to a layer
- Introduction to joins and relates
Introduction to joins and relates

Introduction to joins and relates
- Repair broken data sources for layers and tables
Repair broken data sources for layers and tables

Repair broken data sources for layers and tables
Symbolize a layer
- Symbolize feature layers
Symbolize feature layers

Symbolize feature layers
- Change the symbology of imagery
Change the symbology of imagery

Change the symbology of imagery
Label a layer
- Labeling basics
Labeling basics
Group layers together

Group layers together
- Work with group layers
Work with group layers
Create and edit layer features

Create and edit layer features
- Editing in ArcGIS Pro
Editing in ArcGIS Pro

Editing in ArcGIS Pro
- Introduction to 2D and 3D features
Introduction to 2D and 3D features

Introduction to 2D and 3D features
Work with a layer's attribute table

Work with a layer's attribute table
- Common table and attribute tasks
Common table and attribute tasks
Query and filter a layer's data

Query and filter a layer's data
- Filter features with definition queries
Filter features with definition queries

Filter features with definition queries
- Query layers
Query layers
- Use display filters
Use display filters
Change a layer's projection

Change a layer's projection
- Coordinate systems, projections, and transformations
Coordinate systems, projections, and transformations
Work with a layer in 3D

Work with a layer in 3D
- Configure a scene for 3D editing
Configure a scene for 3D editing

## Related topics

Related topics
- Feature layers
Feature layers
- Add layers to a map or scene
Add layers to a map or scene

Add layers to a map or scene
- Maps
Maps