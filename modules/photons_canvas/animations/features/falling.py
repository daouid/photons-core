from photons_canvas.animations import Animation, an_animation, options
from photons_canvas.canvas import CanvasColor

from delfick_project.norms import dictobj, Meta, sb
import random
import math


def clamp(val, mn=0, mx=1):
    if val < mn:
        return mn
    elif val > mx:
        return mx
    return val


class Options(dictobj.Spec):
    line_hues = dictobj.NullableField(
        options.split_by_comma(options.hue_range_spec()), wrapper=sb.optional_spec
    )
    fade_amount = dictobj.Field(sb.float_spec, default=0.1)
    line_tip_hues = dictobj.NullableField(
        options.split_by_comma(options.hue_range_spec()), wrapper=sb.optional_spec
    )

    min_speed = dictobj.Field(sb.float_spec, default=0.2)
    max_speed = dictobj.Field(sb.float_spec, default=0.4)

    def setup(self, *args, **kwargs):
        super().setup(*args, **kwargs)

        options.normalise_speed_options(self)

        if self.line_hues == []:
            self.line_hues = None

        if self.line_tip_hues == []:
            self.line_tip_hues = None

        if self.line_hues is sb.NotSpecified:
            self.line_hues = [options.hue_range_spec().normalise(Meta.empty(), "rainbow")]

        if self.line_tip_hues is sb.NotSpecified:
            self.line_tip_hues = None


class Line:
    def __init__(self, column, state):
        self.state = state
        self.parts = []
        self.column = column

        self.blank_lines = state.options.line_hues is None

        self.line_hues = state.options.line_hues or [options.HueRange(90, 90)]

        if self.blank_lines and state.options.line_tip_hues is None:
            self.line_tip_hues = [options.HueRange(40, 40)]
        else:
            self.line_tip_hues = state.options.line_tip_hues

        self.fill()

    @property
    def bottom(self):
        if not hasattr(self, "_bottom"):
            self._bottom = self.state.bottom - random.randrange(10)
        return self._bottom

    @bottom.setter
    def bottom(self, value):
        self._bottom = value

    @property
    def max_length(self):
        return min([self.state.top - self.state.bottom, 20])

    def pixels(self):
        j = self.bottom + sum(len(p) for p in self.parts)
        for part in self.parts:
            info = {"hues": []}
            for hue in part:
                j -= 1
                if hue is not None:
                    if "position" not in info:
                        info["position"] = j
                    info["hues"].insert(0, hue)

            hues = info["hues"]
            if not hues:
                continue

            position = info["position"]

            if len(hues) == 1:
                hue = hues[0]
                brightness = clamp(1.0 - (position - math.floor(position)))
                color = CanvasColor(hue, 1, brightness, 3500)
                yield (self.column, math.floor(position)), color

            else:
                closeness = clamp(1.0 - (position - math.floor(position)))
                head_color = CanvasColor(hues[0], 1, closeness, 3500)
                middle_hue = hues[0] + min([10, (hues[2] - hues[0]) * closeness])
                if middle_hue > 360:
                    middle_hue -= 360

                middle_color = CanvasColor(middle_hue, 1, 1, 3500)
                body_color = CanvasColor(hues[2], 1, 1, 3500)

                for i, color in enumerate((head_color, middle_color, body_color)):
                    yield (self.column, math.floor(position) + i), color

    def fill(self):
        top = self.bottom
        for part in self.parts:
            top += len(part)

        while top < self.state.top:
            part = list(self.make_part())
            self.parts.insert(0, part)
            top += len(part)

    @property
    def rate(self):
        if self.state.options.min_speed == self.state.options.max_speed:
            return self.state.options.min_speed

        mn = int(self.state.options.min_speed * 100)
        mx = int(self.state.options.max_speed * 100)
        return random.randint(mn, mx) / 100

    def progress(self):
        self.bottom -= self.rate
        bottom = math.floor(self.bottom)
        if bottom + len(self.parts[-1]) < self.state.bottom:
            self.bottom += len(self.parts.pop())
        self.fill()

    def make_part_length(self):
        return random.randrange(0, self.max_length) + 5

    def make_part(self, allow_blank=True):
        length = self.make_part_length()
        if allow_blank and random.randrange(0, 100) < 50:
            for _ in range(length):
                yield None
            return

        if not self.blank_lines:
            hue_range = random.choice(self.line_hues)

        line = [None for i in range(length)]

        if self.line_tip_hues is not None:
            line[-1] = random.choice(self.line_tip_hues).make_hue()
            length -= 1

        if not self.blank_lines:
            tail_hue = hue_range.make_hue()
            line[length - 1] = tail_hue
            line[length - 2] = tail_hue

            if self.line_tip_hues is None:
                line[length - 3] = tail_hue

        yield from line


class TileFallingState:
    def __init__(self, canvas, options):
        self.canvas = canvas
        self.options = options

        self.lines = {}
        self.coords = None

    def set_coords(self, coords):
        if coords == self.coords:
            return

        self.coords = coords
        (self.left, self.right), (self.top, self.bottom), (self.width, self.height) = coords.bounds

        for column in range(self.left, self.right):
            if column not in self.lines:
                self.lines[column] = Line(column, self)

    def tick(self):
        for line in self.lines.values():
            line.progress()
        return self

    def make_canvas(self):
        if not self.coords:
            return self.canvas

        for point, pixel in list(self.canvas):
            changed = pixel.brightness - self.options.fade_amount
            if changed < 0:
                del self.canvas[point]
            else:
                pixel.brightness = changed

        drawn = set()
        for coord in self.coords:
            for i in range(coord.left_x, coord.left_x + coord.width):
                if i in drawn:
                    continue

                line = self.lines[i]
                for point, pixel in line.pixels():
                    self.canvas[point] = pixel

                drawn.add(i)

        return self.canvas


@an_animation("falling", Options)
class TileFallingAnimation(Animation):
    """Falling lines of pixels"""

    async def process_event(self, event):
        if event.state is None:
            event.state = TileFallingState(event.canvas, self.options)

        if event.is_new_device:
            event.state.set_coords(event.coords)

        if event.is_tick:
            event.state.tick()
            return event.state.make_canvas()
