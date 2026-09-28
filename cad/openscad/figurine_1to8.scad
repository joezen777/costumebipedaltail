// 1:8 scale low-poly display figurine: skinny 5 ft 8 in (1727 mm) male body with a protogen head
// ----------------------------------------------------------------------------------------
// Resin (Anycubic Photon Mono 5s) companion to the 1:8 tail kit (mini_kit.scad). A raised
// "cyber spine" rail on the back carries a T-channel: the kit's lumbar-belt plate
// (01_hip_mount_plate) slides down into it from the top, its stand tab running in the centre
// groove and its edges captured behind two lips. A pin pushed through a pair of lip holes
// stops the plate at that level, so the tail can be tried at different heights.
//
// Frame: the pelvis frame of the tail CAD, scaled 1:8. Origin = pelvis centre at 0.55 H above
// the floor, +X forward (the tail hangs toward -X), +Z up, +Y the figure's left.
// At DZ = 0 the plate sits exactly where the full-size design puts it (plate_z above the
// pelvis centre, front face harness_plate_offset behind it).
//
// FIG = "body" | "head" | "base" | "pin" | "assembly" | "none"
include <mini_kit.scad>
MINI = "none";                 // silence the kit dispatcher
FIG = "assembly";

H   = 1727 * S;                // 215.9 mm figure height (to the crown of a human head)
fz  = -0.55 * 1727 * S;        // floor, -118.7 (same floor as the kit's display stand)
LP = 8;                        // low-poly facet count for all organic shapes
$fn = 8;                       // = LP (a literal: $fn is first assigned in mini_kit.scad, before LP exists)

// ---- plate / channel geometry (all from the kit's hip plate) -------------------------------
pt      = max(hip_plate_t * S, 1.6);           // 1.6 plate thickness
pfx     = -harness_plate_offset * S;           // -15.0 plate front (body) face
pw      = hip_plate_w * S;                     // 23.75
ph      = hip_plate_h * S;                     // 18.75
pz      = plate_z * S;                         // 5.0 plate centre at the design level
c_x     = 0.20;                                // channel clearance behind the plate (x)
c_y     = 0.20;                                // channel clearance at each plate edge (y)
mouth   = 10.3;                                // half-width of the opening between the lips
lip_t   = 1.5;                                 // lip thickness (x)
rail_hw = 14.6;                                // rail half-width
rail_front = -8.0;                             // rail is fused into the body forward of this
tab_hw  = 3.0 + 0.25;                          // stand tab: 6 wide ...
tab_d   = 3.0 + 0.4;                           // ... 3 deep
DZ_MIN  = -16;                                 // lowest level (plate sits on the channel floor)
LEVELS  = [for (d = [-12 : 4 : 36]) d];        // pin rows: plate raised by d mm (1:8) from design
pin_r   = 0.5;  pin_hole_r = 0.6;  pin_y = 11.25;
ch_bot  = pz - ph / 2 + DZ_MIN - 0.1;          // -20.5
rail_bot = ch_bot - 1.6;
rail_top = pz + ph / 2 + LEVELS[len(LEVELS) - 1] + 3.5;
lip_back = pfx - pt - c_x - lip_t;             // -18.3 outer face of the lips

// ---- primitives ---------------------------------------------------------------------------------
module ell(c, r, k = 0) translate(c) scale([max(r[0] - k, 0.2), max(r[1] - k, 0.2), max(r[2] - k, 0.2)]) sphere(r = 1);
module cap(a, b, ra, rb) hull() { translate(a) sphere(r = ra); translate(b) sphere(r = rb); }
module mir() { children(); mirror([0, 1, 0]) children(); }

// ---- body -------------------------------------------------------------------------------------------
// torso cross-sections: [centre, radii]; the union of consecutive hulls keeps the lumbar curve
TS = [
    [[-1.0, 0, -12], [11.0, 17.5, 5]],        // crotch / lower pelvis
    [[-1.5, 0,  -2], [12.0, 18.8, 6]],        // hips (greater trochanter)
    [[ 0.5, 0,  14], [10.6, 15.3, 5]],        // waist
    [[ 1.8, 0,  34], [12.6, 17.8, 8]],        // chest
    [[ 0.0, 0,  50], [10.0, 19.2, 6]],        // shoulder girdle
];
module torso(k = 0) {
    for (i = [0 : len(TS) - 2]) hull() { ell(TS[i][0], TS[i][1], k); ell(TS[i + 1][0], TS[i + 1][1], k); }
    mir() {
        ell([-5.5, 8, -9], [8, 8.5, 9], k);           // glutes
        ell([-5.5, 9, 42], [6.5, 7.5, 9], k);         // shoulder blades
    }
}

