// 1:8 scale articulated resin replica kit of the Barney tail (Anycubic Photon Mono 5s)
// ----------------------------------------------------------------------------------
// One piece per vertebra: snap-fit socket cup (3 flex slits) at the proximal end, ball on a
// kinked neck (rest curve built in) at the distal end, fins + skin ring, mushroom pegs for
// orthodontic elastics ("springs") and a twine bore ("cord"). Dimensions follow the full-size
// Barney variant (suit_tail_barney.scad) scaled 1:8, with resin-safe minimums.
//
// MINI = "vertebra" (INDEX 1..N) | "hip" | "stand" | "coupon" | "assembly"
include <suit_tail_barney.scad>
PART = "none";                 // silence the full-size dispatcher
MINI = "assembly";

S = 1 / 8;
mclear   = 0.08;               // ball-socket radial clearance (resin); tune with the coupon
cup_wall = 0.9;
slit_w   = 0.45;
fin_tm   = 0.8;                // resin-safe minimum wall
bore_m   = 0.65;               // Ø1.3 mm twine bore
peg_r    = 0.45; peg_len = 1.3; peg_head = 0.75;
$fn = 40;

Lm = L * S;
function Rb(j)   = max(RB(j) * S, 2.4);
function Rsk(j)  = Rb(j) + mclear;
function rnk(j)  = max(0.42 * Rb(j), 1.0);
function x1m(j)  = 0.45 * Rb(j) + 1.4;                  // neck stays on the child axis this far from the ball
function wm(j)   = max(spring_arm(j) * S, Rsk(j) + cup_wall + 1.2);
function RFm(i)  = max(RF(i) * S, wm(i) + 0.8);
function apm(j)  = max(span_parent(j) * S, x1m(j) + 2.5);
function rsp(i)  = max(1.4, (i < N ? rnk(i + 1) : 1.2) + 0.3);
function spine_end(i) = Lm - (i < N ? x1m(i + 1) + 2.2 : 0);

module rod(a, b, r) { hull() { translate(a) sphere(r = r); translate(b) sphere(r = r); } }
module az(a) { rotate([a, 0, 0]) children(); }             // about X: 0 dorsal (+Z), 90 -> -Y, 180 ventral, 270 -> +Y

// mushroom peg pointing radially outward from `base` (in the plane of azimuth a)
module peg(pos) {
    translate(pos) {
        cylinder(r = peg_r, h = peg_len, $fn = 16);
        translate([0, 0, peg_len]) sphere(r = peg_head, $fn = 16);
    }
}

// socket cup for joint j, pivot at the origin, opening toward -X
module cup(j) {
    Rs = Rsk(j); ro = Rs + cup_wall;
    difference() {
        intersection() {
            sphere(r = ro, $fn = 48);
            translate([-0.45 * Rb(j), -ro, -ro]) cube([2 * ro, 2 * ro, 2 * ro]);
        }
        sphere(r = Rs, $fn = 48);
        // flex slits (between the band pegs)
        for (a = [60, 180, 300]) az(a) translate([-0.45 * Rb(j) - 0.1, -slit_w / 2, 0]) cube([0.75 * Rb(j), slit_w, ro + 1]);
        // twine exit toward the child
        rotate([0, 90, 0]) cylinder(r = bore_m, h = ro + 1, $fn = 16);
    }
}

// ears on the cup carrying the child-side pegs of joint j (dorsal, ventral, left, right)
module cup_ears(j) {
    for (a = [0, 90, 180, 270]) az(a) {
        translate([-1.2, -0.7, Rsk(j) + cup_wall - 0.3]) cube([1.2, 1.4, wm(j) - Rsk(j) - cup_wall + 0.3]);
        peg([-0.6, 0, wm(j) - 0.3]);                      // sunk into the tab so it fuses
    }
}

