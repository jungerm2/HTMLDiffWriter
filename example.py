import matplotlib.animation as manim
import matplotlib.pyplot as plt
import numpy as np

from HTMLDiffWriter import HTMLDiffWriter

np.random.seed(0)
plt.rcParams['animation.embed_limit'] = 2 ** 128
plt.rcParams['animation.frame_format'] = 'svg'


def update_line(num, data, line):
    line.set_data(range(num), data[:num])
    return line,


size = 10
fig = plt.figure()
data = np.random.rand(size)
l, = plt.plot([], [], 'r-')
plt.xlim(0, size - 1)
plt.ylim(0, 1)

anim = manim.FuncAnimation(fig, update_line, range(1, size + 1), fargs=(data, l),
                           interval=50, blit=True)

# Write both to disc for comparison
writer = manim.HTMLWriter(embed_frames=True)
anim.save('anim.html', writer=writer)

diff_writer = HTMLDiffWriter(embed_frames=True)
anim.save('anim_diff.html', writer=diff_writer)
