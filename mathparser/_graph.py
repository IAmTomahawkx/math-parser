if __name__ != "__main__":
    exit(-1)

import sys, json
from matplotlib import pyplot

target = sys.argv[1]
data = json.loads(sys.argv[2])
kws = data['keys']
no = data['no']

fig, ax = pyplot.subplots()
ax.plot(list(kws.keys()), list(kws.values()))
ax.grid()
ax.set(label=f"Graph {no}")

with open(target, "wb") as f:
    fig.savefig(f)

pyplot.close(fig)
