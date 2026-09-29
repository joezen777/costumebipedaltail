// Passive suitmation tail - parametric OpenSCAD model
// ----------------------------------------------------------------------------
// Units: millimetres / degrees. Formulas mirror cad/geometry.py (the single
// dimensional spec used by FreeCAD and the physics model); the consistency
// test (tests/test_cad.py) compares the echoed values against it.
//
// Joint frame: origin at the ball centre, +X distal along the tail, +Z dorsal.
// The ball belongs to the parent (hip mount or vertebra i-1); the socket seat,
// the bolted cap and the frame belong to vertebra i.
//
// Printing: PETG, Ender 3 V2 + Sprite Pro, 1.2 mm nozzle, 1.3 mm lines,
// 0.6 mm layers (0.4 mm for ball halves). Every PART_* view below is already
// in print orientation (flat face on z = 0). See docs/printing.md.
//
// Select a view with -D 'PART="..."' -D 'INDEX=n':
//   assembly, vertebra, ball, socket, hip_mount, section, motion_envelope
//   print_ball_left, print_ball_right, print_cap, print_body, print_hip_mount,
//   print_tip_adapter, test_section (4-joint POC), foam_tip
// ----------------------------------------------------------------------------

PART  = "assembly";
INDEX = 1;
POSE  = "neutral";        // neutral | turn | max  (assembly views)

// ---- README section 20 top-level parameters --------------------------------
joint_count        = 8;
tail_length        = 1400;
mech_length        = 1200;
root_diameter      = 190;
last_mech_diameter = 70;
tip_diameter       = 40;
taper_exponent     = 1.3;
cord_diameter      = 6;
cord_preload       = 5;          // N - set with the tip compression spring
max_yaw            = [8, 10, 12, 15, 18, 20, 24, 28];
pitch_ratio        = 0.7;
max_pitch          = [for (y = max_yaw) y * pitch_ratio];
max_roll           = 7;

// ---- secondary parameters --------------------------------------------------
skin_root   = 20;   skin_tip = 4;
root_pitch  = 15;   rest_droop = 1.5;
rest_droop_list = [];      // per-joint rest bends (deg, + = down); overrides rest_droop (variants)
ball_ratio  = 0.15; ball_min = 17;  ball_max = 28;
clear       = 0.4;  liner = 0.5;    stop_pad = 0.8;
line_w      = 1.3;
bolt_clear  = 4.5;  nut_af = 7.0;   nut_h = 3.2;   head_d = 7.0;  head_h = 4.0;
pin_protrude = 3;
cap_ear_x = 5;     spring_hole = 4.5;  coil_od_ratio = 0.08;
root_back_offset = 200;  harness_plate_offset = 120;
root_dz = 0;   plate_z = 0;      // pivot / mounting-plate centre heights relative to the pelvis centre
hip_plate_w = 190;  hip_plate_h = 150;  hip_plate_t = 8;
tip_plug_len = 25;
function fin_t(i) = (RF(i) > 50 ? 3 : 2) * line_w + 0.1;   // 4.0 / 2.7 mm: three or two 1.3 mm lines
fin_t_hip = 3 * line_w + 0.1;
hip_arm_t = 12;

$fn = 72;

// ---- derived (mirrors cad/geometry.py) ---------------------------------------
N  = joint_count;
L  = mech_length / N;
function u(i)      = N > 1 ? (i - 1) / (N - 1) : 0;
function D(i)      = last_mech_diameter + (root_diameter - last_mech_diameter) * pow(1 - u(i), taper_exponent);
function skin(i)   = skin_root + (skin_tip - skin_root) * u(i);
function RF(i)     = D(i) / 2 - skin(i);
function RB(i)     = min(max(ball_ratio * D(i), ball_min), ball_max);
function RS(i)     = RB(i) + clear + liner;
bore_r             = cord_diameter / 2 + 1.0;
function wall(n=3) = n * line_w;
function RN(i)     = max(0.5 * RB(i), bore_r + wall());
function yawl(i)   = max_yaw[i - 1];
function pitchl(i) = max_pitch[i - 1];
function alpha(i)  = asin((RN(i) + stop_pad) / RS(i));
function beta_y(i) = yawl(i) + alpha(i);
function beta_p(i) = pitchl(i) + alpha(i);
wall_s             = 5 * line_w;
slot_depth         = pin_protrude + 1.0;
function cap_h(i)  = RS(i) * cos(beta_p(i));
function cap_outer_r(i) = RS(i) + wall_s;
function bolt_pcd_r(i)  = cap_outer_r(i) + bolt_clear / 2 + line_w + 1.0;
lobe_r             = bolt_clear / 2 + 2 * line_w + 0.5;
cap_lobe_t         = 6;
function flange_bolt_r(i) = RN(i) + head_d / 2 + 1.0;
function flange_r(i)      = flange_bolt_r(i) + lobe_r;
flange_t           = 6;
function max_bend(i) = max(yawl(i), pitchl(i));
function droop(i) = (i == 1 || i > N) ? 0 : (len(rest_droop_list) > 0 ? rest_droop_list[i - 1] : rest_droop);
function DF(i) = max(cap_h(i) * cos(max_bend(i)) + cap_outer_r(i) * sin(max_bend(i)),
                     cap_lobe_t + head_h + (bolt_pcd_r(i) + lobe_r) * sin(max_bend(i))) + head_h + 2
                 + flange_r(i) * sin(abs(droop(i)));          // wedge flange tilt
