# Bishop clips (exec'd after anims.py). Storyboard row 3: raises the crozier, the orb gathers light,
# then the staff is thrust at the target and a bolt leaves the orb (the viewer / Unity draw the bolt).
# BOLT_FRAME is when the bolt leaves the orb; it reaches the target BOLT_FLIGHT frames later.
BOLT_FRAME, BOLT_FLIGHT = 22, 4
SPELL_FRAME, SPELL_FLIGHT = 48, 8   # Spell: the light shot leaves the staff on frame 48 and lands 8 frames later

STAFF_UP = ("weapon", (0, 0.04, 1), (0, -1, 0))
STAFF_SKY = ("weapon", (0, -0.15, 1), (0, -1, 0))

PRAY = P(ARMS(upper_arm_R=(-0.2, -0.12, -0.97), forearm_R=(-0.05, -0.92, 0.38),     # staff upright at the right
              upper_arm_L=(0.2, -0.25, -0.95), forearm_L=(-0.55, -0.8, 0.2)),        # left hand at the chest
         spine=(3, 0, 0), head=(-3, 0, 0))

def bishop_clips(rig):
    g = PRAY
    hold = (STAFF_UP,)
    out = []
    out.append(clip(rig, "Idle", [
        K(1, g), K(20, add(g, P(chest=(-2, 0, 0), head=(-6, 6, 0)))), K(40, add(g, P(chest=(1, 0, 0), head=(2, -6, 0)))),
        K(60, g)], loop=True, aims=hold))

    # Walk: a measured, processional step; the robe hides most of the legs. 48-frame cycle.
    def step(s):
        return P(g, {"thigh.L": (14 * s, 0, 2), "shin.L": (-8 if s > 0 else -20, 0, 0), "foot.L": (6 * s, 0, 0)},
                 {"thigh.R": (-14 * s, 0, -2), "shin.R": (-20 if s > 0 else -8, 0, 0), "foot.R": (-6 * s, 0, 0)},
                 spine=(4, 0, 0), chest=(2, -4 * s, 0), hips=(0, 5 * s, 0))
    def passing(lift):
        o = "R" if lift == "L" else "L"
        return P(g, {f"thigh.{lift}": (24, 0, 0), f"shin.{lift}": (-40, 0, 0), f"thigh.{o}": (2, 0, 0), f"shin.{o}": (-6, 0, 0)},
                 spine=(4, 0, 0))
    out.append(clip(rig, "Walk", [K(1, step(1)), K(13, passing("R")), K(25, step(-1)), K(37, passing("L")), K(49, step(1))],
                    loop=True, aims=hold))

    # Attack (cast): staff raised high, the left hand draws power, lean back, then the staff is driven forward and
    # down at the target - the bolt leaves the orb on BOLT_FRAME.
    raise_ = P(ARMS(upper_arm_R=(-0.35, -0.2, 0.9), forearm_R=(-0.1, -0.3, 0.95),
                    upper_arm_L=(0.5, -0.5, -0.7), forearm_L=(0.2, -0.95, 0.25)),
               {"thigh.L": (14, 0, 2), "shin.L": (-16, 0, 0), "thigh.R": (-8, 0, -2), "shin.R": (-10, 0, 0), "foot.R": (12, 0, 0)},
               spine=(-10, -10, 0), chest=(-6, -6, 0), head=(-12, 0, 0))
    gather = add(raise_, P(spine=(-6, -4, 0), head=(-6, 0, 0)))
    thrust = P(ARMS(upper_arm_R=(-0.15, -0.95, 0.2), forearm_R=(0.0, -1, 0.05),
                    upper_arm_L=(0.45, -0.35, -0.8), forearm_L=(0.3, -0.7, 0.6)),
               {"thigh.L": (34, 0, 2), "shin.L": (-36, 0, 0), "thigh.R": (-20, 0, -2), "shin.R": (-10, 0, 0), "foot.R": (30, 0, 0)},
               spine=(18, 12, 0), chest=(8, 8, 0), head=(-14, 0, 0))
    point = [("weapon", (0, -1, 0.35), (0, 0, 1))]   # crook leaning toward the target
    out.append(clip(rig, "Attack", [
        K(1, g), K(9, raise_, aims=[STAFF_SKY]), K(16, gather, aims=[STAFF_SKY]),
        K(BOLT_FRAME, thrust, (0, -0.08, 0), aims=point), K(BOLT_FRAME + 8, thrust, (0, -0.09, 0), aims=point),
        K(BOLT_FRAME + 18, P(g, spine=(4, 0, 0)), aims=hold), K(BOLT_FRAME + 26, g)], aims=hold, flowing=True))

    # Spell (storyboard "魔法発動シーン"): 構え -> 杖を掲げる -> 魔力の収束①② -> 魔法陣の展開①② -> 詠唱 -> 魔力の最大化
    # -> 発射の準備 -> 魔法の発射 (SPELL_FRAME) -> 飛翔 -> 着弾 -> 余波 -> 構えに戻る. The viewers draw the circles, the orb and the shot.
    chant = P(ARMS(upper_arm_R=(-0.3, -0.15, 0.94), forearm_R=(-0.05, -0.2, 0.98), upper_arm_L=(0.55, -0.6, 0.3), forearm_L=(0.3, -0.8, 0.5)),
              {"thigh.L": (10, 0, 4), "shin.L": (-12, 0, 0), "thigh.R": (-6, 0, -4), "shin.R": (-10, 0, 0)},
              spine=(-8, 0, 0), chest=(-6, 0, 0), head=(-18, 0, 0))
    swell = add(chant, P(spine=(-6, 0, 0), chest=(-4, 0, 0), head=(-6, 0, 0)))
    ready = P(raise_, {"thigh.L": (22, 0, 2), "shin.L": (-26, 0, 0), "thigh.R": (-10, 0, -2), "shin.R": (-14, 0, 0), "foot.R": (16, 0, 0)},
              spine=(-12, -12, 0), chest=(-8, -8, 0))
    out.append(clip(rig, "Spell", [
        K(1, g), K(10, raise_, aims=[STAFF_SKY]), K(18, gather, aims=[STAFF_SKY]), K(26, add(gather, P(head=(-4, 6, 0))), aims=[STAFF_SKY]),
        K(32, chant, aims=[STAFF_SKY]), K(40, swell, aims=[STAFF_SKY]), K(44, ready, aims=[STAFF_SKY]),
        K(SPELL_FRAME, thrust, (0, -0.08, 0), aims=point), K(SPELL_FRAME + 10, thrust, (0, -0.09, 0), aims=point),
        K(SPELL_FRAME + 22, P(g, spine=(4, 0, 0)), aims=hold), K(SPELL_FRAME + 30, g)], aims=hold, flowing=True))
    # Block: the staff is swung across the body as a ward
    ward = P(ARMS(upper_arm_R=(-0.3, -0.6, -0.75), forearm_R=(0.7, -0.6, 0.35), upper_arm_L=(0.4, -0.6, -0.7), forearm_L=(-0.6, -0.7, 0.3)),
             {"thigh.L": (20, 0, 2), "shin.L": (-30, 0, 0), "thigh.R": (-12, 0, -2), "shin.R": (-18, 0, 0), "foot.R": (24, 0, 0)},
             spine=(10, 0, 0), head=(-6, 0, 0))
    across = [("weapon", (-0.9, -0.15, 0.4), (0, -1, 0))]
    out.append(clip(rig, "Block", [K(1, g), K(9, ward, aims=across), K(16, ward, aims=across),
                                   K(18, add(ward, P(spine=(-10, 0, 0))), (0, 0.06, 0), aims=across), K(26, ward, (0, 0.05, 0), aims=across),
                                   K(36, g)], aims=hold))
    # Hit: the ward is beaten down and the bishop staggers back
    reel = add(ward, P(spine=(-22, 0, 6), head=(-20, 10, 0), thigh_L=(-12, 0, 0), thigh_R=(12, 0, 0), shin_R=(-28, 0, 0)))
    out.append(clip(rig, "Hit", [K(1, g), K(9, ward, aims=across), K(16, ward, aims=across),
                                 K(19, reel, (0, 0.12, 0), (-5, 0, 2), aims=across), K(30, ward, (0, 0.12, 0), aims=across),
                                 K(44, g)], aims=hold))
    # Death: the ward fails, the bishop sinks to his knees, the staff falls, he topples forward
    kneel = P({"thigh.L": (85, 0, 6), "shin.L": (-120, 0, 0), "foot.L": (30, 0, 0), "thigh.R": (20, 0, -6), "shin.R": (-125, 0, 0), "foot.R": (50, 0, 0)},
              ARMS(upper_arm_R=(-0.2, -0.2, -0.95), forearm_R=(-0.1, -0.5, -0.85), upper_arm_L=(0.2, -0.2, -0.95), forearm_L=(0.1, -0.5, -0.85)),
              spine=(28, 0, -6), chest=(12, 0, 0), head=(30, -15, 0))
    flat = P({"thigh.L": (10, 0, 6), "shin.L": (-20, 0, 0), "thigh.R": (6, 0, -6), "shin.R": (-14, 0, 0)},
             ARMS(upper_arm_R=(-0.3, -0.25, 0.92), forearm_R=(-0.2, -0.45, 0.87), upper_arm_L=(0.3, -0.25, 0.92), forearm_L=(0.2, -0.45, 0.87)),
             spine=(4, 0, 0), head=(-30, 30, 0))
    free = [("weapon", None, None)]
    out.append(clip(rig, "Death", [
        K(1, g), K(9, ward, aims=across), K(14, ward, aims=across), K(17, reel, (0, 0.08, 0), (-6, 0, 3), aims=free),
        K(28, kneel, (0, 0.04, 0), drop=0.52, aims=free), K(34, kneel, (0, 0, 0), (8, 0, 0), 0.52, free),
        K(46, flat, (0, -0.16, 0.02), (82, 0, 0), 0.1, free), K(50, flat, (0, -0.17, 0.035), (78, 0, 0), 0.1, free),
        K(56, flat, (0, -0.17, 0.02), (82, 0, 0), 0.1, free), K(74, flat, (0, -0.17, 0.02), (82, 0, 0), 0.1, free)], aims=hold))
    # Victory: the crozier lifted high, the free hand raised in blessing
    bless = P(ARMS(upper_arm_R=(-0.35, -0.1, 0.92), forearm_R=(-0.05, -0.1, 0.99), upper_arm_L=(0.6, -0.4, 0.6), forearm_L=(0.2, -0.3, 0.93)),
              spine=(-6, 0, 0), chest=(-6, 0, 0), head=(-16, 0, 0))
    out.append(clip(rig, "Victory", [K(1, g), K(12, bless, aims=[STAFF_SKY]), K(30, add(bless, P(head=(0, 8, 0))), aims=[STAFF_SKY]),
                                     K(44, bless, aims=[STAFF_SKY])], aims=hold))
    for a in out: natural_wrist(rig, a, "hand.R")   # the fist turns with the weapon
    return out

CLIPS["Bishop"] = bishop_clips
