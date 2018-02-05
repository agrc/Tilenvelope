# Tilenvelope

creating polygons from photo imagery centroids

## Install

`pip install -r requirements.txt`

## Assumptions

1. Input data will be contained in a file geodatabase
1. Input data will be a point feature class
1. Input data will have a 26912 projection
1. Input data will have a frame format attribute in the format of `LxW Inches` where `L` and `W` are numbers
1. Input data will have a number type scale attribute or convertable to a number format

## Usage

```py
'''tileenvelope.py

Usage:
    tileenvelope.py generate-indices from <file> [--output OUTPUT --scale SCALE --size SIZE]

Options:
    --output OUTPUT           output location. defaults to the <file> input with `_tileenvelope` appended.
    --scale SCALE             the attribute name containing the scale at which the image was taken [default: Scale]
    --size SIZE               the attribute name containing the size of the image in inches [default: FrameFormat]
'''
```

An `error` field is appended and populated with causes of issues. Check that out after using.