function seat_depth(i) = RS(i) + wall();
function coil_od(i)    = min(max(coil_od_ratio * D(i), 5), 16);
function spring_arm(i) = min(max(cap_outer_r(i) + coil_od(i) / 2 + 0.5, 0.8 * RF(i)), D(i) / 2 - 6);
function span_parent(i) = DF(i) + flange_t + 4;     // parent anchor behind the pivot
// child anchor: an ear on the socket cap, cap_ear_x PROXIMAL of the pivot (twist-stable geometry)
function body_len(i)   = i == N ? L - tip_plug_len : L - DF(i + 1) - flange_t;
function pin(i)        = RB(i) >= 19 ? [4, 12, 7, 4] : [3, 8, 5.5, 3];   // d, len, head d, head h
function pin_pocket_z(i) = RB(i) + pin_protrude - pin(i)[1];
function slot_w(i)     = pin(i)[0] + 0.6 + 2 * (RB(i) + pin_protrude / 2) * sin(max_roll);
function cord_flare(i) = max_bend(i) + 6;
function spine_r(i)    = i < N ? max(flange_bolt_r(i + 1) - 5.3, bore_r + wall()) : bore_r + wall(4);

// report the derived table (parsed by tests/test_cad.py)
for (i = [1 : N])
    echo(str("DIMS,", i, ",", D(i), ",", RF(i), ",", RB(i), ",", RS(i), ",", RN(i), ",",
             beta_y(i), ",", beta_p(i), ",", cap_h(i), ",", DF(i), ",", body_len(i), ",", spring_arm(i)));

// ---- helpers -----------------------------------------------------------------
module along_x(h, r1, r2) { rotate([0, 90, 0]) cylinder(h = h, r1 = r1, r2 = r2); }
module along_mx(h, r1, r2) { rotate([0, -90, 0]) cylinder(h = h, r1 = r1, r2 = r2); }
module hexnut_pocket(depth) { cylinder(d = nut_af / cos(30) + 0.4, h = depth, $fn = 6); }
module at_lobes() { for (a = [45, 135, 225, 315]) rotate([a, 0, 0]) children(); }   // about the X axis
module at_springs() { for (a = [90, -90, 0]) rotate([a, 0, 0]) children(); }        // +z (dorsal), +/-y (lateral)
// rotate([a,0,0]) turns +Z toward -Y for a=90, so children are drawn on +Z.

// Elliptical cone of half-angles by (about Y, lateral swing) and bp (dorsal swing) along -X.
module ellip_cone_mx(h, by, bp) {
    scale([1, tan(by), tan(bp)]) rotate([0, -90, 0]) cylinder(h = h, r1 = 0, r2 = h);
}

// ---- ball ------------------------------------------------------------------------
module ball(i) {
    R = RB(i); rn = RN(i); df = DF(i); p = pin(i); d = droop(i);
    x1 = cap_h(i) + 3;                      // neck stays on the joint axis through the cap mouth
    difference() {
        union() {
            sphere(r = R, $fn = 96);
            along_mx(x1, rn, rn);
            // wedge: the neck turns onto the PARENT axis (rest bend d) outside the socket
            hull() {
                translate([-x1 + 0.5, 0, 0]) along_mx(0.5, rn, rn);
                rotate([0, -d, 0]) translate([-df + 0.5, 0, 0]) along_mx(0.5, rn, rn);
            }
            rotate([0, -d, 0]) translate([-df, 0, 0]) along_mx(flange_t, flange_r(i), flange_r(i));
        }
        // cord: straight toward the neck, flared on the distal side where the child axis swings
        along_mx(x1 + 1, bore_r, bore_r);
        rotate([0, -d, 0]) along_mx(df + flange_t + 1, bore_r, bore_r);
        along_x(R + 1, bore_r, bore_r + (R + 1) * tan(cord_flare(i)));
        // flange bolts (heads on the neck side)
        rotate([0, -d, 0]) at_lobes() translate([-df - flange_t - 1, 0, flange_bolt_r(i)]) along_x(flange_t + 2, bolt_clear / 2, bolt_clear / 2);
        // roll-key screw: head captured inside the ball, shank out through the dorsal pole
        translate([0, 0, pin_pocket_z(i) - p[3]]) cylinder(d = p[2] + 0.6, h = p[3] + 0.2, $fn = 24);
        translate([0, 0, pin_pocket_z(i)]) cylinder(d = p[0] + 0.3, h = R + 1, $fn = 24);
        // registration dowels (1.75 mm filament) in the split plane
        for (s = [-1, 1]) translate([s * 0.55 * R, 0, -0.45 * R]) rotate([90, 0, 0]) cylinder(d = 1.9, h = 12, center = true, $fn = 12);
    }
}