module arm() {
    Sh = [0, 20, 51]; E = [-1.5, 23.5, 17.5]; W = [1.0, 25.5, -13];
    ell([0, 19.5, 52], [5.5, 5.2, 6.2]);                      // deltoid
    hull() { translate(Sh) sphere(r = 4.2); ell([-0.5, 22.0, 36], [4.2, 4.1, 9]); translate(E) sphere(r = 3.2); }   // upper arm
    hull() { translate(E) sphere(r = 3.3); ell([-0.3, 24.2, 8], [3.7, 3.4, 7]); translate(W) sphere(r = 2.3); }     // forearm
    hull() {                                                    // hand, palm toward the thigh
        ell(W + [0.4, 0.2, -2.0], [3.3, 1.8, 2.5]);
        ell([2.0, 26.3, -25.5], [4.4, 1.8, 5.0]);
        ell([2.2, 26.5, -33.5], [2.8, 1.5, 3.2]);
    }
    cap([3.8, 25.2, -17], [5.6, 24.4, -24], 1.2, 1.0);        // thumb
}

module leg() {
    Hp = [0, 10, -4]; K = [0.8, 8.8, -57]; A = [-0.5, 8.3, -110.3];
    hull() { translate(Hp) sphere(r = 8.6); ell([1.2, 9.8, -24], [7.0, 7.0, 12]); ell(K + [0.4, 0, 0], [5.2, 5.0, 5.0]); }   // thigh
    hull() { ell(K + [0.4, 0, 0], [5.0, 4.8, 5.0]); ell([-1.6, 8.7, -72], [4.9, 4.6, 11]); translate(A) sphere(r = 2.9); }  // shin + calf
    hull() {                                                    // foot, toes turned out a little
        ell(A, [3.0, 3.2, 3.0]);
        ell([-3.5, 8.3, fz + 3.2], [3.0, 3.0, 3.2]);
        ell([17.0, 9.8, fz + 2.3], [4.5, 5.2, 2.3]);
        ell([23.5, 10.4, fz + 1.7], [3.0, 4.4, 1.7]);
        translate([-3.5, 8.3, fz]) scale([2.6, 2.6, 1]) cylinder(r = 1, h = 0.4);     // flat sole
        translate([19.0, 10.0, fz]) scale([6.5, 4.4, 1]) cylinder(r = 1, h = 0.4);
    }
    translate([7, 9.2, fz - 3]) cylinder(r = 1.5, h = 3.01, $fn = 20);   // base peg
}

module neck() hull() { ell([-0.8, 0, 50], [6.4, 6.4, 3]); translate([0, 0, 68.9]) cylinder(r = 5.8, h = 0.1, $fn = LP); }

module rail() hull() {
    for (y = [-rail_hw + 1, rail_hw - 1], z = [rail_bot + 1, rail_top - 1]) translate([lip_back + 1, y, z]) sphere(r = 1, $fn = LP);
    for (y = [-rail_hw - 1.5, rail_hw + 1.5], z = [rail_bot + 4, rail_top + 1]) translate([rail_front, y, z]) sphere(r = 1, $fn = LP);
}

module body_solid() {
    torso(); neck(); rail();
    mir() { arm(); leg(); }
    translate([0, 0, 69]) cylinder(r = 1.95, h = 4, $fn = 24);                     // head peg (Ø3.9)
    translate([0, 0, 72.6]) cylinder(r1 = 1.95, r2 = 1.6, h = 0.4, $fn = 24);
}

