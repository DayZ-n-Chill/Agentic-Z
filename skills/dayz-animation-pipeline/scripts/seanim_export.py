#!/usr/bin/env python3
"""Convert an authoring-viewer anim JSON (per-frame per-bone LOCAL quaternions)
into a SEAnim file (the open bridge format to DayZ's .anm via DayZATool).

Bone-frame convention (2026-10-02):
  The viewer stores each bone's rotation and rest offset in its rig's
  bone-local frame, inside a right-handed Y-up world. DayZ is left-handed and
  its .anm/SEAnim bone-local frame puts a chain child on X (finger phalanx
  offsets are (length,0,0) in a DayZATool-extracted vanilla SEAnim).
  seanim_rot/seanim_pos_cm apply one reflection per rig family, read from the
  rig's rest offsets (detect_rig_frame); any other rig is refused:
    jd  - JD Master Rig (jd_dayz.json): calibrated 2026-06-29, exact offline.
    fbx - BI FBX rig built by build_rig_dayz.py (rig_dayz.json): derived from
          the calibrated map offline; in game (2026-10-02) one LeftArm pose
          played as authored through it and wrong through the jd map.
  A root bone (no parent) is relative to the viewer world, which neither map
  covers. In game (a custom weapon, 2026-06-30) the jd map played a full-body action
  wrong (head and body needed Route A). In-game playback is the gate.
--rest-pose takes a DayZATool-extracted vanilla SEAnim of the same slot and
emits only the bones it contains (that mask fixed the flop in game). Its
positions are not used: DayZATool marks most bones of vanilla action extracts
RELATIVE (offsets from rest), and this file is ABSOLUTE. A bone the viewer rig
holds off bind is written off bind: the JD rig's RightHand_Dummy sent the
weapon to the back in game; leave it out of the reference.
The round-trip gate is structural: it re-reads what was written, not whether
the map is right (test_seanim_export.py checks the map).

Offline tool: it reads and writes only the paths it is given and needs neither
P:\\, DayZ Tools nor the game, so it does not gate on /dayz-preflight.
"""
import argparse, json, math, os, re, sys

def load_writer():
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import seanim_writer
    return seanim_writer

UNIT_CM = 100.0  # rig meters -> SEAnim cm (verified against the finger offsets of a local
                 # DayZATool extract of an AKS-74U clip; which clip under
                 # P:\DZ\anims\anm\player\ was not recorded, so not checked on P:\)

# Viewer bone-local frame -> DayZATool .seanim bone-local frame. Each map is a change of
# basis with det -1: rest offsets p -> M p, quaternion vector parts v -> -M v, w kept.
#  jd:  CALIBRATED 2026-06-29 against a DayZATool-extracted reference (one fire clip: its .txa via
#       plugin vs .anm extract): EXACT to 0.00deg over 73 bone/frame pairs.
#       rot (x,y,z,w) -> (-y,-z,x,w); pos (x,y,z) -> (y,z,-x).
#  fbx: the FBX rig's bone frames are the JD frames turned 90deg about Z, q_fbx = (y,-x,z,w)_jd
#       (113/114 rest rotations within 1deg, the root excepted), so this is the calibrated map
#       after that turn. DERIVED 2026-10-02, offline: rest offsets through it match DayZATool-
#       extracted vanilla SEAnims (77/77 bones within 5deg, 1.2% longer) and rest rotations land
#       within 0.87deg of where the jd map lands the JD rig; no rotation pair. In game 2026-10-02
#       (DayZDiag 1.29.163709) LeftArm keyed straight ahead on the FBX rig came out forward through
#       this map and out to the side through the jd map: one bone, rotations only
#       (weapon-anim-authoring-viewer.md, "Route C bone-frame maps, per rig").
#       rot (x,y,z,w) -> (-x,-z,-y,w); pos (x,y,z) -> (x,z,y).
def seanim_rot(frame, q):
    x, y, z, w = q
    if frame == 'jd':
        return (-y, -z, x, w)
    if frame == 'fbx':
        return (-x, -z, -y, w)
    raise ValueError('unknown rig frame %r' % (frame,))

def seanim_pos_cm(frame, p):
    x, y, z = p
    if frame == 'jd':
        v = (y, z, -x)
    elif frame == 'fbx':
        v = (x, z, y)
    else:
        raise ValueError('unknown rig frame %r' % (frame,))
    return tuple(c * UNIT_CM for c in v)

# Anatomical chain bones of OFP2_ManSkeleton. Only a child and a parent both on this list count
# for the bone axis: helpers (RightHand_Dummy, which the JD rig moves to the grip, its child
# Weapon_Root, IK helpers), Extra bones and face bones do not.
ANATOMICAL = re.compile(r'(Left|Right)(Shoulder|Arm|ArmRoll|ForeArm|ForeArmRoll|Hand|Hand(Thumb|Index|Middle)[1-3]'
                        r'|HandRing[1-3]?|HandPinky[1-3]?|UpLeg|UpLegRoll|Leg|LegRoll|Foot|ToeBase)')