// clamshell halves split on the X-Z plane, laid flat for printing
module ball_half(i, side = 1) {
    rotate([side > 0 ? 90 : -90, 0, 0])
        intersection() {
            ball(i);
            translate([-200, side > 0 ? 0 : -200, -200]) cube([400, 200, 400]);
        }
}

// ---- socket --------------------------------------------------------------------
module roll_slot(i, x_lo, x_hi) {
    // dorsal groove the roll-key pin runs in: long in pitch, tight in roll
    w = slot_w(i); r0 = RS(i) - 0.5; r1 = RB(i) + pin_protrude + 1.0;
    intersection() {
        translate([x_lo, -w / 2, 0]) cube([x_hi - x_lo, w, r1 + 1]);
        difference() { sphere(r = r1, $fn = 64); sphere(r = r0 - 0.01, $fn = 64); }
        // angular extent: pitch limit plus the pin radius, either side of the pole
        a = pitchl(i) + asin((pin(i)[0] / 2 + 0.5) / RB(i)) + 2;
        intersection() {
            rotate([0, a, 0]) translate([-400, -200, -200]) cube([400, 400, 400]);
            rotate([0, -a, 0]) translate([0, -200, -200]) cube([400, 400, 400]);
        }
    }
}

// socket cavity: sphere plus a 45 deg relief cone on the cap side (printable ceiling)
module socket_cavity(i) {
    Rs = RS(i);
    sphere(r = Rs, $fn = 96);
    translate([-Rs * sin(45), 0, 0]) along_mx(Rs * sin(45), Rs * cos(45), 0);
}

module cap(i) {
    Rs = RS(i); h = cap_h(i);
    difference() {
        union() {
            along_mx(h, cap_outer_r(i), cap_outer_r(i));
            at_lobes() hull() {
                translate([0, 0, bolt_pcd_r(i)]) along_mx(cap_lobe_t, lobe_r, lobe_r);
                translate([0, 0, cap_outer_r(i) - 3]) along_mx(cap_lobe_t, lobe_r, lobe_r);
            }
            // spring ears (dorsal, left, right): child end of the joint's springs
            at_springs() hull() {
                translate([-cap_ear_t(i), -ear_w(i) / 2, cap_outer_r(i) - 4]) cube([cap_ear_t(i), ear_w(i), 1]);
                // rounded end kept inside the cap's flat (print-bed) face: stadium of radius cap_ear_x
                for (x = [-cap_ear_x, -cap_ear_t(i) + cap_ear_x]) translate([x, 0, spring_arm(i)]) rotate([90, 0, 0]) cylinder(r = cap_ear_x, h = ear_w(i) * 0.6, center = true);
            }
        }
        socket_cavity(i);
        ellip_cone_mx(h + 2, beta_y(i), beta_p(i));
        roll_slot(i, -h - 1, 0.01);
        at_lobes() translate([1, 0, bolt_pcd_r(i)]) along_mx(cap_lobe_t + 2, bolt_clear / 2, bolt_clear / 2);
        at_springs() translate([-cap_ear_x, 0, spring_arm(i)]) rotate([90, 0, 0]) cylinder(d = spring_hole, h = 40, center = true, $fn = 24);
    }
}
function ear_w(i) = max(12, 0.6 * cap_outer_r(i));
function cap_ear_t(i) = RB(i) >= 22 ? 16 : 12;   // root caps carry dorsal spring pairs up to ~400 N

// seat = the part of the socket inside the vertebra body (x >= 0)
module socket_half(i, which = "seat") {
    if (which == "cap") cap(i);
    else difference() {
        intersection() { vertebra_frame(i); translate([-1, -200, -200]) cube([seat_depth(i) + 8, 400, 400]); }
    }
}