// T-channel + tab groove, open at the top
module channel() {
    top = rail_top + 20;
    translate([pfx - pt - c_x, -(pw / 2 + c_y), ch_bot]) cube([pt + c_x, pw + 2 * c_y, top - ch_bot]);
    translate([lip_back - 5, -mouth, ch_bot]) cube([5 + lip_t + 0.01, 2 * mouth, top - ch_bot]);
    translate([pfx - 0.1, -tab_hw, ch_bot]) cube([tab_d + 0.1, 2 * tab_hw, top - ch_bot]);
    // the plate's boss and joint-1 ball hang below the plate edge: open the mouth and a centre
    // slot out through the rail bottom so they pass; the plate edges still land on the floor
    translate([lip_back - 5, -mouth, rail_bot - 5]) cube([5 + lip_t + 0.01, 2 * mouth, ch_bot - rail_bot + 5.01]);
    translate([lip_back - 5, -tab_hw, rail_bot - 5]) cube([5 + lip_t + pt + c_x + tab_d, 2 * tab_hw, ch_bot - rail_bot + 5.01]);
    // top lead-in: chamfer the lips so the plate finds the channel
    translate([0, 0, rail_top - 1.2]) hull() {
        translate([lip_back - 0.01, -mouth, 0]) cube([0.01, 2 * mouth, 0.01]);
        translate([lip_back - 0.01, -mouth - 1.2, 1.3]) cube([lip_t + 0.02, 2 * mouth + 2.4, 0.01]);
    }
}

// level pins: holes through both lips into the rail, one pair per level
module pin_holes() for (d = LEVELS, s = [-1, 1]) {
    z = pz - ph / 2 + d - pin_hole_r - 0.05;
    translate([lip_back - 1, s * pin_y, z]) rotate([0, 90, 0]) cylinder(r = pin_hole_r, h = lip_t + pt + c_x + 1 + 2.2, $fn = 16);
}

// tick marks on the rail sides at each level; the design level (DZ = 0) gets a long one
module ticks() for (d = concat([DZ_MIN], LEVELS), s = [-1, 1]) {
    z = pz - ph / 2 + d;
    len_ = d == 0 ? 6 : 2.5;
    translate([lip_back + 0.8, s * rail_hw - 0.3, z - 0.25]) cube([len_, 0.6, 0.5]);
}

module cavity() {
    intersection() {
        torso(2.0);
        translate([-9.2, -40, -8]) cube([40, 80, 54]);
    }
    translate([0, 0, -26]) cylinder(r = 1.2, h = 20, $fn = 16);                                   // drain through the crotch
    translate([pfx, 0, 40]) rotate([0, 90, 0]) cylinder(r = 1.0, h = 8, $fn = 16);                // vent into the tab groove
}

module body() {
    difference() {
        intersection() { body_solid(); translate([-100, -100, fz - 3]) cube([200, 200, 300]); }
        channel(); pin_holes(); ticks(); cavity();
    }
}

