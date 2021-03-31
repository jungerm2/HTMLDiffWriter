import pytest
import base64
import functools
import numpy as np
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, HTMLWriter
from matplotlib.testing.decorators import _raise_on_image_difference
from matplotlib.testing.compare import convert

from SVGFuncAnimation import SVGFuncAnimation


def make_same_size(path1, path2, method=min):
    img1 = Image.open(path1)
    img2 = Image.open(path2)

    w, h = method(img1.width, img2.width), method(img1.height, img2.height)
    img1 = img1.resize((w, h))
    img2 = img2.resize((w, h))

    img1.save(path1)
    img2.save(path2)


def get_frames(anim, size):
    if isinstance(anim, SVGFuncAnimation):
        return [anim.grab_frame(i) for i in range(size)]
    elif isinstance(anim, FuncAnimation):
        with mpl.rc_context({"animation.frame_format": "svg"}):
            with TemporaryDirectory() as tmpdir:
                path = Path(tmpdir, "temp.html")
                writer = HTMLWriter(embed_frames=True)
                anim.save(str(path), writer=writer)
                return [base64.b64decode(f).decode('ascii')
                        for f in writer._saved_frames[:size]]


@functools.lru_cache
def get_line_anim_frames(constructor, size, fmt):
    np.random.seed(0)

    def update_line(num, data, line):
        line.set_data(range(num), data[:num])
        return line,

    fig = plt.figure()
    data = np.random.rand(size)
    l, = plt.plot([], [], fmt)
    plt.xlim(0, size - 1)
    plt.ylim(0, 1)

    anim = constructor(fig, update_line, range(1, size + 1), fargs=(data, l))
    plt.close(fig)

    return get_frames(anim, size)


@pytest.mark.parametrize("index", [0, 4, 9])
@pytest.mark.parametrize("marker", ['bo', 'g^', 'r1', 'cp', 'm*', 'yX', 'kD'])
def test_line_animation(marker, index):
    func_frame = get_line_anim_frames(FuncAnimation, 10, marker)[index]
    svg_frame = get_line_anim_frames(SVGFuncAnimation, 10, marker)[index]

    with TemporaryDirectory() as tmpdir:
        func_path = Path(tmpdir, "expected.svg")

        with open(func_path, 'w') as f:
            f.write(func_frame)

        svg_path = Path(tmpdir, "actual.svg")

        with open(svg_path, 'w') as f:
            f.write(svg_frame)

        new_func_path = convert(func_path, False)
        new_svg_path = convert(svg_path, False)

        _raise_on_image_difference(new_func_path, new_svg_path, tol=0)


# TODO:
#   Add + test embed limit rcParam
#   Test proper cleanup of tempdir
#   Test frames param int/generator/None
#   Test other plot types (scatter, hist, (math)text)
#   Test grab_frame returns valid XML doc
#   Test init_func vs no init_func
#   Test user func returns unknown artist
#   Test user func returns None
#   Test artist with no initial draw (i.e: Text w/ empty str)
#   -----------------------
#   Refactor tests w/ better fixtures + skip_ifs (if needed?)
#   Move test failure images (diffs, etc) to non-tempdir
