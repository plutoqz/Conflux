<!-- source: https://developers.arcgis.com/python/latest/guide/overview-of-the-arcgis-api-for-python/ -->
# Overview of the ArcGIS API for Python | ArcGIS API for Python | Esri Developer

> Source: https://developers.arcgis.com/python/latest/guide/overview-of-the-arcgis-api-for-python/

The ArcGIS API for Python is a powerful, modern and easy to use Pythonic library to perform GIS visualization and analysis, spatial data management and GIS system administration tasks that can run both interactively, and using scripts.

The ArcGIS API for Python is a powerful, modern and easy to use Pythonic library to perform GIS visualization and analysis, spatial data management and GIS system administration tasks that can run both interactively, and using scripts.

## A Pythonic GIS API

A Pythonic GIS API
The ArcGIS API for Python provides a pythonic representation of a GIS. A pythonic API is one which corresponds to Python best practices in its design and uses standard Python constructs and data structures with clean, readable idioms. The API makes it easy and natural for a Python programmer to use ArcGIS, and conversely, an ArcGIS user to script and automate their GIS.

The ArcGIS API for Python provides a pythonic representation of a GIS. A pythonic API is one which corresponds to Python best practices in its design and uses standard Python constructs and data structures with clean, readable idioms. The API makes it easy and natural for a Python programmer to use ArcGIS, and conversely, an ArcGIS user to script and automate their GIS.
The ArcGIS API for Python is implemented using the online and on-premises web GIS platform provided by ArcGIS Online and ArcGIS Enterprise respectively. The API has Python modules, classes, functions, and types for managing and working with elements of the ArcGIS platform information model.

The ArcGIS API for Python is implemented using the online and on-premises web GIS platform provided by ArcGIS Online and ArcGIS Enterprise respectively. The API has Python modules, classes, functions, and types for managing and working with elements of the ArcGIS platform information model.

## Architecture of the API

Architecture of the API
The API is distributed as thearcgispackage via conda and pip. Within thearcgispackage, which represents the generic GIS model, functionality is organized into a number of different modules that makes it simple to use and understand. Each module has a handful of types and functions that are focused towards one aspect of the GIS.

The API is distributed as the

```
arcgis
```

arcgis
package via conda and pip. Within the

```
arcgis
```

arcgis
package, which represents the generic GIS model, functionality is organized into a number of different modules that makes it simple to use and understand. Each module has a handful of types and functions that are focused towards one aspect of the GIS.
This diagram below depicts the modules present in the API.

This diagram below depicts the modules present in the API.
Thegismodule is the most important and provides the entry point into the GIS. It lets you manage users, groups and content in the GIS. GIS admins spend a lot of time on this module.

The

```
gis
```

gis
module is the most important and provides the entry point into the GIS. It lets you manage users, groups and content in the GIS. GIS admins spend a lot of time on this module.
The modules in green are used to access the various spatial capabilities or geographic datasets in the GIS. These modules include a family of geoprocessing functions, types and other helper objects for working with spatial data of a particular type.

The modules in green are used to access the various spatial capabilities or geographic datasets in the GIS. These modules include a family of geoprocessing functions, types and other helper objects for working with spatial data of a particular type.
The modules in blue provide additional functionality for your workflows. They include thegeocodingmodule which is for finding places, thegeometrymodule for representing the geometries of feature data and functions for working with them, thegeoprocessingmodule that makes it easy to import third party geoprocessing tools and work with them and thegeoenrichmentmodule that helps you enrich your datasets with thematic information.

The modules in blue provide additional functionality for your workflows. They include the

```
geocoding
```

geocoding
module which is for finding places, the

```
geometry
```

geometry
module for representing the geometries of feature data and functions for working with them, the

```
geoprocessing
```

geoprocessing
module that makes it easy to import third party geoprocessing tools and work with them and the

```
geoenrichment
```

geoenrichment
module that helps you enrich your datasets with thematic information.
The modules in orange allow you to visualize and disseminate your GIS data and analysis. Thewidgetsmodule includes the MapView Jupyter notebook widget for visualizing maps and layers, themappingmodule has types and functions for working with web maps and web layers and theappsmodule helps you create and manage web applications built with ArcGIS.

The modules in orange allow you to visualize and disseminate your GIS data and analysis. The

