import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as manim

from HTMLDiffWriter import HTMLDiffWriter, _add_base64_prefix, _diff_frames


def get_animation(size, frame_format='svg'):
    np.random.seed(0)
    plt.rcParams['animation.frame_format'] = frame_format

    def update_line(num, data, line):
        line.set_data(range(num), data[:num])
        return line,

    fig = plt.figure()
    data = np.random.rand(size)
    l, = plt.plot([], [], 'r-')
    plt.xlim(0, size - 1)
    plt.ylim(0, 1)

    return manim.FuncAnimation(fig, update_line, range(1, size + 1), fargs=(data, l),
                               interval=50, blit=True)


def apply_patch(base, patch):
    target = list(base)
    for [low, high, data] in patch:
        if data == '':
            for i in range(low, high):
                target[i] = ''
        elif low == high:
            if low >= len(target):
                target.append(data)
            else:
                target[low] = data + target[low]
        else:
            for i in range(low, high):
                target[i] = ''
            target[low] = data
    return ''.join(target)


anim = get_animation(10)
diff_writer = HTMLDiffWriter(embed_frames=True)
anim.save('test_anim.html', writer=diff_writer)

prefixed_frames = [frame.replace('\n', '') for frame in diff_writer._saved_frames]
prefixed_frames = _add_base64_prefix(prefixed_frames, diff_writer.frame_format)

base = prefixed_frames[0]
prev = prefixed_frames[0]
for next in prefixed_frames[1:]:
    patch = _diff_frames(prev, next)
    base = apply_patch(base, patch)
    assert base == next
    prev = next
assert base == prefixed_frames[-1]