module socket(i) { socket_half(i, "seat"); cap(i); }

// ---- vertebra frame ---------------------------------------------------------------
module vertebra_frame(i) {
    Rs = RS(i); bl = body_len(i); sd = seat_depth(i); rf = RF(i);
    ho = cap_outer_r(i);
    x_f0 = 0;                                // fins run from the socket housing to the distal flange
    rr = (i < N) ? flange_r(i + 1) : spine_r(i) + 6;
    difference() {
        union() {
            // socket housing
            along_x(sd, ho, ho);
            // cap bolt lobes with 45 deg undersides (print upside-down: x = 0 is the top)
            at_lobes() hull() {
                translate([0, 0, bolt_pcd_r(i)]) along_x(7, lobe_r, lobe_r);
                translate([0, 0, ho - 3]) along_x(7 + (bolt_pcd_r(i) + lobe_r - ho + 3), 1, 1);
            }
            // spine tube
            translate([sd - 2, 0, 0]) along_x(bl - sd + 2, spine_r(i), spine_r(i));
            // distal flange (matches the next ball flange, or the tip adapter)
            translate([bl - flange_t, 0, 0]) along_x(flange_t, rr, rr);
            // four longitudinal fins: dorsal, ventral, left, right - skin former and spring anchors
            // (diamond lightening windows cut from the fins only, 45 deg edges print without support)
            difference() {
                for (a = [0, 90, 180, 270]) rotate([a, 0, 0])
                    translate([x_f0, -fin_t(i) / 2, 0]) cube([bl - x_f0, fin_t(i), rf]);
                for (a = [0, 90, 180, 270]) rotate([a, 0, 0]) fin_windows(i);
            }
            // 45 deg cone under the socket housing, down to the spine: the housing floor would
            // otherwise be a flat ceiling between the fins in print orientation (flange down)
            translate([sd - 0.01, 0, 0]) along_x(ho - spine_r(i), ho, spine_r(i));
            // skirt wall under the skin ring, standing on the bed (distal end): carries the ring's
            // bottom rim, with diamond windows between the fins and arched notches at the spring anchors
            skin_ring_skirt(i);
            // bosses around the parent-side spring holes (tear-out margin)
            if (i < N) at_springs() intersection() {
                translate([bl - 4, 0, spring_arm(i + 1)]) rotate([90, 0, 0]) cylinder(r = 7, h = fin_t(i) + 4, center = true);
                translate([bl - 20, -20, 0]) cube([20, 40, 400]);
            }
            // skin ring at mid-length, 45 deg underside toward the distal (print-bottom) end
            xm = x_f0 + 0.5 * (bl - x_f0);
            translate([xm, 0, 0]) rotate([0, 90, 0]) difference() {
                union() {
                    cylinder(r = rf, h = 2 * line_w + 0.2);
                    translate([0, 0, 2 * line_w + 0.2]) cylinder(r1 = rf, r2 = rf - 8, h = 8);
                }
                translate([0, 0, -1]) cylinder(r = rf - 3 * line_w, h = 2 * line_w + 2.2);
                translate([0, 0, 2 * line_w + 0.2 - 0.01]) cylinder(r1 = rf - 3 * line_w, r2 = rf - 8 - 3 * line_w, h = 8.02);
            }
            // base ring at the distal end ties the fins together
            translate([bl - flange_t, 0, 0]) difference() {
                along_x(flange_t, rf, rf);
                translate([-1, 0, 0]) along_x(flange_t + 2, rf - 3 * line_w, rf - 3 * line_w);
            }
        }
        // socket seat + slot
        socket_cavity(i);
        roll_slot(i, -0.01, sd);
        // cord bore
        translate([-1, 0, 0]) along_x(bl + 2, bore_r, bore_r);
        // cap bolts: through-hole + nylock nut pocket opening toward +x
        at_lobes() translate([-1, 0, bolt_pcd_r(i)]) {
            along_x(12, bolt_clear / 2, bolt_clear / 2);
            translate([1 + 7 - nut_h - 0.3, 0, 0]) rotate([0, 90, 0]) hexnut_pocket(nut_h + 20);
        }
        // spring anchor holes: proximal fin edge (this joint) and distal fin edge (next joint)
        // parent-side spring anchors for the next joint, 4 mm from the fin ends
        if (i < N) at_springs() translate([bl - 4, 0, spring_arm(i + 1)]) rotate([90, 0, 0]) cylinder(d = spring_hole, h = 20, center = true, $fn = 24);
        // distal flange bolts + nut pockets (nuts inside the body, heads on the ball side)
        if (i < N) at_lobes() {
            translate([bl - flange_t - 1, 0, flange_bolt_r(i + 1)]) along_x(flange_t + 2, bolt_clear / 2, bolt_clear / 2);
            // nut sits 2.5 mm into the inner face of the flange (anti-rotation), open toward the socket
            translate([bl - flange_t + 2.5 - 20, 0, flange_bolt_r(i + 1)]) rotate([0, 90, 0]) hexnut_pocket(20);
        }
        if (i == N) at_lobes() translate([bl - flange_t - 1, 0, spine_r(i) + 2]) along_x(flange_t + 2, 1.6, 1.6);
    }
}