```
widgets
```

widgets
module includes the MapView Jupyter notebook widget for visualizing maps and layers, the

```
mapping
```

mapping
module has types and functions for working with web maps and web layers and the

```
apps
```

apps
module helps you create and manage web applications built with ArcGIS.

### arcgis.gismodule


```
arcgis.gis
```

arcgis.gis
module
Thearcgis.gismodule provides an information model for GIS hosted within ArcGIS Online or Portal for ArcGIS. This module provides functionality to manage (create, read, update and delete) GIS users, groups and content. This module is the most important and provides the entry point into the GIS.

The

```
arcgis.gis
```

arcgis.gis
module provides an information model for GIS hosted within ArcGIS Online or Portal for ArcGIS. This module provides functionality to manage (create, read, update and delete) GIS users, groups and content. This module is the most important and provides the entry point into the GIS.

#### arcgis.gissubmodules


```
arcgis.gis
```

arcgis.gis
submodules
These submodules assist in various administrative level operations on server and server extension components of a Web GIS deployment. It also contains modules for working with auxiliary functionality such as the specific deployments for ArcGIS Notebooks and various sharing aspects to a Web GIS.

These submodules assist in various administrative level operations on server and server extension components of a Web GIS deployment. It also contains modules for working with auxiliary functionality such as the specific deployments for ArcGIS Notebooks and various sharing aspects to a Web GIS.

### arcgis.envmodule


```
arcgis.env
```

arcgis.env
module
Thearcgis.envmodule provides a shared environment used by the different modules. It stores globals such as the currently active GIS as well as environment settings that are common among all geoprocessing tools, such as the output spatial reference.

The

```
arcgis.env
```

arcgis.env
module provides a shared environment used by the different modules. It stores globals such as the currently active GIS as well as environment settings that are common among all geoprocessing tools, such as the output spatial reference.

### arcgis.featuresmodule


```
arcgis.features
```

arcgis.features
module
Entities located in space with a geometrical representation (such as points, lines or polygons) and a set of properties can be represented as features. Thearcgis.featuresmodule is used for working with feature data, feature layers and collections of feature layers in the GIS.  It also contains the Spatially Enabled DataFrame (SeDF) which extends the popular Pandas DataFrame to work directly with spatial data.

Entities located in space with a geometrical representation (such as points, lines or polygons) and a set of properties can be represented as features. The

```
arcgis.features
```

arcgis.features
module is used for working with feature data, feature layers and collections of feature layers in the GIS.  It also contains the Spatially Enabled DataFrame (
SeDF
) which extends the popular Pandas DataFrame to work directly with spatial data.

#### arcgis.featuressubmodules


```
arcgis.features
```

arcgis.features
submodules
Several submodules contain spatial analysis functions which operate against feature data. Themanagerssubmodule includes classes for administering the definition level functionality ofFeature Layers, as well as specialized classes for managingSynchronization,Versionsand serviceWebhooks.

Several submodules contain spatial analysis functions which operate against feature data. The
managers
submodule includes classes for administering the definition level functionality of
Feature Layers
, as well as specialized classes for managing
Synchronization
,
Versions
and service
Webhooks
.

### arcgis.rastermodule


```
arcgis.raster
```

arcgis.raster
module
Raster data is made up of a grid of cells, where each cell or pixel can have a value. Raster data is useful for storing data that varies continuously, as in a satellite image, a surface of chemical concentrations, or an elevation surface. Thearcgis.rastermodule contains classes and raster analysis functions for working with raster data and imagery layers.

Raster data is made up of a grid of cells, where each cell or pixel can have a value. Raster data is useful for storing data that varies continuously, as in a satellite image, a surface of chemical concentrations, or an elevation surface. The

```
arcgis.raster
```

arcgis.raster
module contains classes and raster analysis functions for working with raster data and imagery layers.

#### arcgis.rastersubmodules


```
arcgis.raster
```

arcgis.raster
submodules
These submodules contain manyanalytical functionsto work with imagery services. It includes a module for theRaster Function Templateandorthomappingfunctionality.

These submodules contain many
analytical functions
to work with imagery services. It includes a module for the
Raster Function Template
and
orthomapping
functionality.

### arcgis.networkmodule


```
arcgis.network
```