module vertebra_mini(i) {
    d = i < N ? droop(i + 1) : 0;
    E = [spine_end(i), 0, 0];
    difference() {
        union() {
            cup(i);
            cup_ears(i);
            // spine
            rod([Rsk(i) + 0.4, 0, 0], E, rsp(i));
            // fins + mid skin ring
            x0 = Rsk(i) - 0.2; x2 = spine_end(i) + (i < N ? 1.2 : -1);
            for (a = [0, 90, 180, 270]) az(a) translate([x0, -fin_tm / 2, 0]) cube([x2 - x0, fin_tm, RFm(i)]);
            translate([0.5 * (x0 + x2), 0, 0]) rotate([0, 90, 0]) difference() {
                cylinder(r = RFm(i), h = 0.8, $fn = 64);
                translate([0, 0, -1]) cylinder(r = RFm(i) - 0.8, h = 3, $fn = 64);
            }
            if (i < N) {
                // kinked neck and the ball of joint i+1 (rest bend d built in)
                K = [Lm, 0, 0] + [-x1m(i + 1) * cos(d), 0, x1m(i + 1) * sin(d)];
                rod(E, K, rnk(i + 1));
                translate([Lm, 0, 0]) rotate([0, d, 0]) {
                    rotate([0, -90, 0]) cylinder(r = rnk(i + 1), h = x1m(i + 1));
                    sphere(r = Rb(i + 1), $fn = 48);
                }
                // parent-side pegs for joint i+1: placed in the child's rest frame, braced to the fins
                for (a = [0, 90, 180, 270]) {
                    P = [Lm, 0, 0] + [[cos(d), 0, sin(d)], [0, 1, 0], [-sin(d), 0, cos(d)]] *
                        ([-apm(i + 1), -sin(a) * wm(i + 1), cos(a) * wm(i + 1)]);
                    hull() {
                        translate(P) sphere(r = 0.7, $fn = 16);
                        az(a) translate([spine_end(i) - 1.5, 0, min(RFm(i), wm(i + 1)) - 0.8]) sphere(r = 0.7, $fn = 16);
                    }
                    translate([Lm, 0, 0]) rotate([0, d, 0]) az(a) peg([-apm(i + 1), 0, wm(i + 1)]);
                }
            } else {
                // last vertebra carries the (rigid, at this scale) foam tip
                tl = (tail_length - mech_length) * S;
                translate([spine_end(i) - 1.5, 0, 0]) rotate([0, 90, 0])
                    cylinder(r1 = last_mech_diameter / 2 * S, r2 = tip_diameter / 2 * S, h = tl);
                translate([spine_end(i) - 1.5 + tl, 0, 0]) sphere(r = tip_diameter / 2 * S);
            }
        }
        // twine path
        if (i < N) {
            d2 = droop(i + 1);
            K = [Lm, 0, 0] + [-x1m(i + 1) * cos(d2), 0, x1m(i + 1) * sin(d2)];
            rod([-1, 0, 0], E, bore_m);
            rod(E, K, bore_m);
            translate([Lm, 0, 0]) rotate([0, d2, 0]) {
                rotate([0, -90, 0]) cylinder(r = bore_m, h = x1m(i + 1) + 0.1, $fn = 16);
                rotate([0, 90, 0]) cylinder(r1 = bore_m, r2 = bore_m + Rb(i + 1) * tan(40), h = Rb(i + 1) + 0.2, $fn = 24);
            }
        } else {
            rod([-1, 0, 0], [spine_end(i) + 2, 0, 0], bore_m);
            translate([spine_end(i) + 2, 0, 0]) rotate([180, 0, 0]) cylinder(r = bore_m, h = 12, $fn = 16);   // tie-off exit (ventral)
        }
    }
}

// ---- hip mount + lumbar-belt plate (1:8) ---------------------------------------------------
module root_frame_m() { translate([-root_back_offset * S, 0, root_dz * S]) rotate([0, 180 - root_pitch, 0]) rotate([180, 0, 0]) children(); }

