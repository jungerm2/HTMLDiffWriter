import uuid
import xml
import pytest
import base64
import functools
import numpy as np
from pathlib import Path

from PIL import Image
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, HTMLWriter
from matplotlib.backends.backend_svg import RendererSVG
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


def get_frames(anim, size, tmpdir):
    if isinstance(anim, SVGFuncAnimation):
        return [anim.grab_frame(i) for i in range(size)]
    elif isinstance(anim, FuncAnimation):
        with mpl.rc_context({"animation.frame_format": "svg"}):
            path = Path(tmpdir, "temp.html")
            writer = HTMLWriter(embed_frames=True)
            anim.save(str(path), writer=writer)
            return [base64.b64decode(f).decode("ascii") for f in writer._saved_frames[:size]]


def get_line_anim(constructor, size, fmt="r-", use_init=False):
    np.random.seed(0)

    fig = plt.figure()
    data = np.random.rand(size)
    (l,) = plt.plot([], [], fmt)
    plt.xlim(0, size - 1)
    plt.ylim(0, 1)

    def init():
        l.set_data([], [])
        return (l,)

    def update_line(num, data, line):
        line.set_data(range(num+1), data[:num+1])
        return (line,)

    anim = constructor(fig, update_line, range(size), init_func=init if use_init else None, fargs=(data, l),)
    plt.close(fig)
    return anim


@functools.lru_cache
def get_line_anim_frames(constructor, size, tmpdir, fmt="r-", use_init=False):
    anim = get_line_anim(constructor, size, fmt=fmt, use_init=use_init)
    return get_frames(anim, size, tmpdir)


@functools.lru_cache
def get_text_anim_frames(constructor, size, tmpdir, init_text="", use_init=False, math_mode=False):
    np.random.seed(0)
    simple_text = ["First", "Second", "Third"]
    math_text = [r"$\sum_{i=0}^\infty x_i$", r"$E=mc^2$", r"$c=\sqrt{a^2+b^2}$"]

    fig = plt.figure()
    x, y = np.random.rand(2, size)
    txt = plt.text(0.5, 0.5, init_text, fontsize=15)
    text = math_text if math_mode else simple_text
    plt.xlim(0, 1)
    plt.ylim(0, 1)

    def init():
        txt.set_text(init_text)
        return (txt,)

    def update_text(num):
        txt.set_text(text[num % 3])
        txt.set_x(x[num])
        txt.set_y(y[num])
        return (txt,)

    anim = constructor(fig, update_text, range(size), init_func=init if use_init else None)
    plt.close(fig)
    return get_frames(anim, size, tmpdir)


def compare_svgs(tmpdir, expected, actual, tol=0):
    expected_path = Path(tmpdir, "expected.svg")
    actual_path = Path(tmpdir, "actual.svg")

    with open(expected_path, "w") as f:
        f.write(expected)

    with open(actual_path, "w") as f:
        f.write(actual)

    new_expected_path = convert(expected_path, False)
    new_actual_path = convert(actual_path, False)

    _raise_on_image_difference(new_expected_path, new_actual_path, tol=tol)


@pytest.mark.parametrize("index", [0, 4, 9])
def test_svg_validity(tmpdir, index):
    svg_frame = get_line_anim_frames(SVGFuncAnimation, 10, tmpdir, fmt="r-")[index]
    parser = xml.parsers.expat.ParserCreate()
    parser.Parse(svg_frame)  # this will raise ExpatError if the svg is invalid


def test_cleanup_temporaries(tmpdir):
    with tmpdir.as_cwd():
        get_line_anim_frames(SVGFuncAnimation, 10, tmpdir, fmt="r-")
        assert list(Path(str(tmpdir)).iterdir()) == []


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("anim_type", [get_line_anim_frames, get_text_anim_frames])
def test_init_func(tmpdir, anim_type, index):
    svg_init_frame = anim_type(SVGFuncAnimation, 3, tmpdir, use_init=True)[index]
    svg_frame = anim_type(SVGFuncAnimation, 3, tmpdir, use_init=False)[index]
    compare_svgs(tmpdir, svg_frame, svg_init_frame, tol=0)


