import matplotlib
from matplotlib import pyplot
import io

def plot(points: dict, no: int):
    fig, ax = pyplot.subplots()
    ax.plot(list(points.keys()), list(points.values()))
    ax.grid()
    ax.set(label=f"Graph {no}")
    b = io.BytesIO()
    fig.savefig(b)
    b.seek(0)
    pyplot.close(fig)

    return b
