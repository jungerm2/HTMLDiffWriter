import xml
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
def get_line_anim_frames(constructor, size, fmt='r-', use_init=False):
    np.random.seed(0)

    fig = plt.figure()
    data = np.random.rand(size)
    l, = plt.plot([], [], fmt)
    plt.xlim(0, size - 1)
    plt.ylim(0, 1)

    def init():
        l.set_data([], [])
        return l,

    def update_line(num, data, line):
        line.set_data(range(num), data[:num])
        return line,

    anim = constructor(fig, update_line, range(1, size + 1),
                       init_func=init if use_init else None,
                       fargs=(data, l))
    plt.close(fig)
    return get_frames(anim, size)


@functools.lru_cache
def get_text_anim_frames(constructor, size, init_text=' ', use_init=False, math_mode=False):
    np.random.seed(0)

    fig = plt.figure()
    x, y = np.random.rand(2, size)
    txt = plt.text(.5, .5, init_text, fontsize=15)
    text = [r'$\sum_{i=0}^\infty x_i$', r'$E=mc^2$', r'$c=\sqrt{a^2+b^2}$'] \
        if math_mode else ['First', 'Second', 'Third']
    plt.xlim(0, 1)
    plt.ylim(0, 1)

    def init():
        txt.set_text(init_text)
        return txt,

    def update_text(num):
        txt.set_text(text[num % 3])
        txt.set_x(x[num])
        txt.set_y(y[num])
        return txt,

    anim = constructor(fig, update_text, range(size),
                       init_func=init if use_init else None)
    plt.close(fig)
    return get_frames(anim, size)


def compare_svgs(tmpdir, expected, actual, tol=0):
    expected_path = Path(tmpdir, "expected.svg")
    actual_path = Path(tmpdir, "actual.svg")

    with open(expected_path, 'w') as f:
        f.write(expected)

    with open(actual_path, 'w') as f:
        f.write(actual)

    new_expected_path = convert(expected_path, False)
    new_actual_path = convert(actual_path, False)

    _raise_on_image_difference(new_expected_path, new_actual_path, tol=tol)


@pytest.mark.parametrize("index", [0, 4, 9])
def test_svg_validity(index):
    svg_frame = get_line_anim_frames(SVGFuncAnimation, 10, fmt='r-')[index]
    parser = xml.parsers.expat.ParserCreate()
    parser.Parse(svg_frame)  # this will raise ExpatError if the svg is invalid


def test_cleanup_temporaries(tmpdir):
    with tmpdir.as_cwd():
        get_line_anim_frames(SVGFuncAnimation, 10, fmt='r-')
        assert list(Path(str(tmpdir)).iterdir()) == []


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("anim_type", [get_line_anim_frames, get_text_anim_frames])
def test_init_func(tmpdir, anim_type, index):
    svg_init_frame = anim_type(SVGFuncAnimation, 3, use_init=True)[index]
    svg_frame = anim_type(SVGFuncAnimation, 3, use_init=False)[index]
    compare_svgs(tmpdir, svg_frame, svg_init_frame, tol=0)


@pytest.mark.parametrize("index", [0, 4, 9])
@pytest.mark.parametrize("marker", ['bo', 'g^', 'r1', 'cp', 'm*', 'yX', 'kD'])
def test_line_animation(tmpdir, marker, index):
    func_frame = get_line_anim_frames(FuncAnimation, 10, fmt=marker)[index]
    svg_frame = get_line_anim_frames(SVGFuncAnimation, 10, fmt=marker)[index]
    compare_svgs(tmpdir, func_frame, svg_frame, tol=0)


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("math_mode", [True, False])
def test_text_animation(tmpdir, math_mode, index):
    func_frame = get_text_anim_frames(FuncAnimation, 3, math_mode=math_mode)[index]
    svg_frame = get_text_anim_frames(SVGFuncAnimation, 3, math_mode=math_mode)[index]
    compare_svgs(tmpdir, func_frame, svg_frame, tol=0)


# TODO:
#   [ ] Add + test embed limit rcParam
#   [ ] Add + Test frames param int/generator/None
#   [x] Test proper cleanup of tempdir
#   [\] Test other plot types (scatter, hist, (math)text, legends)
#       - Scatter/Hist not needed as we test for basic markers already
#       - Text works differently, we need a test
#   [x] Test grab_frame returns valid XML doc
#   [x] Test init_func vs no init_func
#   [ ] Test user func returns unknown artist
#   [ ] Test user func returns None
#       - Is this something we should support?
#         We would need to track what artists changed, OR redraw all...
#   [ ] Test artist with no initial draw (i.e: Text w/ empty str)
#   -----------------------
#   Refactor tests w/ better fixtures + skip_ifs (if needed?)
#   Move test failure images (diffs, etc) to non-tempdir