// single-line cylindrical wall from the distal end (the print bed) up to the skin ring's bottom rim:
// pointed arches (45 deg peaks) open from the bed between the fins, a band under the rim, and a 45 deg
// flare at the top from the one-line wall out to the rim's full 3-line width
skirt_t = line_w + 0.1;
function ring_rim_x(i) = 0.5 * body_len(i) + 2 * line_w + 0.2 + 8;     // x of the ring's bottom rim
module skin_ring_skirt(i) {
    bl = body_len(i); rf = RF(i); x0 = ring_rim_x(i); r_o = rf - 8; r_i = r_o - skirt_t;
    rim_w = 3 * line_w; flare = rim_w - skirt_t;               // 45 deg: as tall as it is wide
    h = bl - x0; band = flare + 2;                              // solid band under the rim
    arc = 2 * PI * r_o / 4 - fin_t(i) - 12;                     // usable arc per quadrant (6 mm from each fin)
    na = max(1, ceil(arc / 45));
    W = min((arc - (na - 1) * 4) / na, 2 * (h - band));        // arch width; peak must stay under the band
    hv = h - band - W / 2;                                      // straight sides below the 45 deg peak
    difference() {
        union() {
            translate([x0 - 0.01, 0, 0]) difference() { along_x(h + 0.01, r_o, r_o); translate([-1, 0, 0]) along_x(h + 2, r_i, r_i); }
            translate([x0 - 0.01, 0, 0]) difference() { along_x(flare, r_o, r_o); translate([-0.01, 0, 0]) along_x(flare + 0.02, r_o - rim_w, r_i); }
        }
        if (hv >= 0) for (q = [0 : 3], k = [0 : na - 1]) {
            ang = q * 90 + (k + 0.5) * 90 / na;
            rotate([ang, 0, 0]) translate([0, 0, r_o]) hull() {
                translate([bl - hv, -W / 2, -10]) cube([hv + 1, W, 20]);
                translate([bl - hv - W / 2, 0, 0]) cube([0.01, 0.01, 20], center = true);
            }
        }
        // arched notches (vertical sides, 45 deg pointed top) where the springs hook onto the fins
        if (i < N) at_springs() translate([0, 0, r_o]) hull() {
            translate([bl - 11, -7, -10]) cube([12, 14, 20]);
            translate([bl - 18, 0, 0]) cube([0.01, 0.01, 20], center = true);
        }
    }
}

module fin_windows(i) {
    bl = body_len(i); rf = RF(i); x_f0 = 0;
    xm = x_f0 + 0.5 * (bl - x_f0);
    r_out = rf - 7;
    for (seg = [[x_f0 + 7, xm - 2], [xm + 2 * line_w + 10, bl - flange_t - 3]]) {
        r_in = (seg[0] < seat_depth(i) + 3 ? cap_outer_r(i) : spine_r(i)) + 4;
        len = seg[1] - seg[0];
        h = min(len / 2 - 1, (r_out - r_in) / 2);
        nr = max(1, floor((r_out - r_in + 3) / (2 * h + 3)));
        if (h > 5) for (k = [0 : nr - 1])
            translate([(seg[0] + seg[1]) / 2, 0, r_in + h + k * (2 * h + 3)])
                rotate([90, 0, 0]) rotate([0, 0, 45]) cube([h * sqrt(2), h * sqrt(2), 20], center = true);
    }
}

// vertebra i with its cap and the ball of the next joint bolted on
module vertebra(i) {
    color("SteelBlue") vertebra_frame(i);
    color("LightSteelBlue") cap(i);
    if (i < N) color("Goldenrod") translate([L, 0, 0]) rotate([0, droop(i + 1), 0]) ball(i + 1);
    else color("Goldenrod") translate([body_len(i), 0, 0]) tip_adapter();
}

