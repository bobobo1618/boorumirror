import sys
def hash_image(filename):
    import numpy
    from gi.repository import Vips
    # Load image
    im = Vips.Image.new_from_file(filename)

    # Convert to greyscale
    bwim = im.sRGB2scRGB().scRGB2BW()

    # Determine suitable square image dimensions
    edge_length = float((8 * min((im.width, im.height,)))//8)
    xscale, yscale = edge_length/im.width, edge_length/im.height

    # Transform image
    res_im = bwim.affine([xscale, 0, 0, yscale], oarea=[0, 0, edge_length, edge_length])

    values = numpy.zeros(64)
    block_size = edge_length / 8.0
    count = 0
    for x in xrange(0, 8):
        for y in xrange(0, 8):
            area = []
            values[count] = res_im.extract_area(
                block_size * x,
                block_size * y,
                block_size,
                block_size,
            ).avg()
            count += 1

    avg_value = numpy.average(values)
    bits = (
        (1 if value > avg_value else 0)
        for value in values
    )

    out = 0
    for bit in bits:
        out = (out << 1) | bit

    if out >= 2**63:
        out -= 2**64
    return out

if __name__ == '__main__':
    filename = sys.argv[-1]
    out = hash_image(filename)
    print out
