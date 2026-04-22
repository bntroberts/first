import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.ticker import MultipleLocator
import subprocess
import os

# Annual average 10-year treasury yield data 1970-1995 (%)
years = list(range(1970, 1996))
yields = [
    7.35,   # 1970
    6.16,   # 1971
    6.21,   # 1972
    6.84,   # 1973
    7.56,   # 1974
    7.99,   # 1975
    7.61,   # 1976
    7.42,   # 1977
    8.41,   # 1978
    9.44,   # 1979
    11.46,  # 1980
    13.91,  # 1981
    13.00,  # 1982
    11.10,  # 1983
    12.46,  # 1984
    10.62,  # 1985
    7.68,   # 1986
    8.38,   # 1987
    8.85,   # 1988
    8.49,   # 1989
    8.55,   # 1990
    7.86,   # 1991
    7.01,   # 1992
    5.87,   # 1993
    7.09,   # 1994
    6.57,   # 1995
]

# Interpolate to monthly for smoother animation
months_per_year = 12
n_years = len(years)
x_annual = np.array(years, dtype=float)
y_annual = np.array(yields, dtype=float)

# Create dense monthly x values
x_monthly = np.linspace(1970, 1995, (n_years - 1) * months_per_year + 1)
y_monthly = np.interp(x_monthly, x_annual, y_annual)

# Video settings
FPS = 30
DURATION = 10  # seconds
TOTAL_FRAMES = FPS * DURATION
WIDTH, HEIGHT = 1920, 1080
DPI = 100

fig, ax = plt.subplots(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

# Style
ax.spines['bottom'].set_color('#444c56')
ax.spines['left'].set_color('#444c56')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(colors='#adbac7', labelsize=14)
ax.xaxis.label.set_color('#adbac7')
ax.yaxis.label.set_color('#adbac7')

# Axes setup
ax.set_xlim(1970, 1995)
ax.set_ylim(4, 16)
ax.set_xlabel('Year', fontsize=16, color='#adbac7', labelpad=12)
ax.set_ylabel('Yield (%)', fontsize=16, color='#adbac7', labelpad=12)
ax.xaxis.set_major_locator(MultipleLocator(5))
ax.xaxis.set_minor_locator(MultipleLocator(1))
ax.yaxis.set_major_locator(MultipleLocator(2))
ax.yaxis.set_minor_locator(MultipleLocator(1))
ax.grid(which='major', color='#21262d', linewidth=0.8, linestyle='-')
ax.grid(which='minor', color='#161b22', linewidth=0.4, linestyle='-')

# Title
title = fig.text(
    0.5, 0.94,
    'U.S. 10-Year Treasury Yield (1970–1995)',
    ha='center', va='top',
    fontsize=26, fontweight='bold', color='#e6edf3',
    fontfamily='DejaVu Sans'
)
fig.text(
    0.5, 0.885,
    'Annual Average Yield (%)',
    ha='center', va='top',
    fontsize=15, color='#768390',
    fontfamily='DejaVu Sans'
)

# Gradient fill — drawn as static background (full data, invisible initially)
ax.fill_between(x_monthly, y_monthly, 4, alpha=0, color='#388bfd')

# Live line and fill
line, = ax.plot([], [], color='#388bfd', linewidth=2.5, zorder=5)
fill = ax.fill_between([], [], [], alpha=0.0)  # placeholder

# Year label on the right of the line
year_label = ax.text(0, 0, '', ha='left', va='center',
                     fontsize=13, color='#e6edf3',
                     bbox=dict(boxstyle='round,pad=0.3', fc='#161b22', ec='none', alpha=0.8))

# Peak annotation (shown when the line reaches ~1981)
peak_ann = ax.annotate(
    '  Peak: 13.91%\n  Sep 1981',
    xy=(1981, 13.91), xytext=(1983.5, 14.9),
    fontsize=12, color='#ffa657',
    arrowprops=dict(arrowstyle='->', color='#ffa657', lw=1.5),
    bbox=dict(boxstyle='round,pad=0.4', fc='#161b22', ec='#ffa657', alpha=0.0),
    alpha=0.0
)


def init():
    line.set_data([], [])
    year_label.set_text('')
    return line, year_label


def update(frame):
    global fill

    # How far through the data we are (0→1)
    progress = frame / (TOTAL_FRAMES - 1)
    idx = int(progress * (len(x_monthly) - 1))
    idx = max(1, idx)

    xdata = x_monthly[:idx + 1]
    ydata = y_monthly[:idx + 1]

    line.set_data(xdata, ydata)

    # Update fill under the line
    fill.remove()
    fill = ax.fill_between(xdata, ydata, 4,
                           alpha=0.18, color='#388bfd', zorder=3)

    # Moving year label
    cur_year = xdata[-1]
    cur_yield = ydata[-1]
    year_label.set_position((cur_year + 0.1, cur_yield))
    year_label.set_text(f'{cur_yield:.2f}%')

    # Fade in peak annotation once line passes 1982
    if cur_year >= 1982.5:
        fade = min(1.0, (cur_year - 1982.5) / 1.5)
        peak_ann.set_alpha(fade)
        peak_ann.get_bbox_patch().set_alpha(fade * 0.9)
        peak_ann.arrow_patch.set_alpha(fade)

    return line, year_label, fill


anim = animation.FuncAnimation(
    fig, update, frames=TOTAL_FRAMES,
    init_func=init, blit=False, interval=1000 / FPS
)

out_path = '/home/user/first/treasury_yields_1970_1995.mp4'
print(f'Rendering {TOTAL_FRAMES} frames at {FPS}fps → {out_path}')

writer = animation.FFMpegWriter(
    fps=FPS,
    codec='libx264',
    bitrate=8000,
    extra_args=['-pix_fmt', 'yuv420p', '-preset', 'slow', '-crf', '18']
)
anim.save(out_path, writer=writer, dpi=DPI)
print(f'Done. File size: {os.path.getsize(out_path) / 1024 / 1024:.1f} MB')
