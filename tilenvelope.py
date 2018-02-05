#!/usr/bin/env python
# * coding: utf8 *
'''tileenvelope.py

Usage:
    tileenvelope.py generate-indices from <file> [--output OUTPUT --scale SCALE --size SIZE --input-sr SR]

Options:
    --output OUTPUT           output location
    --scale SCALE             the scale at which the image was taken [default: Scale]
    --size SIZE               the size of the image in inches [default: FrameFormat]
'''

import re
import sys

from docopt import docopt

import arcpy

arcpy.env.overwriteOutput = True
nad83 = arcpy.SpatialReference(26912)
inches_in_meter = 39.37008
batch_size = 5000
i = 0
activity = ['/', '-', '\\', '|']


def create_polygon(scale, size, shape):
    #: get utm centroid
    coords = arcpy.Point(*shape)
    centroid = arcpy.PointGeometry(coords, nad83)

    utm = centroid.centroid

    if utm.X < 15000 or utm.X > 707933:
        return 'centroid: {},{}'.format(shape[0], shape[1]), arcpy.Polygon(arcpy.Point(0, 0))

    if utm.X is None or utm.X == 0 or utm.X == utm.Y:
        return 'centroid: {},{}'.format(shape[0], shape[1]), arcpy.Polygon(arcpy.Point(0, 0))

    if scale is None:
        return 'scale: {}'.format(scale), arcpy.Polygon(arcpy.Point(0, 0))

    if not isinstance(scale, (int, float, complex)):
        scale = float(scale)

    #: pull out size information
    expected_matches = 2
    match = re.search('(\d)x(\d)', size)

    if match is None or len(match.groups()) < expected_matches:
        return 'size: {}'.format(size), arcpy.Polygon(arcpy.Point(0, 0))

    length = float(match.group(1))
    width = float(match.group(2))

    #: calculate ground distance
    length_in_meters = (length * scale) / inches_in_meter
    half_length = length_in_meters / 2

    if length == width:
        width_in_meters = length_in_meters
        half_width = half_length
    else:
        width_in_meters = (width * scale) / inches_in_meter
        half_width = width_in_meters / 2

    #: create polygon
    top_left = arcpy.Point(utm.X - half_length, utm.Y + half_width)
    top_right = arcpy.Point(utm.X + half_length, utm.Y + half_width)
    bottom_left = arcpy.Point(utm.X - half_length, utm.Y - half_width)
    bottom_right = arcpy.Point(utm.X + half_length, utm.Y - half_width)

    coords = arcpy.Array([top_left, top_right, bottom_right, bottom_left])

    return None, arcpy.Polygon(coords, nad83)


def create_field_mapping(cursor):
    return dict((field.lower(), i) for i, field in enumerate(cursor.fields))


if __name__ == '__main__':
    arguments = docopt(__doc__, version='tileenvelope 1.0.0')

    if arguments['generate-indices']:
        input_file = arguments['<file>'].lower()
        output_file = arguments['--output']
        scale = arguments['--scale'].lower()
        size = arguments['--size'].lower()

        if not arcpy.Exists(input_file):
            print('{} does not exist'.format(input_file))
            sys.exit()

        if '.gdb' not in input_file:
            print('please use a file geodatabase for this tool')
            sys.exit()

        gdb, name = input_file.split('.gdb')
        gdb = gdb + '.gdb'

        if name == '':
            print('Add the point feature class to the gdb input string')
            sys.exit()

        if arcpy.Describe(gdb).workspaceType != 'LocalDatabase':
            print('please use a file geodatabase for this tool')
            sys.exit()

        input_description = arcpy.Describe(input_file)
        if input_description.shapeType != 'Point':
            print('please input a point feature class for this tool')
            sys.exit()

        if input_description.SpatialReference.factoryCode != nad83.factoryCode:
            print('project your data to utm nad83z12n (26912)')
            sys.exit()

        if not output_file:
            output_file = input_file + '_tilenvelope'

        if arcpy.Exists(output_file):
            print('trucating {}'.format(output_file))
            arcpy.management.TruncateTable(output_file)
        else:
            print('creating {}'.format(output_file))
            arcpy.management.CreateFeatureclass(gdb, name.strip('\\') + '_tilenvelope', geometry_type='POLYGON', spatial_reference=nad83)

            skip_fields = ['objectid', 'shape']
            for field in input_description.fields:
                if field.name.lower() in skip_fields:
                    continue

                arcpy.management.AddField(output_file, field.name, field.type, field.precision, field.scale, field.length, field.aliasName, field.isNullable,
                                          field.required, field.domain)

            arcpy.management.AddField(output_file, 'error', 'TEXT', field_length=250)

        #: read photo centroid info
        with arcpy.da.SearchCursor(input_file, ['*']) as cursor:
            mapping = create_field_mapping(cursor)
            scale_index = mapping[scale]
            size_index = mapping[size]

            fields = list(cursor.fields)
            fields.append('error')
            fields[mapping['shape']] = 'shape@'

            with arcpy.da.InsertCursor(output_file, fields) as insert_cursor:
                output_mapping = create_field_mapping(insert_cursor)

                for row in cursor:
                    i += 1
                    scale = row[scale_index]
                    size = row[size_index]
                    shape = row[mapping['shape']]
                    error, shape = create_polygon(scale, size, shape)

                    row = list(row)
                    row[output_mapping['shape@']] = shape
                    row.append(error)

                    insert_cursor.insertRow(row)

                    sys.stdout.write('\r{}'.format(activity[i % 4]))
                    sys.stdout.flush()

                    if i % batch_size == 0:
                        print('\n created {} polygons'.format(i))
