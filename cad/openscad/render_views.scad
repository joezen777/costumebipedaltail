// Visualisation views built from the exported print STLs (fast preview, and a
// check that the printed parts reassemble). Driven by cad/render_views.py.
include <suit_tail.scad>
PART = "none";          // silence the dispatcher in suit_tail.scad
VIEW = "neutral";       // neutral | turn | max | exploded | test_section | cord
STL  = "../stl/full/";
SHOW_ACTOR = true;

module stl_body(i)  { rotate([0, -90, 0]) translate([0, 0, -body_len(i)]) import(str(STL, "body_", i, ".stl")); }
module stl_cap(i)   { rotate([0, -90, 0]) import(str(STL, "cap_", i, ".stl")); }
module stl_ball(i)  { rotate([-90, 0, 0]) import(str(STL, "ball_", i, "_left.stl"));
                      rotate([90, 0, 0])  import(str(STL, "ball_", i, "_right.stl")); }
module stl_hip()    { translate([-harness_plate_offset, 0, 0]) rotate([0, -90, 0]) import(str(STL, "hip_mount.stl")); }
module stl_tip()    { rotate([0, 90, 0]) import(str(STL, "tip_adapter.stl")); }

function vyaw(i) = VIEW == "turn" ? 0.55 * yawl(i) : VIEW == "max" ? yawl(i) : 0;

module spring_line(i, a) {
    // joint-i springs drawn in the parent frame at pivot i; child end follows the joint yaw a
    for (r = [90, -90, 0]) color("Crimson") hull() {
        rotate([r, 0, 0]) translate([-span_parent(i), 0, spring_arm(i)]) sphere(r = coil_od(i) / 2, $fn = 12);
        rotate([0, 0, a]) rotate([r, 0, 0]) translate([-cap_ear_x, 0, spring_arm(i)]) sphere(r = coil_od(i) / 2, $fn = 12);
    }
}

module vchain(i, n_last, envelope = false, cord = false) {
    if (i <= n_last) {
        spring_line(i, vyaw(i));
        rotate([0, 0, vyaw(i)]) {
            color("SteelBlue") stl_body(i);
            color("LightSteelBlue") stl_cap(i);
            if (envelope) joint_motion_envelope(i, L * 0.9);
            if (cord) color("Gold") along_x(L, 2, 2);
            if (VIEW == "neutral" || VIEW == "turn") color("OliveDrab", 0.18)
                along_x(L, D(i) / 2, (i < N ? D(i + 1) : last_mech_diameter) / 2);
            if (i < N) { translate([L, 0, 0]) color("Goldenrod") stl_ball(i + 1); }
            else { translate([body_len(i), 0, 0]) color("Goldenrod") stl_tip();
                   translate([L, 0, 0]) color("SandyBrown", 0.55) along_x(tail_length - mech_length, last_mech_diameter / 2, tip_diameter / 2); }
            translate([L, 0, 0]) rotate([0, rest_droop, 0]) vchain(i + 1, n_last, envelope, cord);
        }
    }
}

module skin(i_last) {
    // translucent foam-skin envelope for the neutral pose
    root_frame() for (i = [1 : i_last]) translate([(i - 1) * L, 0, 0])
        color("OliveDrab", 0.18) along_x(L, D(i) / 2, (i < N ? D(i + 1) : last_mech_diameter) / 2);
}

if (VIEW == "exploded") {
    // one vertebra exploded along its axis, ball halves split sideways
    i = INDEX;
    color("LightSteelBlue") translate([-60, 0, 0]) stl_cap(i);
    color("Goldenrod") translate([-120, 0, 0]) { rotate([-90, 0, 0]) translate([0, 0, 0]) import(str(STL, "ball_", i, "_left.stl"));
                                                 translate([0, -40, 0]) rotate([90, 0, 0]) import(str(STL, "ball_", i, "_right.stl")); }
    color("SteelBlue") stl_body(i);
    color("Goldenrod") translate([L + 60, 0, 0]) { rotate([-90, 0, 0]) import(str(STL, "ball_", i + 1, "_left.stl"));
                                                    translate([0, -40, 0]) rotate([90, 0, 0]) import(str(STL, "ball_", i + 1, "_right.stl")); }
} else {
    color("DimGray") stl_hip();
    n_last = VIEW == "test_section" ? 4 : N;
    root_frame() {
        color("Goldenrod") stl_ball(1);
        vchain(1, n_last, envelope = (VIEW == "max"), cord = (VIEW == "cord"));
    }
    if (SHOW_ACTOR) performer_reference();
    color("Gainsboro") translate([-1800, -900, -0.55 * 1727 - 1]) cube([2200, 1800, 1]);   // floor
}
