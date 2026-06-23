def intersects(box1, box2):
    x0a, y0a, x1a, y1a = box1
    x0b, y0b, x1b, y1b = box2

    return not (
        x1a < x0b or
        x1b < x0a or
        y1a < y0b or
        y1b < y0a
    )