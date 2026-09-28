"""Run a configuration through the standard motion tests (optionally in parallel)."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

from . import motions
from .metrics import evaluate, score
from .params import TailParams
from .sim import TailSim


def stability(p: TailParams):
    """Lowest small-motion frequencies about the rest pose (negative = unstable)."""
    from .linear import linear_modes
    sim = TailSim(p)
    if p.springs_enabled and "D" not in p.spring_sides or not p.springs_enabled and p.joint_stiffness is None:
        return dict(lowest_mode_hz=float("nan"), modes_hz=[])
    f = linear_modes(sim)[0]
    return dict(lowest_mode_hz=float(f[0]), modes_hz=[round(float(x), 3) for x in f[:6]])


def run_tests(p: TailParams, tests=None, keep=False):
    tests = tests or motions.standard_tests()
    out, raw = {"linear": stability(p)}, {}
    for mo in tests:
        r = TailSim(p).run(mo)
        out[mo.name] = evaluate(r)
        if keep:
            raw[mo.name] = r
    sc, terms = score(out)
    return (out, sc, terms, raw) if keep else (out, sc, terms)


def quick_tests():
    return [motions.hip_snap(), motions.dramatic_turn(), motions.Walk(1.5), motions.Walk(2.0)]


def _job(args):
    p, quick = args
    try:
        out, sc, terms = run_tests(p, quick_tests() if quick else None)
        return p, out, sc, terms
    except Exception as e:  # keep a sweep alive if one configuration is unstable
        return p, {"error": repr(e)}, float("inf"), {}


def run_many(params, quick=True, workers=6):
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(_job, [(p, quick) for p in params]))