// ---- hip mount ----------------------------------------------------------------------
// Frame: pelvis frame, origin at the pelvis centre, +X forward, +Z up.
// Joint 1 frame = translate([-root_back_offset,0,0]) * rotation below.
// net: +X -> (-cos rp, 0, -sin rp) backward & down; +Z -> (-sin rp, 0, cos rp) dorsal; +Y -> -Y
module root_frame() { translate([-root_back_offset, 0, root_dz]) rotate([0, 180 - root_pitch, 0]) rotate([180, 0, 0]) children(); }

// arm profile in the joint-1 frame (t = thickness): 12 mm at the plate end, w + 5 deep at the flange
module hip_arm(t) {
    pf = DF(1) + flange_t; w = spring_arm(1);
    hull() {
        translate([-pf - 12, -t / 2, 0]) cube([12, t, w + 5]);
        translate([-pf - 30, -t / 2, 0]) cube([30, t, 12]);
    }
}
// flatten onto the plate: a sliver 1 mm inside the back face (pelvis x = -harness_plate_offset - hip_plate_t),
// so the web hull fuses into the plate instead of stopping a hair short of it
module onto_plate() { pb = -harness_plate_offset - hip_plate_t; translate([pb + 1, 0, 0]) scale([0.001, 1, 1]) translate([-pb, 0, 0]) children(); }

// plate lightening: honeycomb of hexagonal holes (flat-to-flat, uniform webs), clear of the edges, boss, webs
// and strap slots
knot_r = 11;  knot_depth = 10;                    // cord knot pocket in the plate's front face: 22 mm x 10 mm + 45 deg roof
hole_R = 12.7;                                     // hex circumradius (22 mm across flats)
hole_pitch = 28;                                   // 28 - 22 = 6 mm web between every pair of neighbours
hole_y0 = hole_pitch / 2;  hole_z0 = -5.5;         // grid phase that fits the most holes (17) symmetrically
function hip_hole_ok(y, z) = let(m = 6 + hole_R, bz = root_dz, lz = root_dz + 6, w = spring_arm(1))
    abs(y) <= hip_plate_w / 2 - 8 - hole_R && abs(z - plate_z) <= hip_plate_h / 2 - 8 - hole_R
    && norm([y, z - bz]) >= flange_r(1) + 6 + m                                          // boss footprint
    && !(abs(y) < fin_t_hip / 2 + m && z > bz && z < bz + w + 5 + m)                     // dorsal web
    && !(abs(z - lz) < fin_t_hip / 2 + 4 + m && abs(y) < w + 5 + m)                      // lateral webs
    && !(abs(abs(y) - 78) < 2.5 + m && ((abs(z - (plate_z - 45)) < 14 + m) || (abs(z - (plate_z + 45)) < 14 + m)))
    && !(abs(y) < 26 + m && abs(z - (plate_z + hip_plate_h / 2 - 10)) < 2.5 + m);       // top webbing slot
HIP_HOLES = [for (r = [-8 : 8], c = [-8 : 8]) let(y = (c + (r % 2 == 0 ? 0 : 0.5)) * hole_pitch + hole_y0, z = plate_z + r * hole_pitch * sin(60) + hole_z0)
             if (hip_hole_ok(y, z)) [y, z]];