arcgis.network
module
Thearcgis.networkmodule contains classes and functions for network analysis. Network layers and analysis can be used for operations such as finding the closest facility, the best route for a vehicle, the best routes for a fleet of vehicles, locating facilities using location allocation, calculating an OD cost matrix, and generating service areas.

The

```
arcgis.network
```

arcgis.network
module contains classes and functions for network analysis. Network layers and analysis can be used for operations such as finding the closest facility, the best route for a vehicle, the best routes for a fleet of vehicles, locating facilities using location allocation, calculating an OD cost matrix, and generating service areas.

### arcgis.notebookmodule


```
arcgis.notebook
```

arcgis.notebook
module
Thearcgis.notebookmodule serves to provide support functions for managing ArcGIS Notebooks that operate identically regardless of the Web GIS deployment type. These operations aid in snapshots and execution functionality.

The

```
arcgis.notebook
```

arcgis.notebook
module serves to provide support functions for managing ArcGIS Notebooks that operate identically regardless of the Web GIS deployment type. These operations aid in snapshots and execution functionality.

### arcgis.schematicsmodule


```
arcgis.schematics
```

arcgis.schematics
module
Schematics are simplified representations of networks, intended to explain their structure and make the way they operate understandable. Thearcgis.schematicsmodule contains the types and functions for working with schematic layers and datasets.

Schematics are simplified representations of networks, intended to explain their structure and make the way they operate understandable. The

```
arcgis.schematics
```

arcgis.schematics
module contains the types and functions for working with schematic layers and datasets.

### arcgis.geoanalyticsmodule


```
arcgis.geoanalytics
```

arcgis.geoanalytics
module
Thearcgis.geoanalyticsmodule provides types and functions for distributed analysis of large feature and tabular datasets. These GeoAnalytics tools work with big data registered in the GIS’s datastores as well as with feature layers.

The

```
arcgis.geoanalytics
```

arcgis.geoanalytics
module provides types and functions for distributed analysis of large feature and tabular datasets. These GeoAnalytics tools work with big data registered in the GIS’s datastores as well as with feature layers.

### arcgis.geocodingmodule


```
arcgis.geocoding
```

arcgis.geocoding
module
Thearcgis.geocodingmodule provides classes and functions for geocoding, batch geocoding and reverse geocoding. Geocoders can find point locations of addresses, business names, and so on. The output points can be visualized on a map, inserted as stops for a route, or loaded as input for spatial analysis.

The

```
arcgis.geocoding
```

arcgis.geocoding
module provides classes and functions for geocoding, batch geocoding and reverse geocoding. Geocoders can find point locations of addresses, business names, and so on. The output points can be visualized on a map, inserted as stops for a route, or loaded as input for spatial analysis.

### arcgis.geometrymodule


```
arcgis.geometry
```

arcgis.geometry
module
Thearcgis.geometrymodule defines useful geometry types for working with geographic information and GIS functionality. It provides functions which use geometric types as input and output as well as functions for easily converting geometries between different representations.

The

```
arcgis.geometry
```

arcgis.geometry
module defines useful geometry types for working with geographic information and GIS functionality. It provides functions which use geometric types as input and output as well as functions for easily converting geometries between different representations.

### arcgis.geoenrichmentmodule


```
arcgis.geoenrichment
```

arcgis.geoenrichment
module
Thearcgis.geoenrichmentmodule provides the ability to get facts about a location or area. Using GeoEnrichment, you can get information about the people and places in a specific area or within a certain distance or drive time from a location. You can use this data to enhance the accuracy of your predictive models or better explain the inferences you gain from them.

The

```
arcgis.geoenrichment
```

arcgis.geoenrichment
module provides the ability to get facts about a location or area. Using GeoEnrichment, you can get information about the people and places in a specific area or within a certain distance or drive time from a location. You can use this data to enhance the accuracy of your predictive models or better explain the inferences you gain from them.

### arcgis.geoprocessingmodule


```
arcgis.geoprocessing
```

arcgis.geoprocessing
module
Users can create and share geoprocessing tools in the GIS. Thearcgis.geoprocessingmodule provides helper types with dynamically created methods to invoke these tools, and provides simple types that can be used as parameters for these tools along with native Python types.

Users can create and share geoprocessing tools in the GIS. The

```
arcgis.geoprocessing
```