@pytest.mark.parametrize("index", [0, 4, 9])
@pytest.mark.parametrize("marker", ["bo", "g^", "r1", "cp", "m*", "yX", "kD"])
def test_line_animation(tmpdir, marker, index):
    func_frame = get_line_anim_frames(FuncAnimation, 10, tmpdir, fmt=marker)[index]
    svg_frame = get_line_anim_frames(SVGFuncAnimation, 10, tmpdir, fmt=marker)[index]
    compare_svgs(tmpdir, func_frame, svg_frame, tol=0)


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("math_mode", [True, False])
@pytest.mark.parametrize("init_text", ["", "non-empty-text"])
def test_text_animation(tmpdir, init_text, math_mode, index):
    func_frame = get_text_anim_frames(FuncAnimation, 3, tmpdir, init_text=init_text, math_mode=math_mode)[index]
    svg_frame = get_text_anim_frames(SVGFuncAnimation, 3, tmpdir, init_text=init_text, math_mode=math_mode)[index]
    compare_svgs(tmpdir, func_frame, svg_frame, tol=0)


@pytest.mark.parametrize("frames, save_count", [
    [10, None], [range(10), None], [iter(range(10)), 10], [lambda: range(10), 10]
])
def test_frames_param_type(monkeypatch, frames, save_count):
    def mock_uuid(*args, **kwargs):
        class DummyUUID:
            hex = 'ABCDEF'
        return DummyUUID()

    def mock_make_id(*args, **kwargs):
        return 'dummyid1234'

    def get_anim(frames, save_count, size=10):
        np.random.seed(0)
        fig = plt.figure()
        data = np.random.rand(size)
        (l,) = plt.plot([], [], 'r-')
        plt.xlim(0, size-1)
        plt.ylim(0, 1)
        index = 0

        def update_line(ununsed):
            nonlocal index
            l.set_data(range(index + 1), data[:index + 1])
            index += 1
            return (l,)

        anim = SVGFuncAnimation(fig, update_line, frames, save_count=save_count)
        anim.grab_frames()
        plt.close(fig)
        return anim._embedded_frames

    # Remove all randomness associated with unique ids in the end SVG
    # this enables us to compare the SVGs directly without inkscape
    monkeypatch.setattr(uuid, 'uuid4', mock_uuid)
    monkeypatch.setattr(RendererSVG, '_make_id', mock_make_id)
    assert get_anim(range(10), 10) == get_anim(frames, save_count)


def test_embed_limit(caplog, tmpdir):
    caplog.set_level("WARNING")
    with tmpdir.as_cwd():
        with mpl.rc_context({"animation.embed_limit": 1e-6}):  # ~1 byte.
            anim = get_line_anim(SVGFuncAnimation, 2, fmt='r-')
            anim.grab_frames()
    assert len(caplog.records) == 1
    # record, = caplog.records
    # assert (record.name == "matplotlib.animation"
    #         and record.levelname == "WARNING")


# TODO:
#   [x] Add + test embed limit rcParam
#   [x] Add + Test frames param int/generator/None
#   [x] Test proper cleanup of tempdir
#   [x] Test other plot types (scatter, hist, (math)text, legends)
#       - Scatter/Hist not needed as we test for basic markers already
#       - Text works differently, we need a test
#   [x] Test grab_frame returns valid XML doc
#   [x] Test init_func vs no init_func
#   [ ] Test user func returns unknown artist
#       - This currently throws an error, can we instead redraw the whole
#         thing, figure out what's changed and only emit a (performance) warning?
#   [ ] Test user func returns None
#       - Is this something we should support?
#         We would need to track what artists changed, OR redraw all...
#           * We can set everything in the figure to animated and then redraw all
#             artists that are stale, visible and aren't empty Text artists. This
#             kinda works but probably isn't really viable.
#   [x] Test artist with no initial draw (i.e: Text w/ empty str)
#   -----------------------
#   Refactor tests w/ better fixtures + skip_ifs (if needed?)
#   Move test failure images (diffs, etc) to non-tempdir
