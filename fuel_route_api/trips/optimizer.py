"""
Pure fuel-stop optimizer (no Django, no I/O) -> easy to unit test.

Classic "gas station" greedy, optimal for minimising cost with a variable fill:
  * at each stop, if a CHEAPER stop is reachable on the current range, buy only
    enough fuel to reach the first such stop;
  * otherwise fill the tank and drive to the cheapest reachable stop.
The trip starts with an empty tank, so the origin is a virtual stop
(priced at the nearest real station) and the destination is a $0 sentinel.
"""
from dataclasses import dataclass, field

EPS = 1e-6


class NoFeasiblePlan(Exception):
    pass


@dataclass
class Candidate:
    station_idx: int
    mile: float
    price: float
    detour: float


@dataclass
class Purchase:
    candidate: Candidate | None   # None => the initial fill at the origin
    price: float
    miles_bought: float
    gallons: float = field(init=False)
    cost: float = field(init=False)

    def __post_init__(self):
        self.gallons = 0.0
        self.cost = 0.0


@dataclass
class _Node:
    mile: float
    price: float
    candidate: Candidate | None


def plan_fuel_stops(candidates, total_miles, start_price, range_miles=500.0, mpg=10.0):
    nodes = [_Node(0.0, start_price, None)]
    nodes += [_Node(c.mile, c.price, c) for c in sorted(candidates, key=lambda c: c.mile) if 0 < c.mile < total_miles]
    nodes.append(_Node(total_miles, 0.0, None))

    last, i, fuel = len(nodes) - 1, 0, 0.0
    purchases = []
    while i < last:
        cur = nodes[i]
        reach = cur.mile + range_miles + EPS
        window = []
        j = i + 1
        while j <= last and nodes[j].mile <= reach:
            window.append(j)
            j += 1
        if not window:
            raise NoFeasiblePlan(
                f"No fuel station within {range_miles:.0f} miles after mile {cur.mile:.0f}."
            )
        cheaper = next((k for k in window if nodes[k].price < cur.price), None)
        if cheaper is not None:
            nxt, buy = cheaper, max(0.0, nodes[cheaper].mile - cur.mile - fuel)
        else:
            nxt = min(window, key=lambda k: (nodes[k].price, nodes[k].mile))
            buy = max(0.0, range_miles - fuel)
        if buy > EPS:
            p = Purchase(cur.candidate, cur.price, buy)
            p.gallons = buy / mpg
            p.cost = p.gallons * cur.price
            purchases.append(p)
        fuel = max(0.0, fuel + buy - (nodes[nxt].mile - cur.mile))
        i = nxt
    return purchases
