from photons_canvas import CanvasColor

import itertools
import random


class Black:
    pass


class Patterns:
    def __init__(self):
        self.styles = iter(self.compute_styles())

    def make_color(self, hue, dim=False):
        if hue is Black:
            c = CanvasColor(0, 0, 0, 3500)
        else:
            c = CanvasColor(hue, 1, 0.5, 3500)

        if c.saturation == 1:
            if not dim:
                c.brightness = 1
            else:
                c.brightness = dim

        return c

    def compute_styles(self):
        colors = [0, 50, 100, 180, 250, 300]
        options = list(self.options(colors))
        random.shuffle(options)

        os = iter(itertools.cycle(options))

        while True:
            nxt = next(os)
            for sp in nxt:
                yield sp

    def options(self, colors):
        shifted = colors[2:] + colors[:2]

        yield [("color", (color,)) for color in colors]
        yield [("split", (color,)) for color in colors]

        for attr in ("x", "cross", "hourglass", "inverse_hourglass"):
            yield [(attr, (color,)) for color in colors]
            yield [(attr, (Black, color)) for color in colors]
            if attr != "x":
                yield [(attr, (h1, h2)) for h1, h2 in zip(colors, shifted)]

    def set_canvas(self, canvas, coord):
        typ, options = next(self.styles)
        getattr(self, f"set_{typ}")(canvas, coord, *options)

    def set_color(self, canvas, coord, hue):
        for (i, j) in coord.points:
            canvas[(i, j)] = self.make_color(hue, dim=0.5)

    def set_split(self, canvas, coord, hue):
        (left_x, _), (top_y, _), (width, height) = coord.bounds

        for (i, j) in coord.points:
            h = Black
            if i > left_x + width / 2:
                h = hue

            canvas[(i, j)] = self.make_color(h, dim=0.5)

    def get_i_and_j_lists(self, coord):
        (left_x, _), (top_y, _), (width, height) = coord.bounds

        iss = set()
        jss = set()

        for (i, j) in coord.points:
            iss.add(i)
            jss.add(j)

        iss = sorted(iss)
        jss = sorted(jss)

        liss, riss = iss[len(iss) // 2 :], iss[: len(iss) // 2]
        tjss, bjss = jss[len(jss) // 2 :], jss[: len(jss) // 2]

        return (liss, riss), (tjss, bjss)

    def set_cross(self, canvas, coord, hue1, hue2=None):
        (liss, riss), (tjss, bjss) = self.get_i_and_j_lists(coord)

        if hue2 is None:
            hue2 = Black

        def make_color(t):
            h = [hue1, hue2][t]
            return self.make_color(h, dim=0.5 if h is Black or t else False)

        for ii, (li, ri) in enumerate(zip(liss, reversed(riss))):
            for jj, (tj, bj) in enumerate(zip(tjss, reversed(bjss))):
                for point in ((li, tj), (ri, tj), (li, bj), (ri, bj)):
                    if ii == 0 or jj == 0:
                        canvas[point] = make_color(False)
                    else:
                        canvas[point] = make_color(True)

    def set_x(self, canvas, coord, hue1, hue2=None):
        (liss, riss), (tjss, bjss) = self.get_i_and_j_lists(coord)

        if hue2 is None:
            hue2 = Black

        def make_color(t):
            h = [hue1, hue2][t]
            return self.make_color(h, dim=0.5 if h is Black or not t else False)

        skip = 1
        for ii, (li, ri) in enumerate(zip(liss, reversed(riss))):
            for jj, (tj, bj) in enumerate(zip(tjss, reversed(bjss))):
                for point in ((li, tj), (ri, tj), (li, bj), (ri, bj)):
                    s = skip - 1
                    if ii == s and jj == s or ii == jj or ii + 1 == jj or jj + 1 == ii:
                        canvas[point] = make_color(False)
                    else:
                        canvas[point] = make_color(True)
            skip += skip

    def set_inverse_hourglass(self, canvas, coord, hue1, hue2=None):
        (liss, riss), (tjss, bjss) = self.get_i_and_j_lists(coord)

        if hue2 is None:
            hue2 = Black

        def make_color(t):
            h = [hue1, hue2][t]
            return self.make_color(h, dim=0.5 if h is Black or not t else False)

        skip = 1
        for ii, (li, ri) in enumerate(zip(liss, reversed(riss))):
            for jj, (tj, bj) in enumerate(zip(tjss, reversed(bjss))):
                for point in ((li, tj), (ri, tj), (li, bj), (ri, bj)):
                    s = skip - 1
                    if ii <= s and jj <= s:
                        canvas[point] = make_color(False)
                    else:
                        canvas[point] = make_color(True)
            skip += skip

    def set_hourglass(self, canvas, coord, hue1, hue2=None):
        (liss, riss), (tjss, bjss) = self.get_i_and_j_lists(coord)

        if hue2 is None:
            hue2 = Black

        def make_color(t):
            h = [hue1, hue2][t]
            return self.make_color(h, dim=0.5 if h is Black or t else False)

        skip = 1
        for ii, (li, ri) in enumerate(zip(liss, reversed(riss))):
            for jj, (tj, bj) in enumerate(zip(tjss, reversed(bjss))):
                for point in ((li, tj), (ri, tj), (li, bj), (ri, bj)):
                    s = skip - 1
                    if ii == s and jj >= s:
                        canvas[point] = make_color(False)
                    else:
                        canvas[point] = make_color(True)
            skip += skip