module hip_mount() {
    df = DF(1); pf = df + flange_t;
    w = spring_arm(1);
    pb = -harness_plate_offset - hip_plate_t;        // plate back face
    difference() {
        union() {
            // harness plate (vertical, faces backward)
            translate([pb, -hip_plate_w / 2, plate_z - hip_plate_h / 2])
                cube([hip_plate_t, hip_plate_w, hip_plate_h]);
            // boss from the plate's FRONT face to the ball-1 flange, so the part of the boss that hangs below
            // the plate still sits on the print bed (no floating ledge)
            hull() {
                translate([-harness_plate_offset - 1, 0, root_dz]) rotate([0, 90, 0]) cylinder(r = flange_r(1) + 6, h = 1);
                root_frame() translate([-pf, 0, 0]) along_mx(8, flange_r(1), flange_r(1));
            }
            // spring-anchor arms: 12 mm thick, 30 mm deep at the boss (dorsal spring up to ~220 N)
            root_frame() at_springs() hip_arm(hip_arm_t);
            for (a = [90, -90, 0]) {
                // 45 deg flare from the 4 mm web out to the full 12 mm arm
                root_frame() rotate([a, 0, 0]) hull() { hip_arm(hip_arm_t); translate([-(hip_arm_t - fin_t_hip) / 2, 0, 0]) hip_arm(fin_t_hip); }
                // thin web from the arm down to the plate
                hull() { root_frame() rotate([a, 0, 0]) hip_arm(fin_t_hip); onto_plate() root_frame() rotate([a, 0, 0]) hip_arm(fin_t_hip); }
            }
        }
        // anything past the flange face belongs to the ball (only behind the plate's back face)
        intersection() {
            root_frame() translate([-pf + 0.01, -100, -100]) cube([100, 200, 200]);
            translate([pb - 1000, -500, -500]) cube([1000, 1000, 1000]);
        }
        // lumbar-support-belt attachment: four 25 mm strap slots (hook-and-loop straps wrap the belt's
        // back panel) and a top 50 mm webbing slot (a bottom one would sit under the boss)
        for (y = [-78, 78], z = [-45, 45]) translate([pb - 1, y - 2.5, plate_z + z - 14]) cube([hip_plate_t + 2, 5, 28]);
        translate([pb - 1, -26, plate_z + hip_plate_h / 2 - 10 - 2.5]) cube([hip_plate_t + 2, 52, 5]);
        // plate lightening holes (vertical through-holes in print orientation)
        for (h = HIP_HOLES) translate([pb - 1, h[0], h[1]]) rotate([0, 90, 0]) cylinder(r = hole_R, h = hip_plate_t + 2, $fn = 6);   // flats face the neighbours
        // cord anchor: bore from the flange face out through the plate's front face into a knot pocket
        // (a figure-eight / double-overhand stopper in 6 mm cord is ~15-18 mm across), fully recessed so the
        // belt panel covers it; straight sides then a 45 deg roof down to the bore (prints without support)
        root_frame() along_mx(pf + 120, bore_r, bore_r);
        translate([-harness_plate_offset + 0.01, 0, root_dz + (root_back_offset - harness_plate_offset) * tan(root_pitch)])
            rotate([0, -90, 0]) {
                cylinder(r = knot_r, h = knot_depth + 0.01);
                // full 45 deg cone to a point: the 6 deg-tilted bore pierces it, leaving no flat ledge
                translate([0, 0, knot_depth]) cylinder(r1 = knot_r, r2 = 0, h = knot_r);
            }
        // ball-1 flange bolts with nut pockets
        root_frame() at_lobes() translate([-pf + 1, 0, flange_bolt_r(1)]) {
            along_mx(12, bolt_clear / 2, bolt_clear / 2);
            translate([-6, 0, 0]) rotate([0, -90, 0]) hexnut_pocket(20);
        }
        // spring anchor holes
        root_frame() at_springs() translate([-span_parent(1), 0, w]) rotate([90, 0, 0]) cylinder(d = spring_hole, h = 20, center = true, $fn = 24);
    }
}

// ---- tip adapter + foam tip -------------------------------------------------------------
// Bolts to vertebra N's distal flange; holds the cord preload spring and the foam spike.
module tip_adapter() {
    r = spine_r(N) + 6;
    difference() {
        union() {
            along_x(6, r, r);
            along_x(tip_plug_len, 10.5, 10.5);
            translate([tip_plug_len, 0, 0]) along_x(45, 7, 2);        // foam spike
            for (k = [0 : 3]) translate([tip_plug_len + 8 + 9 * k, 0, 0]) along_x(5, 8 - 1.2 * k, 5 - 1.2 * k);  // barbs
        }
        translate([-1, 0, 0]) along_x(8, bore_r, bore_r);                  // cord enters the pocket only
        translate([6, 0, 0]) along_x(tip_plug_len - 9, 7, 7);        // Ø14 compression-spring pocket, 3 mm floor
        translate([8, 0, -5]) cube([tip_plug_len - 13, 12, 10]);      // side window: fit spring, tie the knot
        at_lobes() translate([-1, 0, spine_r(N) + 2]) along_x(8, 1.6, 1.6); // M3 screws into the flange
    }
}

// 4-joint test section terminator: bolts to vertebra 4's distal flange (ball-5 pattern),
// anchors the cord and carries an M8 threaded rod with washer ballast that stands in
// for vertebrae 5..N + foam tip (mass and lever from docs/physics.md).
module test_ballast_plate(j = 5) {
    r = flange_r(j);
    difference() {
        union() {
            along_mx(flange_t, r, r);
            along_x(30, 12, 12);
        }
        translate([-flange_t - 1, 0, 0]) along_x(40, 4.2, 4.2);                   // M8 rod
        translate([18, 0, 0]) rotate([0, 90, 0]) hexnut_pocket_m8(20);
        at_lobes() translate([-flange_t - 1, 0, flange_bolt_r(j)]) along_x(flange_t + 2, bolt_clear / 2, bolt_clear / 2);
        for (a = [0, 180]) rotate([a, 0, 0]) translate([-flange_t - 1, 0, 8]) along_x(flange_t + 2, 2.5, 2.5); // cord pass + tie
    }
}
module hexnut_pocket_m8(depth) { cylinder(d = 13 / cos(30) + 0.4, h = depth, $fn = 6); }