# Roll fingerprints: (parent, child_a, child_b, vanilla (y, z) of child_a - child_b across the
# parent bone, DayZ cm). DayZATool extracts of vanilla p_erc_attackl_inplace_01_ras and of an
# AKS-74U clip (a local extract; which clip was not recorded, so not checked on P:\; the
# .anm files are binary): RightShoulder - LeftShoulder in Spine3 = (0, 0, 2.0); RightHandIndex1 -
# RightHandRing in RightHand = (-5.22, -2.75, -0.15), mirrored on the left hand. Through their
# maps both rigs read within 0.07deg of these; a rig rolled about its bone axes by ROLL_TOL_DEG
# or more reads further off.
ROLL_CHECKS = (('Spine3', 'RightShoulder', 'LeftShoulder', (0.0, 2.0)),
               ('RightHand', 'RightHandIndex1', 'RightHandRing', (-2.75, -0.15)),
               ('LeftHand', 'LeftHandIndex1', 'LeftHandRing', (2.75, 0.15)))
ROLL_TOL_DEG = 2.0

def detect_rig_frame(rig, min_per_side=4):
    """'jd' or 'fbx' from the rig's rest offsets; ValueError for any other rig.

    Bone axis: a chain child (offset within ~18deg of one axis, >= 5 mm) of a Left*
    bone sits on + of that axis and a child of a Right* bone on -, the split DayZ
    has on X; the axis is Y in the JD rig and X in the FBX rig. Only ANATOMICAL
    children of ANATOMICAL parents count. Roll: through the chosen map, each
    ROLL_CHECKS pair must lie within ROLL_TOL_DEG of vanilla's across-bone
    direction. Refused: a Blender-native rig (every child at +Y), a rig mixing
    frames, a rig rolled about its bone axes by ROLL_TOL_DEG or more on Spine3 or a
    hand, and one whose hand or shoulder layout differs as much. Not seen: a smaller
    roll, or one confined to bones the pairs do not reach.
    """
    seen = {'Left': {}, 'Right': {}}
    for b in rig['bones']:
        par = b.get('parent') or ''
        if not (ANATOMICAL.fullmatch(b['name']) and ANATOMICAL.fullmatch(par)):
            continue
        side = 'Left' if par.startswith('Left') else 'Right'
        v = b['pos']
        n = math.sqrt(sum(c * c for c in v))
        if n < 0.005:
            continue
        i = max(range(3), key=lambda k: abs(v[k]))
        if abs(v[i]) < 0.95 * n:
            continue
        label = ('+' if v[i] > 0 else '-') + 'XYZ'[i]
        seen[side].setdefault(label, []).append(b['name'])
    left, right = sorted(seen['Left']), sorted(seen['Right'])
    if not (len(left) == 1 and len(right) == 1 and left[0][0] == '+' and right[0][0] == '-'
            and left[0][1] == right[0][1] and left[0][1] in 'XY'
            and len(seen['Left'][left[0]]) >= min_per_side and len(seen['Right'][right[0]]) >= min_per_side):
        found = lambda s: ', '.join('%s x%d (e.g. %s)' % (k, len(v), v[0]) for k, v in sorted(seen[s].items())) or 'none'
        raise ValueError('cannot read the rig frame from rest offsets: chain children of Left* bones: %s; '
                         'of Right* bones: %s. Expected all +Y/-Y (JD rig) or all +X/-X (FBX rig from '
                         'build_rig_dayz.py), at least %d per side.' % (found('Left'), found('Right'), min_per_side))
    frame = 'jd' if left[0][1] == 'Y' else 'fbx'
    pos = {b['name']: b['pos'] for b in rig['bones']}
    parent = {b['name']: b.get('parent') for b in rig['bones']}
    for par, a, b2, (ey, ez) in ROLL_CHECKS:
        if parent.get(a) != par or parent.get(b2) != par:
            raise ValueError('cannot check the rig frame\'s roll: %s and %s are not both children of %s'
                             % (a, b2, par))
        d = [x - y for x, y in zip(seanim_pos_cm(frame, pos[a]), seanim_pos_cm(frame, pos[b2]))]
        across = math.hypot(d[1], d[2])
        if across < 0.5:
            raise ValueError('cannot check the rig frame\'s roll on %s: %s and %s are %.2f cm apart across '
                             'the bone' % (par, a, b2, across))
        cosang = (d[1] * ey + d[2] * ez) / (across * math.hypot(ey, ez))
        off = math.degrees(math.acos(max(-1.0, min(1.0, cosang))))
        if off > ROLL_TOL_DEG:
            raise ValueError('the rig frame reads %s by its bone axes but is rolled on %s: %s - %s lies %.1f deg '
                             'from vanilla across the bone (tolerance %g deg)'
                             % (frame, par, a, b2, off, ROLL_TOL_DEG))
    return frame

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--anim', required=True, help='viewer export JSON')
    ap.add_argument('--rig', required=True, help='the rig JSON the anim was authored on (rig_dayz.json or jd_dayz.json)')
    ap.add_argument('--out', required=True, help='output .seanim')
    ap.add_argument('--rest-pose', default=None, help='DayZATool-extracted vanilla SEAnim of the same slot: emit only its bones (optional)')
    ap.add_argument('--keys-only', action='store_true', help='emit only authored keyframes (default: dense)')
    a = ap.parse_args()
    sw = load_writer()

    anim = json.load(open(a.anim, encoding='utf-8'))
    rig = json.load(open(a.rig, encoding='utf-8'))
    try:
        frame = detect_rig_frame(rig)
    except ValueError as e:
        sys.exit('seanim_export: %s' % e)
    rest_pos = {b['name']: b['pos'] for b in rig['bones']}
    parent = {b['name']: b.get('parent') for b in rig['bones']}
    order = anim['bone_order']
    missing = [b for b in order if b not in rest_pos]
    if missing:
        sys.exit('seanim_export: %d anim bone(s) are not in the rig (pass the rig the anim was authored on): %s'
                 % (len(missing), ','.join(missing[:8])))
    fps = float(anim.get('fps', 30))
    frames = anim['frames']
    use_frames = set(anim['keyframes']) if a.keys_only else set(range(len(frames)))
    print('rig frame: %s (%s map)' % (frame, 'calibrated' if frame == 'jd' else 'derived'))

    if any(fr.get('pos') for fr in frames):
        print('WARN: the anim carries per-frame positions; they are ignored (only rest offsets are written)',
              file=sys.stderr)

    if a.rest_pose:
        if not os.path.exists(a.rest_pose):
            sys.exit('seanim_export: --rest-pose not found: %s' % a.rest_pose)
        refset = {b['name'] for b in sw.read_seanim(a.rest_pose)['bones']}
        print('rest-pose loaded:', len(refset), 'bones')
        # Structural parity with a vanilla action anim: emit ONLY the bones the
        # reference contains (vanilla action anims are spine-UP — they exclude
        # EntityPosition/Pelvis/legs; the idle provides the lower body). Including
        # the rig's absolute root/pelvis orientation makes the player flop in-game.
        kept = [b for b in order if b in refset]
        dropped = [b for b in order if b not in refset]
        if not kept:
            sys.exit('seanim_export: no anim bone is in the --rest-pose reference')
        order = kept
        print('bone-mask: emit %d bones (vanilla parity); dropped %d e.g. %s' % (len(kept), len(dropped), ','.join(dropped[:8])))

    roots = [b for b in order if not parent.get(b)]
    if roots:
        print('WARN: root bone(s) %s exported: their local frame is the viewer world, which the bone-frame '
              'map does not cover (an action anim drops them with --rest-pose)' % ','.join(roots), file=sys.stderr)

    bones = []
    for name in order:
        rot_keys = []
        for fr in sorted(use_frames):
            q = frames[fr]['bones'].get(name)
            if q:
                rot_keys.append((fr, seanim_rot(frame, q)))
        # Rest offset: the rig's, through the map. Not the --rest-pose reference's: DayZATool marks
        # most bones of vanilla action extracts RELATIVE (SEAnim bone modifiers, inherited by child
        # bones; read_seanim returns them, this script writes none), so their positions are offsets
        # from rest.
        pos_keys = [(0, seanim_pos_cm(frame, rest_pos[name]))]
        bones.append({'name': name, 'pos_keys': pos_keys, 'rot_keys': rot_keys})

    # No SEAnim note events: DayZATool rejects free-text notes ("malformed
    # event"). The convention caveat lives in the docstring/README, not in the
    # binary. Keeping notes empty makes --generate-anim output clean.
    sw.write_seanim(a.out, bones, framerate=fps, looped=False, anim_type=0, notes=[])

    # --- offline gate: structural round-trip (every emitted bone, rot + pos keys) ---
    rd = sw.read_seanim(a.out)
    # The writer sets frame_count to the last frame written plus one: len(frames) when dense,
    # the last authored keyframe plus one with --keys-only.
    written = max(f for b in bones for grp in ('pos_keys', 'rot_keys') for f, _ in b[grp]) + 1
    assert rd['frame_count'] == written, (rd['frame_count'], written)
    assert abs(rd['framerate'] - fps) < 1e-6
    assert [b['name'] for b in rd['bones']] == order, 'bone order mismatch'
    for src, got in zip(bones, rd['bones']):
        for grp, eps in (('rot_keys', 1e-5), ('pos_keys', 1e-3)):
            assert len(src[grp]) == len(got[grp]), (src['name'], grp, len(src[grp]), len(got[grp]))
            for (f0, v0), (f1, v1) in zip(src[grp], got[grp]):
                assert f0 == f1 and all(abs(x - y) < eps for x, y in zip(v0, v1)), (src['name'], grp, 'round-trip fail')
    print('SEAnim written:', a.out, os.path.getsize(a.out), 'bytes')
    print('  frames=%d  bones=%d  fps=%g  rig frame=%s' % (rd['frame_count'], len(rd['bones']), rd['framerate'], frame))
    print('  GATE: binary round-trip OK on every bone (rot+pos keys); bone order; fps OK')

if __name__ == '__main__':
    main()
