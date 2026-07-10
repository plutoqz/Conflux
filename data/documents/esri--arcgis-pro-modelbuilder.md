<!-- source: https://pro.arcgis.com/en/pro-app/latest/help/analysis/geoprocessing/modelbuilder/what-is-modelbuilder-.htm -->
# What is ModelBuilder? | ArcGIS Pro documentation

> Source: https://pro.arcgis.com/en/pro-app/latest/help/analysis/geoprocessing/modelbuilder/what-is-modelbuilder-.htm

##### Table of Contents

Table of Contents

# What is ModelBuilder?

What is ModelBuilder?
ModelBuilder is a visual programming language for building geoprocessing workflows. Geoprocessing models automate and document spatial analysis and data management processes. You create and modify geoprocessing models in ModelBuilder, where a model is represented as a diagram that chains together sequences of processes and geoprocessing tools, using the output of one process as the input to another process.

ModelBuilder is a visual programming language for building geoprocessing workflows. Geoprocessing models automate and document spatial analysis and data management processes. You create and modify geoprocessing models in ModelBuilder, where a model is represented as a diagram that chains together sequences of processes and geoprocessing tools, using the output of one process as the input to another process.
ModelBuilder in ArcGIS Pro allows you to do the following:

ModelBuilder in ArcGIS Pro allows you to do the following:
- Build a model byadding and connecting data and tools.
Build a model byadding and connecting data and tools.

Build a model by
adding and connecting data and tools
.
- Iterativelyprocess every feature class, raster, file, or table in a workspace.
Iterativelyprocess every feature class, raster, file, or table in a workspace.

Iteratively
process every feature class, raster, file, or table in a workspace.
- Visualize your workflow sequence as an easy-to-understand diagram.
Visualize your workflow sequence as an easy-to-understand diagram.

Visualize your workflow sequence as an easy-to-understand diagram.
- Run a modelstep by step, up to a selected step, or run the entire model.
Run a modelstep by step, up to a selected step, or run the entire model.

Run a model
step by step, up to a selected step, or run the entire model.
- Make your model into a geoprocessing toolthat can be shared or can be used in Python scripting and other models.
Make your model into a geoprocessing toolthat can be shared or can be used in Python scripting and other models.

Make your model into a geoprocessing tool
that can be shared or can be used in Python scripting and other models.
This video was created with ArcGIS Pro 3.7.
Learn more about using ModelBuilder

Learn more about using ModelBuilder

## Example

Example
This geoprocessing model is used by a conservation organization to identify potential habitats for an indigenous bird species based on vegetation type, distance from major roads, climate, slope, and elevation.

This geoprocessing model is used by a conservation organization to identify potential habitats for an indigenous bird species based on vegetation type, distance from major roads, climate, slope, and elevation.
The model runs the following tools in sequence:

The model runs the following tools in sequence:
- Select Layer By Attribute—Select the correct vegetation type from a Vegetation map layer.
Select Layer By Attribute—Select the correct vegetation type from a Vegetation map layer.

Select Layer By Attribute
—Select the correct vegetation type from a Vegetation map layer.
- Buffer—Create areas within a distance of 1,500 feet around major roads.
Buffer—Create areas within a distance of 1,500 feet around major roads.

Buffer
—Create areas within a distance of 1,500 feet around major roads.
- Erase—Erase the buffer areas from the selected vegetation areas.
Erase—Erase the buffer areas from the selected vegetation areas.

Erase
—Erase the buffer areas from the selected vegetation areas.
- Intersect—Overlay the output of theErasetool with other map layers, including slope, elevation, and climate. This identifies the areas that meet all criteria.
Intersect—Overlay the output of theErasetool with other map layers, including slope, elevation, and climate. This identifies the areas that meet all criteria.

Intersect
—Overlay the output of the
Erase
tool with other map layers, including slope, elevation, and climate. This identifies the areas that meet all criteria.