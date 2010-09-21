# -*- coding: utf-8 -*-

import math
import itertools

from pyPdf import PdfFileWriter, PdfFileReader
from pyPdf.pdf import PageObject

def lower_divisor_iterator(value):
    """
    Iterates over all divisors of the given value smaller or equal to the
    value's square root in decreasing order.
    """
    i = int(math.sqrt(value))
    while i > 0:
        if value % i == 0:
            yield i
        i -= 1

def _get_rotation_scaling(width, height, cell_x_count, cell_y_count):
    """
    Calculate rotaion and scaling factor for best useage of target page, i.e.
    largest possible scaling factor for least scaling.
    """
    # 1. Check no rotation
    plain_scaling_factor = min(1. / cell_x_count, 1. / cell_y_count)
    # 2. Check rotation by 90°
    #   (Example: Page XXXX would at best yield AABB for 2 pages on 1 sheet,
    #                  XXXX                     AABB
    #    i.e. the original width needs to hold 2 x the sheet's height, and
    #         the original height holds 1/2 x the sheet's width)
    rotate_scaling_factor = min(1. * width / (cell_x_count * height),
                                1. * height / (cell_y_count * width))

    if rotate_scaling_factor > plain_scaling_factor:
        return 90, rotate_scaling_factor
    else:
        return 0, plain_scaling_factor

def _get_optimal_placement(width, height, page_count):
    """
    Calculates the optimal placement on a sheet for the given number of pages.

    Estimates:
        - Rotation (0° / 90°)
        - Scaling factor (< 1)
        - Cell structure (width x height)
    """
    rotation = scaling_factor = None
    cell_x_count = cell_y_count = None

    # Check all possible decompositions
    # TODO don't start at square root, as that would asume next to quadratic
    #   layout of the page, choose a decomposition next to the page's ratio
    for lower_divisor in lower_divisor_iterator(page_count):
        higher_divisor = page_count / lower_divisor

        # Check A x B with A < B
        rot1, scal1 = _get_rotation_scaling(width, height,
                                            lower_divisor, higher_divisor)
        # Check B x A with A < B
        rot2, scal2 = _get_rotation_scaling(width, height,
                                            higher_divisor, lower_divisor)

        scal, rot, x, y = max((scal1, rot1, lower_divisor, higher_divisor),
                              (scal2, rot2, higher_divisor, lower_divisor))

        if scaling_factor is None or scaling_factor < scal:
            scaling_factor = scal
            rotation = rot
            cell_x_count = x
            cell_y_count = y
        else:
            # Once the scaling factor decreases in both directions we won't get
            #   any better
            break

    return rotation, scaling_factor, cell_x_count, cell_y_count

def n_pages_on_one(pages, pages_sheet):
    width = float(pages[0].mediaBox.getWidth())
    height = float(pages[0].mediaBox.getHeight())

    # Calculate placement parameters
    rotation, scaling, cell_x_count, cell_y_count = _get_optimal_placement(
        width, height, pages_sheet)

    # Get placement matrix, ajust to rotation
    if rotation:
        # From down to up, left to right
        # Also ajust to "one-off issue"
        placement = list(itertools.product(range(1, cell_x_count+1),
                                           range(cell_y_count-1, -1, -1)))
    else:
        # From left to right, up to down
        placement = map(lambda (x, y): (y, x),
                        list(itertools.product(range(cell_y_count),
                                               range(cell_x_count))))

    new_pages = []

    # Merge pages
    for new_page_idx in range(int(math.ceil(1. * len(pages) / pages_sheet))):
        offset = new_page_idx * pages_sheet
        # Start from blank page
        new_page = PageObject.createBlankPage(None, width, height)

        # Get `pages_sheet` number of pages and merge together
        for idx, page in enumerate(pages[offset:offset+pages_sheet]):
            x, y = placement[idx]

            # Get coordinates
            w = width * x / cell_x_count
            h = height * (y+1) / cell_y_count
            # TODO align page so that it takes the center of its cell
            new_page.mergeRotatedScaledTranslatedPage(page,
                                                      rotation, scaling,
                                                      w, height-h)

        new_pages.append(new_page)

    return new_pages