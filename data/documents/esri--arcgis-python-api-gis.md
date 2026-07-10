<!-- source: https://developers.arcgis.com/python/latest/guide/the-gis-module/ -->
# The gis module | ArcGIS API for Python | Esri Developer

> Source: https://developers.arcgis.com/python/latest/guide/the-gis-module/

Thegismodule is the representation of your GIS. Well, what is a GIS? A geographic information system (GIS) lets you visualize, question, analyze, and interpret data to understand spatial relationships, patterns, and trends. GIS benefits organizations of all sizes and in almost every industry. If you are new to GIS,this is a good place to start.

The

```
gis
```

gis
module is the representation of your GIS. Well, what is a GIS? A geographic information system (GIS) lets you visualize, question, analyze, and interpret data to understand spatial relationships, patterns, and trends. GIS benefits organizations of all sizes and in almost every industry. If you are new to GIS,
this is a good place to start
.
Your GIS can be one that is hosted with ArcGIS Online or on premises using an instance of ArcGIS Enterprise. What does a GIS consist of? A GIS is a collaborative environment that allows you to create, visualize, and share maps, scenes, apps, layers, analytics, and data. To know more about this concept, referhere.

Your GIS can be one that is hosted with ArcGIS Online or on premises using an instance of ArcGIS Enterprise. What does a GIS consist of? A GIS is a collaborative environment that allows you to create, visualize, and share maps, scenes, apps, layers, analytics, and data. To know more about this concept, refer
here
.

## Architecture of the gis module

Architecture of the gis module
Thegismodule provides an information model for a GIS hosted within ArcGIS Online or an instance of ArcGIS Enterprise hosted in your premises. This module provides functionality to manage (create, read, update and delete) GIS users, groups and content. This module is the most important and provides the entry point into the GIS.

The

```
gis
```

gis
module provides an information model for a GIS hosted within ArcGIS Online or an instance of ArcGIS Enterprise hosted in your premises. This module provides functionality to manage (create, read, update and delete) GIS users, groups and content. This module is the most important and provides the entry point into the GIS.
Below is a graphic of thegismodule and its various classes:

Below is a graphic of the

```
gis
```

gis
module and its various classes:
The main classes in the gis module are:

The main classes in the gis module are:
- GIS: represents the GIS, either ArcGIS Online or an ArcGIS Portal
GIS: represents the GIS, either ArcGIS Online or an ArcGIS Portal

GIS
: represents the GIS, either ArcGIS Online or an ArcGIS Portal
- User: represents a GIS user
User: represents a GIS user

User
: represents a GIS user
- Role: represents the role of a GIS user
Role: represents the role of a GIS user

Role
: represents the role of a GIS user
- Group: represents a group in the GIS
Group: represents a group in the GIS

Group
: represents a group in the GIS
- Item: represents an Item in the GIS
Item: represents an Item in the GIS

Item
: represents an Item in the GIS
- Resource manager classes for managing GIS users, groups, content and datastores:UserManager: to manage usersRoleManager: to create and manage rolesGroupManager: to manage groups in the GISContentManager: to access, add, modify, delete GIS content
Resource manager classes for managing GIS users, groups, content and datastores:

Resource manager classes for managing GIS users, groups, content and datastores:
- UserManager: to manage users
UserManager
: to manage users
- RoleManager: to create and manage roles
RoleManager
: to create and manage roles
- GroupManager: to manage groups in the GIS
GroupManager
: to manage groups in the GIS
- ContentManager: to access, add, modify, delete GIS content
ContentManager
: to access, add, modify, delete GIS content
This section of the guide helps you get familiar with thegismodule through focused examples and narrative text. Refer to the sample notebooks forOrg administratorsto observe how this module can be used to automate the management of your GIS.

This section of the guide helps you get familiar with the

```
gis
```

gis
module through focused examples and narrative text. Refer to the sample notebooks for
Org administrators
to observe how this module can be used to automate the management of your GIS.
Was this page helpful?
Yes
No