// ---- protogen head (head frame: origin on the neck top, +X forward) ----------------------------------
module helmet(k = 0) hull() {
    ell([-2.0, 0, 13.0], [12.5, 11.2, 12.0], k);      // cranium
    ell([12.5, 0, 8.6], [9.5, 8.2, 6.4], k);          // snout / visor dome
}
module visor_zone() intersection() {
    translate([1.0, -30, 0]) rotate([0, 14, 0]) cube([60, 60, 60]);           // forehead edge
    translate([-30, -30, 3.2]) rotate([0, -4, 0]) cube([80, 60, 60]);         // above the jaw line
}
// pixel LED face (eyes + zigzag mouth), recessed through the visor panel
PX = 0.8; PP = 1.0;
EYE = [[1, 0], [2, 0], [3, 0], [0, 1], [1, 1], [2, 1], [3, 1], [4, 1], [0, 2], [1, 2], [2, 2], [3, 2], [1, 3], [2, 3]];
MOUTH = [for (i = [-6 : 6]) [i, [0, 1, 2, 1][(i + 12) % 4]]];
module face_pixels() {
    for (s = [-1, 1], p = EYE) translate([0, s * (1.6 + p[0] * PP) - (s < 0 ? PX : 0), 13.6 - p[1] * PP]) cube([40, PX, PX]);
    for (p = MOUTH) translate([0, p[0] * PP - PX / 2, 6.0 + p[1] * PP * 0.8]) cube([40, PX, PX]);
}
module visor() difference() {
    intersection() { helmet(-0.4); visor_zone(); }
    face_pixels();
}
module ear() {
    a = [-3, 3.8, 21.5]; b = [-4.5, 10.2, 17.5]; c = [-8.0, 9.8, 34.0];
    n = cross(b - a, c - a) / norm(cross(b - a, c - a));          // faces forward
    m = (a + b + c) / 3;
    difference() {
        hull() { translate(a) sphere(r = 1.6, $fn = LP); translate(b) sphere(r = 1.6, $fn = LP); translate(c) sphere(r = 0.6, $fn = LP); }
        hull() for (p = [a, b, c]) translate(p + 0.3 * (m - p) + 1.25 * n) sphere(r = 0.7, $fn = LP);   // inner ear
    }
    hull() { translate(a + [1, -1, -2]) sphere(r = 2.0, $fn = LP); translate(b + [1, -1, -1]) sphere(r = 1.8, $fn = LP); }   // ear root
}
module side_disc() translate([-1.5, 10.6, 12.5]) rotate([-90, 0, 0]) difference() {
    union() { cylinder(r = 4.6, h = 1.2, $fn = 16); translate([0, 0, 1.2]) cylinder(r1 = 4.6, r2 = 4.1, h = 0.5, $fn = 16); translate([0, 0, 1.3]) sphere(r = 1.7, $fn = LP); }
    translate([0, 0, 1.3]) difference() { cylinder(r = 3.5, h = 2, $fn = 16); cylinder(r = 2.9, h = 2, $fn = 16); }   // LED ring groove
}
module ruff() for (a = [0 : 30 : 330]) rotate([0, 0, a]) ell([6.5, 0, 0.5], [4.2, 3.4, 4.2]);    // fur collar tufts

module head() {
    difference() {
        union() {
            helmet(); visor();
            ell([8.5, 0, 3.6], [7.8, 7.4, 3.8]);                          // furry lower jaw
            mir() { ear(); side_disc(); }
            ruff();
        }
        translate([0, 0, -10]) cylinder(r = 6.1, h = 10, $fn = 16);       // sits over the neck top
        translate([0, 0, -1]) cylinder(r = 2.1, h = 6, $fn = 24);         // peg socket (Ø4.2)
    }
}
HEAD_POS = [0, 0, 69];

// ---- display base + level pin --------------------------------------------------------------------
module base() {
    difference() {
        hull() for (x = [-44, 30], y = [-26, 26]) translate([x, y, fz - 4]) cylinder(r = 6, h = 4, $fn = LP);
        mir() translate([7, 9.2, fz - 3.3]) cylinder(r = 1.7, h = 4, $fn = 20);
    }
}
module pin() { cylinder(r = pin_r, h = 6.5, $fn = 16); translate([0, 0, 6.5]) cylinder(r = 1.1, h = 0.7, $fn = 20); }

// ---- the kit's tail, posed from its exported STLs (renders / checks only) ---------------------------
KIT_DIR = "../stl/replica_1to8_resin/";
KIT_V = ["11_vertebra_1", "12_vertebra_2", "13_vertebra_3", "14_vertebra_4", "15_vertebra_5", "16_vertebra_6"];
DZ = 0;                                                    // plate raise from the design level
module place(i) { if (i <= 1) children(); else place(i - 1) translate([Lm, 0, 0]) rotate([0, droop(i), 0]) children(); }
module kit_tail(dz = DZ) translate([0, 0, dz]) {
    color("SteelBlue") import(str(KIT_DIR, "01_hip_mount_plate.stl"));
    color("DarkOliveGreen") root_frame_m() for (i = [1 : N]) place(i) import(str(KIT_DIR, KIT_V[i - 1], ".stl"));
}

if (FIG == "body") body();
else if (FIG == "head") head();
else if (FIG == "base") base();
else if (FIG == "pin") pin();
else if (FIG == "visor") visor();                        // render helper only (colour the visor)
else if (FIG == "tail_posed") root_frame_m() place(INDEX) import(str(KIT_DIR, KIT_V[INDEX - 1], ".stl"));
else if (FIG == "assembly") {
    color("Wheat") body(); color("DimGray") base();
    translate(HEAD_POS) color("WhiteSmoke") head();
}