arcgis.geoprocessing
module provides helper types with dynamically created methods to invoke these tools, and provides simple types that can be used as parameters for these tools along with native Python types.

### arcgis.graphmodule


```
arcgis.graph
```

arcgis.graph
module
Thearcgis.graphmodule contains classes and functions for working with the entities and relationships of an ArcGIS Knowledge graph. The available functions allow for searching and querying the graph data, and viewing the data model of the graph database.

The

```
arcgis.graph
```

arcgis.graph
module contains classes and functions for working with the entities and relationships of an ArcGIS Knowledge graph. The available functions allow for searching and querying the graph data, and viewing the data model of the graph database.

### arcgis.realtimemodule


```
arcgis.realtime
```

arcgis.realtime
module
Thearcgis.realtimemodule provides types and functions for receiving real-time data feeds and sensor data streamed from the GIS to perform continuous processing and analysis. It includes support for stream layers that allow Python scripts to subscribe to the streamed feature data or broadcast updates or alerts.

The

```
arcgis.realtime
```

arcgis.realtime
module provides types and functions for receiving real-time data feeds and sensor data streamed from the GIS to perform continuous processing and analysis. It includes support for stream layers that allow Python scripts to subscribe to the streamed feature data or broadcast updates or alerts.

### arcgis.mappingmodule


```
arcgis.mapping
```

arcgis.mapping
module
Thearcgis.mappingmodule provides components for visualizing GIS data and analysis. This module includes WebMap and WebScene components that enable 2D and 3D mapping and visualization in the GIS. This module includes layers like MapImageLayer and VectorTileLayer, as well as anogcsubmodule for working with OGC services.

The

```
arcgis.mapping
```

arcgis.mapping
module provides components for visualizing GIS data and analysis. This module includes WebMap and WebScene components that enable 2D and 3D mapping and visualization in the GIS. This module includes layers like MapImageLayer and VectorTileLayer, as well as an
ogc
submodule for working with OGC services.

### arcgis.widgetsmodule


```
arcgis.widgets
```

arcgis.widgets
module
Thearcgis.widgetsmodule provides components for visualizing GIS data and analysis. This module includes the MapView Jupyter notebook widget for visualizing maps and layers

The

```
arcgis.widgets
```

arcgis.widgets
module provides components for visualizing GIS data and analysis. This module includes the MapView Jupyter notebook widget for visualizing maps and layers

### arcgis.appsmodule


```
arcgis.apps
```

arcgis.apps
module
Thearcgis.appsmodule allows you to manage some of the web based applications available in ArcGIS.

The

```
arcgis.apps
```

arcgis.apps
module allows you to manage some of the web based applications available in ArcGIS.

### arcgis.authmodule


```
arcgis.auth
```

arcgis.auth
module
Thearcgis.authmodule provides access to customrequestsauthentication handlers classes used for logging into the ArcGIS Web GIS systems. Users can customize and/or use these classes for their own python applications.

The

```
arcgis.auth
```

arcgis.auth
module provides access to custom

```
requests
```

requests
authentication handlers classes used for logging into the ArcGIS Web GIS systems. Users can customize and/or use these classes for their own python applications.

#### How this website is organized

How this website is organized
Theguidepages explain each individual concept of the API and the best practices. Thesample notebooksexplain how to use the API to write Python scripts, incorporating capabilities such as mapping, query, analysis, geocoding, routing, portal administration, and more to solve real world problems. If you are looking for recipes, you may find them as sample notebooks.

The
guide
pages explain each individual concept of the API and the best practices. The
sample notebooks
explain how to use the API to write Python scripts, incorporating capabilities such as mapping, query, analysis, geocoding, routing, portal administration, and more to solve real world problems. If you are looking for recipes, you may find them as sample notebooks.
Theapi referenceprovides a reference for each class, its properties and methods in thearcgispackage. TheArcGIS API for Python Communityis anEsri Communitywhere you can share your thoughts about the API, request for features, conduct polls, report bugs, ask questions and engage with the Python community in general.

The
api reference
provides a reference for each class, its properties and methods in the

```
arcgis
```

arcgis
package. The
ArcGIS API for Python Community
is an
Esri Community
where you can share your thoughts about the API, request for features, conduct polls, report bugs, ask questions and engage with the Python community in general.
Was this page helpful?
Yes
No