# King clips (exec'd after anims.py). Storyboard row 6: the king raises the greatsword in both hands high over
# the crown, steps in and brings it down in one royal cleave through the target on frame 16 - the blade bites
# the board and a golden shockwave rings out (the viewer / Unity draw the wave at KING_SLAM_FRAME).
KING_SLAM_FRAME = 19
SWORD_UP = ("weapon", (0, -0.25, 1), (1, 0, 0))
K_SHIELD = ("shield", "strap", (0.3, -1, 0))   # held upright before him, blade edge-on to the enemy

def two_hand(rig, act, free_from=None, target="grip.L"):
    """Bake the left arm onto the long grip with an IK constraint (posing both arms by direction never
    brought the fists together). free_from: from this frame on the left hand lets go (Death)."""
    pbs = rig.pose.bones
    fa = pbs["forearm.L"]
    ik = fa.constraints.new('IK'); ik.target = rig; ik.subtarget = target; ik.chain_count = 2
    rig.animation_data.action = act
    f0, f1 = (int(x) for x in act.frame_range)
    if free_from:
        ik.influence = 1.0; ik.keyframe_insert("influence", frame=free_from - 3)
        ik.influence = 0.0; ik.keyframe_insert("influence", frame=free_from)
    for o in bpy.context.selected_objects: o.select_set(False)   # bake acts on the ACTIVE armature: with several
    rig.select_set(True); bpy.context.view_layer.objects.active = rig   # pieces built it was another one ("Nothing to bake")
    bpy.ops.object.mode_set(mode='POSE')
    for b in pbs: b.select = b.name in ("upper_arm.L", "forearm.L")   # Blender 5: selection lives on the pose bone
    bpy.ops.nla.bake(frame_start=f0, frame_end=f1, only_selected=True, visual_keying=True, clear_constraints=True,
                     use_current_action=True, bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    for fc in fcurves(act):
        if "influence" in fc.data_path or fc.data_path.endswith(".scale"): fcurves_remove(act, fc)
    for b in pbs: b.scale = (1, 1, 1)
    for c in [c for c in fa.constraints if c.type == 'IK']: fa.constraints.remove(c)   # never leave it on the rig
    rig.animation_data.action = None

def fcurves_remove(act, fc):
    for ly in getattr(act, "layers", ()):
        for st in ly.strips:
            for cb in st.channelbags:
                if fc in cb.fcurves[:]: cb.fcurves.remove(fc); return
    if hasattr(act, "fcurves") and fc in act.fcurves[:]: act.fcurves.remove(fc)

KING_DUEL_BLOCK = 1.65   # the first, blocked cleave is swung from 1.65 squares (the king then steps in for the kill)
T_K_GUARD = (T_GUARD[0], T_GUARD[1] - (KING_DUEL_BLOCK - PAWN_DUEL), T_GUARD[2] + 0.07)   # top of the X: the chop stays clear of the head
KING_BLOCK_LUNGE = 0.0317   # solved: the point meets the top of the X on frame 16, 9 cm clear of the body

def king_clips(rig):
    G = P(ARMS(upper_arm_R=(-0.22, -0.25, -0.94), forearm_R=(0.05, -0.92, 0.35),
               upper_arm_L=(0.35, -0.35, -0.87), forearm_L=(-0.8, -0.5, 0.2)),   # forearm across the front: the shield faces the enemy
          spine=(3, 0, 0), head=(-4, 0, 0))
    out = []
    hold = (SWORD_UP, K_SHIELD)
    out.append(clip(rig, "Idle", [K(1, G), K(30, add(G, P(chest=(-2, 0, 0), head=(0, 6, 0)))), K(60, add(G, P(head=(0, -6, 0)))),
                                  K(90, G)], loop=True, aims=hold))
    # Walk: a heavy, measured royal step under the robe
    def step(s):
        return P(G, {"thigh.L": (14 * s, 0, 2), "shin.L": (-8 if s > 0 else -18, 0, 0), "foot.L": (6 * s, 0, 0)},
                 {"thigh.R": (-14 * s, 0, -2), "shin.R": (-18 if s > 0 else -8, 0, 0), "foot.R": (-6 * s, 0, 0)},
                 chest=(0, -4 * s, 0), hips=(0, 5 * s, 0))
    def passing(lift):
        o = "R" if lift == "L" else "L"
        return P(G, {f"thigh.{lift}": (24, 0, 0), f"shin.{lift}": (-40, 0, 0), f"thigh.{o}": (2, 0, 0), f"shin.{o}": (-6, 0, 0)})
    out.append(clip(rig, "Walk", [K(1, step(1)), K(13, passing("R")), K(25, step(-1)), K(37, passing("L")), K(49, step(1))],
                    loop=True, aims=hold))
    # Attack: both fists high over the crown, blade hanging back; a stamp forward and a straight overhead cleave
    # through the target's chest (frame 16) down into the board (KING_SLAM_FRAME)
    raise_ = P(ARMS(upper_arm_R=(-0.3, 0.0, 0.95), forearm_R=(0.35, 0.25, 0.9), upper_arm_L=(0.45, -0.5, -0.74), forearm_L=(-0.6, -0.75, 0.25)),
               {"thigh.L": (12, 0, 3), "shin.L": (-16, 0, 0), "thigh.R": (-8, 0, -3), "shin.R": (-12, 0, 0), "foot.R": (12, 0, 0)},
               spine=(-12, 0, 0), chest=(-6, 0, 0), head=(-10, 0, 0))
    cut = P(ARMS(upper_arm_R=(-0.15, -0.9, 0.4), forearm_R=(0.35, -0.9, -0.2), upper_arm_L=(0.6, -0.3, -0.75), forearm_L=(0.2, -0.9, 0.3)),
            {"thigh.L": (28, 0, 4), "shin.L": (-34, 0, 0), "thigh.R": (-16, 0, -4), "shin.R": (-10, 0, 0), "foot.R": (24, 0, 0)},
            spine=(22, 0, 0), chest=(8, 0, 0), head=(-14, 0, 0))
    slam = P(ARMS(upper_arm_R=(-0.2, -0.8, -0.55), forearm_R=(0.35, -0.7, -0.6), upper_arm_L=(0.6, -0.3, -0.75), forearm_L=(0.2, -0.9, 0.3)),
             {"thigh.L": (34, 0, 4), "shin.L": (-46, 0, 0), "foot.L": (8, 0, 0), "thigh.R": (-14, 0, -4), "shin.R": (-24, 0, 0), "foot.R": (30, 0, 0)},
             spine=(34, 0, 0), chest=(10, 0, 0), head=(-20, 0, 0))
    back = [("weapon", (0, 0.75, 0.66), (1, 0, 0))]       # blade hanging back over the crown
    chop = [("weapon", "target", T_CHEST)]                  # through the chest
    ground_ = [("weapon", (0, -0.72, -0.69), (1, 0, 0))]  # point bitten into the board (tip just at z=0)
    out.append(clip(rig, "Attack", [
        K(1, G), K(9, raise_, aims=back), K(13, raise_, (0, 0.02, 0), aims=back),
        K(16, cut, (0, -0.02, 0), aims=chop), K(KING_SLAM_FRAME, slam, (0, -0.03, 0), aims=ground_),
        K(28, slam, (0, -0.03, 0), aims=ground_), K(38, add(G, P(spine=(6, 0, 0))), (0, -0.01, 0)), K(48, G)],
        aims=hold, flowing=True))
    for fc in fcurves(out[-1]):   # the held slam (19..28) must not overshoot: free handles drove the blade into the board
        for kp in fc.keyframe_points:
            if KING_SLAM_FRAME <= kp.co.x <= 28: kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
        fc.update()
    # AttackBlocked (battle sheet): the overhead cleave stopped on the pawn's crossed blades, the greatsword
    # rebounding; KING_BLOCK_LUNGE solved so the outer blade lands on the guard (pawn KING_DUEL_BLOCK ahead)
    KB = KING_BLOCK_LUNGE
    tg = [("weapon", "target", T_K_GUARD)]
    out.append(clip(rig, "AttackBlocked", [
        K(1, G), K(9, raise_, aims=back), K(13, raise_, (0, 0.02, 0), aims=back),
        K(16, cut, (0, KB, 0), aims=tg), K(18, cut, (0, KB + 0.01, 0), aims=tg),
        K(23, add(raise_, P(spine=(6, 0, 0))), (0, KB * 0.3, 0), aims=back), K(36, G)], aims=hold, flowing=True))
    # Block: the great shield raised square to the attacker, the sword drawn back ready
    parry = P(ARMS(upper_arm_R=(-0.3, 0.2, -0.93), forearm_R=(-0.05, -0.9, 0.4), upper_arm_L=(0.4, -0.55, -0.73), forearm_L=(-0.85, -0.45, 0.25)),
              {"thigh.L": (16, 0, 2), "shin.L": (-22, 0, 0), "thigh.R": (-8, 0, -2), "shin.R": (-16, 0, 0), "foot.R": (16, 0, 0)},
              spine=(4, 0, 0), head=(-4, 0, 0))
    across = [("weapon", (-0.1, -0.3, 0.95), (1, 0, 0)), ("shield", "strap", (0.1, -1, 0))]
    out.append(clip(rig, "Block", [K(1, G), K(9, parry, aims=across), K(16, parry, aims=across),
                                   K(18, add(parry, P(spine=(-8, 0, 0))), (0, 0.05, 0), aims=across), K(26, parry, (0, 0.04, 0), aims=across),
                                   K(36, G)], aims=hold))
    reel = add(parry, P(spine=(-20, 0, 6), head=(-18, 10, 0), thigh_L=(-10, 0, 0), thigh_R=(12, 0, 0), shin_R=(-26, 0, 0)))
    out.append(clip(rig, "Hit", [K(1, G), K(9, parry, aims=across), K(16, parry, aims=across),
                                 K(19, reel, (0, 0.11, 0), (-5, 0, 2), aims=across), K(30, parry, (0, 0.1, 0), aims=across),
                                 K(44, G)], aims=hold))
    kneel = P({"thigh.L": (85, 0, 6), "shin.L": (-120, 0, 0), "foot.L": (30, 0, 0), "thigh.R": (20, 0, -6), "shin.R": (-125, 0, 0), "foot.R": (50, 0, 0)},
              ARMS(upper_arm_R=(-0.2, -0.2, -0.95), forearm_R=(-0.1, -0.5, -0.85), upper_arm_L=(0.2, -0.2, -0.95), forearm_L=(0.1, -0.5, -0.85)),
              spine=(24, 0, -6), chest=(10, 0, 0), head=(26, -15, 0))
    flat = P({"thigh.L": (10, 0, 6), "shin.L": (-20, 0, 0), "thigh.R": (6, 0, -6), "shin.R": (-14, 0, 0)},
             ARMS(upper_arm_R=(-0.3, -0.25, 0.92), forearm_R=(-0.2, -0.45, 0.87), upper_arm_L=(0.3, -0.25, 0.92), forearm_L=(0.2, -0.45, 0.87)),
             spine=(4, 0, 0), head=(-30, 30, 0))
    free = [("weapon", None, None)]
    out.append(clip(rig, "Death", [
        K(1, G), K(9, parry, aims=across), K(14, parry, aims=across), K(17, reel, (0, 0.08, 0), (-6, 0, 3), aims=free),
        K(28, kneel, (0, 0.04, 0), drop=0.52, aims=free), K(34, kneel, (0, 0, 0), (8, 0, 0), 0.52, free),
        K(46, flat, (0, -0.16, 0.02), (82, 0, 0), 0.1, free), K(50, flat, (0, -0.17, 0.035), (78, 0, 0), 0.1, free),
        K(56, flat, (0, -0.17, 0.02), (82, 0, 0), 0.1, free), K(74, flat, (0, -0.17, 0.02), (82, 0, 0), 0.1, free)], aims=hold))
    # Victory: the sword thrust to the sky, the shield grounded at his side, then the sword lowered point-down
    sky = P(ARMS(upper_arm_R=(-0.15, -0.1, 0.98), forearm_R=(0.15, -0.05, 0.99), upper_arm_L=(0.32, -0.1, -0.94), forearm_L=(0.25, -0.55, -0.8)),
            spine=(-8, 0, 0), chest=(-4, 0, 0), head=(-16, 0, 0))
    rest = P(ARMS(upper_arm_R=(-0.2, -0.45, -0.87), forearm_R=(0.15, -0.85, 0.1), upper_arm_L=(0.32, -0.1, -0.94), forearm_L=(0.25, -0.55, -0.8)),
             head=(-6, 0, 0))
    up = [("weapon", (0, 0, 1), (1, 0, 0))]; down = [("weapon", (0, -0.15, -1), (1, 0, 0))]
    out.append(clip(rig, "Victory", [K(1, G), K(10, sky, aims=up), K(26, sky, aims=up), K(36, rest, aims=down), K(54, rest, aims=down)],
                    aims=hold))
    for a in out:
        natural_wrist(rig, a, "hand.R", edge=True)   # the fist turns with the sword, its edges in line with the fist
    return out

CLIPS["King"] = king_clips
