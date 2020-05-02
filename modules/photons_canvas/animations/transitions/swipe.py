from photons_canvas.animations.features.falling import (
    Line as FallingLine,
    Options as FallingOptions,
)
from photons_canvas.animations import Animation, Finish, an_animation
from photons_canvas.canvas import Canvas

from delfick_project.norms import dictobj, sb
from collections import defaultdict
import random


class Options(FallingOptions):
    min_speed = dictobj.Field(sb.float_spec, default=1)
    max_speed = dictobj.Field(sb.float_spec, default=2)


class Line(FallingLine):
    def __init__(self, options, y, left_x, width):
        class state:
            def __init__(s):
                s.top = -left_x
                s.bottom = -width - left_x
                s.options = options

        super().__init__(y, state())

        self.y = y
        self.px = None
        self.parts = [list(self.make_part(allow_blank=False))]
        self.bottom = -width - left_x + len(self.parts[0]) + 5

    def make_part_length(self):
        return 3 + random.randrange(0, 5)

    def progress(self):
        self.bottom -= self.rate
        self.px = {(x, y): color for (y, x), color in self.pixels()}


@an_animation("swipe", Options, transition=True)
class Animation(Animation):
    def setup(self):
        self.canvas = None
        self.top_canvas = None

    async def process_event(self, event):
        if not event.is_tick:
            return

        if self.canvas is None and event.canvas:
            self.points = [point for point, _ in event.canvas]
            self.canvas = event.canvas.clone()
            self.right_x = max([x for x, _ in self.points])

        if event.state is None:
            event.state = defaultdict(dict)

            for device in event.devices:
                s = event.state[device.serial]
                bounds = device.coords.bounds
                for coord in device.coords:
                    for _, y in coord.points:
                        if y not in s:
                            s[y] = Line(self.options, y, bounds.left_x, bounds.width)

        for by_device in event.state.values():
            for line in by_device.values():
                line.progress()

        self.fade()

        if self.top_canvas:
            for point, pixel in self.top_canvas:
                self.canvas[point] = pixel

        self.set_lines(event.state)

        if self.top_canvas is None:
            return

        for point, pixel in self.top_canvas:
            self.canvas[point] = pixel

        if all(
            point in self.top_canvas and self.top_canvas[point].brightness <= 0
            for point in self.points
        ):
            raise Finish("done")

        return self.canvas

    def fade(self):
        if self.top_canvas is not None:
            for point in self.points:
                if point in self.top_canvas:
                    pixel = self.top_canvas[point].clone()

                    if self.options.fade_amount == 0:
                        pixel.brightness = 0
                    else:
                        pixel.brightness = max([0, pixel.brightness - self.options.fade_amount])

                    self.top_canvas[point] = pixel

    def set_lines(self, state):
        for serial, st in state.items():
            for line in st.values():
                points = list(line.px.items())
                if not any(pixel.brightness > 0 for _, pixel in points):
                    continue

                if self.top_canvas is None:
                    self.top_canvas = Canvas()

                for i in range(points[0][0][0], self.right_x + 1):
                    point = (i, line.y)
                    if point in self.canvas:
                        self.top_canvas[(i, line.y)] = self.canvas[(i, line.y)]

                for point, pixel in points:
                    if point in self.points and pixel.brightness > 0:
                        self.top_canvas[point] = pixel
