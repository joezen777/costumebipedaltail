"""Parameters and derived geometry for the passive suitmation tail.

All lengths are metres, masses kilograms, angles degrees unless a name says
otherwise. Every value the README asks to expose is a field here; derived
per-vertebra quantities are computed by the ``TailParams`` methods so the
physics model, the CAD generators and the documentation share one source.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
import json
import math

import numpy as np

# README section 28 reference values for an 8-joint tail.
REF_YAW_LIMITS_8 = [8, 10, 12, 15, 18, 20, 24, 28]
REF_MASSES_8 = [0.450, 0.400, 0.330, 0.270, 0.210, 0.160, 0.110, 0.070]

# Named friction levels (README section 11). mu is the ball/socket Coulomb
# coefficient; visc is additional viscous damping per joint in N*m*s/rad at the
# root, scaled by distal inertia toward the tip.
FRICTION_LEVELS = {
    "VERY_LOW": dict(mu=0.05, visc=0.02),   # greased PETG / PTFE tape liner
    "LOW": dict(mu=0.12, visc=0.05),        # dry PETG on PETG, smooth
    "MEDIUM": dict(mu=0.25, visc=0.10),     # felt liner
    "HIGH": dict(mu=0.45, visc=0.20),       # rubber / TPU liner
}


def _interp_list(ref, n, power=1.0):
    """Resample a reference per-joint list to n entries along u = i/(n-1)."""
    ref = np.asarray(ref, float)
    u_ref = np.linspace(0, 1, len(ref))
    u = np.linspace(0, 1, n) ** power if n > 1 else np.zeros(1)
    return np.interp(u, u_ref, ref)


@dataclass
class TailParams:
    # --- performer and mounting -------------------------------------------
    actor_height: float = 1.727            # 5 ft 8 in
    pelvis_height_ratio: float = 0.55      # sacrum height / stature
    root_back_offset: float = 0.20         # pelvis centre -> joint 1 pivot
    root_pitch_deg: float = 15.0           # tail root points down behind the actor
    rest_droop_deg: float = 1.5            # additional rest pitch per joint

    # --- overall size (README 2-4) ----------------------------------------
    joint_count: int = 8
    mech_length: float = 1.2
    foam_tip_length: float = 0.2
    root_diameter: float = 0.190
    last_mech_diameter: float = 0.070
    tip_diameter: float = 0.040
    taper_exponent: float = 1.3
    skin_root: float = 0.020               # foam skin thickness at root
    skin_tip: float = 0.004

    # --- joint limits (README 7-8) ----------------------------------------
    yaw_limits: list | None = None         # per joint, degrees; None -> reference
    progressive_limits: bool = True        # False -> uniform limit = mean of list
    pitch_ratio: float = 0.7
    max_roll: float = 7.0
    roll_unrestricted: bool = False
    stop_timeconst: float = 0.012          # TPU bumper stop softness (s)
    stop_dampratio: float = 0.6

    # --- masses (README 10) -----------------------------------------------
    masses: list | None = None             # None -> reference / resampled
    diameters_override: list | None = None # explicit envelope diameters (m), e.g. a test section
    mass_total: float = 2.000              # used when resampling to other N
    mass_taper: float = 1.16               # exponent of mass(u) when resampled
    foam_tip_mass: float = 0.075
    com_offset: float = 0.015              # COM below the pivot axis (README 9)

    # --- ball/socket and friction (README 5, 11) ---------------------------
    ball_radius_ratio: float = 0.15        # R_ball = ratio * D, clamped
    ball_radius_min: float = 0.017
    ball_radius_max: float = 0.028
    friction: str = "MEDIUM"
    mu: float | None = None                # overrides friction level
    visc: float | None = None
    friction_radius_factor: float = 1.0    # effective friction radius / R_ball

    # --- central cord (README 6) ------------------------------------------
    cord_enabled: bool = True
    cord_diameter: float = 0.006
    cord_preload: float = 10.0             # N
    cord_stiffness: float = 2000.0         # N/m, cord in series with tip spring
    cord_damping: float = 20.0             # N*s/m

    # --- spring spine: passive restoring springs (see docs/physics.md) ------
    springs_enabled: bool = True
    yaw_local_hz: float = 0.7              # per-joint yaw "local" frequency
    pitch_local_hz: float = 1.3
    lateral_preload_margin: float = 0.6    # lateral preload / (k * arm * yaw limit)
    deadband_deg: float = 3.5              # max friction dead band the springs must overcome
    min_mode_hz: float = 0.1               # stiffen lateral springs until the lowest mode exceeds this
    spring_damping: float = 0.0
    spring_override: list | None = None    # [{"k":..,"T0":..}] per spring: reuse built hardware instead of re-designing

    # --- foam tip ----------------------------------------------------------
    tip_bend_stiffness: float = 0.6        # N*m/rad, foam bending
    tip_bend_damping: float = 0.02

    # --- floor contact -----------------------------------------------------
    floor_enabled: bool = True
    floor_friction: float = 0.6

    # --- numerics ----------------------------------------------------------
    dt: float = 0.0005
    record_every: int = 10                 # 200 Hz output at dt = 0.5 ms
    settle_time: float = 2.5

    label: str = "reference"

    # ---------------------------------------------------------------- derived
    @property
    def n(self) -> int:
        return int(self.joint_count)

    @property
    def spacing(self) -> float:
        return self.mech_length / self.n

    @property
    def pivot_height(self) -> float:
        return self.actor_height * self.pelvis_height_ratio

    def u(self) -> np.ndarray:
        return np.linspace(0, 1, self.n) if self.n > 1 else np.zeros(1)

    def diameters(self) -> np.ndarray:
        """Envelope (skin) diameter of each vertebra, README section 4."""
        if self.diameters_override is not None:
            return np.asarray(self.diameters_override, float)
        u = self.u()
        return self.last_mech_diameter + (self.root_diameter - self.last_mech_diameter) * (1 - u) ** self.taper_exponent

    def skin(self) -> np.ndarray:
        u = self.u()
        return self.skin_root + (self.skin_tip - self.skin_root) * u

    def frame_diameters(self) -> np.ndarray:
        return self.diameters() - 2 * self.skin()

    def ball_radii(self) -> np.ndarray:
        """Ball radius of joint i (ball on parent, socket on vertebra i)."""
        return np.clip(self.ball_radius_ratio * self.diameters(), self.ball_radius_min, self.ball_radius_max)

    def yaw_limit_list(self) -> np.ndarray:
        ref = self.yaw_limits if self.yaw_limits is not None else REF_YAW_LIMITS_8
        lim = np.asarray(ref, float) if len(ref) == self.n else _interp_list(ref, self.n)
        if not self.progressive_limits:
            lim = np.full(self.n, float(np.mean(lim)))
        return lim

    def pitch_limit_list(self) -> np.ndarray:
        return self.pitch_ratio * self.yaw_limit_list()

    def mass_list(self) -> np.ndarray:
        if self.masses is not None:
            m = np.asarray(self.masses, float)
            if len(m) != self.n:
                raise ValueError("masses must have joint_count entries")
            return m
        if self.n == 8 and abs(self.mass_taper - 1.16) < 1e-9 and abs(self.mass_total - 2.0) < 1e-9:
            return np.asarray(REF_MASSES_8)
        u = self.u()
        shape = 70 + (450 - 70) * (1 - u) ** self.mass_taper
        return shape / shape.sum() * self.mass_total

    def friction_values(self) -> tuple[float, float]:
        lvl = FRICTION_LEVELS[self.friction]
        mu = lvl["mu"] if self.mu is None else self.mu
        visc = lvl["visc"] if self.visc is None else self.visc
        return mu, visc

    def cad(self):
        """The matching printable-geometry spec (cad/geometry.py, millimetres)."""
        from cad.geometry import CadParams
        return CadParams(
            joint_count=self.n, mech_length=self.mech_length * 1000,
            tail_length=(self.mech_length + self.foam_tip_length) * 1000,
            root_diameter=self.root_diameter * 1000, last_mech_diameter=self.last_mech_diameter * 1000,
            tip_diameter=self.tip_diameter * 1000, taper_exponent=self.taper_exponent,
            skin_root=self.skin_root * 1000, skin_tip=self.skin_tip * 1000,
            cord_diameter=self.cord_diameter * 1000, cord_preload=self.cord_preload,
            max_yaw=list(map(float, self.yaw_limit_list())), pitch_ratio=self.pitch_ratio, max_roll=self.max_roll,
            root_pitch=self.root_pitch_deg, rest_droop=self.rest_droop_deg,
            ball_ratio=self.ball_radius_ratio, ball_min=self.ball_radius_min * 1000, ball_max=self.ball_radius_max * 1000,
            root_back_offset=self.root_back_offset * 1000)

    def spring_arms(self) -> tuple[np.ndarray, np.ndarray]:
        """Radial offsets (lateral, dorsal) of the spring lines of action per
        joint, taken from the printable geometry: they clear the bolted socket
        cap and sit inside the vertebra frame (cad/geometry.py: spring_arm)."""
        from cad import geometry as g
        c = self.cad()
        lat = np.array([g.spring_arm(c, i) for i in range(1, self.n + 1)]) / 1000
        return lat, lat.copy()

    def spring_spans(self) -> tuple[np.ndarray, float]:
        """Parent anchor distance behind each pivot, and the signed x of the child
        anchor in the child frame (negative = proximal of the pivot, on the cap)."""
        from cad import geometry as g
        c = self.cad()
        par = np.array([g.spring_span_parent(c, i) for i in range(1, self.n + 1)]) / 1000
        return par, g.spring_span_child(c) / 1000

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def variant(self, **kw) -> "TailParams":
        return replace(self, **kw)


def configuration_set(base: TailParams | None = None, com: float = 0.015, preload: float = 10.0) -> dict:
    """README section 27 configurations A-D plus reference ablations."""
    base = base or TailParams()
    return {
        "A_friction_only": base.variant(label="A", cord_enabled=False, com_offset=0.0, progressive_limits=False),
        "B_cord_preload": base.variant(label="B", cord_enabled=True, cord_preload=preload, com_offset=0.0, progressive_limits=False),
        "C_offset_com": base.variant(label="C", cord_enabled=True, cord_preload=preload, com_offset=com, progressive_limits=False),
        "D_progressive": base.variant(label="D", cord_enabled=True, cord_preload=preload, com_offset=com, progressive_limits=True),
    }