module foam_tip_reference() {
    // 200 mm flexible upholstery/EVA foam extension - NOT printed
    color("SandyBrown", 0.6) along_x(tail_length - mech_length, last_mech_diameter / 2, tip_diameter / 2);
}

// ---- motion envelope ------------------------------------------------------------------------
// Swept limit cone of vertebra i's axis relative to its parent (yaw x pitch ellipse).
module joint_motion_envelope(i, len = 0) {
    h = len > 0 ? len : L;
    color("Tomato", 0.25) scale([1, tan(yawl(i)), tan(pitchl(i))]) rotate([0, 90, 0]) cylinder(h = h, r1 = 0, r2 = h);
}

// ---- assembly ------------------------------------------------------------------------------------
function pose_yaw(i) = POSE == "turn" ? 0.55 * yawl(i) : POSE == "max" ? yawl(i) : 0;

module chain(i, envelope = false) {
    if (i <= N) rotate([0, 0, pose_yaw(i)]) {
        vertebra(i);
        if (envelope) joint_motion_envelope(i);
        translate([L, 0, 0]) rotate([0, droop(i + 1), 0]) chain(i + 1, envelope);
    }
}

module central_cord() {
    // straight-line indicator of the cord through the ball centres (neutral pose)
    color("Gold") along_x(mech_length, 1.5, 1.5);
}

module tail_assembly(envelope = false) {
    color("DimGray") hip_mount();
    root_frame() {
        color("Goldenrod") ball(1);
        chain(1, envelope);
        // foam tip after vertebra N (approximate for curved poses)
    }
}

module performer_reference() {
    // 5 ft 8 in (1727 mm) performer, pelvis centre at 0.55 H (pelvis frame origin)
    color("LightGray", 0.25) translate([0, 0, -0.55 * 1727]) {
        translate([-110, -180, 0]) cube([220, 360, 0.53 * 1727]);
        translate([-120, -200, 0.53 * 1727]) cube([240, 400, 0.34 * 1727]);
        translate([0, 0, 0.93 * 1727]) sphere(r = 110);
    }
}

// 4-joint physical test section (README section 21): hip mount + vertebrae 1-4
module test_section() {
    color("DimGray") hip_mount();
    root_frame() {
        color("Goldenrod") ball(1);
        vertebra_frame(1); cap(1);
        translate([L, 0, 0]) rotate([0, droop(2), 0]) { ball(2); vertebra_frame(2); cap(2);
            translate([L, 0, 0]) rotate([0, droop(3), 0]) { ball(3); vertebra_frame(3); cap(3);
                translate([L, 0, 0]) rotate([0, droop(4), 0]) { ball(4); vertebra_frame(4); cap(4); } } }
    }
}

// ---- views -------------------------------------------------------------------------------------------
if (PART == "assembly") { tail_assembly(); performer_reference(); }
else if (PART == "assembly_bare") tail_assembly();
else if (PART == "vertebra") vertebra(INDEX);
else if (PART == "ball") ball(INDEX);
else if (PART == "socket") socket(INDEX);
else if (PART == "hip_mount") hip_mount();
else if (PART == "motion_envelope") tail_assembly(envelope = true);
else if (PART == "section") difference() {
    union() { color("Goldenrod") ball(INDEX); vertebra_frame(INDEX); cap(INDEX);
              if (INDEX < N) translate([L, 0, 0]) rotate([0, droop(INDEX + 1), 0]) color("Goldenrod") ball(INDEX + 1); }
    translate([-300, 0, -300]) cube([600, 300, 600]);
}
else if (PART == "test_section") test_section();
else if (PART == "foam_tip") foam_tip_reference();
// print-oriented single parts
else if (PART == "print_ball_left") ball_half(INDEX, 1);
else if (PART == "print_ball_right") ball_half(INDEX, -1);
else if (PART == "print_cap") translate([0, 0, 0]) rotate([0, 90, 0]) cap(INDEX);            // x=0 face on the bed
else if (PART == "print_body") translate([0, 0, body_len(INDEX)]) rotate([0, 90, 0]) vertebra_frame(INDEX); // distal flange on the bed, socket up
else if (PART == "print_hip_mount") rotate([0, 90, 0]) translate([harness_plate_offset, 0, 0]) hip_mount();
else if (PART == "print_tip_adapter") rotate([0, -90, 0]) tip_adapter();
else if (PART == "print_test_ballast_plate") rotate([0, -90, 0]) translate([flange_t, 0, 0]) test_ballast_plate(5);