module hip_mini() {
    pt = max(hip_plate_t * S, 1.6);
    E = [-apm(1) - 1.5, 0, 0];
    difference() {
        union() {
            translate([-harness_plate_offset * S - pt, -hip_plate_w * S / 2, plate_z * S - hip_plate_h * S / 2])
                cube([pt, hip_plate_w * S, hip_plate_h * S]);
            // boss to the ball of joint 1 (joint-1 rest bend is part of the root pitch)
            hull() {
                translate([-harness_plate_offset * S - pt, 0, root_dz * S]) rotate([0, 90, 0]) cylinder(r = 2.6, h = 0.5);
                root_frame_m() translate(E) sphere(r = 2.0);
            }
            root_frame_m() {
                rod(E, [-x1m(1), 0, 0], rnk(1));
                rotate([0, -90, 0]) cylinder(r = rnk(1), h = x1m(1));
                sphere(r = Rb(1), $fn = 48);
                for (a = [0, 90, 180, 270]) az(a) {
                    hull() { translate([-apm(1), 0, wm(1)]) sphere(r = 0.7); translate([-apm(1) - 1, 0, 1]) sphere(r = 1.0); }
                    peg([-apm(1), 0, wm(1)]);
                }
            }
            // stand tab on the plate's front (body) face
            translate([-harness_plate_offset * S - 0.01, -3, plate_z * S - 5]) cube([3, 6, 10]);
        }
        // twine: through the ball and boss, out of the top of the boss to tie off
        root_frame_m() {
            rod([Rb(1) + 1, 0, 0], E, bore_m);
            translate([Rb(1) * 0.2, 0, 0]) rotate([0, 90, 0]) cylinder(r1 = bore_m, r2 = bore_m + Rb(1) * tan(40), h = Rb(1) + 0.2, $fn = 24);
        }
        root_frame_m() translate(E) rotate([0, 0, 0]) cylinder(r = bore_m, h = 12, $fn = 16);
        // belt-strap slots (miniature, decorative)
        for (y = [-78, 78], z = [-45, 45]) translate([-harness_plate_offset * S - pt - 1, y * S - 0.4, (plate_z + z - 14) * S]) cube([pt + 2, 0.8, 28 * S]);
    }
}

// ---- display stand: floor plate + post with a slot for the hip tab ----------------------------
floor_z = -0.55 * 1727 * S;
module stand_mini() {
    reach = 900 * S;
    difference() {
        union() {
            translate([-reach - 25, -18, floor_z]) cube([reach + 35, 36, 2.5]);
            translate([-harness_plate_offset * S, -8, floor_z]) cube([8, 16, plate_z * S - floor_z + 12]);
        }
        translate([-harness_plate_offset * S - 0.5, -3.15, plate_z * S - 5.15]) cube([3.8, 6.3, 10.3]);
    }
}

// ---- snap-fit test coupon (smallest and largest joint) -----------------------------------------
module coupon() {
    for (k = [0, 1]) { j = k == 0 ? 1 : N;
        translate([k * 14, 0, 0]) { cup(j); translate([0, 12, 0]) { sphere(r = Rb(j), $fn = 48); rotate([0, -90, 0]) cylinder(r = rnk(j), h = 6); } } }
}

// ---- assembled preview ------------------------------------------------------------------------------
module chain_mini(i) {
    if (i <= N) { vertebra_mini(i); translate([Lm, 0, 0]) rotate([0, droop(i + 1 <= N ? i + 1 : N), 0]) chain_mini(i + 1); }
}

if (MINI == "vertebra") vertebra_mini(INDEX);
else if (MINI == "hip") hip_mini();
else if (MINI == "stand") stand_mini();
else if (MINI == "coupon") coupon();
else if (MINI == "assembly") { color("SteelBlue") hip_mini(); color("Silver") stand_mini(); color("DarkOliveGreen") root_frame_m() chain_mini(1); }
