# -*- coding: utf-8 -*-
"""
AZ Kimodo Motion - text-to-motion generation core.

Wraps the kimodo.cpp CLI (`kmd-generate`) and turns its raw output into a
keyed joint chain in the scene. The generator is a standalone executable, not
a Maya plug-in, so nothing here needs to be loaded into Maya's process.

kmd-generate writes two raw float32 blobs per take:

    root_positions.f32          frames * 3            (metres, Y-up)
    local_rotations_xyzw.f32    frames * joints * 4   (local quaternions, xyzw)

The joint count identifies the skeleton (30 = SOMA, 34 = Unitree G1). Both
tables come from kimodo.cpp's demo/skeletons_extra.go, whose offsets are the
parent-local differences of NVIDIA's Apache-2.0 neutral-joint assets.

The install root is resolved from $AZ_KIMODO_ROOT, falling back to the local
build. Nothing here hard-fails at import time - `probe()` reports what is
missing so the UI can say so instead of raising.

Launch in Maya:
    from azkimodo import az_kimodo_gen_qt
    az_kimodo_gen_qt.show()

VERSION 1.44.1

History
    1.44.1 Pose accuracy sits in the pose list, next to RECALCULATE.
    1.44.0 Pose accuracy. The solve holds a pose only softly, so the bake now
           carries each edited pose the rest of the way, easing in and out
           around it, which hits it without the jerk of a forced solve.
    1.43.1 A solve no longer stops halfway with arms near the body: the new
           ground turn had taken the name of the helper that keeps arms out.
           A pose both moved and turned no longer throws later placed poses
           off the path.
    1.43.0 Main carries the turn. Its rotateY is baked to where the take faces,
           with the sway of the gait left on the hips. Turn Main on a pose and
           the character faces that way by that pose and stays, and the rest of
           its path swings round with it.
    1.42.0 Main height belongs to the poses. Lift Main on a pose and the model
           sees it the way it sees the pelvis, so it solves a real jump, and
           the neighbouring poses stay on the ground. Y gets clean keys on the
           pose frames and the hips carry the rest. "Main stays at this height"
           keeps the old step up. Undo works: reading poses and rebuilding the
           marks no longer fill the queue, a solve is one undo step, and undo
           brings the pose list back. Cancel says it cancelled, is pinned under
           the body and is in the pose list too.
    1.41.1 The pose list follows the timeline: going to a frame with a pose
           selects it, and a frame without one clears the selection.
    1.41.0 Main places the character. Drag it on a frame and keep the pose: the
           character arrives there by that frame and stays, on X, Y and Z. The
           model is given the new path but never the height, and whatever it
           still misses by is written into Main, so the placement is exact.
    1.40.0 Made to work on Advanced Skeleton rigs that are not built on the UE5
           Mannequin. IK baking looked its bones up by UE5 names, found no limbs
           and skipped silently; it now works from the FK controls every such
           rig has. The chest was never animated at all, because the map asked
           for FKSpine3_M and these rigs have FKChest_M. A pose moved with an IK
           control is now read from the deformation joints, so Update sees it.
    1.39.0 Arms stay out of the body. The rig's own mesh is measured when it
           arrives - how thick the torso and arms really are - and after a bake
           any elbow or forearm that ends up inside is swung out, smoothly over
           time, with the hand keeping its orientation. For characters whose
           proportions are far from the generator's skeleton.
    1.38.1 Raising Main on Y now moves the whole character and stays that way.
           It has no keys, so the bake ignored it and the character fell back
           to the ground under a raised Main, while reading a pose took the
           height for part of the motion and told the model the body was
           floating, which broke the gait.
    1.38.0 A progress bar along the bottom of the window, fed by the solver's
           own steps. A generator built before this reports none, and the bar
           simply runs without a percentage.
    1.37.0 Limbs can be baked onto the IK controls. The FK bake stays as the
           source: each frame the IK controls are matched to the bones it
           produces, then the limb is switched to IK. Switching is possible at
           any time without generating again.
    1.36.0 Pose analyzer in place of the library. Analyze reads the animation
           at a chosen step and marks those frames on the timeline; a pose list
           window edits, adds and deletes them; Recalculate solves through
           exactly that list and bakes it onto the controls.
    1.35.0 One list of poses: click one and the character takes it, adjust it
           and update, or delete it. Deleting a pose that was already applied
           takes it back out of the animation on the next Apply.
    1.34.0 A pose no longer drags the character to where it was posed. It is
           fitted to the take on its frame: ground position and facing from
           the animation, height so the lower foot sits where the animation's
           does.
    1.33.0 Several poses in one solve. Add pose reads the pose and keeps it,
           so the timeline can move on to the next frame; Apply solves them
           together. A pose posed but not added is picked up by Apply rather
           than lost.
    1.32.0 Planted feet are locked after the bake. The model slides its feet a
           little even with no pins at all, so the body is now shifted along
           the ground to keep a foot that is standing where it stood. Edited
           frames stay where the animator put them.
    1.31.2 Apply pose no longer makes the feet slide as much. Pins every 5
           frames at strength 2 tripled the slide of planted feet in the
           model's own output (median 0.15 to 0.44 cm a frame). Every 10
           frames at strength 1 brings that to 0.27 while the take strays no
           further from what it was, and the root is no longer pinned along a
           straight line between them.
    1.31.1 The head no longer sinks into the body when solving through pins.
           The neck bones cannot be read off this rig, so they were left out
           of the pin, and the head's position was worked out through a neck
           that was simply wrong. The model, trained with every joint position
           held, then folded the neck: the head came down from 33 cm above the
           chest to 1. The neck is now read off its FK controls, which the
           retarget writes exactly, and a position stays pinned whenever the
           rotations leading to it are known.
    1.31.0 Editing a take is one button. Pose the character on a frame and
           press Apply pose: the tool reads the pose, snapshots the rest of
           the animation off the rig, solves again with the same prompt and
           seed, and bakes the result. The prompt, seed and earlier edits live
           on the rig, so they survive closing the window and saving the scene.
    1.30.1 Pin range pointed at a RETARGET field that moved to CHARACTER.
    1.30.0 The character comes with the window. Opening the tool finds a rig
           the retarget can drive in the scene, or imports the character
           file, records its bind pose and measures the reference - so the
           first thing on screen is a character ready to animate, not an
           empty retarget to set up. Retarget after generate is on by
           default; the take lands on the character as it arrives.
    1.28.0 Clearing the rig puts the FK/IK blends back. A retarget has to
           move a limb to FK or the bake is ignored, but it wrote the value
           straight on and nothing ever undid it, so a rig that shipped with
           its legs in IK stayed in FK for good.
    1.27.0 Reading a pose off the rig was measured against the wrong
           reference. The bind skeleton takes its orientation from
           constraints rather than from its parents, so the alignment never
           reached the joints that inherit one - wrists came back 65 degrees
           out, forearms 22, and the error doubled every time a pin was
           re-read. The reference is measured on the controls now and read
           back off the bones, and a bone that does not follow its own control
           one for one - the two neck bones here, one blended and one with no
           driver at all - is left unread instead of reporting its parent.
           Round trip measured 65.5 degrees before, 0.000 after; five passes
           of the loop drift 65.5/131.1/163.6 before, 0.000 after.
    1.26.0 Ease a hard pin in and out. It used to switch on between one
           frame and the next and the solve lurched to meet it - 133 cm of
           movement in a single frame where 18 was normal. The mask is a
           weight now, so the edges of a hold fade. A hold also reaches the
           frame it names - one ending on 60 let go on 58. A locked grab no
           longer forces hard pinning on: measured over a twenty-frame hold
           it held no better than the soft version and jumped 130 cm in one
           frame where the soft version jumped 36.
    1.25.1 The frame and hold fields react when you finish typing, not on
           every keystroke. Typing 78 delivered 7 first, which moved the pin
           and rebuilt the table out from under the field being typed into,
           so the second digit never arrived.
    1.25.0 A pin can hold until a later frame. A grab lasts, and one pinned
           instant let the hand drift either side of it; a hold now spreads
           itself across its own span.
    1.24.0 A pin editor rather than a pin list: one row per pin, its frame
           and what it holds editable in place, and the two things you do to
           it - re-read the pose, remove it - on the row itself.
           A rig now keeps its references side by side; one slot meant the
           retarget wiped the one a capture needs.
    1.23.0 Measure the reference hips at bind, not at whatever pose the
           scene was showing. A pose read off an animated rig recorded that
           frame as the reference, so every pin came out standing at the
           origin and the character never travelled. The guard meant to
           catch this asked the bind bones, which carry no keys.
    1.22.0 Offer dropping the reference pose's leftover twist. Aligning by
           the shortest arc says nothing about rotation around the bone, so
           the rig's bind roll survives into the reference - a real gap, but
           on this rig removing it changed nothing measurable, so it is off
           by default instead of being sold as the fix.
    1.21.0 A damping dial for the head and neck. The generator swings them
           30 to 42 degrees on an ordinary run and this rig cannot absorb
           it - its second neck bone has no driver and simply follows the
           first - so the bend piles up in one place and the mesh twists.
    1.20.0 Bake the travel onto the rig's global control instead of the hips,
           so it follows the character rather than sitting at the origin
           while the shot walks away from it.
    1.19.0 Respect the scene frame rate. The model samples at 30 Hz and the
           tool laid one sample per frame whatever the scene was set to, so
           a 24 fps scene played every take a quarter too fast. Takes are
           resampled now - positions blended, rotations slerped.
    1.18.0 Fill the gaps between key poses with root-only pins, so the
           character covers the ground instead of loitering by one pin and
           bolting to the next. Measured on a four-metre run: 6/15/33 per
           cent of the first leg covered at its quarter points, against
           12/50/64 with the path pinned.
    1.17.0 Cache the encoded prompt. Encoding loads a 13 GB text model -
           17.6 s of a 50 s run - and is identical while the words do not
           change, so a run now writes its embedding out and later runs of
           the same prompt hand that back instead of encoding again.
    1.16.2 Read a pin at its own frame. Both pinning and updating read the
           rig wherever the timeline happened to sit, so editing a pin on an
           already-animated rig captured the current frame's pose instead of
           the one being edited.
    1.16.1 Draw a pin's ghost where the character is. A pose read off the
           rig stores its hips in model space, measured from the rig's bind
           position, so the preview stood near the world origin instead of
           on the character.
    1.16.0 Pins can be edited: re-read the pose, change what it holds, or
           move it to another frame. Changing the Hold needs no rig at all -
           the mask comes from the mode and the pose is already stored.
    1.15.0 Read a pinned pose off the bind skeleton rather than the FK
           controls, so a pose made with the IK legs or arms is the pose
           that gets pinned. The FK controls do not move in IK, so they
           captured a pose nobody was looking at.
    1.14.1 Record the bind pose for a rig that was opened rather than
           imported. Only the FBX import captured it, so setting the target
           by selection left pins with nothing to measure against.
    1.14.0 Pinned poses stand up in the scene as coloured ghosts that appear
           only on their own frame, so a pin can be scrubbed to and looked
           at instead of being a number in a list.
    1.13.0 An exact pin. Holding every joint rotation - the only thing the
           decoder reads - and forcing it makes a pinned frame come back as
           authored rather than approximately.
    1.12.0 A "Hands locked" pin that actually locks. Pinning a hand POSITION
           cannot hold it - the decoder rebuilds every joint from rotations
           and never reads a joint position - so this freezes the arm
           chain's rotations instead, which hard pinning can force even
           though the model was never conditioned on them.
    1.11.0 Hands-only pins, pinning a run of frames in one press, a dial for
           how hard the solve is pulled toward the pins, and a hard mode that
           forces the pinned channels exactly instead of pulling toward them.
    1.10.0 Four defects an audit surfaced. Reading a pose off the rig used
           to pose the rig first and hand back that pose instead of the
           animator's; a retarget with no cached reference measured it after
           cutting the keys, off a drifted pose; the pinned take came back
           shifted because the origin was never added back; and the modes
           that place the body in the world left the hips position free, so
           the root path they promised to hold was only half held.
    1.9.0  Bake onto an Advanced Skeleton control rig, not just the bind
           skeleton: its FK controls sit on the bones, so the map is the
           bone map renamed. Blends are moved to FK first, since a limb left
           in IK ignores whatever lands on its FK controls.
    1.8.0  Pin poses straight off the character rig. The capture inverts the
           retarget, so it is exact for every mapped joint; the ones the rig
           has no bone for are left out of the mask rather than pinned at an
           inherited value.
    1.7.0  Partial pins. The sampler mask is per element, so a pin can hold
           just the root path, just the feet, or one half of the body, and
           the constraint file now carries that mask instead of the tool
           hard-coding one policy.
    1.6.1  Catch a pin past the end of the take in the UI, naming the frame
           and the limit, instead of letting the generator report it a
           minute into the solve.
    1.6.0  Pose pins: author poses on a copy of the generator's skeleton,
           pin them to frames, and let the diffusion sampler fill in the
           motion around them through the new kmd-constrain build.
    1.5.1  Store the rig's bind pose on import and put it back when the rig
           is cleared. Dropping curves leaves a joint where it last was,
           not at bind, and re-measuring off that pose gave a root-motion
           scale of 0.10 instead of 0.96.
    1.5.0  A new generation supersedes the last: the previous take's joints
           are deleted rather than hidden. "Clear rig animation" wipes the
           baked keys and the cached reference pose, which is the way out
           when the first retarget ran on a rig that was not in bind pose.
    1.4.0  Retarget modes: a new take replaces the rig's animation by
           default, or appends after the last key. The reference pose is
           cached on the rig, because it is only in bind pose once.
    1.3.1  Refuse the generated take as a retarget target and say which
           bones a rig is missing; generation leaves the take selected, so
           pick-from-selection used to land on it.
    1.3.0  Reload both modules from show() and from the menu; a UI-only reload
           left a stale core behind and every newly added function vanished.
    1.2.0  FBX import hardened: settings pinned instead of inherited from the
           user's sticky presets (MergeMode silently imported nothing), first
           LOD lifted out of its LOD group, contents reported after import.
           Empty prompt reports plainly instead of raising.
    1.1.0  Retarget onto an existing skeleton; UE5 Mannequin map, rest-pose
           alignment so a T-posed source drives an A-posed rig.
    1.0.0  Generate through kmd-generate and key the take onto a fresh chain.
"""

from __future__ import print_function

import contextlib
import hashlib
import json
import math
import os
import shutil
import struct
import time

try:
    import maya.cmds as cmds
    import maya.mel as mel
    import maya.api.OpenMaya as om2
except Exception:
    cmds = None
    mel = None
    om2 = None

VERSION = "1.44.1"

def _default_root():
    """The first kimodo.cpp checkout on any drive, else C:/kimodo.cpp.

    $AZ_KIMODO_ROOT still wins - see install_root. This only decides what
    happens when nothing has been said, which on a machine set up by
    kimodo.bat means the folder it chose.
    """
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        candidate = "%s:/kimodo.cpp" % letter
        if os.path.isfile(candidate + "/demo/main.go"):
            return candidate
    return "C:/kimodo.cpp"


DEFAULT_ROOT = _default_root()

# Newest build first: the Vulkan build is the one worth running when present.
_GENERATOR_CANDIDATES = (
    "build/vulkan/kmd-generate.exe",
    "build/release/kmd-generate.exe",
    "build/debug/kmd-generate.exe",
    "build/vulkan/kmd-generate",
    "build/release/kmd-generate",
)

MODEL_CATALOG = (
    ("soma-rp-v1.1", "SOMA RP v1.1", "models/kimodo-soma-rp-v1.1-f32.gguf",
     "soma30", "Rigplay data, 30-joint human skeleton - the default"),
    ("soma-seed-v1.1", "SOMA SEED v1.1", "models/kimodo-soma-seed-v1.1-f32.gguf",
     "soma30", "Open SEED data, same 30-joint human skeleton"),
    ("g1-rp-v1", "G1 RP v1", "models/kimodo-g1-rp-v1-f32.gguf",
     "g1skel34", "Rigplay data retargeted to the Unitree G1 robot"),
    ("g1-seed-v1", "G1 SEED v1", "models/kimodo-g1-seed-v1-f32.gguf",
     "g1skel34", "Open SEED data retargeted to the Unitree G1 robot"),
    ("smplx-rp-v1", "SMPL-X RP v1", "models/kimodo-smplx-rp-v1-f32.gguf",
     "smplx22", "Restricted licence - not distributed"),
)

# The model samples motion at a fixed 30 Hz. A scene running at anything else
# needs the take resampled, or it plays at the wrong speed - 150 samples laid
# on 24 fps frames is five seconds of motion crammed into four.
MODEL_FPS = 30.0
FPS = MODEL_FPS
MIN_FRAMES = 20
MAX_FRAMES = 150


# --------------------------------------------------------------------------- #
# Skeleton tables
# --------------------------------------------------------------------------- #

SOMA30 = {
    "key": "soma30",
    "names": [
        "Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw",
        "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm",
        "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder",
        "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd",
        "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase",
        "RightLeg", "RightShin", "RightFoot", "RightToeBase",
    ],
    "parents": [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16,
                17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28],
    "offsets": [
        (0.0, 0.0, 0.0),
        (-0.00013727, 0.0500376256, -0.00053726669),
        (-1.86574103e-9, 0.0712530139, -0.000298248546),
        (-5.75188398e-9, 0.0755006305, -0.00815970992),
        (-0.00181676517, 0.263112953, -0.00553348292),
        (-2.85102231e-8, 0.0770939664, 0.0230258546),
        (-4.5975437e-8, 0.0612891595, 0.0195370861),
        (2.63687901e-5, 0.0047559225, 0.0309494062),
        (0.0320638079, 0.0538020513, 0.0758688308),
        (-0.0322244017, 0.05361869, 0.0755823359),
        (0.0162165175, 0.232371641, 0.0511341324),
        (0.149198457, 2.19397873e-8, -0.0550232576),
        (0.287393078, 2.50268389e-9, -2.58787737e-5),
        (0.270939812, -7.06625108e-9, 2.60897248e-5),
        (0.122686267, -0.0322017573, 0.0483306876),
        (0.190119595, -0.00312878387, -0.000339570373),
        (-0.0138011824, 0.231803086, 0.0521415786),
        (-0.150371962, 1.17387901e-7, -0.0554560437),
        (-0.287366393, 1.87628082e-8, -2.59709359e-5),
        (-0.271336198, -1.16767401e-9, 2.61269368e-5),
        (-0.122642483, -0.0321145448, 0.0480403904),
        (-0.190005945, -0.00306615542, -0.0003157343),
        (0.10043214, -0.0843452671, 0.0259565473),
        (-1e-8, -0.432217537, -0.00802912805),
        (1e-8, -0.421550959, -0.0348152298),
        (0.0, -0.0505947206, 0.132315294),
        (-0.10047278, -0.0829525995, 0.0262031695),
        (1e-8, -0.433622059, -0.00805555828),
        (2e-8, -0.421173943, -0.0347839785),
        (-3.42907669e-9, -0.0507960932, 0.132841956),
    ],
}

G1SKEL34 = {
    "key": "g1skel34",
    "names": [
        "pelvis_skel", "left_hip_pitch_skel", "left_hip_roll_skel",
        "left_hip_yaw_skel", "left_knee_skel", "left_ankle_pitch_skel",
        "left_ankle_roll_skel", "left_toe_base", "right_hip_pitch_skel",
        "right_hip_roll_skel", "right_hip_yaw_skel", "right_knee_skel",
        "right_ankle_pitch_skel", "right_ankle_roll_skel", "right_toe_base",
        "waist_yaw_skel", "waist_roll_skel", "waist_pitch_skel",
        "left_shoulder_pitch_skel", "left_shoulder_roll_skel",
        "left_shoulder_yaw_skel", "left_elbow_skel", "left_wrist_roll_skel",
        "left_wrist_pitch_skel", "left_wrist_yaw_skel", "left_hand_roll_skel",
        "right_shoulder_pitch_skel", "right_shoulder_roll_skel",
        "right_shoulder_yaw_skel", "right_elbow_skel", "right_wrist_roll_skel",
        "right_wrist_pitch_skel", "right_wrist_yaw_skel", "right_hand_roll_skel",
    ],
    "parents": [-1, 0, 1, 2, 3, 4, 5, 6, 0, 8, 9, 10, 11, 12, 13, 0, 15, 16,
                17, 18, 19, 20, 21, 22, 23, 24, 17, 26, 27, 28, 29, 30, 31, 32],
    "offsets": [
        (0.0, 0.0, 0.0), (0.064452, -0.1027, 0.0), (0.052, -0.030465, 0.0),
        (0.0, -0.12412, 0.025001), (0.0021489, -0.17734, -0.078273),
        (-9.4445e-05, -0.30001, 0.0), (0.0, -0.017558, 0.0),
        (0.0, -0.035, 0.14), (-0.064452, -0.1027, 0.0),
        (-0.052, -0.030465, 0.0), (0.0, -0.12412, 0.025001),
        (-0.0021489, -0.17734, -0.078273), (9.4445e-05, -0.30001, 0.0),
        (0.0, -0.017558, 0.0), (0.0, -0.035, 0.14), (0.0, 0.0, 0.0),
        (0.0, 0.044, -0.0039635), (0.0, 0.0, 0.0),
        (0.10022, 0.24778, 0.0039563), (0.038, -0.013831, 0.0),
        (0.00624, -0.1032, 0.0), (0.0, -0.080518, 0.015783),
        (0.00188791, -0.01, 0.1), (0.0, 0.0, 0.038), (0.0, 0.0, 0.046),
        (0.0, 0.0, 0.1), (-0.10021, 0.24778, 0.0039563),
        (-0.038, -0.013831, 0.0), (-0.00624, -0.1032, 0.0),
        (0.0, -0.080518, 0.015783), (-0.00188791, -0.01, 0.1),
        (0.0, 0.0, 0.038), (0.0, 0.0, 0.046), (0.0, 0.0, 0.1),
    ],
}

SKELETONS = {30: SOMA30, 34: G1SKEL34}


# --------------------------------------------------------------------------- #
# Install discovery
# --------------------------------------------------------------------------- #

def install_root():
    """Where kimodo.cpp lives. $AZ_KIMODO_ROOT wins so the tool survives a move."""
    return os.environ.get("AZ_KIMODO_ROOT", DEFAULT_ROOT).replace("\\", "/").rstrip("/")


def generator_path(root=None):
    """First kmd-generate that actually exists, or "" when none does."""
    base = root or install_root()
    for relative in _GENERATOR_CANDIDATES:
        candidate = os.path.join(base, relative).replace("\\", "/")
        if os.path.isfile(candidate):
            return candidate
    return ""


def text_bundle_path(root=None):
    return os.path.join(root or install_root(),
                        "generated/llm2vec-text-bundle").replace("\\", "/")


def child_environment(generator=None):
    """PATH for the child process.

    ninja drops ggml*.dll into build/<cfg>/bin while the executables land one
    level up, so a fresh build cannot start until that directory is reachable.
    """
    env = dict(os.environ)
    exe = generator or generator_path()
    if exe:
        exe_dir = os.path.dirname(exe)
        extra = [exe_dir, os.path.join(exe_dir, "bin")]
        env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def available_models(root=None):
    """Catalog entries whose GGUF is actually on disk, in catalog order."""
    base = root or install_root()
    found = []
    for model_id, label, relative, skeleton_key, note in MODEL_CATALOG:
        path = os.path.join(base, relative).replace("\\", "/")
        if os.path.isfile(path):
            found.append({"id": model_id, "label": label, "path": path,
                          "skeleton_key": skeleton_key, "note": note})
    return found


def probe(root=None):
    """Report install health without raising, for the UI to display."""
    base = root or install_root()
    generator = generator_path(base)
    bundle = text_bundle_path(base)
    models = available_models(base)

    problems = []
    if not os.path.isdir(base):
        problems.append("install root not found: %s" % base)
    if not generator:
        problems.append("kmd-generate not built under %s/build" % base)
    if not os.path.isdir(bundle):
        problems.append("text bundle missing: %s" % bundle)
    if not models:
        problems.append("no motion GGUF found under %s/models" % base)

    return {"root": base, "generator": generator, "text_bundle": bundle,
            "models": models, "problems": problems, "ok": not problems}


# --------------------------------------------------------------------------- #
# Command assembly
# --------------------------------------------------------------------------- #

def write_segments(out_dir, segments):
    """Write one prompt file per segment. Returns the paths, in order.

    generate.cpp reads each file whole, trailing newline included, so the text
    is written without one.
    """
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    paths = []
    for index, segment in enumerate(segments):
        path = os.path.join(out_dir, "p%02d.txt" % (index + 1)).replace("\\", "/")
        with open(path, "wb") as handle:
            handle.write(segment["prompt"].strip().encode("utf-8"))
        paths.append(path)
    return paths


def build_command(model_path, out_dir, segments, steps=100, seed=42,
                  transition=8, root=None):
    """Assemble the kmd-generate argv for one or many prompt segments."""
    base = root or install_root()
    generator = generator_path(base)
    if not generator:
        raise IOError("kmd-generate not found under %s" % base)

    prompt_paths = write_segments(out_dir, segments)
    bundle = text_bundle_path(base)

    if len(segments) == 1:
        return [generator, model_path, bundle, prompt_paths[0],
                str(int(segments[0]["frames"])), str(int(steps)),
                str(int(seed)), out_dir]

    argv = [generator, model_path, bundle, "--sequence", str(int(transition)),
            str(int(steps)), str(int(seed)), out_dir]
    for segment, path in zip(segments, prompt_paths):
        argv += [str(int(segment["frames"])), path]
    return argv


def new_take_dir(root=None):
    """Timestamped folder so takes never overwrite each other."""
    base = os.path.join(root or install_root(), "maya-output")
    path = os.path.join(base, time.strftime("%Y%m%d_%H%M%S")).replace("\\", "/")
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def discard_unfinished_take(take_dir):
    """Remove the folder of a cancelled solve. A finished motion is never touched."""
    if not take_dir or not os.path.isdir(take_dir):
        return
    if os.path.basename(os.path.dirname(take_dir.rstrip("/"))) != "maya-output":
        return
    if not os.path.exists(os.path.join(take_dir, "root_positions.f32")):
        shutil.rmtree(take_dir, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Blob parsing
# --------------------------------------------------------------------------- #

def _read_f32(path):
    with open(path, "rb") as handle:
        blob = handle.read()
    if len(blob) % 4:
        raise ValueError("%s is not a whole number of float32 values" % path)
    return struct.unpack("<%df" % (len(blob) // 4), blob)


def load_take(folder):
    """Return (frames, joints, roots, quats) for a kmd-generate output folder."""
    root_path = os.path.join(folder, "root_positions.f32")
    quat_path = os.path.join(folder, "local_rotations_xyzw.f32")
    for path in (root_path, quat_path):
        if not os.path.isfile(path):
            raise IOError("missing %s" % path)

    roots = _read_f32(root_path)
    quats = _read_f32(quat_path)

    if len(roots) % 3:
        raise ValueError("root_positions.f32 is not a multiple of 3 floats")
    frames = len(roots) // 3

    if not frames or len(quats) % (frames * 4):
        raise ValueError("local_rotations_xyzw.f32 does not divide into "
                         "%d frames" % frames)
    joints = len(quats) // (frames * 4)

    if joints not in SKELETONS:
        raise ValueError("no skeleton table for %d joints (known: %s)"
                         % (joints, sorted(SKELETONS)))
    return frames, joints, roots, quats


# --------------------------------------------------------------------------- #
# Scene construction
# --------------------------------------------------------------------------- #

def scene_fps():
    """Frames per second of the scene, whatever time unit it is set to.

    Asking the API how many UI units fit in a second covers every unit Maya
    has, including the NTSC rates that are not whole numbers, without a table
    of names to fall out of date.
    """
    try:
        return om2.MTime(1.0, om2.MTime.kSeconds).asUnits(om2.MTime.uiUnit())
    except Exception:
        return MODEL_FPS


def resample_take(frames, joints, roots, quats, fps):
    """Move a 30 Hz take onto the scene's frame rate, keeping its duration.

    Positions are blended straight; rotations go through slerp, since a
    straight blend of two quaternions shortens the arc and dips the limb.
    """
    if abs(fps - MODEL_FPS) < 1e-6 or frames < 2:
        return frames, roots, quats

    seconds = float(frames) / MODEL_FPS
    out_frames = max(2, int(round(seconds * fps)))
    step = MODEL_FPS / fps

    out_roots = []
    out_quats = []
    for frame in range(out_frames):
        position = min(frame * step, float(frames - 1))
        first = int(position)
        second = min(first + 1, frames - 1)
        blend = position - first

        for axis in range(3):
            a = roots[first * 3 + axis]
            b = roots[second * 3 + axis]
            out_roots.append(a + (b - a) * blend)

        for joint in range(joints):
            base_a = (first * joints + joint) * 4
            base_b = (second * joints + joint) * 4
            if blend <= 0.0 or first == second:
                out_quats.extend(quats[base_a:base_a + 4])
                continue
            mixed = om2.MQuaternion.slerp(
                om2.MQuaternion(*quats[base_a:base_a + 4]),
                om2.MQuaternion(*quats[base_b:base_b + 4]), blend)
            out_quats.extend([mixed.x, mixed.y, mixed.z, mixed.w])

    return out_frames, out_roots, out_quats


def take_frame_to_scene(frame, start_frame=1, fps=None):
    """A take frame is a model sample; the scene may count time differently."""
    fps = scene_fps() if fps is None else fps
    return start_frame + int(round(frame * fps / MODEL_FPS))


def scene_scale():
    """Metres to whatever the scene is working in."""
    unit = cmds.currentUnit(query=True, linear=True)
    return {"mm": 1000.0, "cm": 100.0, "m": 1.0,
            "in": 39.3700787, "ft": 3.2808399}.get(unit, 100.0)


def build_skeleton(skeleton, scale, prefix):
    """Create the rest hierarchy and return the joint names in table order."""
    names = skeleton["names"]
    parents = skeleton["parents"]
    offsets = skeleton["offsets"]

    created = []
    for index, name in enumerate(names):
        parent = parents[index]
        if parent < 0:
            cmds.select(clear=True)
        else:
            cmds.select(created[parent], replace=True)
        created.append(cmds.joint(name=prefix + name, position=(0.0, 0.0, 0.0)))

    # cmds.joint back-orients a parent the moment its first child appears, so
    # the rest pose only settles once every joint exists. Re-stamp it here and
    # zero jointOrient, so the baked quaternions can drive .rotate directly.
    for index, joint in enumerate(created):
        offset = offsets[index]
        cmds.setAttr(joint + ".jointOrient", 0.0, 0.0, 0.0, type="double3")
        cmds.setAttr(joint + ".rotate", 0.0, 0.0, 0.0, type="double3")
        cmds.setAttr(joint + ".translate",
                     offset[0] * scale, offset[1] * scale, offset[2] * scale,
                     type="double3")
        cmds.setAttr(joint + ".rotateOrder", 0)  # XYZ, matches the euler below

    cmds.select(clear=True)
    return created


def _euler_degrees(x, y, z, w):
    """xyzw quaternion -> XYZ euler in degrees, via Maya's own conversion."""
    euler = om2.MQuaternion(x, y, z, w).asEulerRotation()
    euler.reorderIt(om2.MEulerRotation.kXYZ)
    return (om2.MAngle(euler.x, om2.MAngle.kRadians).asDegrees(),
            om2.MAngle(euler.y, om2.MAngle.kRadians).asDegrees(),
            om2.MAngle(euler.z, om2.MAngle.kRadians).asDegrees())


def apply_animation(joints, frames, roots, quats, scale, start_frame):
    joint_count = len(joints)
    root = joints[0]

    for frame in range(frames):
        time_value = start_frame + frame

        base = frame * 3
        cmds.setKeyframe(root, attribute="translateX", time=time_value,
                         value=roots[base] * scale)
        cmds.setKeyframe(root, attribute="translateY", time=time_value,
                         value=roots[base + 1] * scale)
        cmds.setKeyframe(root, attribute="translateZ", time=time_value,
                         value=roots[base + 2] * scale)

        offset = frame * joint_count * 4
        for index, joint in enumerate(joints):
            cursor = offset + index * 4
            rx, ry, rz = _euler_degrees(quats[cursor], quats[cursor + 1],
                                        quats[cursor + 2], quats[cursor + 3])
            cmds.setKeyframe(joint, attribute="rotateX", time=time_value, value=rx)
            cmds.setKeyframe(joint, attribute="rotateY", time=time_value, value=ry)
            cmds.setKeyframe(joint, attribute="rotateZ", time=time_value, value=rz)

    # Euler curves taken straight from quaternions flip whenever a channel wraps.
    for joint in joints:
        cmds.filterCurve(joint + ".rotateX", joint + ".rotateY",
                         joint + ".rotateZ", filter="euler")


def import_take(folder, scale=None, start_frame=1, prefix="kimodo_",
                set_range=True, group=True, match_scene_fps=True):
    """Build the skeleton for a take folder and key the motion onto it."""
    frames, joints, roots, quats = load_take(folder)
    skeleton = SKELETONS[joints]

    if scale is None:
        scale = scene_scale()

    fps = scene_fps()
    samples = frames
    if match_scene_fps:
        frames, roots, quats = resample_take(frames, joints, roots, quats, fps)

    created = build_skeleton(skeleton, scale, prefix)
    apply_animation(created, frames, roots, quats, scale, start_frame)

    top = created[0]
    if group:
        # With an older take of the same name in the scene these are paths, and
        # grouping changes every path.
        ids = cmds.ls(created, uuid=True)
        holder = cmds.group(top, name=prefix + "take_GRP")
        created = [cmds.ls(uid, long=True)[0] for uid in ids]
        cmds.addAttr(holder, longName="kimodoTake", dataType="string")
        cmds.setAttr(holder + ".kimodoTake", folder, type="string")
        top = holder

    if set_range:
        end = start_frame + frames - 1
        cmds.playbackOptions(minTime=start_frame, maxTime=end,
                             animationStartTime=start_frame,
                             animationEndTime=end)

    prompt = read_prompt(folder)
    rate = ""
    if frames != samples:
        rate = (" - resampled from %d samples at %g fps to %g fps"
                % (samples, MODEL_FPS, fps))
    print("[AZ Kimodo Motion %s] %s: %d frames, %d joints, unit scale %.4g%s%s"
          % (VERSION, skeleton["key"], frames, joints, scale, rate,
             (" - %r" % prompt) if prompt else ""))
    return {"top": top, "joints": created, "frames": frames,
            "samples": samples, "fps": fps,
            "joint_count": joints, "skeleton": skeleton["key"], "folder": folder}


def read_prompt(folder):
    path = os.path.join(folder, "prompt.txt")
    if not os.path.isfile(path):
        segment = os.path.join(folder, "p01.txt")
        path = segment if os.path.isfile(segment) else ""
    if not path:
        return ""
    try:
        with open(path, "rb") as handle:
            return handle.read().decode("utf-8", "replace").strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------- #
# Blocking convenience path (scripting; the UI runs QProcess instead)
# --------------------------------------------------------------------------- #

def generate(segments, model_id=None, steps=100, seed=42, transition=8,
             out_dir=None, import_result=True, start_frame=1,
             prefix="kimodo_", root=None):
    """Run the generator and optionally import the take.

    Blocks for as long as the solve takes - roughly a minute per 150 frames at
    100 steps - so keep it out of the UI thread.
    """
    import subprocess

    base = root or install_root()
    models = available_models(base)
    if not models:
        raise IOError("no motion models found under %s/models" % base)

    chosen = models[0]
    if model_id:
        for model in models:
            if model["id"] == model_id:
                chosen = model
                break
        else:
            raise ValueError("model %r is not available" % model_id)

    out_dir = out_dir or new_take_dir(base)
    argv = build_command(chosen["path"], out_dir, segments, steps, seed,
                         transition, base)

    completed = subprocess.run(argv, cwd=base, env=child_environment(),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = completed.stdout.decode("utf-8", "replace") if completed.stdout else ""
    if completed.returncode != 0:
        raise RuntimeError("kmd-generate failed (%d):\n%s"
                           % (completed.returncode, output))

    if not import_result:
        return {"folder": out_dir, "log": output}

    result = import_take(out_dir, start_frame=start_frame, prefix=prefix)
    result["log"] = output
    return result


# --------------------------------------------------------------------------- #
# Retarget
# --------------------------------------------------------------------------- #
#
# Every generated joint is built with jointOrient zeroed on a zero rest pose,
# so each source joint's rest world rotation is the identity. The usual
# rest-delta formula
#
#     target_world(t) = target_rest * inverse(source_rest) * source_world(t)
#
# therefore collapses to `target_rest * source_world(t)`, which is what the
# solver below applies. That is also why a T-posed source drives an A-posed
# target correctly: the whole rest difference is carried by target_rest.

UE5_MANNY = "ue5_manny"

# Parent first: a target's local rotation is derived from its parent's already
# updated world rotation, so the order here is load-bearing.
RETARGET_MAPS = {
    (SOMA30["key"], UE5_MANNY): [
        ("Hips", "pelvis"),
        ("Spine1", "spine_01"),
        ("Spine2", "spine_02"),
        ("Chest", "spine_03"),
        ("Neck1", "neck_01"),
        ("Neck2", "neck_02"),
        ("Head", "head"),
        ("LeftShoulder", "clavicle_l"),
        ("LeftArm", "upperarm_l"),
        ("LeftForeArm", "lowerarm_l"),
        ("LeftHand", "hand_l"),
        ("RightShoulder", "clavicle_r"),
        ("RightArm", "upperarm_r"),
        ("RightForeArm", "lowerarm_r"),
        ("RightHand", "hand_r"),
        ("LeftLeg", "thigh_l"),
        ("LeftShin", "calf_l"),
        ("LeftFoot", "foot_l"),
        ("LeftToeBase", "ball_l"),
        ("RightLeg", "thigh_r"),
        ("RightShin", "calf_r"),
        ("RightFoot", "foot_r"),
        ("RightToeBase", "ball_r"),
    ],
}

AS_MANNY = "as_manny"

# Advanced Skeleton's FK controls sit exactly on the bones they drive, so the
# control map is the bone map with the control names substituted. Animation
# lands on the controls, which is what an animator can then edit.
RETARGET_MAPS[(SOMA30["key"], AS_MANNY)] = [
    ("Hips", "RootX_M"),
    ("Spine1", "FKSpine1_M"),
    ("Spine2", "FKSpine2_M"),
    ("Chest", "FKSpine3_M"),
    ("Neck1", "FKNeck_M"),
    ("Neck2", "FKNeckPart2_M"),
    ("Head", "FKHead_M"),
    ("LeftShoulder", "FKScapula_L"),
    ("LeftArm", "FKShoulder_L"),
    ("LeftForeArm", "FKElbow_L"),
    ("LeftHand", "FKWrist_L"),
    ("RightShoulder", "FKScapula_R"),
    ("RightArm", "FKShoulder_R"),
    ("RightForeArm", "FKElbow_R"),
    ("RightHand", "FKWrist_R"),
    ("LeftLeg", "FKHip_L"),
    ("LeftShin", "FKKnee_L"),
    ("LeftFoot", "FKAnkle_L"),
    ("LeftToeBase", "FKToes_L"),
    ("RightLeg", "FKHip_R"),
    ("RightShin", "FKKnee_R"),
    ("RightFoot", "FKAnkle_R"),
    ("RightToeBase", "FKToes_R"),
]

# A limb left in IK ignores its FK controls entirely, so the blends have to be
# moved to FK before a bake means anything. 0 is FK, 10 is IK.
AS_FKIK_SWITCHES = ("FKIKArm_L", "FKIKArm_R", "FKIKLeg_L", "FKIKLeg_R",
                    "FKIKSpine_M")

# Where a character's travel belongs on this rig. Baking it onto the hips
# control leaves the global control sitting at the origin while the character
# walks away from it - nothing to grab to move the shot, and every pose edit
# happens far from the one control that should have followed.
AS_TRAVEL_CONTROL = "Main"

# Enough of the hierarchy to tell one target rig from another by name alone.
# The control rig is checked first: it also carries the bind skeleton, and
# driving the controls is what the animator actually wants.
TARGET_SIGNATURES = {
    AS_MANNY: ("RootX_M", "FKChest_M", "FKWrist_L", "FKKnee_R", "FKToes_L"),
    UE5_MANNY: ("pelvis", "spine_05", "clavicle_l", "thigh_r", "ball_l"),
}

TARGET_ORDER = (AS_MANNY, UE5_MANNY)

TARGET_LABELS = {UE5_MANNY: "UE5 Mannequin skeleton",
                 AS_MANNY: "Advanced Skeleton controls"}


def rest_positions(skeleton, scale=1.0):
    """Forward-kinematic rest positions from the skeleton table, in order."""
    parents = skeleton["parents"]
    offsets = skeleton["offsets"]
    positions = []
    for index, offset in enumerate(offsets):
        parent = parents[index]
        base = positions[parent] if parent >= 0 else (0.0, 0.0, 0.0)
        positions.append((base[0] + offset[0] * scale,
                          base[1] + offset[1] * scale,
                          base[2] + offset[2] * scale))
    return positions


def source_hip_height(skeleton, scale=1.0):
    """Hips-above-ground at rest: the reference length for scaling root motion."""
    positions = rest_positions(skeleton, scale)
    return positions[0][1] - min(position[1] for position in positions)


_IDENTITY = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
             0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def unpack_lod_groups(groups):
    """Lift the first LOD out of each LOD group so the mesh is actually visible.

    Game FBXs such as the UE5 Mannequin carry an LOD group whose threshold
    array is empty. Maya picks a level by camera distance, and with no
    thresholds to compare against it draws nothing - the skeleton appears and
    the character seems not to have imported at all.

    Reparenting is skipped unless the group's own matrix is the identity: on a
    skinned mesh, a compensating transform would show up as a double transform.
    """
    lifted, skipped = [], []
    for group in groups:
        if cmds.getAttr(group + ".matrix") != _IDENTITY:
            skipped.append(group)
            continue
        children = cmds.listRelatives(group, children=True, type="transform",
                                      fullPath=True) or []
        if not children:
            continue
        parent = cmds.listRelatives(group, parent=True, fullPath=True)
        moved = (cmds.parent(children[0], parent[0]) if parent
                 else cmds.parent(children[0], world=True))
        lifted.append(moved[0])
        cmds.setAttr(group + ".visibility", False)
    return lifted, skipped


FBX_IMPORT_SETUP = (
    # "Add and update animation" is the factory default, and it merges into
    # same-named nodes instead of creating new ones: import a rig into a scene
    # that already holds one and nothing appears at all - no joints, no mesh.
    # "add" always brings the file in as fresh nodes.
    "FBXImportMode -v add",
    "FBXImportSkins -v true",
    "FBXImportShapes -v true",
    "FBXImportCacheFile -v true",
    "FBXImportFillTimeline -v false",
    "FBXImportCameras -v false",
    "FBXImportLights -v false",
    "FBXImportConstraints -v false",
    "FBXImportUpAxis y",
    "FBXImportSetLockedAttribute -v true",
)


def configure_fbx_import():
    """Pin the importer's settings instead of inheriting the user's presets.

    FBX import options are sticky per user and per session, so whatever was
    last used in the FBX dialog silently decides what a scripted import brings
    in. Resetting and restating them makes the tool behave the same on every
    machine. Each command is applied on its own: an option a given FBX plug-in
    build does not know about must not abort the rest.
    """
    applied, refused = [], []
    try:
        mel.eval("FBXResetImport")
    except Exception:
        refused.append("FBXResetImport")
    for command in FBX_IMPORT_SETUP:
        try:
            mel.eval(command)
            applied.append(command.split()[0])
        except Exception:
            refused.append(command.split()[0])
    return applied, refused


def import_target_fbx(path, namespace=None, unpack_lods=True):
    """Import a skeleton FBX and return its root joint (long name)."""
    if not os.path.isfile(path):
        raise IOError("no such file: %s" % path)
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya", quiet=True)

    before = set(cmds.ls(type="joint", long=True))
    before_lods = set(cmds.ls(type="lodGroup", long=True))
    before_meshes = set(cmds.ls(type="mesh", long=True))

    _, refused = configure_fbx_import()
    if refused:
        print("[AZ Kimodo Motion %s] FBX options this plug-in refused: %s"
              % (VERSION, ", ".join(refused)))

    if namespace:
        # FBXImport has no namespace flag, so this path keeps cmds.file.
        cmds.file(path, i=True, type="FBX", ignoreVersion=True,
                  preserveReferences=True, namespace=namespace)
    else:
        mel.eval('FBXImport -f "%s"' % path.replace("\\", "/"))

    fresh = [joint for joint in cmds.ls(type="joint", long=True)
             if joint not in before]
    if not fresh:
        raise RuntimeError(
            "%s brought in no joints. If the rig is already in the scene, "
            "the importer had nothing to add - delete it first, or import "
            "into a namespace." % path)

    lifted, skipped = [], []
    if unpack_lods:
        lifted, skipped = unpack_lod_groups(
            [group for group in cmds.ls(type="lodGroup", long=True)
             if group not in before_lods])

    meshes = [mesh for mesh in cmds.ls(type="mesh", long=True)
              if mesh not in before_meshes
              and not cmds.getAttr(mesh + ".intermediateObject")]
    print("[AZ Kimodo Motion %s] imported %d joints, %d mesh shapes from %s%s%s"
          % (VERSION, len(fresh), len(meshes), os.path.basename(path),
             ("; lifted %s out of its LOD group"
              % ", ".join(node.split("|")[-1] for node in lifted)) if lifted else "",
             ("; left %d LOD group(s) alone - not at identity"
              % len(skipped)) if skipped else ""))
    if not meshes:
        print("[AZ Kimodo Motion %s] WARNING: skeleton only - the file carried "
              "no geometry, or the mesh merged into nodes already in the scene."
              % VERSION)

    roots = [joint for joint in fresh
             if not (cmds.listRelatives(joint, parent=True, type="joint") or [])]
    root = sorted(roots, key=len)[0] if roots else sorted(fresh, key=len)[0]
    capture_bind_pose(root)
    return root


def _descendant_joints(root):
    """Every transform under `root`, itself included.

    A control rig is driven through curve transforms rather than joints, so
    this deliberately does not filter by type - the name map decides what is
    actually used.
    """
    nodes = cmds.listRelatives(root, allDescendents=True, type="transform",
                               fullPath=True) or []
    return [root] + nodes


def _by_short_name(root):
    """Short name -> long name for the joints under `root`.

    Namespaces and import prefixes are stripped, so a map written against the
    bare UE5 names still resolves.
    """
    table = {}
    for joint in _descendant_joints(root):
        short = joint.split("|")[-1].split(":")[-1]
        table.setdefault(short, joint)
    return table


def is_generated_skeleton(node):
    """True when `node` belongs to a take this tool generated.

    import_take tags its group with `kimodoTake` and then selects it, so the
    pick-from-selection button lands on the generated chain unless something
    stops it - and retargeting a take onto itself is never what anyone means.
    """
    current = node
    while current:
        if cmds.attributeQuery("kimodoTake", node=current, exists=True):
            return True
        parents = cmds.listRelatives(current, parent=True, fullPath=True)
        current = parents[0] if parents else None
    return False


def identify_target(root):
    """Which known rig is this? Returns a TARGET_SIGNATURES key, or ""."""
    names = _by_short_name(root)
    for key in TARGET_ORDER:
        if all(bone in names for bone in TARGET_SIGNATURES[key]):
            return key
    return ""


def switch_to_fk(root):
    """Move Advanced Skeleton's blends to FK so the FK controls actually drive.

    A limb sitting in IK ignores whatever is baked onto its FK controls, and
    this rig ships with the legs in IK - the animation would look like it had
    simply not applied.
    """
    names = _by_short_name(root)
    moved = []
    for switch in AS_FKIK_SWITCHES:
        node = names.get(switch)
        if not node or not cmds.objExists(node + ".FKIKBlend"):
            continue
        if cmds.getAttr(node + ".FKIKBlend", lock=True):
            continue
        if abs(cmds.getAttr(node + ".FKIKBlend")) > 1e-6:
            cmds.setAttr(node + ".FKIKBlend", 0.0)
            moved.append(switch)
    return moved


def describe_target(root):
    """Why a rig was not recognised, in words worth showing a user."""
    if is_generated_skeleton(root):
        return ("that is the generated skeleton, not a rig to drive - pick "
                "the character's root joint instead")
    names = _by_short_name(root)
    parts = []
    for key, signature in TARGET_SIGNATURES.items():
        absent = [bone for bone in signature if bone not in names]
        parts.append("%s needs %s" % (TARGET_LABELS.get(key, key),
                                      ", ".join(absent)))
    return ("no map matches this hierarchy (%d joints); %s"
            % (len(names), "; ".join(parts)))


# A short spine: where the Mannequin build has FKSpine3_M, a plain Advanced
# Skeleton rig has its chest control instead.
AS_ALTERNATE_CONTROLS = {"FKSpine3_M": "FKChest_M"}


def _with_alternates(mapping, names):
    return [(source, target if target in names
             else AS_ALTERNATE_CONTROLS.get(target, target))
            for source, target in mapping]


def resolve_pairs(source_joints, skeleton, target_root, target_key=""):
    """Match up the source/target joint pairs."""
    target_key = target_key or identify_target(target_root)
    if not target_key:
        raise ValueError("%s: %s" % (target_root.split("|")[-1],
                                     describe_target(target_root)))

    mapping = RETARGET_MAPS.get((skeleton["key"], target_key))
    if mapping is None:
        raise ValueError("no retarget map from %s to %s"
                         % (skeleton["key"], target_key))

    source_by_name = dict(zip(skeleton["names"], source_joints))
    target_by_name = _by_short_name(target_root)
    mapping = _with_alternates(mapping, target_by_name)

    pairs, missing = [], []
    for source_name, target_name in mapping:
        source = source_by_name.get(source_name)
        target = target_by_name.get(target_name)
        if source and target:
            pairs.append((source, target))
        else:
            missing.append(target_name if source else source_name)
    return pairs, missing, target_key


def _rotation_matrix(node):
    """World rotation of `node` as an MMatrix, translation and scale removed."""
    values = cmds.xform(node, query=True, worldSpace=True, matrix=True)
    transform = om2.MTransformationMatrix(om2.MMatrix(values))
    return transform.rotation(asQuaternion=True).asMatrix()


def _matrix_angle(matrix):
    """How far a rotation matrix turns, in degrees."""
    quaternion = om2.MTransformationMatrix(
        om2.MMatrix(matrix)).rotation(asQuaternion=True)
    return math.degrees(2.0 * math.acos(min(1.0, abs(quaternion.w))))


def _set_world_rotation(node, matrix, rotate_order):
    euler = om2.MTransformationMatrix(matrix).rotation(asQuaternion=False)
    euler.reorderIt(rotate_order)
    cmds.xform(node, worldSpace=True, rotation=(
        om2.MAngle(euler.x, om2.MAngle.kRadians).asDegrees(),
        om2.MAngle(euler.y, om2.MAngle.kRadians).asDegrees(),
        om2.MAngle(euler.z, om2.MAngle.kRadians).asDegrees()))


def _without_twist(matrix, axis):
    """Drop the rotation a matrix carries about `axis`, keep the rest.

    Swing-twist decomposition: project the quaternion's vector part onto the
    axis to isolate the twist, then divide it out.
    """
    if axis.length() < 1e-6:
        return matrix
    axis = axis.normal()
    q = om2.MTransformationMatrix(matrix).rotation(asQuaternion=True)
    vector = om2.MVector(q.x, q.y, q.z)
    projected = axis * (vector * axis)
    # A quaternion has no length() in the API 2.0 binding, so measure the four
    # components directly: a twist that small is no twist at all.
    if (projected * projected) + q.w * q.w < 1.e-12:
        return matrix
    twist = om2.MQuaternion(projected.x, projected.y, projected.z, q.w)
    twist.normalizeIt()
    return (q * twist.inverse()).asMatrix()


def align_to_source_rest(pairs, mapping, skeleton, scale, rotate_orders,
                         drop_twist=False):
    """Swing the target into the source's rest pose and return that pose.

    The generated skeleton rests in a T-pose; a game rig such as the UE5
    Mannequin binds in an A-pose. Measuring the source's motion against a T-pose
    and replaying it on an A-posed rest offsets every limb by the difference
    between the two - visibly, arms end up far too low. So each mapped bone is
    first swung onto the direction its source counterpart has at rest, parent
    first, and the resulting orientations become the reference pose.

    The swing is the minimal arc between the two bone directions, which leaves
    roll around the bone unconstrained; a bone whose child is not itself mapped
    simply inherits its parent's correction.
    """
    source_rest = rest_positions(skeleton, scale)
    source_index = {name: index for index, name in enumerate(skeleton["names"])}

    # source joint -> its first mapped descendant, which is what defines the
    # bone direction to swing onto. Walking up past unmapped joints keeps the
    # map free to skip spine or neck links the target does not have.
    parents = skeleton["parents"]
    mapped_names = [name for name, _ in mapping]
    mapped_child = {}
    for name in mapped_names:
        ancestor = parents[source_index[name]]
        while ancestor >= 0:
            ancestor_name = skeleton["names"][ancestor]
            if ancestor_name in mapped_names:
                mapped_child.setdefault(ancestor_name, name)
                break
            ancestor = parents[ancestor]

    for index, (source, target) in enumerate(pairs):
        source_name = mapping[index][0]
        child_name = mapped_child.get(source_name)
        if not child_name:
            continue

        head = source_rest[source_index[source_name]]
        tail = source_rest[source_index[child_name]]
        wanted = om2.MVector(tail[0] - head[0], tail[1] - head[1],
                             tail[2] - head[2])
        if wanted.length() < 1e-6:
            continue

        target_child = pairs[mapped_names.index(child_name)][1]
        head_ws = cmds.xform(target, query=True, worldSpace=True,
                             translation=True)
        tail_ws = cmds.xform(target_child, query=True, worldSpace=True,
                             translation=True)
        current = om2.MVector(tail_ws[0] - head_ws[0], tail_ws[1] - head_ws[1],
                              tail_ws[2] - head_ws[2])
        if current.length() < 1e-6:
            continue

        # The minimal arc turns the bone onto the right direction and adds
        # nothing about the bone's own axis, so whatever roll the rig bound
        # with survives into the reference. That is a real gap, and dropping
        # the twist is offered here for a rig where it bites - but measured on
        # this one it changed nothing (the neck's wander went 23.93 to 24.57
        # degrees, every other bone stayed at 0.00), so it is off by default
        # rather than sold as a fix.
        swing = om2.MQuaternion(current.normal(), wanted.normal())
        aligned = _rotation_matrix(target) * swing.asMatrix()
        if drop_twist:
            aligned = _without_twist(aligned, wanted)
        _set_world_rotation(target, aligned, rotate_orders[index])

    return [_rotation_matrix(target) for _, target in pairs]


REST_ATTR = "azKimodoRetargetRest"

RETARGET_MODES = ("replace", "append")


def _rest_signature(skeleton_key, target_key, align_rest, drop_twist=False):
    return "%s|%s|%d|%d" % (skeleton_key, target_key,
                            1 if align_rest else 0, 1 if drop_twist else 0)


def read_stored_rest(target_root, signature):
    """The reference pose measured by an earlier retarget, if it still applies.

    A rig is only in its bind pose the first time round; after one retarget it
    carries keys, and re-measuring would take an animated frame as the
    reference. Caching the reference on the rig itself lets every later take
    reuse the pose that was measured while it was still clean.
    """
    if not cmds.attributeQuery(REST_ATTR, node=target_root, exists=True):
        return None
    try:
        stored = json.loads(cmds.getAttr(target_root + "." + REST_ATTR) or "")
    except Exception:
        return None
    if not isinstance(stored, dict):
        return None
    # A rig needs more than one reference at a time - the retarget measures
    # against the controls and a capture against the bind skeleton - so they
    # are kept side by side. One slot meant whichever ran last wiped the other,
    # and the capture then re-measured off an animated pose.
    entry = stored.get(signature)
    if isinstance(entry, dict):
        return entry
    if stored.get("signature") == signature:      # the single-slot format
        return stored
    return None


def write_stored_rest(target_root, signature, rotations, rest_hips, hips_scale,
                      unfollowed=()):
    if not cmds.attributeQuery(REST_ATTR, node=target_root, exists=True):
        cmds.addAttr(target_root, longName=REST_ATTR, dataType="string")

    stored = {}
    try:
        existing = json.loads(cmds.getAttr(target_root + "." + REST_ATTR) or "")
        if isinstance(existing, dict):
            if "signature" in existing:           # the old single-slot format
                stored = {existing["signature"]: existing}
            else:
                stored = existing
    except Exception:
        stored = {}

    stored[signature] = {"signature": signature,
                         "rotations": [list(matrix) for matrix in rotations],
                         "rest_hips": list(rest_hips),
                         "hips_scale": hips_scale,
                         # Joints whose bone does not follow its control, so a
                         # capture must not claim to have read them.
                         "unfollowed": list(unfollowed)}
    cmds.setAttr(target_root + "." + REST_ATTR, json.dumps(stored),
                 type="string")


def clear_retarget_keys(joints, hips, travel=None):
    """Drop the curves an earlier retarget left, so a new take replaces it."""
    for joint in list(joints) + ([travel] if travel else []):
        attributes = ["rotateX", "rotateY", "rotateZ"]
        if joint == hips or joint == travel:
            attributes += ["translateX", "translateY", "translateZ"]
        for attribute in attributes:
            if cmds.keyframe(joint + "." + attribute, query=True,
                             keyframeCount=True):
                cmds.cutKey(joint, attribute=attribute, clear=True)


_KEYED_ATTRIBUTES = ("rotateX", "rotateY", "rotateZ",
                     "translateX", "translateY", "translateZ")


def snapshot_curves(joints):
    """Lift the rig's existing keys out as plain data.

    Appending means baking while the previous take still drives the rig, and a
    driven joint does not reliably report the world rotation just written to
    it - the parent's old curve wins. So the bake always runs on a curve-free
    rig and the earlier keys are put back afterwards.
    """
    saved = {}
    for joint in joints:
        for attribute in _KEYED_ATTRIBUTES:
            plug = joint + "." + attribute
            if not cmds.objExists(plug):
                continue
            times = cmds.keyframe(plug, query=True, timeChange=True) or []
            if not times:
                continue
            values = cmds.keyframe(plug, query=True, valueChange=True) or []
            saved[plug] = list(zip(times, values))
    return saved


def restore_curves(saved):
    for plug, keys in saved.items():
        node, attribute = plug.rsplit(".", 1)
        for time_value, value in keys:
            cmds.setKeyframe(node, attribute=attribute, time=time_value,
                             value=value)


def last_keyed_frame(joints):
    """Last keyframe across `joints`, or None when none of them is animated."""
    latest = None
    for joint in joints:
        for attribute in ("rotateX", "rotateY", "rotateZ"):
            plug = joint + "." + attribute
            if not cmds.keyframe(plug, query=True, keyframeCount=True):
                continue
            times = cmds.keyframe(plug, query=True, timeChange=True) or []
            if times:
                latest = max(times) if latest is None else max(latest, max(times))
    return latest


BIND_ATTR = "azKimodoBindPose"

_POSE_ATTRIBUTES = ("translate", "rotate")


def capture_bind_pose(target_root):
    """Record the rig's pose while it is still untouched.

    Deleting animation curves does not return a joint to its bind pose - it
    leaves it wherever the last evaluation put it. Measuring a retarget
    reference off that gives a plausible-looking result with a badly wrong
    root-motion scale, so the clean pose is stored the moment the rig arrives.
    """
    pose = {}
    for joint in _descendant_joints(target_root):
        entry = {}
        for attribute in _POSE_ATTRIBUTES:
            plug = joint + "." + attribute
            if cmds.objExists(plug):
                entry[attribute] = list(cmds.getAttr(plug)[0])
        pose[joint.split("|")[-1]] = entry

    if not cmds.attributeQuery(BIND_ATTR, node=target_root, exists=True):
        cmds.addAttr(target_root, longName=BIND_ATTR, dataType="string")
    cmds.setAttr(target_root + "." + BIND_ATTR, json.dumps(pose), type="string")
    return pose


def _set_triple(node, attribute, values):
    """Write a translate/rotate triple, channel by channel.

    A rig locks individual channels - a control that may only rotate, a group
    with a locked translateX - and the compound plug still reports unlocked,
    so setting it whole raises. Each channel is written on its own and a
    locked or driven one is simply left alone.
    """
    written = 0
    for index, axis in enumerate("XYZ"):
        plug = "%s.%s%s" % (node, attribute, axis)
        if not cmds.objExists(plug) or cmds.getAttr(plug, lock=True):
            continue
        if cmds.listConnections(plug, source=True, destination=False):
            continue
        try:
            cmds.setAttr(plug, values[index])
            written += 1
        except Exception:
            pass
    return written


def restore_bind_pose(target_root):
    """Put the rig back to the pose captured at import. False when none was."""
    if not cmds.attributeQuery(BIND_ATTR, node=target_root, exists=True):
        return False
    try:
        pose = json.loads(cmds.getAttr(target_root + "." + BIND_ATTR) or "")
    except Exception:
        return False
    if not pose:
        return False

    for joint in _descendant_joints(target_root):
        entry = pose.get(joint.split("|")[-1])
        if not entry:
            continue
        for attribute, values in entry.items():
            _set_triple(joint, attribute, values)
    return True


def delete_take(top):
    """Remove a generated take's joints from the scene."""
    if top and cmds.objExists(top):
        cmds.delete(top)
        return True
    return False


BLEND_ATTR = "azKimodoRigBlends"


def remember_fkik(root):
    """Record the FK/IK blends before a retarget overrides them.

    Baking onto FK controls only shows if the limb is listening to them, so
    every retarget moves the blends to FK. That used to be a one-way trip: the
    value was written straight onto the rig, nothing keyed it, and clearing the
    animation did not bring it back - so a rig that shipped with its legs in IK
    stayed in FK forever after the first take. Recorded once, on the first
    retarget, so a second one does not record the zeros it just wrote.
    """
    if cmds.attributeQuery(BLEND_ATTR, node=root, exists=True):
        return False
    names = _by_short_name(root)
    blends = {}
    for switch in AS_FKIK_SWITCHES:
        node = names.get(switch)
        plug = (node + ".FKIKBlend") if node else ""
        if plug and cmds.objExists(plug):
            blends[switch] = cmds.getAttr(plug)
    if not blends:
        return False
    cmds.addAttr(root, longName=BLEND_ATTR, dataType="string")
    cmds.setAttr(root + "." + BLEND_ATTR, json.dumps(blends), type="string")
    return True


def restore_fkik(root):
    """Put the FK/IK blends back the way they were before the first retarget."""
    if not cmds.attributeQuery(BLEND_ATTR, node=root, exists=True):
        return []
    try:
        blends = json.loads(cmds.getAttr(root + "." + BLEND_ATTR) or "")
    except Exception:
        blends = {}
    names = _by_short_name(root)
    moved = []
    for switch, value in (blends or {}).items():
        node = names.get(switch)
        plug = (node + ".FKIKBlend") if node else ""
        if not plug or not cmds.objExists(plug):
            continue
        if cmds.getAttr(plug, lock=True):
            continue
        # A key on the channel would win the moment the timeline moved, so the
        # take's own keys go before the value does.
        if cmds.keyframe(plug, query=True, keyframeCount=True):
            cmds.cutKey(node, attribute="FKIKBlend", clear=True)
        if abs(cmds.getAttr(plug) - value) > 1e-6:
            cmds.setAttr(plug, value)
            moved.append(switch)
    cmds.setAttr(root + "." + BLEND_ATTR, lock=False)
    cmds.deleteAttr(root + "." + BLEND_ATTR)
    return moved


def clear_rig(target_root, keys=True, cache=True):
    """Put a retargeted rig back to a clean state.

    Clears the baked animation and drops the cached reference pose, so the
    next retarget measures the rig fresh. Needed when the first retarget was
    run on a rig that was not in its bind pose: the wrong reference would
    otherwise be reused for every take after it.
    """
    removed_keys = 0
    if keys:
        for joint in _descendant_joints(target_root):
            for attribute in _KEYED_ATTRIBUTES:
                plug = joint + "." + attribute
                if not cmds.objExists(plug):
                    continue
                if cmds.keyframe(plug, query=True, keyframeCount=True):
                    cmds.cutKey(joint, attribute=attribute, clear=True)
                    removed_keys += 1

    blends = restore_fkik(target_root)
    restored = restore_bind_pose(target_root)

    if cmds.attributeQuery(SOLVE_ATTR, node=target_root, exists=True):
        cmds.deleteAttr(target_root + "." + SOLVE_ATTR)
    if cmds.attributeQuery(MAIN_BASE_ATTR, node=target_root, exists=True):
        cmds.deleteAttr(target_root + "." + MAIN_BASE_ATTR)

    dropped = False
    if cache and cmds.attributeQuery(REST_ATTR, node=target_root, exists=True):
        cmds.setAttr(target_root + "." + REST_ATTR, lock=False)
        cmds.deleteAttr(target_root + "." + REST_ATTR)
        dropped = True

    print("[AZ Kimodo Motion %s] cleared %d animated channels on %s%s%s%s"
          % (VERSION, removed_keys, target_root.split("|")[-1],
             "; restored the bind pose" if restored else
             "; NO bind pose stored - pose the rig yourself before retargeting",
             "; dropped the cached rest pose" if dropped else "",
             ("; put %s back to IK" % ", ".join(blends)) if blends else ""))
    return {"channels": removed_keys, "cache_dropped": dropped,
            "bind_restored": restored, "blends_restored": blends}


# The generator gives the head and neck a life of their own - measured on a
# run, the head swings 30 degrees and the first neck joint 42, in steps of up
# to 34 across five frames. A character rig usually cannot absorb that: this
# one drives its neck through a blended chain and leaves the second neck bone
# with no driver at all, so the bend lands in one place and the mesh twists.
# Damping scales how far the neck and head are allowed to turn away from the
# chest, which is the knob an animator would reach for anyway.
NECK_CHAIN = ("Neck1", "Neck2", "Head")


def _damped_neck(source_by_name, amount):
    """World rotations for the neck chain, turned down toward the chest."""
    parent = source_by_name.get("Chest")
    if parent is None or amount >= 0.999:
        return {}

    identity = om2.MQuaternion()
    world = _rotation_matrix(parent)
    previous_source = parent
    damped = {}
    for name in NECK_CHAIN:
        joint = source_by_name.get(name)
        if joint is None:
            break
        local = _rotation_matrix(previous_source).inverse() * _rotation_matrix(joint)
        turn = om2.MTransformationMatrix(local).rotation(asQuaternion=True)
        world = world * om2.MQuaternion.slerp(identity, turn, amount).asMatrix()
        damped[joint] = om2.MMatrix(world)
        previous_source = joint
    return damped


# --------------------------------------------------------------------------- #
# IK bake
# --------------------------------------------------------------------------- #
#
# The FK bake remains the source of truth. A limb in FK puts its bones where the
# take wants them, and each IK control is then placed by its offset from its
# bone at bind: control_now = control_bind * bone_bind^-1 * bone_now.

IK_ATTR = "azKimodoIKOffsets2"
AS_IK_LIMBS = {
    "legs": (
        {"switch": "FKIKLeg_L", "ik": "IKLeg_L", "pole": "PoleLeg_L",
         "toes": "IKToes_L", "upper": "FKHip_L", "mid": "FKKnee_L",
         "end": "FKAnkle_L", "tip": "FKToes_L"},
        {"switch": "FKIKLeg_R", "ik": "IKLeg_R", "pole": "PoleLeg_R",
         "toes": "IKToes_R", "upper": "FKHip_R", "mid": "FKKnee_R",
         "end": "FKAnkle_R", "tip": "FKToes_R"},
    ),
    "arms": (
        {"switch": "FKIKArm_L", "ik": "IKArm_L", "pole": "PoleArm_L",
         "toes": None, "upper": "FKShoulder_L", "mid": "FKElbow_L",
         "end": "FKWrist_L", "tip": None},
        {"switch": "FKIKArm_R", "ik": "IKArm_R", "pole": "PoleArm_R",
         "toes": None, "upper": "FKShoulder_R", "mid": "FKElbow_R",
         "end": "FKWrist_R", "tip": None},
    ),
}
IK_LIMB_CHOICES = (("FK controls", ()), ("IK legs", ("legs",)),
                   ("IK legs and arms", ("legs", "arms")), ("IK arms", ("arms",)))


def _ik_limbs(root, which=("legs", "arms")):
    """The limbs this rig has, with every name resolved to a node. Empty if none."""
    controls = _by_short_name(root)
    found = []
    for kind in which:
        for limb in AS_IK_LIMBS[kind]:
            if all(name in controls for name in limb.values() if name):
                found.append(dict((key, controls[name] if name else None)
                                  for key, name in limb.items()))
    return found


def _deform_joint(root, control):
    """The deformation joint behind an FK control: FKElbow_L drives Elbow_L."""
    system = _by_short_name(root).get("DeformationSystem")
    short = control.split("|")[-1].split(":")[-1]
    if not system or not short.startswith("FK"):
        return None
    return _by_short_name(system).get(short[2:])


def _ik_controls(root):
    nodes = []
    for limb in _ik_limbs(root):
        nodes += [limb[key] for key in ("ik", "pole", "toes") if limb[key]]
    return nodes


@contextlib.contextmanager
def quietly():
    """Run work the animator did not do and should not have to undo.

    Reading a pose hops the timeline and puts channels back, and the marks on
    the time slider are rebuilt whole. None of that is an edit, yet every command
    would take a place in the undo queue and bury the edits that are. Auto key
    stays out too: a channel put back is not a new key.
    """
    undoing = cmds.undoInfo(query=True, stateWithoutFlush=True)
    keying = cmds.autoKeyframe(query=True, state=True)
    cmds.undoInfo(stateWithoutFlush=False)
    cmds.autoKeyframe(state=False)
    try:
        yield
    finally:
        cmds.autoKeyframe(state=keying)
        cmds.undoInfo(stateWithoutFlush=undoing)


@contextlib.contextmanager
def undo_chunk(name):
    """Everything inside is one undo step."""
    cmds.undoInfo(openChunk=True, chunkName="AZ Kimodo Motion " + name)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)


def _hold_channels(nodes):
    held = []
    for node in nodes:
        for attribute in _KEYED_ATTRIBUTES:
            plug = "%s.%s" % (node, attribute)
            if cmds.objExists(plug) and cmds.getAttr(plug, settable=True):
                held.append((plug, cmds.getAttr(plug)))
    return held


def _world(node):
    return om2.MMatrix(cmds.xform(node, query=True, worldSpace=True, matrix=True))


def _position(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def _with_bind_pose(root, measure):
    """Run `measure` with the rig standing at bind, then leave it as it was."""
    with quietly():
        _measure_at_bind(root, measure)


def _measure_at_bind(root, measure):
    if not cmds.attributeQuery(BIND_ATTR, node=root, exists=True):
        raise RuntimeError("no bind pose is recorded for this rig")
    bind = json.loads(cmds.getAttr(root + "." + BIND_ATTR) or "{}")

    controls = [node for node in _descendant_joints(root)
                if cmds.listRelatives(node, shapes=True, type="nurbsCurve")]
    held = _hold_channels(controls)
    # A locked blend would stop the put-back below at its first plug.
    blends = [(limb["switch"] + ".FKIKBlend",
               cmds.getAttr(limb["switch"] + ".FKIKBlend")) for limb in _ik_limbs(root)
              if cmds.getAttr(limb["switch"] + ".FKIKBlend", settable=True)]
    now = cmds.currentTime(query=True)
    try:
        # A keyed channel takes a plain setAttr until the time next changes,
        # which is all a measurement needs.
        for node in controls:
            for attribute, values in (bind.get(node.split("|")[-1]) or {}).items():
                for axis, value in zip("XYZ", values):
                    plug = "%s.%s%s" % (node, attribute, axis)
                    if cmds.objExists(plug) and cmds.getAttr(plug, settable=True):
                        cmds.setAttr(plug, value)
        for plug, _value in blends:
            cmds.setAttr(plug, 0.0)
        measure()
    finally:
        cmds.currentTime(now + 1, edit=True)
        cmds.currentTime(now, edit=True)
        for plug, value in blends + held:
            cmds.setAttr(plug, value)


def _ik_offsets(root):
    """Each IK control's offset from its bone at bind, measured once per rig."""
    if cmds.attributeQuery(IK_ATTR, node=root, exists=True):
        try:
            stored = json.loads(cmds.getAttr(root + "." + IK_ATTR) or "")
            if stored:
                return stored
        except ValueError:
            pass
    offsets = {}

    def measure():
        for limb in _ik_limbs(root):
            offsets[limb["ik"]] = list(_world(limb["ik"]) * _world(limb["end"]).inverse())
            pole = [a - b for a, b in zip(_position(limb["pole"]), _position(limb["mid"]))]
            offsets[limb["pole"]] = pole
            if limb["toes"]:
                offsets[limb["toes"]] = list(_world(limb["toes"]) * _world(limb["tip"]).inverse())
            for key in ("upper", "mid", "end", "tip"):
                joint = _deform_joint(root, limb[key]) if limb[key] else None
                if joint:
                    offsets["joint:" + limb[key]] = list(
                        _world(limb[key]) * _world(joint).inverse())

    _with_bind_pose(root, measure)

    if not cmds.attributeQuery(IK_ATTR, node=root, exists=True):
        cmds.addAttr(root, longName=IK_ATTR, dataType="string")
    cmds.setAttr(root + "." + IK_ATTR, json.dumps(offsets), type="string")
    return offsets


def _match_limb(limb, offsets, last_pole):
    """Put one limb's IK controls where its bones are. Returns the pole direction."""
    cmds.xform(limb["ik"], worldSpace=True,
               matrix=list(om2.MMatrix(offsets[limb["ik"]]) * _world(limb["end"])))

    upper, mid, end = (_position(limb[key]) for key in ("upper", "mid", "end"))
    bend = [m - (u + e) * 0.5 for m, u, e in zip(mid, upper, end)]
    length = sum(v * v for v in bend) ** 0.5
    reach = sum(v * v for v in offsets[limb["pole"]]) ** 0.5
    # A straight limb has no bend to read, so the pole stays on its last side.
    if length > 1e-3 * reach:
        direction = [v / length for v in bend]
    else:
        direction = last_pole or [v / reach for v in offsets[limb["pole"]]]
    cmds.xform(limb["pole"], worldSpace=True,
               translation=[m + d * reach for m, d in zip(mid, direction)])

    if limb["toes"]:
        _set_world_rotation(limb["toes"],
                            om2.MMatrix(offsets[limb["toes"]]) * _world(limb["tip"]),
                            cmds.getAttr(limb["toes"] + ".rotateOrder"))
    return direction


def _read_ik_limbs(root, pairs, rest):
    """What a limb in IK is doing, in the terms the FK controls would use.

    In IK the FK controls stay on the last bake and say nothing about a pose made
    with the IK controls, so the deformation joints are read instead and put back
    through each joint's offset from its FK control.
    """
    limbs = [limb for limb in _ik_limbs(root)
             if cmds.getAttr(limb["switch"] + ".FKIKBlend") > 5.0]
    if not limbs:
        return {}
    offsets = _ik_offsets(root)
    source_of = dict((control, (source, rest[i]))
                     for i, (source, control) in enumerate(pairs))
    read = {}
    for limb in limbs:
        for key in ("upper", "mid", "end", "tip"):
            control = limb[key]
            offset = offsets.get("joint:%s" % control) if control else None
            if not offset or control not in source_of:
                continue
            joint = _deform_joint(root, control)
            source, reference = source_of[control]
            # Rotation alone: a stretchy limb scales its joints, and the model
            # has no use for that.
            read[source] = (reference.inverse()
                            * om2.MTransformationMatrix(om2.MMatrix(offset)).asRotateMatrix()
                            * _rotation_matrix(joint))
    return read


def clear_ik_keys(root):
    for node in _ik_controls(root):
        for attribute in _KEYED_ATTRIBUTES:
            plug = "%s.%s" % (node, attribute)
            if cmds.objExists(plug) and cmds.keyframe(plug, query=True, keyframeCount=True):
                cmds.cutKey(node, attribute=attribute, clear=True)


def set_limb_mode(root, which=()):
    """Switch limbs to IK for the kinds in `which`, FK for the rest."""
    for kind, limbs in AS_IK_LIMBS.items():
        for limb in _ik_limbs(root, (kind,)):
            cmds.setAttr(limb["switch"] + ".FKIKBlend", 10.0 if kind in which else 0.0)


def bake_ik(root, first, last, which):
    """Key the IK controls of `which` limbs from the FK bake, then switch to IK."""
    limbs = _ik_limbs(root, which)
    if not limbs:
        return 0
    offsets = _ik_offsets(root)
    for limb in limbs:
        cmds.setAttr(limb["switch"] + ".FKIKBlend", 0.0)
    restore = cmds.currentTime(query=True)
    poles = {}
    try:
        cmds.refresh(suspend=True)
        for frame in range(int(first), int(last) + 1):
            cmds.currentTime(frame, edit=True)
            for limb in limbs:
                poles[limb["ik"]] = _match_limb(limb, offsets, poles.get(limb["ik"]))
                cmds.setKeyframe(limb["ik"], time=frame,
                                 attribute=("translateX", "translateY", "translateZ",
                                            "rotateX", "rotateY", "rotateZ"))
                cmds.setKeyframe(limb["pole"], time=frame,
                                 attribute=("translateX", "translateY", "translateZ"))
                if limb["toes"]:
                    cmds.setKeyframe(limb["toes"], time=frame,
                                     attribute=("rotateX", "rotateY", "rotateZ"))
    finally:
        cmds.refresh(suspend=False)
        cmds.currentTime(restore, edit=True)
    for limb in limbs:
        for key in ("ik", "toes"):
            if limb[key]:
                cmds.filterCurve(limb[key] + ".rotateX", limb[key] + ".rotateY",
                                 limb[key] + ".rotateZ", filter="euler")
        cmds.setAttr(limb["switch"] + ".FKIKBlend", 10.0)
    return len(limbs)


def match_ik_now(root):
    """Bring limbs in IK to the FK pose on the current frame, unkeyed."""
    limbs = [limb for limb in _ik_limbs(root)
             if cmds.getAttr(limb["switch"] + ".FKIKBlend") > 5.0]
    if not limbs:
        return
    offsets = _ik_offsets(root)
    for limb in limbs:
        cmds.setAttr(limb["switch"] + ".FKIKBlend", 0.0)
    for limb in limbs:
        _match_limb(limb, offsets, None)
    for limb in limbs:
        cmds.setAttr(limb["switch"] + ".FKIKBlend", 10.0)


# --------------------------------------------------------------------------- #
# Arms and the body
# --------------------------------------------------------------------------- #
#
# The retarget copies world rotations, which is right for a character shaped
# like the generator's skeleton. On a wide torso the same rotations put the
# forearm inside the belly. Nothing about the motion says so, only the mesh, so
# the mesh is what gets measured.

BODY_ATTR = "azKimodoBody"
BODY_MIN_RADIUS = 0.03        # metres, so a thin mesh still has some body
BODY_SAMPLE_VERTS = 15000
ARM_CLEARANCE_DEFAULT = 1.0   # scene units of air kept around the arm
ARM_SIDES = (("LeftArm", "LeftForeArm", "LeftHand"),
             ("RightArm", "RightForeArm", "RightHand"))
_BODY_TORSO = ("Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head")
_BODY_OTHER = (("LeftLeg", "LeftShin"), ("LeftShin", "LeftFoot"),
               ("LeftFoot", "LeftToeBase"), ("RightLeg", "RightShin"),
               ("RightShin", "RightFoot"), ("RightFoot", "RightToeBase"))
_BODY_TIP = "_tip"


def _skinned_meshes(root):
    """Mesh shapes skinned to this character's skeleton."""
    bone_root, _key = bone_source_root(root)
    roots = (bone_root, root)
    found = []
    for cluster in cmds.ls(type="skinCluster") or []:
        influences = cmds.ls(cmds.skinCluster(cluster, query=True, influence=True) or [],
                             long=True) or []
        if not any(name.startswith(tuple(r + "|" for r in roots)) for name in influences):
            continue
        for mesh in cmds.skinCluster(cluster, query=True, geometry=True) or []:
            for shape in cmds.ls(mesh, long=True, type="mesh") or []:
                # Hidden helpers - a pin mesh, a modelling copy - are not body.
                if shape not in found and cmds.ls(shape, visible=True) \
                        and not cmds.getAttr(shape + ".intermediateObject"):
                    found.append(shape)
    return found


def _mesh_points(shapes):
    points = []
    for shape in shapes:
        selection = om2.MSelectionList()
        selection.add(shape)
        fn = om2.MFnMesh(selection.getDagPath(0))
        points.extend((p.x, p.y, p.z) for p in fn.getPoints(om2.MSpace.kWorld))
    stride = max(1, len(points) // BODY_SAMPLE_VERTS)
    return points[::stride]


def _closest_on_segment(p, a, b):
    ab = [b[i] - a[i] for i in range(3)]
    span = sum(v * v for v in ab) or 1e-9
    t = max(0.0, min(1.0, sum((p[i] - a[i]) * ab[i] for i in range(3)) / span))
    return [a[i] + ab[i] * t for i in range(3)]


def _percentile(values, fraction=0.9):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))] if ordered else 0.0


def measure_body(root, skeleton=SOMA30):
    """How thick the character's torso and arms are, from its mesh. None if no mesh.

    Taken at bind, where the arms stand clear of the torso, so giving each vertex
    to its nearest bone sorts arm from torso without knowing how the rig is
    weighted or what its joints are called.
    """
    shapes = _skinned_meshes(root)
    if not shapes:
        return None
    pairs, _mapping, _key = target_pairs(root, skeleton)
    control = dict(pairs)
    chain = [n for n in _BODY_TORSO if n in control]
    missing = [n for n in ("Hips", "Head") + tuple(j for side in ARM_SIDES for j in side)
               if n not in control]
    if missing or len(chain) < 3:
        return None

    result = {}

    def measure():
        at = dict((name, _position(node)) for name, node in control.items())
        points = _mesh_points(shapes)
        scale = scene_scale()

        neck = [at["Head"][i] - at[chain[-2]][i] for i in range(3)]
        length = sum(v * v for v in neck) ** 0.5 or 1.0
        top = [at["Head"][i] + neck[i] / length * 0.25 * scale for i in range(3)]

        torso = [(a, b, at[a], at[b]) for a, b in zip(chain, chain[1:])]
        torso.append(("Head", _BODY_TIP, at["Head"], top))
        arms = []
        for upper, fore, hand in ARM_SIDES:
            end = [at[hand][i] + (at[hand][i] - at[fore][i]) * 0.6 for i in range(3)]
            arms += [(upper, at[upper], at[fore]), (fore, at[fore], at[hand]),
                     (hand, at[hand], end)]
        legs = [(at[a], at[b]) for a, b in _BODY_OTHER if a in at and b in at]

        centre = at["Hips"][0]
        shoulder_width = abs(at[ARM_SIDES[0][0]][0] - centre)
        lateral = [[] for _ in torso]
        depth = [[] for _ in torso]
        thick = dict((name, []) for name, _a, _b in arms)
        for p in points:
            best, kind, index, near = None, None, None, None
            for i, (_a, _b, a, b) in enumerate(torso):
                c = _closest_on_segment(p, a, b)
                d = sum((p[k] - c[k]) ** 2 for k in range(3))
                if best is None or d < best:
                    best, kind, index, near = d, "torso", i, c
            # Inboard of the shoulder is torso, however close an arm hangs: the
            # side of a wide belly is nearer the upper arm than the spine.
            beyond = abs(p[0] - centre) > shoulder_width
            for i, (_n, a, b) in enumerate(arms if beyond else ()):
                c = _closest_on_segment(p, a, b)
                d = sum((p[k] - c[k]) ** 2 for k in range(3))
                if d < best:
                    best, kind, index, near = d, "arm", i, c
            for a, b in legs:
                c = _closest_on_segment(p, a, b)
                d = sum((p[k] - c[k]) ** 2 for k in range(3))
                if d < best:
                    best, kind = d, "leg"
            if kind == "torso":
                lateral[index].append(abs(p[0] - near[0]))
                depth[index].append(abs(p[2] - near[2]))
            elif kind == "arm":
                thick[arms[index][0]].append(best ** 0.5)

        floor = BODY_MIN_RADIUS * scale
        result["torso"] = [
            {"from": seg[0], "to": seg[1],
             "lateral": max(floor, _percentile(lateral[i])),
             "depth": max(floor, _percentile(depth[i])),
             "bind": list(_rotation_matrix(control[seg[0]]).inverse()),
             "tip": [top[k] - at["Head"][k] for k in range(3)]}
            for i, seg in enumerate(torso)]
        # The median, not the outline: a big cartoon hand spreads its fingers far
        # from the bone, and clearing those would hold the whole arm off the body.
        result["arm"] = dict((name, max(floor * 0.5, _percentile(values, 0.5)))
                             for name, values in thick.items())

        # An arm that already sits close at bind is not a collision. Its own
        # distance there is as near as it will ever be asked to stand off.
        segments = _torso_now(result, control)
        limits = {}
        for upper, fore, hand in ARM_SIDES:
            mid = [(at[fore][k] + at[hand][k]) * 0.5 for k in range(3)]
            for name, point, radius in ((fore, at[fore], result["arm"][upper]),
                                        (fore + "_mid", mid, result["arm"][fore]),
                                        (hand, at[hand], result["arm"][hand])):
                limits[name] = min(1.0, _inside(point, segments, radius, 0.0)[0] * 0.98)
        result["limit"] = limits

    _with_bind_pose(root, measure)
    if not cmds.attributeQuery(BODY_ATTR, node=root, exists=True):
        cmds.addAttr(root, longName=BODY_ATTR, dataType="string")
    cmds.setAttr(root + "." + BODY_ATTR, json.dumps(result), type="string")
    return result


def read_body(root):
    if not cmds.attributeQuery(BODY_ATTR, node=root, exists=True):
        return None
    try:
        return json.loads(cmds.getAttr(root + "." + BODY_ATTR) or "") or None
    except ValueError:
        return None


def _torso_now(body, control):
    """The torso's segments as they stand on the current frame."""
    segments = []
    for seg in body["torso"]:
        start = control[seg["from"]]
        turn = om2.MMatrix(seg["bind"]) * _rotation_matrix(start)
        a = _position(start)
        if seg["to"] == _BODY_TIP:
            v = om2.MVector(seg["tip"]) * turn
            b = [a[0] + v.x, a[1] + v.y, a[2] + v.z]
        else:
            b = _position(control[seg["to"]])
        segments.append((a, b, om2.MVector(1, 0, 0) * turn, om2.MVector(0, 0, 1) * turn,
                         seg["lateral"], seg["depth"]))
    return segments


def _inside(p, segments, radius, clearance):
    """(how deep, as 1 = on the surface and less = inside, way out) for a point."""
    worst, push = None, None
    for a, b, x_axis, z_axis, lateral, depth in segments:
        c = _closest_on_segment(p, a, b)
        r = om2.MVector(p[0] - c[0], p[1] - c[1], p[2] - c[2])
        x = (r * x_axis) / (lateral + radius + clearance)
        z = (r * z_axis) / (depth + radius + clearance)
        k = (x * x + z * z) ** 0.5
        if worst is None or k < worst:
            worst, push = k, (r, x_axis, k)
    return worst, push


def _pushed(p, segments, radius, clearance, limit):
    """Where a point has to go to stand clear, or None if it already does."""
    k, data = _inside(p, segments, radius, clearance)
    if k >= limit:
        return None
    r, x_axis, _k = data
    # Dead on the axis has no direction of its own to leave in.
    direction = r if r.length() > 1e-4 else x_axis
    if k < 1e-3:
        return [p[0] + direction.x, p[1] + direction.y, p[2] + direction.z]
    grow = limit / k - 1.0
    return [p[0] + r.x * grow, p[1] + r.y * grow, p[2] + r.z * grow]


def _swing(pivot, point, goal):
    """The rotation about `pivot` that carries `point` onto the direction of `goal`."""
    return om2.MQuaternion(
        om2.MVector(point[0] - pivot[0], point[1] - pivot[1], point[2] - pivot[2]),
        om2.MVector(goal[0] - pivot[0], goal[1] - pivot[1], goal[2] - pivot[2]))


def _rotated(point, pivot, turn):
    v = om2.MVector(point[0] - pivot[0], point[1] - pivot[1], point[2] - pivot[2]).rotateBy(turn)
    return [pivot[0] + v.x, pivot[1] + v.y, pivot[2] + v.z]


def _settled(turns, spread=4, blur=8):
    """Smooth corrections so an arm eases out rather than jumping.

    Each frame first takes the strongest correction near it, then those are
    averaged - blurring alone would let a brief touch back into the body.
    """
    count = len(turns)
    def strength(turn):
        return abs(turn.w)
    wide = []
    for i in range(count):
        window = turns[max(0, i - spread):i + spread + 1]
        wide.append(min(window, key=strength))
    out = []
    for i in range(count):
        w, x, y, z = 0.0, 0.0, 0.0, 0.0
        for j in range(max(0, i - blur), min(count, i + blur + 1)):
            weight = blur + 1 - abs(i - j)
            turn = wide[j]
            sign = -1.0 if turn.w < 0 else 1.0
            w += weight * sign * turn.w
            x += weight * sign * turn.x
            y += weight * sign * turn.y
            z += weight * sign * turn.z
        out.append(om2.MQuaternion(x, y, z, w).normal())
    return out


def keep_arms_out(root, first, last, clearance=ARM_CLEARANCE_DEFAULT,
                  skeleton=SOMA30, keep_frames=(), keep_fade=4):
    """Swing elbows and forearms out of the body on the baked range. Frames changed.

    A frame in `keep_frames` holds a pose the animator set, so it is left as it
    is, even if that pose touches the body, with the correction fading in around it.
    """
    body = read_body(root) or measure_body(root, skeleton)
    if not body:
        return 0
    control = dict(target_pairs(root, skeleton)[0])
    frames = list(range(int(first), int(last) + 1))
    restore = cmds.currentTime(query=True)
    touched = 0
    identity = om2.MQuaternion()
    try:
        cmds.refresh(suspend=True)
        plans = []
        for upper, fore, hand in ARM_SIDES:
            plans.append((upper, fore, hand, [identity] * len(frames),
                          [identity] * len(frames)))
        for index, frame in enumerate(frames):
            cmds.currentTime(frame, edit=True)
            segments = _torso_now(body, control)
            for upper, fore, hand, upper_turns, fore_turns in plans:
                shoulder = _position(control[upper])
                elbow = _position(control[fore])
                wrist = _position(control[hand])
                first_turn = identity
                goal = _pushed(elbow, segments, body["arm"][upper], clearance,
                               body["limit"][fore])
                if goal:
                    first_turn = _swing(shoulder, elbow, goal)
                    elbow = _rotated(elbow, shoulder, first_turn)
                    wrist = _rotated(wrist, shoulder, first_turn)
                second_turn = identity
                mid = [(elbow[k] + wrist[k]) * 0.5 for k in range(3)]
                for point, radius, limit in (
                        (wrist, body["arm"][hand], body["limit"][hand]),
                        (mid, body["arm"][fore], body["limit"][fore + "_mid"])):
                    goal = _pushed(point, segments, radius, clearance, limit)
                    if goal:
                        second_turn = _swing(elbow, point, goal)
                        break
                upper_turns[index] = first_turn
                fore_turns[index] = second_turn

        for upper, fore, hand, upper_turns, fore_turns in plans:
            if all(abs(t.w) > 0.99999 for t in upper_turns + fore_turns):
                continue
            upper_smooth = _settled(upper_turns)
            fore_smooth = _settled(fore_turns)
            for index, frame in enumerate(frames):
                turn_u, turn_f = upper_smooth[index], fore_smooth[index]
                near = min([abs(frame - kept) for kept in keep_frames] or [keep_fade])
                if near < keep_fade:
                    share = float(near) / keep_fade
                    turn_u = om2.MQuaternion.slerp(identity, turn_u, share)
                    turn_f = om2.MQuaternion.slerp(identity, turn_f, share)
                if abs(turn_u.w) > 0.99999 and abs(turn_f.w) > 0.99999:
                    continue
                cmds.currentTime(frame, edit=True)
                nodes = (control[upper], control[fore], control[hand])
                worlds = [_rotation_matrix(node) for node in nodes]
                wanted = (worlds[0] * turn_u.asMatrix(),
                          worlds[1] * turn_u.asMatrix() * turn_f.asMatrix(),
                          worlds[2])
                for node, world in zip(nodes, wanted):
                    _set_world_rotation(node, world, cmds.getAttr(node + ".rotateOrder"))
                    cmds.setKeyframe(node, attribute=("rotateX", "rotateY", "rotateZ"),
                                     time=frame)
                touched += 1
            for node in (control[upper], control[fore], control[hand]):
                cmds.filterCurve(node + ".rotateX", node + ".rotateY", node + ".rotateZ",
                                 filter="euler")
    finally:
        cmds.refresh(suspend=False)
        cmds.currentTime(restore, edit=True)
    return touched


# Planted means low and slow. Metres, so they hold at any scene scale.
FOOT_PLANT_HEIGHT = 0.02       # above the lowest this foot gets in the take
FOOT_PLANT_SPEED = 1.2         # metres a second
FOOT_PLANT_MIN_FRAMES = 3      # a shorter touch is a foot passing through


def plant_offsets(tracks, height, speed, anchors=(), min_frames=FOOT_PLANT_MIN_FRAMES):
    """Ground offsets that keep planted feet still, one (x, z) per frame.

    `tracks` is one list of (x, y, z) per foot, a position per frame. `height`
    and `speed` are in scene units, per frame for the speed. While a foot is
    planted the body takes the opposite of its slide; while none is, the body
    keeps the offset it has, so nothing jumps. With both planted the average
    is used, since one offset cannot fix two feet moving differently.

    `anchors` are frame indices that must not move. The offset at each is
    taken back out, blending between them, so an edited pose stays put and
    the difference is spread over the frames around it.
    """
    count = len(tracks[0])
    planted = []
    for track in tracks:
        floor = min(point[1] for point in track)
        flags = [track[i][1] < floor + height
                 and track[i + 1][1] < floor + height
                 and ((track[i][0] - track[i + 1][0]) ** 2
                      + (track[i][2] - track[i + 1][2]) ** 2) ** 0.5 < speed
                 for i in range(count - 1)]
        # Drop runs too short to be a real plant.
        i = 0
        while i < len(flags):
            if not flags[i]:
                i += 1
                continue
            end = i
            while end < len(flags) and flags[end]:
                end += 1
            if end - i < min_frames:
                flags[i:end] = [False] * (end - i)
            i = end
        planted.append(flags)

    offsets = [(0.0, 0.0)]
    locked = 0
    for i in range(count - 1):
        feet = [t for t, flags in zip(tracks, planted) if flags[i]]
        x, z = offsets[-1]
        if feet:
            locked += 1
            x -= sum(t[i + 1][0] - t[i][0] for t in feet) / len(feet)
            z -= sum(t[i + 1][2] - t[i][2] for t in feet) / len(feet)
        offsets.append((x, z))

    marks = sorted(set(a for a in anchors if 0 <= a < count))
    if not marks:
        return offsets, locked
    held = []
    for i in range(count):
        if i <= marks[0]:
            back = offsets[marks[0]]
        elif i >= marks[-1]:
            back = offsets[marks[-1]]
        else:
            for a, b in zip(marks, marks[1:]):
                if a <= i <= b:
                    t = float(i - a) / (b - a)
                    back = (offsets[a][0] + (offsets[b][0] - offsets[a][0]) * t,
                            offsets[a][1] + (offsets[b][1] - offsets[a][1]) * t)
                    break
        held.append((offsets[i][0] - back[0], offsets[i][1] - back[1]))
    return held, locked


def lock_feet(feet, first, last, hips, travel=None, anchors=(), levels=()):
    """Shift the baked body along the ground so planted feet stay put."""
    frames = list(range(int(first), int(last) + 1))
    if len(frames) < 2:
        return 0
    restore = cmds.currentTime(query=True)
    try:
        cmds.refresh(suspend=True)
        tracks = [[] for _ in feet]
        for frame in frames:
            cmds.currentTime(frame, edit=True)
            # What the character stands on is what says whether a foot is on
            # the ground. Main itself is no measure: at the top of a jump it is
            # up there with the feet.
            lift = _level_at(levels, frame) if levels else 0.0
            for track, foot in zip(tracks, feet):
                at = cmds.xform(foot, query=True, worldSpace=True, translation=True)
                track.append([at[0], at[1] - lift, at[2]])
        scale = scene_scale()
        offsets, locked = plant_offsets(
            tracks, FOOT_PLANT_HEIGHT * scale,
            FOOT_PLANT_SPEED * scale / scene_fps(),
            [anchor - frames[0] for anchor in anchors])
        for frame, (x, z) in zip(frames, offsets):
            if travel:
                cmds.keyframe(travel + ".translateX", edit=True, relative=True,
                              time=(frame, frame), valueChange=x)
                cmds.keyframe(travel + ".translateZ", edit=True, relative=True,
                              time=(frame, frame), valueChange=z)
            else:
                cmds.currentTime(frame, edit=True)
                at = cmds.xform(hips, query=True, worldSpace=True, translation=True)
                cmds.xform(hips, worldSpace=True,
                           translation=(at[0] + x, at[1], at[2] + z))
                cmds.setKeyframe(hips, attribute=("translateX", "translateY",
                                                  "translateZ"), time=frame)
    finally:
        cmds.refresh(suspend=False)
        cmds.currentTime(restore, edit=True)
    return locked


def main_lift(target_root):
    """What the character stands on at the current frame, in scene units.

    Main's height has two parts. A step up is the animator's and the model never
    sees it. A jump is motion: the model solves it, and Main only carries it. So
    this is the first part, and everything above it counts as the model's.
    """
    travel = _by_short_name(target_root).get(AS_TRAVEL_CONTROL)
    if not travel:
        return 0.0
    base = _main_base(target_root, cmds.currentTime(query=True))
    if base:
        return _base_level(base)
    return cmds.getAttr(travel + ".translateY")


MAIN_BASE_ATTR = "azKimodoMainBase"


def _main_translate(travel, frame=None):
    if frame is None:
        return [cmds.getAttr(travel + ".translate" + axis) for axis in "XYZ"]
    return [cmds.getAttr(travel + ".translate" + axis, time=frame) for axis in "XYZ"]


def _base_level(base):
    """The level in a base entry. An older entry has none: all its height was level."""
    return base[3] if len(base) > 3 else base[1]


def _base_ground(base):
    """What the take stands on before any step, or the level in an older entry."""
    return base[4] if len(base) > 4 else _base_level(base)


def remember_main_base(root, first, last, levels=(), ground=None):
    """Where the bake left Main on each frame: what a later drag is measured from.

    Comparing with the curve would miss a drag made with auto key on, since the
    curve then already holds the new value.
    """
    travel = _by_short_name(root).get(AS_TRAVEL_CONTROL)
    if not travel:
        return
    base = {}
    for frame in range(int(first), int(last) + 1):
        place = _main_translate(travel, frame)
        level = _level_at(levels, frame) if levels else place[1]
        base[str(frame)] = place + [level, level if ground is None else ground,
                                    cmds.getAttr(travel + ".rotateY", time=frame)]
    if not cmds.attributeQuery(MAIN_BASE_ATTR, node=root, exists=True):
        cmds.addAttr(root, longName=MAIN_BASE_ATTR, dataType="string")
    cmds.setAttr(root + "." + MAIN_BASE_ATTR, json.dumps(base), type="string")


def _main_bases(root):
    if not cmds.attributeQuery(MAIN_BASE_ATTR, node=root, exists=True):
        return {}
    try:
        return json.loads(cmds.getAttr(root + "." + MAIN_BASE_ATTR) or "{}")
    except ValueError:
        return {}


def _base_near(bases, frame):
    """The base entry of a scene frame.

    At 24 fps some take lengths end one frame past the bake, and a pose can sit
    on that frame: it belongs to the last frame baked.
    """
    entry = bases.get(str(int(round(frame))))
    if entry or not bases:
        return entry
    last = max(int(key) for key in bases)
    return bases[str(last)] if int(round(frame)) == last + 1 else None


def _main_base(root, frame):
    return _base_near(_main_bases(root), frame)


def main_above(root):
    """How far Main is above what the character stands on, at the current frame."""
    travel = _by_short_name(root).get(AS_TRAVEL_CONTROL)
    return cmds.getAttr(travel + ".translateY") - main_lift(root) if travel else 0.0


def _base_turn(base):
    """Main's rotateY in a base entry. Before it was baked, it was left at zero."""
    return base[5] if len(base) > 5 else 0.0


def main_turn(root):
    """(how far Main has been turned from the bake, its rotateY now), in degrees."""
    travel = _by_short_name(root).get(AS_TRAVEL_CONTROL)
    if not travel:
        return 0.0, None
    now = cmds.getAttr(travel + ".rotateY")
    base = _main_base(root, cmds.currentTime(query=True))
    return (now - _base_turn(base) if base else 0.0), now


def main_place(root):
    """(how far Main has been dragged from the bake, where it is now), or Nones."""
    travel = _by_short_name(root).get(AS_TRAVEL_CONTROL)
    if not travel:
        return None, None
    now = _main_translate(travel)
    base = _main_base(root, cmds.currentTime(query=True))
    if base is None:
        return [0.0, 0.0, 0.0], now
    return [a - b for a, b in zip(now, base)], now


def _ramp(marks, frame, start):
    """A value through (frame, value) marks: from zero at `start`, held after the last."""
    if frame >= marks[-1][0]:
        return marks[-1][1]
    if frame <= marks[0][0]:
        span = marks[0][0] - start
        return marks[0][1] * (frame - start) / span if span > 0 else marks[0][1]
    for (a, va), (b, vb) in zip(marks, marks[1:]):
        if a <= frame <= b:
            return va + (vb - va) * float(frame - a) / (b - a)
    return marks[-1][1]


def _level_at(levels, frame):
    """The level through (frame, level) marks, easing from one to the next."""
    if frame <= levels[0][0]:
        return levels[0][1]
    for (a, value_a), (b, value_b) in zip(levels, levels[1:]):
        if frame <= b:
            if b <= a:
                return value_b
            t = float(frame - a) / (b - a)
            return value_a + (value_b - value_a) * t * t * (3.0 - 2.0 * t)
    return levels[-1][1]


MAIN_STEP_FRAMES = 8    # shortest a step up may take, in scene frames


def _holds_level(pin, ground):
    """True when a pose moves what the character stands on.

    A pose saved before the option existed says nothing. Main only ever stayed
    up then, so any height on it was a step.
    """
    target = pin.get("main_target") if pin.get("edited", True) else None
    if not target:
        return False
    return pin.get("main_hold", abs(target[1] - ground) > 0.01)


def main_plan(poses, start_frame, last_frame, ground):
    """Main's height through the poses: ({scene frame: height}, level marks).

    Every pose says where Main is on its own frame, so one lifted pose rises and
    comes back down between its neighbours, like a pose lifted by the pelvis. A
    pose that holds the level moves it instead: the character gets there by that
    pose and stays.
    """
    first = take_frame_to_scene(0, start_frame)
    last_frame = int(last_frame)
    ordered = [(min(take_frame_to_scene(frame, start_frame), last_frame), pin)
               for frame, pin in sorted(poses.items())]
    levels = [(first, ground)]
    level = ground
    previous = first
    for scene, pin in ordered:
        if _holds_level(pin, ground):
            height = pin["main_target"][1]
            if scene <= first:
                levels = [(first, height)]
            else:
                begin = max(levels[-1][0], min(previous, scene - MAIN_STEP_FRAMES))
                levels += [(begin, level), (scene, height)]
            level = height
        previous = scene
    keys = {}
    for scene, pin in ordered:
        if _holds_level(pin, ground):
            keys[scene] = pin["main_target"][1]
        else:
            keys[scene] = _level_at(levels, scene) + pin.get("main_above", 0.0)
    keys.setdefault(first, levels[0][1])
    keys.setdefault(last_frame, level)
    return keys, levels


def _write_main_height(travel, keys):
    """Key Main's height on the pose frames only."""
    if not cmds.getAttr(travel + ".translateY", settable=True):
        return
    for frame, value in sorted(keys.items()):
        cmds.setKeyframe(travel, attribute="translateY", time=frame, value=value,
                         inTangentType="auto", outTangentType="auto")


def _above_others(poses, frame, start_frame, last_frame, ground, height):
    """A height of Main above what the other poses make the character stand on.

    The pose keeps its place in the plan, because a step's ramp starts at the
    pose before it.
    """
    others = dict(poses)
    others[frame] = {"edited": False}
    _keys, levels = main_plan(others, start_frame, last_frame, ground)
    return height - _level_at(levels, min(take_frame_to_scene(frame, start_frame),
                                          last_frame))


def pose_main_above(root, poses, frame, start_frame):
    """How far Main is above what the character will stand on at this pose.

    Main left on its curve keeps the height the last bake gave it, whatever the
    level does: a step just made earlier carries this pose up with it. Only a drag,
    or this pose's own step being switched off, says something new.
    """
    bases = _main_bases(root)
    first = bases.get(str(take_frame_to_scene(0, start_frame)))
    if not first:
        return main_above(root)
    ground = _base_ground(first)
    travel = _by_short_name(root).get(AS_TRAVEL_CONTROL)
    height = cmds.getAttr(travel + ".translateY")
    base = _base_near(bases, take_frame_to_scene(frame, start_frame))
    if (base and abs(height - base[1]) < 1e-3
            and not _holds_level(poses.get(frame, {}), ground)):
        return base[1] - _base_level(base)
    return _above_others(poses, frame, start_frame, max(int(key) for key in bases),
                         ground, height)


def settle_old_poses(root, solve, poses):
    """Say outright which poses from before the option moved the level."""
    if not solve:
        return
    first = _main_bases(root).get(str(take_frame_to_scene(0, solve["start_frame"])))
    ground = _base_ground(first) if first else 0.0
    for pin in poses.values():
        if pin.get("edited", True) and pin.get("main_target") and "main_hold" not in pin:
            pin["main_hold"] = _holds_level(pin, ground)


def same_pose(pin, other, tolerance=1e-3):
    """True when two pins ask for the same thing, reading noise aside."""
    if (not other or pin.get("main_hold") != other.get("main_hold")
            or pin.get("mode") != other.get("mode")):
        return False
    if abs((pin.get("main_turn") or 0.0) - (other.get("main_turn") or 0.0)) > tolerance:
        return False
    for key in ("main_target", "root"):
        if bool(pin.get(key)) != bool(other.get(key)):
            return False
        if any(abs(a - b) > tolerance
               for a, b in zip(pin.get(key) or (), other.get(key) or ())):
            return False
    return all(abs(a - b) <= tolerance
               for row, other_row in zip(pin["global"], other["global"])
               for a, b in zip(row, other_row))


def scene_to_model(root, skeleton=SOMA30):
    """Metres on the model's skeleton per scene unit on this rig."""
    _pairs, _mapping, key = target_pairs(root, skeleton)
    for align in (True, False):
        stored = read_stored_rest(root, _rest_signature(skeleton["key"], key, align))
        if stored:
            return 1.0 / (stored["hips_scale"] * scene_scale())
    return 1.0 / scene_scale()


def _swing_ground(point, pivot, degrees):
    """Turn a point's ground position about a pivot, the way rotateY does."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    x, z = point[0] - pivot[0], point[2] - pivot[2]
    point[0] = pivot[0] + c * x + s * z
    point[2] = pivot[2] - s * x + c * z


def _turned_rows(rows, degrees):
    """Stored world rotations turned about the vertical."""
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [[c * m[0] + s * m[6], c * m[1] + s * m[7], c * m[2] + s * m[8],
             m[3], m[4], m[5],
             -s * m[0] + c * m[6], -s * m[1] + c * m[7], -s * m[2] + c * m[8]]
            for m in rows]


def _undragged(target, pin):
    """Where a pose's Main was before this Update's drag."""
    return [a - b for a, b in zip(target, pin.get("place") or (0.0, 0.0, 0.0))]


def warp_pose_roots(poses, root, start_frame, released=(), skeleton=SOMA30):
    """A copy of `poses` with what was done to Main given to the model.

    A turn holds from its pose on, and what comes after swings round with it:
    the same steps, in the new direction. On the ground the path is moved through
    each dragged pose and stays there.
    Height applies to its own pose only: the root is set to carry what the pose
    asks above the level, measured against what the last bake put there, so
    solving again changes nothing. Each ground drag is consumed here.
    """
    to_model = scene_to_model(root, skeleton)
    # Only a move on the ground is a mark. A pose lifted straight up says nothing
    # about the path, and counting it would pull the path back to where it was.
    marks = [(frame, pin["place"]) for frame, pin in sorted(poses.items())
             if pin.get("place")
             and abs(pin["place"][0]) + abs(pin["place"][2]) > 0.01]
    # Between two placements that differ on the ground the old gait cannot carry
    # the character there, so poses read from the animation hold only the path
    # and the model finds the steps.
    travelling = []
    previous_frame, previous = 0, [0.0, 0.0, 0.0]
    for frame, delta in marks:
        if abs(delta[0] - previous[0]) + abs(delta[2] - previous[2]) > 1.0:
            travelling.append((previous_frame, frame))
        previous_frame, previous = frame, delta
    dragged = [frame for frame, _delta in marks]
    roots = dict((frame, list(pin["root"])) for frame, pin in poses.items())
    targets = dict((frame, list(pin["main_target"])) for frame, pin in poses.items()
                   if pin.get("edited", True) and pin.get("main_target"))
    facing = dict((frame, pin["main_turn"]) for frame, pin in poses.items()
                  if pin.get("edited", True) and pin.get("main_turn") is not None)
    angles = dict.fromkeys(poses, 0.0)
    turn_marks = [(frame, pin["place_turn"]) for frame, pin in sorted(poses.items())
                  if abs(pin.get("place_turn", 0.0)) > 0.1]
    turned = [frame for frame, _total in turn_marks]
    turned_by = 0.0
    previous_frame = 0
    for mark, total in turn_marks:
        step, turned_by = total - turned_by, total
        pivot = list(roots[mark])
        # Turned as the path is: before the drags, which are added on top of it.
        place = _undragged(targets[mark], poses[mark]) if mark in targets else None
        for frame in poses:
            if frame <= mark:
                continue
            _swing_ground(roots[frame], pivot, step)
            if frame in targets and place:
                point = _undragged(targets[frame], poses[frame])
                _swing_ground(point, place, step)
                drag = poses[frame].get("place") or (0.0, 0.0, 0.0)
                targets[frame] = [a + b for a, b in zip(point, drag)]
            # A later turned pose already says which way it faces.
            if frame not in turned:
                angles[frame] += step
                if frame in facing:
                    facing[frame] += step
        travelling.append((max(previous_frame, mark - MAIN_TURN_WINDOW), mark))
        previous_frame = mark
    free = [frame for frame, pin in poses.items() if pin.get("edited", True)]
    free += list(released)
    bases = _main_bases(root)
    first = bases.get(str(take_frame_to_scene(0, start_frame)))
    ground = _base_ground(first) if first else 0.0
    last_baked = max(int(key) for key in bases) if bases else None
    moved = {}
    for frame, pin in poses.items():
        shifted = dict(pin)
        shifted.pop("place", None)
        shifted.pop("place_turn", None)
        if angles[frame]:
            shifted["global"] = _turned_rows(pin["global"], angles[frame])
        if frame in facing:
            shifted["main_turn"] = facing[frame]
        edited = pin.get("edited", True)
        if (bases and edited and pin.get("main_target") and pin.get("place")
                and abs(pin["place"][1]) > 0.01 and not _holds_level(pin, ground)):
            shifted["main_above"] = _above_others(
                poses, frame, start_frame, last_baked, ground, pin["main_target"][1])
        if not edited and any(a < frame < b for a, b in travelling):
            reshape_pin(shifted, "root")
        # Next to an edit the old height no longer describes anything, and
        # writing it back would keep a hump alive after its cause has gone.
        if not edited and any(abs(frame - other) <= EDIT_FREE_WINDOW for other in free):
            shifted["main_above"] = 0.0
        new_root = roots[frame]
        target = targets.get(frame)
        for axis in (0, 2):
            if not marks:
                break
            step = _ramp([(f, delta[axis]) for f, delta in marks], frame, 0)
            new_root[axis] += to_model * step
            # A pose placed earlier has to move with the path, or the fit would
            # walk the character back to it.
            if target and frame not in dragged:
                target[axis] += step
        if target:
            shifted["main_target"] = target
            base = _base_near(bases, take_frame_to_scene(frame, start_frame))
            if base:
                above = (0.0 if _holds_level(pin, ground)
                         else shifted.get("main_above", 0.0))
                new_root[1] += to_model * (above - (base[1] - _base_level(base)))
        shifted["root"] = new_root
        moved[frame] = shifted
    return moved


MAIN_TURN_SECONDS = 1.0   # about a stride: the sway of a gait stays on the hips
MAIN_TURN_WINDOW = 30     # model frames the model gets to carry out a turn


def _blurred(values, radius):
    """`values` under a triangular blur, holding the ends."""
    last = len(values) - 1
    out = []
    for index in range(len(values)):
        total = weights = 0.0
        for offset in range(-radius, radius + 1):
            weight = radius + 1 - abs(offset)
            total += weight * values[min(last, max(0, index + offset))]
            weights += weight
        out.append(total / weights)
    return out


def _main_turns(source_by_name, start_frame, frames, poses):
    """Main's rotateY on each frame of a take, or None if the take has no legs.

    It follows where the take faces, measured as the generator measures it,
    and lands exactly on the rotation each edited pose asks for.
    """
    left = source_by_name.get("LeftLeg")
    right = source_by_name.get("RightLeg")
    if not (left and right):
        return None
    headings = []
    for frame in range(frames):
        cmds.currentTime(start_frame + frame, edit=True)
        a = cmds.xform(left, query=True, worldSpace=True, translation=True)
        b = cmds.xform(right, query=True, worldSpace=True, translation=True)
        heading = math.degrees(math.atan2(b[2] - a[2], -(b[0] - a[0])))
        # Unbroken across +-180, or Main would spin the long way round.
        if headings:
            heading += 360.0 * round((headings[-1] - heading) / 360.0)
        headings.append(heading)
    radius = max(1, int(scene_fps() * MAIN_TURN_SECONDS / 2.0))
    turns = _blurred(headings, radius)
    marks = []
    for frame, pin in sorted((poses or {}).items()):
        if pin.get("edited", True) and pin.get("main_turn") is not None:
            index = min(max(take_frame_to_scene(frame, start_frame) - start_frame, 0),
                        frames - 1)
            marks.append((index, (pin["main_turn"] - turns[index] + 180.0) % 360.0 - 180.0))
    if marks:
        turns = [turn + _ramp(marks, index, 0) for index, turn in enumerate(turns)]
    return turns


def main_targets(poses, start_frame):
    """{scene frame: Main position} for every pose that says where it should be."""
    return dict((take_frame_to_scene(frame, start_frame), pin["main_target"])
                for frame, pin in poses.items()
                if pin.get("edited", True) and pin.get("main_target"))


POSE_BLEND_SECONDS = 0.5  # how long the bake takes to ease into an edited pose


def _pose_gaps(pairs, source_by_name, skeleton, start_frame, frames, poses, scale,
               hips_scale, neck_damping):
    """What the take misses on each edited pose: {take index: (turns, hips height)}.

    `turns` holds, per source joint, the world rotation from the take to the pose.
    Moves the timeline.
    """
    names = skeleton["names"]
    name_of = dict((joint, name) for name, joint in source_by_name.items())
    gaps = {}
    for frame, pin in sorted((poses or {}).items()):
        if not pin.get("edited", True):
            continue
        index = min(max(take_frame_to_scene(frame, start_frame) - start_frame, 0),
                    frames - 1)
        cmds.currentTime(start_frame + index, edit=True)
        damped = _damped_neck(source_by_name, neck_damping)
        unread = pin.get("unread") or ()
        turns = {}
        for source, _target in pairs:
            name = name_of[source]
            if name in unread:
                continue
            v = pin["global"][names.index(name)]
            wanted = om2.MMatrix([v[0], v[3], v[6], 0.0, v[1], v[4], v[7], 0.0,
                                  v[2], v[5], v[8], 0.0, 0.0, 0.0, 0.0, 1.0])
            taken = damped.get(source) or _rotation_matrix(source)
            turn = om2.MTransformationMatrix(
                taken.inverse() * wanted).rotation(asQuaternion=True)
            if turn.w < 0.0:
                turn = om2.MQuaternion(-turn.x, -turn.y, -turn.z, -turn.w)
            turns[source] = turn
        hips = cmds.xform(source_by_name[names[0]], query=True, worldSpace=True,
                          translation=True)
        gaps[index] = (turns, (pin["root"][1] * scale - hips[1]) * hips_scale)
    return gaps


def _pose_shares(marks, index, blend, accuracy):
    """[(mark, share)] of the sorted pose `marks` that reach a frame of the take.

    Each fades out before it reaches the next pose, so a pose is only ever
    corrected by its own gap.
    """
    shares = []
    earlier = [mark for mark in marks if mark <= index]
    later = [mark for mark in marks if mark > index]
    if earlier and later:
        reach = min(blend, later[0] - earlier[-1])
    else:
        reach = blend
    for mark in earlier[-1:] + later[:1]:
        t = 1.0 - float(abs(index - mark)) / reach
        if t > 0.0:
            shares.append((mark, accuracy * t * t * (3.0 - 2.0 * t)))
    return shares


def fit_main_to_targets(travel, first, last, targets):
    """Write what the solve still misses on the ground into Main, so it is exact.

    Height needs no fit: it was keyed to the poses before the bake.
    """
    if not targets or not travel:
        return
    frames = range(int(first), int(last) + 1)
    ordered = sorted(frame for frame in targets if first <= frame <= last)
    if not ordered:
        return
    for index, axis in ((0, "X"), (2, "Z")):
        plug = "%s.translate%s" % (travel, axis)
        marks = [(frame, targets[frame][index] - cmds.getAttr(plug, time=frame))
                 for frame in ordered]
        if all(abs(value) < 1e-3 for _frame, value in marks):
            continue
        for frame in frames:
            cmds.keyframe(plug, edit=True, relative=True, time=(frame, frame),
                          valueChange=_ramp(marks, frame, first))


def retarget(source_joints, skeleton_key, target_root, start_frame, frames,
             target_key="", hips_scale=None, align_rest=True, mode="replace",
             write_start=None, travel_on_root=True, neck_damping=1.0,
             drop_twist=False, foot_lock=False, keep_frames=(), ik_limbs=(),
             arm_clearance=None, main_poses=None, pose_accuracy=1.0):
    """Bake the generated motion onto an existing skeleton.

    `mode` decides what happens to animation the rig already carries:
    "replace" drops it and writes the take at `start_frame`, "append" keeps it
    and writes after the last existing key.

    The rig must be in its bind pose the first time this runs - that pose
    becomes the reference, and is cached on the rig for every take after it.
    """
    if mode not in RETARGET_MODES:
        raise ValueError("mode must be one of %s" % (RETARGET_MODES,))
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    pairs, missing, target_key = resolve_pairs(source_joints, skeleton,
                                               target_root, target_key)
    if not pairs:
        raise ValueError("nothing to retarget: no joint pairs resolved")

    scale = scene_scale()
    target_joints = [target for _, target in pairs]
    rotate_orders = [cmds.getAttr(target + ".rotateOrder")
                     for target in target_joints]
    hips_target = target_joints[0]
    source_height = source_hip_height(skeleton, scale)

    travel = None
    if travel_on_root and target_key == AS_MANNY:
        travel = _by_short_name(target_root).get(AS_TRAVEL_CONTROL)

    if target_key == AS_MANNY:
        remember_fkik(target_root)
    switched = switch_to_fk(target_root) if target_key == AS_MANNY else []
    if switched:
        print("[AZ Kimodo Motion %s] moved to FK: %s"
              % (VERSION, ", ".join(switched)))

    saved_curves = {}
    place_main = main_targets(main_poses, start_frame) if main_poses else {}
    levels = None
    main_keys = None
    if mode == "replace":
        # Cutting Main's height would leave it on whatever frame the scene is
        # on. It starts this take from the height the last one started at.
        ground = (cmds.getAttr(travel + ".translateY", time=start_frame)
                  if travel else None)
        # The last bake says where the take starts: the curve may hold a jump
        # there and a drag may be sitting on the channels. The first frame holds
        # its place.
        bases = _main_bases(target_root) if travel else {}
        baked = _base_near(bases, start_frame)
        if bases:
            # Every entry of one bake knows the same ground.
            ground = _base_ground(baked or next(iter(bases.values())))
        if baked and place_main:
            place_main.setdefault(write_start if write_start is not None
                                  else start_frame, baked[:3])
        clear_retarget_keys(target_joints, hips_target, travel)
        if travel and cmds.getAttr(travel + ".translateY", settable=True):
            cmds.setAttr(travel + ".translateY", ground)
        if target_key == AS_MANNY:
            clear_ik_keys(target_root)
        if write_start is None:
            write_start = start_frame
        if travel:
            main_keys, levels = main_plan(main_poses or {}, start_frame,
                                          write_start + frames - 1, ground)
    else:
        if write_start is None:
            last = last_keyed_frame(target_joints)
            write_start = start_frame if last is None else int(last) + 1
        saved_curves = snapshot_curves(
            target_joints + ([travel] if travel else []))
        # An old take can end in the air. The new stretch starts from what the
        # character stands on, not from the tail of Main's curve.
        bases = _main_bases(target_root) if travel else {}
        stands_on = (_base_level(bases[str(max(int(key) for key in bases))])
                     if bases else None)
        clear_retarget_keys(target_joints, hips_target, travel)
        if stands_on is not None and cmds.getAttr(travel + ".translateY", settable=True):
            cmds.setAttr(travel + ".translateY", stands_on)
            main_keys = {write_start: stands_on}

    signature = _rest_signature(skeleton["key"], target_key, align_rest,
                                drop_twist)
    stored = read_stored_rest(target_root, signature)
    if stored and len(stored["rotations"]) != len(pairs):
        stored = None
    if stored:
        rest_rotations = [om2.MMatrix(values) for values in stored["rotations"]]
        rest_hips = stored["rest_hips"]
        if hips_scale is None:
            hips_scale = stored["hips_scale"]
    else:
        # Cutting the curves above left every joint wherever the last
        # evaluation put it, not at bind - and measuring the reference off
        # that pose is how the root-motion scale once came out as 0.10
        # instead of 0.96.
        restore_bind_pose(target_root)

        # Root motion scales with leg length, so the feet keep meeting the
        # ground. Measured on the bind pose, before alignment moves the rig.
        rest_hips = cmds.xform(hips_target, query=True, worldSpace=True,
                               translation=True)
        target_floor = min(cmds.xform(target, query=True, worldSpace=True,
                                      translation=True)[1]
                           for target in target_joints)
        if hips_scale is None:
            hips_scale = ((rest_hips[1] - target_floor) / source_height
                          if source_height > 1e-6 else 1.0)

        mapping = [(source_name, target_name)
                   for source_name, target_name
                   in _with_alternates(RETARGET_MAPS[(skeleton["key"], target_key)],
                                       _by_short_name(target_root))
                   if source_name not in missing and target_name not in missing]
        if align_rest:
            rest_rotations = align_to_source_rest(pairs, mapping, skeleton,
                                                  scale, rotate_orders,
                                                  drop_twist)
        else:
            rest_rotations = [_rotation_matrix(target)
                              for target in target_joints]
        write_stored_rest(target_root, signature, rest_rotations, rest_hips,
                          hips_scale)

    # Only now: a first bake measures the rest pose above, with Main on a plain
    # value that no curve can pull away during the measure.
    if main_keys and mode == "replace":
        _write_main_height(travel, main_keys)

    source_hips = source_joints[0]
    source_by_name = dict(zip(skeleton["names"], source_joints))
    if levels is None:
        levels = [(write_start,
                   cmds.getAttr(travel + ".translateY") if travel else 0.0)]
    restore_time = cmds.currentTime(query=True)
    try:
        cmds.refresh(suspend=True)
        main_turns = None
        if travel and cmds.getAttr(travel + ".rotateY", settable=True):
            main_turns = _main_turns(source_by_name, start_frame, frames, main_poses)
        gaps = {}
        if pose_accuracy > 0.0:
            gaps = _pose_gaps(pairs, source_by_name, skeleton, start_frame, frames,
                              main_poses, scale, hips_scale, neck_damping)
        marks = sorted(gaps)
        blend = max(1, int(scene_fps() * POSE_BLEND_SECONDS))
        identity = om2.MQuaternion()
        for frame in range(frames):
            # Read where the take lives, write where it is being placed: in
            # append mode those are different stretches of the timeline.
            read_at = start_frame + frame
            write_at = write_start + frame
            cmds.currentTime(read_at, edit=True)

            shares = _pose_shares(marks, frame, blend, pose_accuracy) if marks else ()
            hips_world = cmds.xform(source_hips, query=True, worldSpace=True,
                                    translation=True)
            placed = (rest_hips[0] + hips_world[0] * hips_scale,
                      rest_hips[1] + (hips_world[1] - source_height) * hips_scale
                      + _level_at(levels, write_at)
                      + sum(gaps[mark][1] * share for mark, share in shares),
                      rest_hips[2] + hips_world[2] * hips_scale)
            if travel:
                # Ground travel goes to the global control so it follows the
                # character; the rise and fall stays on the hips. Putting the
                # height there too would lift everything parented under the
                # global control - the IK feet included - and the character
                # would bob with its own footfalls.
                cmds.setAttr(travel + ".translateX", placed[0] - rest_hips[0])
                cmds.setAttr(travel + ".translateZ", placed[2] - rest_hips[2])
                cmds.setKeyframe(travel, attribute=("translateX", "translateZ"),
                                 time=write_at)
                # Before anything under Main is placed. Those are all written in
                # world space, so the character itself does not change.
                if main_turns:
                    cmds.setAttr(travel + ".rotateY", main_turns[frame])
                    cmds.setKeyframe(travel, attribute="rotateY", time=write_at)
            cmds.xform(hips_target, worldSpace=True, translation=placed)
            cmds.setKeyframe(hips_target,
                             attribute=("translateX", "translateY",
                                        "translateZ"), time=write_at)

            damped = _damped_neck(source_by_name, neck_damping)
            for index, (source, target) in enumerate(pairs):
                rotation = damped.get(source) or _rotation_matrix(source)
                for mark, share in shares:
                    turn = gaps[mark][0].get(source)
                    if turn is not None:
                        rotation = (rotation * om2.MQuaternion.slerp(
                            identity, turn, share).asMatrix())
                _set_world_rotation(target, rest_rotations[index] * rotation,
                                    rotate_orders[index])
                cmds.setKeyframe(target, attribute=("rotateX", "rotateY",
                                                    "rotateZ"), time=write_at)
    finally:
        cmds.refresh(suspend=False)
        cmds.currentTime(restore_time, edit=True)

    if saved_curves:
        restore_curves(saved_curves)
    if main_keys and mode != "replace":
        _write_main_height(travel, main_keys)

    for target in target_joints:
        cmds.filterCurve(target + ".rotateX", target + ".rotateY",
                         target + ".rotateZ", filter="euler")

    end_frame = write_start + frames - 1
    if place_main and travel:
        fit_main_to_targets(travel, write_start, end_frame, place_main)
        keep_frames = list(keep_frames) + sorted(place_main)
    locked = 0
    if foot_lock:
        target_of = dict(pairs)
        feet = [target_of[source_by_name[name]]
                for name in ("LeftToeBase", "RightToeBase")
                if source_by_name.get(name) in target_of]
        if len(feet) == 2:
            locked = lock_feet(feet, write_start, end_frame, hips_target, travel,
                               keep_frames, levels)
    arms_moved = 0
    if arm_clearance is not None:
        arms_moved = keep_arms_out(target_root, write_start, end_frame, arm_clearance,
                                   skeleton, keep_frames)
    if ik_limbs and target_key == AS_MANNY:
        bake_ik(target_root, write_start, end_frame, ik_limbs)
    if mode == "replace" and travel:
        remember_main_base(target_root, write_start, end_frame, levels, ground)
    print("[AZ Kimodo Motion %s] retargeted %d joints onto %s, %s frames "
          "%d-%d (hips scale %.3f, travel on %s)%s"
          % (VERSION, len(pairs), TARGET_LABELS.get(target_key, target_key),
             mode, write_start, end_frame, hips_scale,
             travel.split("|")[-1] if travel else "the hips",
             ("; unmapped: %s" % ", ".join(missing)) if missing else ""))
    return {"pairs": pairs, "missing": missing, "target_key": target_key,
            "hips_scale": hips_scale, "frames": frames, "mode": mode,
            "start": write_start, "end": end_frame,
            "reused_rest": bool(stored), "feet_locked": locked,
            "arms_moved": arms_moved}


# --------------------------------------------------------------------------- #
# Pose pins
# --------------------------------------------------------------------------- #
#
# The motion model is a diffusion model, so part of its representation can be
# pinned while the rest is denoised around it - the same mechanism that carries
# one prompt segment's pose into the next. kmd-constrain exposes it for poses
# supplied from here.
#
# Poses are authored on a copy of the generator's own skeleton rather than on
# the target rig: the joints then match the model one-for-one and nothing is
# lost converting proportions. Measured round-trip on a pose taken from the
# model's own output: about 1 cm per joint.

POSE_PREFIX = "kimodoPose_"
POSE_RIG_ATTR = "kimodoPoseRig"
POSE_MAGIC = b"KMDP"

_CONSTRAIN_CANDIDATES = (
    "build/vulkan/kmd-constrain.exe",
    "build/release/kmd-constrain.exe",
    "build/vulkan/kmd-constrain",
    "build/release/kmd-constrain",
)


def constrain_path(root=None):
    base = root or install_root()
    for relative in _CONSTRAIN_CANDIDATES:
        candidate = os.path.join(base, relative).replace("\\", "/")
        if os.path.isfile(candidate):
            return candidate
    return ""


def build_pose_rig(skeleton_key="soma30", prefix=POSE_PREFIX):
    """A posable copy of the generator's skeleton, in its rest pose."""
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    joints = build_skeleton(skeleton, scene_scale(), prefix)
    holder = cmds.group(joints[0], name=prefix + "RIG_GRP")
    cmds.addAttr(holder, longName=POSE_RIG_ATTR, dataType="string")
    cmds.setAttr(holder + "." + POSE_RIG_ATTR, skeleton["key"], type="string")
    print("[AZ Kimodo Motion %s] pose rig ready: %s (%d joints)"
          % (VERSION, holder, len(joints)))
    return {"top": holder, "joints": joints, "skeleton": skeleton["key"]}


def find_pose_rig():
    """The pose rig in the scene, or None."""
    for node in cmds.ls(type="transform", long=True):
        if cmds.attributeQuery(POSE_RIG_ATTR, node=node, exists=True):
            key = cmds.getAttr(node + "." + POSE_RIG_ATTR)
            skeleton = SOMA30 if key == SOMA30["key"] else G1SKEL34
            joints = []
            for name in skeleton["names"]:
                found = cmds.ls(node + "|*|*" + name, long=True) or \
                    [j for j in _descendant_joints(node)
                     if j.split("|")[-1].endswith(name)]
                if found:
                    joints.append(found[0])
            if len(joints) == len(skeleton["names"]):
                return {"top": node, "joints": joints, "skeleton": key}
    return None


# Which channels a pin holds. The sampler's mask is per element, so a pin does
# not have to be a whole pose - holding only the root row leaves the model free
# to decide how the body walks the path, and holding only the feet fixes the
# contacts while everything above them stays generated.
#
# `root` pins travel, height and heading; `positions` and `rotations` list joint
# names. Only the four end effectors were trained with a rotation condition, so
# no mode asks for another joint's orientation.
_FEET = ("LeftFoot", "LeftToeBase", "RightFoot", "RightToeBase")
_LEGS = ("LeftLeg", "LeftShin", "RightLeg", "RightShin") + _FEET
# Only the four end effectors were trained with a rotation condition, but hard
# pinning does not ask the model to honour a channel - it overwrites it, and
# the decoder rebuilds the skeleton from rotations alone. So freezing the whole
# arm chain's rotations is what actually locks a hand in place: pinning hand
# POSITIONS cannot, because the decoder never reads a joint position.
# Measured over a 31-frame hold: hand positions pinned hard drift 41.6 cm,
# the arm chain pinned hard drifts 1.2 cm.
_ARM_CHAIN = ("Spine1", "Spine2", "Chest",
              "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
              "RightShoulder", "RightArm", "RightForeArm", "RightHand")

_UPPER = ("Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head",
          "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
          "RightShoulder", "RightArm", "RightForeArm", "RightHand")

PIN_MODES = (
    ("full", "Whole pose", None, ("LeftFoot", "RightFoot", "LeftHand", "RightHand"),
     True, "Hold the entire body at this frame - about a centimetre per joint"),
    ("exact", "Whole pose (exact)", None, None, True,
     "Reproduce this frame exactly. Holds every joint's rotation, which is "
     "what the decoder rebuilds the skeleton from, so the frame comes back "
     "as authored. Needs Hard pinning, which the tool turns on for you"),
    # The decoder reads the root as row[0] + the hips position triple, so
    # pinning the root row alone leaves half of it free and the path is not
    # actually held. Every mode that means to place the body in the world
    # therefore pins Hips as well - joint positions are stored relative to it.
    ("root", "Root path only", ("Hips",), (), True,
     "Hold where the hips are and which way they face; the model decides how "
     "the body gets there"),
    ("feet", "Feet only", _FEET + ("Hips",), ("LeftFoot", "RightFoot"), True,
     "Hold the foot contacts and leave the rest of the body generated"),
    ("hands", "Hands only", ("LeftHand", "RightHand", "Hips"),
     ("LeftHand", "RightHand"), True,
     "Nudge both hands toward where they are. A suggestion, not a lock - "
     "for a lock use Hands locked"),
    ("hands_rigid", "Hands locked", ("Hips",), _ARM_CHAIN, True,
     "Freeze the arms outright by holding every rotation from the spine to "
     "the hands. Needs Hard pinning, which the tool turns on for you"),
    ("upper", "Upper body only", _UPPER, ("LeftHand", "RightHand"), True,
     "Hold the spine, head and arms; the legs are generated"),
    ("lower", "Legs only", _LEGS, ("LeftFoot", "RightFoot"), True,
     "Hold the legs and feet; the upper body is generated"),
)

PIN_MODE_KEYS = tuple(mode[0] for mode in PIN_MODES)

# Modes that overwrite channels the model was never conditioned on, and so are
# meaningless unless the solve is told to force them.
# Only an exact key pose is worth forcing. A locked grab used to force it
# too, on the reasoning that asking politely would not hold the arm - but
# measured over a twenty-frame hold it held no better than the polite
# version (82 cm of drift against 84) while jumping three and a half times
# as far in a single frame (130 cm against 36).
PIN_MODES_NEEDING_HARD = ("exact",)


def pin_masks(mode, skeleton):
    """(pin_root, position flags, rotation flags) for one pin mode."""
    for key, _label, positions, rotations, root, _tip in PIN_MODES:
        if key != mode:
            continue
        names = skeleton["names"]
        position_flags = [1] * len(names) if positions is None else \
            [1 if name in positions else 0 for name in names]
        rotation_flags = [1] * len(names) if rotations is None else \
            [1 if name in rotations else 0 for name in names]
        return root, position_flags, rotation_flags
    raise ValueError("unknown pin mode %r (known: %s)"
                     % (mode, ", ".join(PIN_MODE_KEYS)))


def capture_pose(joints, frame, mode="full", skeleton_key="soma30"):
    """Snapshot the pose rig as the constraint file wants it.

    Rotations are stored column-major (R * v), which is the transpose of Maya's
    row-vector matrices, and positions are converted back to the metres the
    model works in.
    """
    scale = scene_scale()
    root = cmds.xform(joints[0], query=True, worldSpace=True, translation=True)
    matrices = []
    for joint in joints:
        matrix = _rotation_matrix(joint)
        matrices.append([matrix[column * 4 + row]
                         for row in range(3) for column in range(3)])
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    pin_root, positions, rotations = pin_masks(mode, skeleton)
    return {"frame": int(frame),
            "mode": mode,
            "root": [value / scale for value in root],
            "scene_root": list(root),
            "global": matrices,
            "pin_root": pin_root,
            "pin_positions": positions,
            "pin_rotations": rotations}


def target_pairs(target_root, skeleton, target_key=""):
    """Mapped (source name, target joint) pairs for a rig, without a source.

    resolve_pairs needs a generated take to match against; capture works the
    other way round, so this resolves the target side alone.
    """
    target_key = target_key or identify_target(target_root)
    if not target_key:
        raise ValueError("%s: %s" % (target_root.split("|")[-1],
                                     describe_target(target_root)))
    mapping = RETARGET_MAPS.get((skeleton["key"], target_key))
    if mapping is None:
        raise ValueError("no retarget map from %s to %s"
                         % (skeleton["key"], target_key))
    names = _by_short_name(target_root)
    pairs, kept = [], []
    for source_name, target_name in _with_alternates(mapping, names):
        if target_name in names:
            pairs.append((source_name, names[target_name]))
            kept.append((source_name, target_name))
    return pairs, kept, target_key


def has_bind_pose(target_root):
    return bool(cmds.attributeQuery(BIND_ATTR, node=target_root, exists=True))


def is_animated(target_root, skeleton=None, target_key=""):
    """True when anything the tool would drive already carries keys."""
    try:
        pairs, _mapping, _key = target_pairs(target_root,
                                             skeleton or SOMA30, target_key)
    except Exception:
        return False
    return last_keyed_frame([target for _, target in pairs]) is not None


def bone_source_root(target_root):
    """Where a pose should be READ from, which is not where it is written.

    Driving happens through the FK controls, but an animator working in IK
    never touches those - the foot follows IKLeg_L and the FK control stays at
    rest, so reading the controls would capture a pose nobody is looking at.
    The bind skeleton moves whatever the rig is doing, so a capture reads that
    instead. On this rig it is a separate top-level hierarchy, not a child of
    the control group.
    """
    try:
        if identify_target(target_root) == UE5_MANNY:
            return target_root, UE5_MANNY
    except Exception:
        pass

    found = []
    for node in cmds.ls(assemblies=True, long=True):
        if node.split("|")[-1] in ("persp", "top", "front", "side"):
            continue
        try:
            if identify_target(node) == UE5_MANNY:
                found.append(node)
        except Exception:
            pass
    if len(found) == 1:
        return found[0], UE5_MANNY
    # Several characters, or none: fall back to the rig itself rather than
    # guessing which skeleton belongs to this rig.
    return target_root, ""


def _hold_fkik(root):
    """Current FKIKBlend values, so switch_to_fk can be undone."""
    names = _by_short_name(root)
    held = []
    for switch in AS_FKIK_SWITCHES:
        node = names.get(switch)
        plug = (node + ".FKIKBlend") if node else ""
        if plug and cmds.objExists(plug) and not cmds.getAttr(plug, lock=True):
            held.append((plug, cmds.getAttr(plug)))
    return held


def _undriven_bones(pairs, control_pairs, probe=15.0):
    """Which mapped bones do not follow their own control one for one.

    A bone can move with the rig and still be unable to carry a reference. This
    rig's second neck bone has no driver and only inherits its parent, and the
    first is driven through a blend, so a single reference matrix describes
    neither of them and a pose read back off them returns something nobody
    authored. Each control is turned on its own and the bone is asked whether
    it turned by the same amount.

    Must run with the limbs already in FK: a leg sitting in IK ignores its FK
    control and would look undriven when it is merely being driven elsewhere.
    """
    bone_by_source = dict(pairs)
    unfollowed = []
    for source, control in control_pairs:
        bone = bone_by_source.get(source)
        if bone is None:
            continue
        ratio = None
        for axis in "YXZ":
            plug = "%s.rotate%s" % (control, axis)
            if not cmds.objExists(plug) or cmds.getAttr(plug, lock=True):
                continue
            if cmds.listConnections(plug, source=True, destination=False):
                continue
            was = cmds.getAttr(plug)
            bone_before = _rotation_matrix(bone)
            control_before = _rotation_matrix(control)
            try:
                cmds.setAttr(plug, was + probe)
                turned = _matrix_angle(
                    control_before.inverse() * _rotation_matrix(control))
                followed = _matrix_angle(
                    bone_before.inverse() * _rotation_matrix(bone))
                # The control is the yardstick, not the number typed into it:
                # a rotate order and a non-zero neighbouring channel make the
                # actual turn something other than the probe.
                ratio = followed / turned if turned > 1e-3 else None
            except Exception:
                ratio = None
            finally:
                try:
                    cmds.setAttr(plug, was)
                except Exception:
                    pass
            if ratio is not None:
                break
        # A control that could not be turned at all says nothing either way,
        # so the bone keeps the benefit of the doubt.
        if ratio is not None and ratio < 0.9:
            unfollowed.append(source)
    return sorted(unfollowed)


def _bone_rest_via_controls(pairs, control_root, skeleton, scale, drop_twist):
    """The reference for reading a pose off the BIND SKELETON, measured on the
    controls that drive it.

    align_to_source_rest swings each mapped joint onto its source's rest
    direction and adds nothing about the joint's own axis, so a joint with no
    mapped child of its own inherits its parent's swing through the DAG. That
    is true of a control chain and false of this rig's bind skeleton, where
    every bone takes its orientation from its own orientConstraint and not from
    its parent. Measured: rotating the bone lowerarm_l by 30 degrees moved
    hand_l by 0.000, while rotating the control FKForeArm_L moved it by 30.

    So measuring on the bones left the five tips that get no swing of their own
    - the head, both hands, both toe bases - in a different basis from the one
    the retarget writes against, and reading a pose back was off by a fixed
    rotation per joint: 65.5 degrees at the wrists, 22.1 at the forearms, 8.4
    at the toes. That error went into the pin, came back out through the next
    generation, and was read again, so it doubled every pass.

    The fix is to swing the CONTROLS and let the rig's own constraints carry
    that onto the bones, then read the reference off the bones. Returns None if
    the bones did not follow, so the caller can keep the old measurement rather
    than cache a reference built on an assumption that did not hold.
    """
    try:
        control_pairs, control_mapping, _key = target_pairs(control_root,
                                                            skeleton)
    except Exception:
        return None
    if not control_pairs:
        return None

    before = [_rotation_matrix(target) for _source, target in pairs]
    fkik = _hold_fkik(control_root)
    try:
        # A limb sitting in IK ignores whatever its FK control is doing, and
        # this rig ships with both legs in IK - the swing would never reach
        # those bones. Put back below, so an animator's IK limb survives.
        switch_to_fk(control_root)
        orders = [cmds.getAttr(target + ".rotateOrder")
                  for _source, target in control_pairs]
        align_to_source_rest(control_pairs, control_mapping, skeleton, scale,
                             orders, drop_twist)
        rest = [_rotation_matrix(target) for _source, target in pairs]
        unfollowed = _undriven_bones(pairs, control_pairs)
    finally:
        for plug, value in fkik:
            try:
                cmds.setAttr(plug, value)
            except Exception:
                pass

    bone_turn = dict((source, _matrix_angle(a.inverse() * b))
                     for (source, _t), a, b in zip(pairs, before, rest))

    if max(bone_turn.values() or [0.0]) < 1e-3:
        print("[AZ Kimodo Motion %s] the bind skeleton did not follow the "
              "controls, so the reference was measured on the bones "
              "themselves" % VERSION)
        return None

    if unfollowed:
        print("[AZ Kimodo Motion %s] not driven by the rig, so left unread: %s"
              % (VERSION, ", ".join(unfollowed)))
    return rest, unfollowed


def capture_reference_rest(target_root, skeleton, target_key="", bind_root=None,
                           drop_twist=False):
    """The aligned reference pose a capture measures against.

    Reuses whatever a retarget already cached on the rig. Otherwise the rig has
    to be in its bind pose to measure one, which is exactly the state it is in
    before the first retarget - and the alignment is cached so this happens
    once.
    """
    pairs, mapping, target_key = target_pairs(target_root, skeleton, target_key)
    if not pairs:
        raise ValueError("no mapped joints found under %s" % target_root)
    bind_root = bind_root or target_root

    # A pose read off a separate bind skeleton needs its own reference, and
    # the way it used to be measured was wrong - see _bone_rest_via_controls.
    # The slot is versioned so a rig saved before this fix stops serving it.
    separate = bind_root != target_root
    signature = _rest_signature(skeleton["key"], target_key, True, drop_twist)
    if separate:
        signature += "|b2"
    stored = read_stored_rest(bind_root, signature)
    if stored and len(stored["rotations"]) != len(pairs):
        stored = None
    if stored:
        return ([om2.MMatrix(values) for values in stored["rotations"]],
                pairs, stored["rest_hips"], stored["hips_scale"], target_key,
                stored.get("unfollowed", []))

    targets = [target for _, target in pairs]
    # A pose is read off the bind skeleton, and those bones carry no keys of
    # their own - they are constrained. Asking them whether the rig is
    # animated always answers no, so ask the rig.
    if is_animated(bind_root):
        raise RuntimeError(
            "the rig carries animation, so its bind pose cannot be measured "
            "now. Retarget a take once (that caches the reference), or press "
            "Clear rig animation while it should be at bind.")

    rotate_orders = [cmds.getAttr(target + ".rotateOrder") for target in targets]
    scale = scene_scale()
    height = source_hip_height(skeleton, scale)

    # align_to_source_rest POSES the rig to measure the reference. Measuring
    # has to happen from the bind pose to mean anything, and a capture must
    # hand back the pose the animator actually made - so the current pose is
    # put aside, the reference is measured from bind, and the pose returns.
    held = [(node, cmds.getAttr(node + ".rotate")[0],
             cmds.getAttr(node + ".translate")[0])
            for node in set(targets) | set(_descendant_joints(bind_root))
            if cmds.objExists(node + ".rotate")]
    if not restore_bind_pose(bind_root):
        raise RuntimeError(
            "no bind pose is recorded for %s. Put the rig at bind and press "
            "Remember bind pose in the RETARGET group - the reference is "
            "measured from it." % bind_root.split("|")[-1])
    try:
        # Only now, with the rig actually at bind, do the hips mean anything.
        # Measuring them first recorded whatever pose the scene happened to be
        # showing, and every pin then read as standing at that spot.
        rest_hips = cmds.xform(targets[0], query=True, worldSpace=True,
                               translation=True)
        floor = min(cmds.xform(target, query=True, worldSpace=True,
                               translation=True)[1] for target in targets)
        hips_scale = (rest_hips[1] - floor) / height if height > 1e-6 else 1.0

        rest, unfollowed = None, []
        if separate:
            measured = _bone_rest_via_controls(pairs, bind_root, skeleton,
                                               scale, drop_twist)
            if measured is not None:
                rest, unfollowed = measured
        if rest is None:
            rest = align_to_source_rest(pairs, mapping, skeleton, scale,
                                        rotate_orders, drop_twist)
        write_stored_rest(bind_root, signature, rest, rest_hips, hips_scale,
                          unfollowed)
    finally:
        for target, rotate, translate in held:
            _set_triple(target, "rotate", rotate)
            _set_triple(target, "translate", translate)
    return rest, pairs, rest_hips, hips_scale, target_key, unfollowed


def prime_references(target_root, skeleton_key="soma30"):
    """Measure now what a later capture will need, while the rig is still clean.

    A retarget caches its reference against the control map; a capture reads
    the bind skeleton and so needs its own. Left until the first pin, that
    measurement lands on a rig that is already carrying a take - and the
    reference has to come from the bind pose or every pin reads as standing
    wherever the scene happened to be.
    """
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    if is_animated(target_root):
        return False
    pose_root, bone_key = bone_source_root(target_root)
    try:
        capture_reference_rest(pose_root, skeleton, bone_key,
                               bind_root=target_root)
    except Exception:
        return False
    return True


# --------------------------------------------------------------------------- #
# Character
# --------------------------------------------------------------------------- #
#
# The tool used to open onto an empty retarget: import a skeleton, record its
# bind pose, pick it as the target, generate, press retarget. Every one of
# those is the same answer every time, so the window now does them itself the
# moment it opens - a rig the retarget knows how to drive is found in the
# scene or brought in from a file, measured, and set as the target. What is
# left for the animator is the prompt.

CHARACTER_OPTVAR = "azKimodoCharacterFile"
CHARACTER_ENV = "AZ_KIMODO_CHARACTER"
_CHARACTER_CANDIDATES = ()
_CAMERAS = ("persp", "top", "front", "side")


def character_file():
    """The rig file the window opens on its own, or "" when none is known.

    $AZ_KIMODO_CHARACTER wins, then whatever was last picked in the UI, then
    a character folder beside the install.
    """
    path = os.environ.get(CHARACTER_ENV, "")
    if path and os.path.isfile(path):
        return path.replace("\\", "/")
    try:
        if cmds.optionVar(exists=CHARACTER_OPTVAR):
            path = cmds.optionVar(query=CHARACTER_OPTVAR) or ""
            if path and os.path.isfile(path):
                return path.replace("\\", "/")
    except Exception:
        pass
    candidates = ("%s/maya/character/Manny_Rig.ma" % install_root(),)
    for candidate in candidates + _CHARACTER_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate.replace("\\", "/")
    return ""


def remember_character_file(path):
    """Keep the picked rig file across sessions."""
    cmds.optionVar(stringValue=(CHARACTER_OPTVAR, path.replace("\\", "/")))


def find_character():
    """A rig already in the scene that the retarget can drive: (root, key).

    Every top-level node is asked whether it is a known rig. Manny's control
    rig and its bind skeleton both answer, so the control rig is preferred -
    that is where the animation is written and the pins are read.
    """
    found = {}
    for node in cmds.ls(assemblies=True, long=True) or []:
        if node.split("|")[-1] in _CAMERAS or is_generated_skeleton(node):
            continue
        try:
            key = identify_target(node)
        except Exception:
            continue
        if key:
            found.setdefault(key, node)
    for key in TARGET_ORDER:
        if key in found:
            return found[key], key
    return None, ""


def load_character(path):
    """Bring a rig file into the scene and return the root the retarget drives.

    Imported rather than referenced: the working scene stays self-contained,
    the animation lands on plain nodes, and nothing depends on the file's
    path later. find_character runs before this, so a rig already present is
    never brought in twice.
    """
    path = path.replace("\\", "/")
    if not os.path.isfile(path):
        raise IOError("no such file: %s" % path)
    if path.lower().endswith(".fbx"):
        root = import_target_fbx(path)
        return root, identify_target(root)

    before = set(cmds.ls(assemblies=True, long=True) or [])
    kind = "mayaBinary" if path.lower().endswith(".mb") else "mayaAscii"
    cmds.file(path, i=True, type=kind, ignoreVersion=True,
              preserveReferences=True, mergeNamespacesOnClash=False,
              options="v=0;")
    fresh = [node for node in cmds.ls(assemblies=True, long=True) or []
             if node not in before]
    found = {}
    for node in fresh:
        try:
            key = identify_target(node)
        except Exception:
            continue
        if key:
            found.setdefault(key, node)
    for key in TARGET_ORDER:
        if key in found:
            return found[key], key
    raise RuntimeError(
        "%s brought in %d top-level node(s) but none of them is a rig the "
        "retarget knows: %s" % (os.path.basename(path), len(fresh),
                                 ", ".join(n.split("|")[-1] for n in fresh)
                                 or "nothing"))


def ensure_character(path=None):
    """A driveable rig in the scene, measured and ready. The window's first act.

    Finds one already present, otherwise loads `path` (or character_file()).
    A rig that has never been measured gets its bind pose recorded and the
    capture reference primed right away - the only moment it is guaranteed
    to be standing at bind is before anything has been written onto it.
    """
    root, key = find_character()
    loaded = False
    used_path = ""
    if root is None:
        used_path = path or character_file()
        if not used_path:
            return {"root": None, "key": "", "loaded": False, "path": "",
                    "notes": ["no character in the scene and no rig file set"]}
        root, key = load_character(used_path)
        loaded = True

    notes = []
    if not has_bind_pose(root):
        if is_animated(root, target_key=key):
            notes.append("the rig is animated and has no recorded bind pose - "
                         "put it at bind and press Remember bind pose")
        else:
            with undo_chunk("measure rig"):
                capture_bind_pose(root)
                notes.append("bind pose recorded")
                if prime_references(root):
                    notes.append("reference measured")
    if not read_body(root) and has_bind_pose(root):
        try:
            with undo_chunk("measure body"):
                measured = measure_body(root)
            if measured:
                notes.append("body measured")
        except Exception as error:
            notes.append("could not measure the body: %s" % error)
    return {"root": root, "key": key, "loaded": loaded, "path": used_path,
            "label": TARGET_LABELS.get(key, key), "notes": notes}


def frame_character(root):
    """Fit the active view to the rig, leaving the selection as it was."""
    keep = cmds.ls(selection=True, long=True) or []
    try:
        cmds.select(root, replace=True)
        cmds.viewFit(animate=False)
    finally:
        if keep:
            cmds.select(keep, replace=True)
        else:
            cmds.select(clear=True)


# --------------------------------------------------------------------------- #
# One-button pose edit
# --------------------------------------------------------------------------- #
#
# A diffusion model cannot move one frame: every solve rebuilds the whole take.
# So the animation already on the rig is pinned at regular intervals and the
# stretch around the edit is left free, which keeps the change local.

SOLVE_ATTR = "azKimodoLastSolve"
POSE_STEP_DEFAULT = 10    # scene frames between analyzed poses
EDIT_FREE_WINDOW = 10     # model frames left free on each side of an edit
EDIT_PIN_WEIGHT = 1.0     # lighter than the usual 2: stronger pins slide the feet


def remember_solve(target_root, solve, edits, unapplied=(), released=(),
                   changed=False, limbs=None):
    """Keep what made the rig's animation on the rig itself.

    Undo rolls this attribute back with the scene, so what the pose list needs
    to follow an undo is all in here.
    """
    if not cmds.attributeQuery(SOLVE_ATTR, node=target_root, exists=True):
        cmds.addAttr(target_root, longName=SOLVE_ATTR, dataType="string")
    cmds.setAttr(target_root + "." + SOLVE_ATTR,
                 json.dumps({"solve": solve,
                             "edits": [edits[key] for key in sorted(edits)],
                             "unapplied": sorted(unapplied),
                             "released": sorted(released),
                             "changed": bool(changed),
                             "limbs": limbs}),
                 type="string")


def solve_text(target_root):
    """The stored solve as it stands, to tell cheaply whether it has changed."""
    if not cmds.attributeQuery(SOLVE_ATTR, node=target_root, exists=True):
        return ""
    return cmds.getAttr(target_root + "." + SOLVE_ATTR) or ""


def read_pose_state(target_root):
    """(unapplied frames, released frames, changed, limb choice) kept with the solve."""
    try:
        stored = json.loads(solve_text(target_root) or "{}")
    except ValueError:
        stored = {}
    return (set(stored.get("unapplied", ())), set(stored.get("released", ())),
            bool(stored.get("changed")), stored.get("limbs"))


def read_solve(target_root):
    """(solve or None, {frame: pin}) recorded on the rig."""
    if not cmds.attributeQuery(SOLVE_ATTR, node=target_root, exists=True):
        return None, {}
    try:
        stored = json.loads(cmds.getAttr(target_root + "." + SOLVE_ATTR) or "")
        return (stored.get("solve"),
                dict((int(pin["frame"]), pin) for pin in stored.get("edits", [])))
    except Exception:
        return None, {}


def pose_frames(frames, start_frame, step):
    """Model frames an analysis samples: every `step` scene frames, plus the last."""
    first = take_frame_to_scene(0, start_frame)
    last = take_frame_to_scene(int(frames) - 1, start_frame)
    fps_ratio = MODEL_FPS / scene_fps()
    wanted = []
    for scene in list(range(first, last + 1, max(1, int(step)))) + [last]:
        frame = min(int(frames) - 1, int(round((scene - start_frame) * fps_ratio)))
        if frame not in wanted:
            wanted.append(frame)
    return wanted


def analyze_poses(target_root, frames, start_frame):
    """{model frame: pin} read off the rig's animation. Moves the timeline."""
    poses = {}
    with quietly():
        restore = cmds.currentTime(query=True)
        try:
            for frame in frames:
                cmds.currentTime(take_frame_to_scene(frame, start_frame), edit=True)
                pin = capture_pose_from_rig(target_root, frame, "full")
                pin["edited"] = False
                pin["main_above"] = main_above(target_root)
                poses[frame] = pin
        finally:
            cmds.currentTime(restore, edit=True)
    return poses


def pose_pins(poses, released=(), window=EDIT_FREE_WINDOW):
    """The pins a solve goes through: the pose list, with room around each edit.

    An analyzed pose close to an edited one still holds the old motion and would
    fight the edit, so it sits this solve out. `released` frames are edited poses
    being deleted: nothing is pinned there and they get the same room, so the
    prompt fills them in again.
    """
    free = [frame for frame, pin in poses.items() if pin.get("edited", True)]
    free += list(released)
    pins = [pin for frame, pin in poses.items()
            if pin.get("edited", True)
            or not any(abs(frame - other) <= window for other in free)]
    return sorted(pins, key=lambda pin: pin["frame"])


POSE_MARK_PREFIX = "kimodoPoseMark"
POSE_MARK_HELD = (0.25, 0.55, 0.95)
POSE_MARK_EDITED = (1.0, 0.55, 0.1)


def clear_pose_marks():
    if not cmds.pluginInfo("timeSliderBookmark", query=True, loaded=True):
        return
    marks = cmds.ls(POSE_MARK_PREFIX + "*", type="timeSliderBookmark") or []
    if marks:
        with quietly():
            cmds.delete(marks)


def set_pose_marks(marks):
    """Show [(scene frame, edited)] as bookmarks on the time slider."""
    if not cmds.pluginInfo("timeSliderBookmark", query=True, loaded=True):
        cmds.loadPlugin("timeSliderBookmark", quiet=True)
    # A saved scene has to ask for the plug-in, or it opens with unknown nodes.
    cmds.pluginInfo("timeSliderBookmark", edit=True, writeRequires=True)
    clear_pose_marks()
    with quietly():
        for priority, (scene, edited) in enumerate(marks):
            node = cmds.createNode("timeSliderBookmark", name=POSE_MARK_PREFIX + "1",
                                   skipSelect=True)
            cmds.setAttr(node + ".name", "Pose edited" if edited else "Pose",
                         type="string")
            cmds.setAttr(node + ".timeRangeStart", scene)
            cmds.setAttr(node + ".timeRangeStop", scene + 1)
            cmds.setAttr(node + ".priority", priority)
            cmds.setAttr(node + ".color",
                         *(POSE_MARK_EDITED if edited else POSE_MARK_HELD),
                         type="double3")


# --------------------------------------------------------------------------- #
# Poses that fit the take
# --------------------------------------------------------------------------- #
#
# A pose read off the rig knows where the character stood. Pinned as it is, a
# pose made at the origin pulls the character back to the origin on that frame,
# and one taken after moving Main sends it running to the new spot and back. So
# the pose is separated from its place and given the take's place instead.

POSE_LIBRARY_FILE = "azKimodoPoses.json"
POSE_RAISE_MIN = 0.03     # metres the pelvis must rise to count as raised
_LOWEST_JOINTS = ("LeftFoot", "LeftToeBase", "RightFoot", "RightToeBase")


def pose_positions(pin, skeleton=SOMA30):
    """Joint positions of a pin, in metres - the generator's own forward kinematics."""
    out = []
    for index, offset in enumerate(skeleton["offsets"]):
        parent = skeleton["parents"][index]
        if parent < 0:
            out.append(list(pin["root"]))
            continue
        rotation = pin["global"][parent]
        out.append([out[parent][axis]
                    + rotation[axis * 3] * offset[0]
                    + rotation[axis * 3 + 1] * offset[1]
                    + rotation[axis * 3 + 2] * offset[2]
                    for axis in range(3)])
    return out


def pose_heading(positions, skeleton=SOMA30):
    """Which way the hips face, measured the way the generator measures it."""
    names = skeleton["names"]
    right = positions[names.index("RightLeg")]
    left = positions[names.index("LeftLeg")]
    return math.atan2(right[2] - left[2], -(right[0] - left[0]))


def drop_main_drag(pin, drag):
    """Take a drag of Main out of a pin's root, in the scale the pin was read in."""
    pin["root"][1] -= drag[1] / (pin["hips_scale"] * scene_scale())


def heading_gap(pin, anchor, skeleton=SOMA30):
    """Degrees between the way a pose was asked to face and the way the take does."""
    gap = math.degrees(pose_heading(pose_positions(pin, skeleton), skeleton)
                       - pose_heading(pose_positions(anchor, skeleton), skeleton))
    return (gap + 180.0) % 360.0 - 180.0


def fit_pose_to_take(pin, anchor, skeleton=SOMA30, turn_more=0.0):
    """A copy of `pin` placed where `anchor`, the take on that frame, stands.

    Ground position comes from the take. The whole pose is turned to face the
    way the take faces. Height is set so the pose's lower foot sits as high as
    the take's lower foot: at the top of a jump the pose stays in the air, and
    a crouch on the ground lowers the hips rather than pushing the feet through
    the floor. A pelvis the animator has moved stays moved, as long as the feet
    stay above the floor: on FK legs the feet ride along with it, and the feet
    alone would say nothing changed. `turn_more` is degrees to face beyond the
    take, for a turn of Main.
    """
    names = skeleton["names"]
    feet = [names.index(name) for name in _LOWEST_JOINTS]
    at = pose_positions(anchor, skeleton)
    posed = pose_positions(pin, skeleton)

    turn = (math.degrees(pose_heading(at, skeleton) - pose_heading(posed, skeleton))
            + turn_more)
    turned = _turned_rows(pin["global"], turn)

    above_hips = min(posed[i][1] for i in feet) - pin["root"][1]
    height = min(at[i][1] for i in feet) - above_hips
    if pin["root"][1] - anchor["root"][1] > POSE_RAISE_MIN:
        height = max(height, pin["root"][1])
    elif (anchor["root"][1] - pin["root"][1] > POSE_RAISE_MIN
          and min(posed[i][1] for i in feet) >= 0.0):
        height = pin["root"][1]

    fitted = dict(pin)
    fitted["global"] = turned
    fitted["root"] = [anchor["root"][0], height, anchor["root"][2]]
    fitted["frame"] = anchor["frame"]
    scene = anchor.get("scene_root")
    if scene:
        fitted["scene_root"] = [scene[0],
                                scene[1] + (height - anchor["root"][1])
                                * pin["hips_scale"] * scene_scale(),
                                scene[2]]
    return fitted


def take_pose_at(target_root, frame, skeleton_key="soma30"):
    """The animation's own pose on the current time, ignoring unkeyed changes.

    Hopping the timeline is the only sure way to get the curves' value, and it
    wipes whatever the animator has posed, so that is put back afterwards.
    """
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    pairs, _mapping, _key = target_pairs(target_root, skeleton)
    nodes = [control for _source, control in pairs] + _ik_controls(target_root)
    travel = _by_short_name(target_root).get(AS_TRAVEL_CONTROL)
    if travel:
        nodes.append(travel)
    held = _hold_channels(nodes)
    now = cmds.currentTime(query=True)
    with quietly():
        try:
            cmds.currentTime(now + 1, edit=True)
            cmds.currentTime(now, edit=True)
            # The hop does not undo a drag of Main made with auto key on: the
            # curve holds the drag then. The bake's own record does.
            base = _main_base(target_root, now) if travel else None
            if base:
                for axis, value in zip("XYZ", base):
                    plug = travel + ".translate" + axis
                    if cmds.getAttr(plug, settable=True):
                        cmds.setAttr(plug, value)
                if cmds.getAttr(travel + ".rotateY", settable=True):
                    cmds.setAttr(travel + ".rotateY", _base_turn(base))
            return capture_pose_from_rig(target_root, frame, "full", skeleton_key)
        finally:
            for plug, value in held:
                cmds.setAttr(plug, value)


def load_pose_on_rig(target_root, pin, skeleton_key="soma30"):
    """Put a pin's pose on the FK controls, unkeyed, on the current frame.

    The inverse of reading one: the retarget's reference turns each stored
    rotation back into what its control should be. A joint the pin never read
    is left alone.
    """
    # Showing a pose is not keying it, whatever the auto key button says.
    keying = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        _put_pose_on_rig(target_root, pin, skeleton_key)
    finally:
        cmds.autoKeyframe(state=keying)


def _put_pose_on_rig(target_root, pin, skeleton_key):
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    pairs, _mapping, key = target_pairs(target_root, skeleton)
    stored = read_stored_rest(target_root,
                              _rest_signature(skeleton["key"], key, True))
    if not stored or len(stored["rotations"]) != len(pairs):
        raise RuntimeError("the rig has not been retargeted yet - generate an "
                           "animation first")
    placed = pin.get("main_target")
    travel = _by_short_name(target_root).get(AS_TRAVEL_CONTROL)
    if placed and travel:
        for axis, value in zip("XYZ", placed):
            plug = travel + ".translate" + axis
            if cmds.getAttr(plug, settable=True):
                cmds.setAttr(plug, value)
    if (travel and pin.get("main_turn") is not None
            and cmds.getAttr(travel + ".rotateY", settable=True)):
        cmds.setAttr(travel + ".rotateY", pin["main_turn"])
    names = skeleton["names"]
    unread = pin.get("unread") or ()
    for (source, control), rest in zip(pairs, stored["rotations"]):
        if source in unread:
            continue
        v = pin["global"][names.index(source)]
        matrix = om2.MMatrix([v[0], v[3], v[6], 0.0, v[1], v[4], v[7], 0.0,
                              v[2], v[5], v[8], 0.0, 0.0, 0.0, 0.0, 1.0])
        _set_world_rotation(control, om2.MMatrix(rest) * matrix,
                            cmds.getAttr(control + ".rotateOrder"))
    # Height too, so a crouch reads as a crouch. Ground position stays where
    # the animation has it.
    scene = pin.get("scene_root")
    if scene:
        bone_root, bone_key = bone_source_root(target_root)
        hips_bone = target_pairs(bone_root, skeleton, bone_key)[0][0][1]
        rise = scene[1] - cmds.xform(hips_bone, query=True, worldSpace=True,
                                     translation=True)[1]
        hips = pairs[0][1]
        at = cmds.xform(hips, query=True, worldSpace=True, translation=True)
        cmds.xform(hips, worldSpace=True, translation=(at[0], at[1] + rise, at[2]))
    match_ik_now(target_root)


def has_unkeyed_pose(target_root, skeleton_key="soma30"):
    """True when a control on the rig has been moved from its animation curve."""
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    now = cmds.currentTime(query=True)
    pairs, _mapping, _key = target_pairs(target_root, skeleton)
    travel = _by_short_name(target_root).get(AS_TRAVEL_CONTROL)
    for control in ([control for _source, control in pairs] + _ik_controls(target_root)
                    + ([travel] if travel else [])):
        for attribute in _KEYED_ATTRIBUTES:
            plug = "%s.%s" % (control, attribute)
            if not cmds.objExists(plug):
                continue
            curve = cmds.keyframe(plug, query=True, eval=True, time=(now, now))
            if curve and abs(curve[0] - cmds.getAttr(plug)) > 1e-3:
                return True
    return False


def _read_controls(target_root, skeleton, wanted):
    """World rotations of `wanted` joints, read off the rig's FK controls.

    For bones that do not follow their control, such as this rig's neck. The
    controls are what the retarget writes, so reading them through the same
    reference gives back what it was given. Empty until a retarget has stored
    that reference, because measuring it needs the rig at bind.
    """
    try:
        pairs, _mapping, key = target_pairs(target_root, skeleton)
        stored = read_stored_rest(
            target_root, _rest_signature(skeleton["key"], key, True))
    except Exception:
        return {}
    if not stored or len(stored["rotations"]) != len(pairs):
        return {}
    return dict(
        (source, om2.MMatrix(rest).inverse() * _rotation_matrix(control))
        for (source, control), rest in zip(pairs, stored["rotations"])
        if source in wanted)


def capture_pose_from_rig(target_root, frame, mode="full",
                          skeleton_key="soma30", target_key=""):
    """Read a pose off a character rig and express it on the model's skeleton.

    The retarget writes `target_world = reference_rest * source_world`, so a
    capture inverts it. Proportions need no correction - the generator runs
    forward kinematics on its own skeleton, and only the root height has to be
    divided back out by the leg-length ratio the retarget multiplied it by.
    """
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    pose_root, bone_key = bone_source_root(target_root)
    rest, pairs, rest_hips, hips_scale, target_key, unfollowed =         capture_reference_rest(pose_root, skeleton, target_key or bone_key,
                               bind_root=target_root)

    names = skeleton["names"]
    skip = set(unfollowed)
    by_name = {}
    for index, (source_name, target) in enumerate(pairs):
        if source_name in skip:
            continue
        by_name[source_name] = rest[index].inverse() * _rotation_matrix(target)
    if skip and pose_root != target_root:
        by_name.update(_read_controls(target_root, skeleton, skip))
    if pose_root == target_root:
        by_name.update(_read_ik_limbs(target_root, pairs, rest))

    # A joint the map does not reach has no orientation of its own to read, so
    # it inherits its parent's - the same thing a zero local rotation means.
    matrices = []
    for index, name in enumerate(names):
        matrix = by_name.get(name)
        if matrix is None:
            parent = skeleton["parents"][index]
            matrix = matrices[parent] if parent >= 0 else om2.MMatrix()
        matrices.append(matrix)

    scale = scene_scale()
    height = source_hip_height(skeleton, scale)
    hips = cmds.xform(pairs[0][1], query=True, worldSpace=True, translation=True)
    lift = main_lift(target_root)
    root = [(hips[0] - rest_hips[0]) / hips_scale / scale,
            ((hips[1] - lift - rest_hips[1]) / hips_scale + height) / scale,
            (hips[2] - rest_hips[2]) / hips_scale / scale]

    # A joint the rig cannot supply was inherited from its parent, not read.
    # Pinning it would hold a value nobody authored, so it leaves the mask.
    pin_root, positions, rotations = pin_masks(mode, skeleton)
    unread = [name for name in names if name not in by_name]
    # A position depends on the rotations above a joint, not its own, so an
    # end joint with no bone of its own still has a known position. Leaving
    # those pinned matters: the model was trained with every position held.
    #
    # A joint the rig simply does not have - a short spine has no Spine2 - does
    # not break that: it inherits its parent, which is what the rig's own bones
    # do there. Only a bone that exists but could not be read leaves the chain
    # above it unknown. Counting the first as the second dropped the whole upper
    # body out of the pin, and the solve then ignored the arms and the head.
    uncertain = set(skip) - set(by_name)
    known = []
    for index, name in enumerate(names):
        parent = skeleton["parents"][index]
        known.append(parent < 0 or (known[parent]
                                    and names[parent] not in uncertain))
        if not known[index]:
            positions[index] = 0
        if name in unread:
            rotations[index] = 0
    unplaced = [name for name, fine in zip(names, known) if not fine]

    return {"frame": int(frame),
            "mode": mode,
            "source": target_key,
            "unread": unread,
            "unplaced": unplaced,
            "root": root,
            "hips_scale": hips_scale,
            # Model space measures the hips from the rig's bind position, so
            # it sits near the origin however far the character has walked.
            # The preview needs the scene position instead.
            "scene_root": list(hips),
            "global": [[matrix[column * 4 + row]
                        for row in range(3) for column in range(3)]
                       for matrix in matrices],
            "pin_root": pin_root,
            "pin_positions": positions,
            "pin_rotations": rotations}


def reshape_pin(pin, mode, skeleton_key="soma30"):
    """Change what a pin holds, in place, without re-reading the rig.

    The mask is derived from the mode and the pose is already stored, so
    changing the Hold is arithmetic - no need to put the rig back the way it
    was when the pin was taken.
    """
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    pin_root, positions, rotations = pin_masks(mode, skeleton)

    # A joint the rig could not supply stays out of the mask however the mode
    # changes - it was inherited, not read.
    unread = pin.get("unread") or ()
    unplaced = pin.get("unplaced") or ()
    for index, name in enumerate(skeleton["names"]):
        if name in unplaced:
            positions[index] = 0
        if name in unread:
            rotations[index] = 0

    pin["mode"] = mode
    pin["pin_root"] = pin_root
    pin["pin_positions"] = positions
    pin["pin_rotations"] = rotations
    return pin


PIN_PREVIEW_ATTR = "kimodoPinPreview"

# Wire colours per mode, so a glance says what a pin is holding.
PIN_PREVIEW_COLOURS = {"exact": 14, "full": 17, "hands_rigid": 13,
                       "hands": 20, "feet": 18, "root": 22, "upper": 9,
                       "lower": 6}


def build_pin_preview(pin, scene_frame, skeleton_key="soma30", window=0):
    """A ghost of a pinned pose, keyed to appear only on its own frame.

    A pin is otherwise invisible - the number in a list. Standing the pose up
    in the scene on the frame it belongs to makes the constraint something you
    can scrub to and look at, which is how you notice a bad pin before paying
    a minute of solve for it.
    """
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    scale = scene_scale()
    prefix = "kimodoPin%d_" % int(pin["frame"])
    joints = build_skeleton(skeleton, scale, prefix)

    # The pin stores column-major world rotations; Maya wants its own row
    # convention back, and children need their parent already placed.
    for index, joint in enumerate(joints):
        values = pin["global"][index]
        matrix = om2.MMatrix([values[0], values[3], values[6], 0.0,
                              values[1], values[4], values[7], 0.0,
                              values[2], values[5], values[8], 0.0,
                              0.0, 0.0, 0.0, 1.0])
        _set_world_rotation(joint, matrix,
                            cmds.getAttr(joint + ".rotateOrder"))
    placement = pin.get("scene_root") or [value * scale for value in pin["root"]]
    cmds.setAttr(joints[0] + ".translate",
                 placement[0], placement[1], placement[2], type="double3")

    holder = cmds.group(joints[0], name=prefix + "GRP")
    cmds.addAttr(holder, longName=PIN_PREVIEW_ATTR, attributeType="long")
    cmds.setAttr(holder + "." + PIN_PREVIEW_ATTR, int(pin["frame"]))

    colour = PIN_PREVIEW_COLOURS.get(pin.get("mode", "full"), 17)
    for joint in joints:
        cmds.setAttr(joint + ".overrideEnabled", 1)
        cmds.setAttr(joint + ".overrideColor", colour)

    # Stepped visibility, so the ghost blinks on for its frame and nothing else.
    for offset, value in ((-window - 1, 0), (0, 1), (window + 1, 0)):
        cmds.setKeyframe(holder, attribute="visibility",
                         time=scene_frame + offset, value=value,
                         inTangentType="step", outTangentType="step")
    cmds.keyTangent(holder + ".visibility", edit=True, ott="step")
    cmds.select(clear=True)
    return holder


def find_pin_previews(frame=None):
    """Ghost groups in the scene, optionally just the one for `frame`."""
    found = []
    for node in cmds.ls(type="transform", long=True):
        if not cmds.attributeQuery(PIN_PREVIEW_ATTR, node=node, exists=True):
            continue
        if frame is None or cmds.getAttr(node + "." + PIN_PREVIEW_ATTR) == frame:
            found.append(node)
    return found


def delete_pin_previews(frame=None):
    nodes = find_pin_previews(frame)
    if nodes:
        cmds.delete(nodes)
    return len(nodes)


def write_pose_file(path, poses, joint_count):
    """Serialise pinned poses into the .kmdp format kmd-constrain reads."""
    ordered = sorted(poses, key=lambda pose: pose["frame"])
    seen = set()
    for pose in ordered:
        if pose["frame"] in seen:
            raise ValueError("frame %d is pinned twice" % pose["frame"])
        seen.add(pose["frame"])

    with open(path, "wb") as handle:
        handle.write(POSE_MAGIC)
        handle.write(struct.pack("<III", 3, len(ordered), joint_count))
        for pose in ordered:
            handle.write(struct.pack("<II", int(pose["frame"]),
                                     1 if pose.get("pin_root", True) else 0))
            handle.write(struct.pack("<3f", *pose["root"]))
            for matrix in pose["global"]:
                handle.write(struct.pack("<9f", *matrix))
            positions = pose.get("pin_positions") or [1] * joint_count
            rotations = pose.get("pin_rotations") or [0] * joint_count
            handle.write(bytes(bytearray(positions)))
            handle.write(bytes(bytearray(rotations)))
            handle.write(struct.pack("<f", float(pose.get("weight", 1.0))))
    return path


def capture_range(joints_or_root, first, last, step=1, mode="full",
                  from_rig=False, start_frame=1, skeleton_key="soma30"):
    """Pin the same body part across a run of frames.

    Holding a hand still means pinning it on every frame it must stay put, so
    this walks the range, moves the scene to each frame - which matters when
    the pose is being read off an animated rig - and captures there.
    """
    if last < first:
        raise ValueError("the last frame comes before the first")
    step = max(1, int(step))
    poses = []
    restore = cmds.currentTime(query=True)
    try:
        for frame in range(int(first), int(last) + 1, step):
            cmds.currentTime(take_frame_to_scene(frame, start_frame), edit=True)
            if from_rig:
                poses.append(capture_pose_from_rig(joints_or_root, frame, mode,
                                                   skeleton_key))
            else:
                poses.append(capture_pose(joints_or_root, frame, mode,
                                          skeleton_key))
    finally:
        cmds.currentTime(restore, edit=True)
    return poses


TRAVEL_STEP = 5


def interpolate_root_pins(pins, step=TRAVEL_STEP, skeleton_key="soma30"):
    """Fill the gaps between key poses with root-only pins along a straight path.

    Only pinned frames are held; the frames between them are the model's own
    guess, and it has no idea it is meant to arrive anywhere. Measured on a
    four-metre run pinned at three frames, the character had covered 6 / 15 /
    33 percent of the first leg at its quarter points - it loitered by the
    first pin and then bolted. Pinning just the root along the way gives
    12 / 50 / 64 instead. Denser than every fifth frame changes nothing.

    The key poses are returned untouched; the added pins hold only the root,
    so the model still invents the gait that carries the body along.
    """
    ordered = sorted(pins, key=lambda pin: pin["frame"])
    if len(ordered) < 2:
        return ordered
    skeleton = SOMA30 if skeleton_key == SOMA30["key"] else G1SKEL34
    pin_root, positions, rotations = pin_masks("root", skeleton)

    taken = set(pin["frame"] for pin in ordered)
    added = []
    for first, second in zip(ordered, ordered[1:]):
        span = second["frame"] - first["frame"]
        if span <= step:
            continue
        distance = sum((second["root"][i] - first["root"][i]) ** 2
                       for i in (0, 2)) ** 0.5
        if distance < 0.05:          # 5 cm: nothing to spread out
            continue
        for frame in range(first["frame"] + step, second["frame"], step):
            if frame in taken:
                continue
            ratio = float(frame - first["frame"]) / float(span)
            # Orientation comes from whichever key pose is nearer, since the
            # heading channels are pinned too and a frozen facing across a
            # whole leg reads worse than one switch in the middle.
            source = first if ratio < 0.5 else second
            pin = dict(source)
            pin["frame"] = frame
            pin["mode"] = "root"
            pin["root"] = [first["root"][i]
                           + (second["root"][i] - first["root"][i]) * ratio
                           for i in range(3)]
            pin["pin_root"] = pin_root
            pin["pin_positions"] = list(positions)
            pin["pin_rotations"] = list(rotations)
            pin.pop("scene_root", None)
            added.append(pin)
            taken.add(frame)

    return sorted(ordered + added, key=lambda pin: pin["frame"])


HOLD_STEP = 3

# Frames of fade at each end of a held span. A hard pin switches on between one
# frame and the next, and the solve lurches to meet it - measured at 133 cm of
# movement in a single frame against 18 cm either side. Easing the weight in
# and out spreads that over a few frames instead.
RAMP_WEIGHTS = (0.25, 0.5, 0.75)


def ramp_pins(pins):
    """Fade each held run in and out instead of switching it on.

    A hard pin is absolute: the frame before it is the model's own guess and
    the frame itself is forced, so the solve lurches across that seam - 133 cm
    of movement in one frame where 18 was normal either side. The copies added
    ahead of a run and after it carry the same pose at a fraction of its
    weight, so the pull grows into the hold and falls away out of it.

    Only spans that actually hold are eased. A single key pose is meant to be
    hit and left, and surrounding it with softer copies of itself would ask the
    character to linger there - trading the pop for a stall.

    Root-only pins are left alone too. They are the travel markers laid along
    the path, already spaced apart and already soft enough not to snap.
    """
    ordered = sorted(pins, key=lambda pin: pin["frame"])
    held = [pin for pin in ordered if pin.get("mode") != "root"]
    if not held:
        return ordered
    taken = set(pin["frame"] for pin in ordered)

    # Pins close enough together are one hold, and only its outer edges ease.
    runs, run = [], [held[0]]
    for previous, pin in zip(held, held[1:]):
        if pin["frame"] - previous["frame"] <= HOLD_STEP:
            run.append(pin)
        else:
            runs.append(run)
            run = [pin]
    runs.append(run)

    added = []
    for run in runs:
        if len(run) < 2:
            continue
        for pin, direction in ((run[0], -1), (run[-1], 1)):
            # Nearest the pin carries the most weight, so the pull grows into
            # the hold rather than arriving all at once.
            for step, weight in enumerate(reversed(RAMP_WEIGHTS), start=1):
                frame = pin["frame"] + direction * step
                if frame < 0 or frame in taken:
                    continue
                copy = dict(pin)
                copy["frame"] = frame
                copy["weight"] = weight
                copy.pop("hold_until", None)
                copy.pop("scene_root", None)
                added.append(copy)
                taken.add(frame)
    return sorted(ordered + added, key=lambda pin: pin["frame"])


def expand_held_pins(pins, step=HOLD_STEP):
    """Turn a pin that holds until a later frame into pins across that span.

    A grab is not a moment - the hand has to stay where it is for as long as
    it holds on. One pinned frame only fixes an instant, and the solve is free
    to drift either side of it, so a hold is spread over its own frames here.
    The copies carry the same pose and the same mask; only the frame differs.
    """
    ordered = sorted(pins, key=lambda pin: pin["frame"])
    taken = set(pin["frame"] for pin in ordered)
    added = []
    for pin in ordered:
        until = int(pin.get("hold_until", pin["frame"]))
        if until <= pin["frame"]:
            continue
        # The last frame is always pinned, even when the span is not a whole
        # number of steps - a hold that ends on 60 stopped at 58 otherwise, and
        # let go two frames early.
        frames = list(range(pin["frame"] + step, until + 1, step))
        if frames[-1:] != [until]:
            frames.append(until)
        for frame in frames:
            if frame in taken:
                continue
            copy = dict(pin)
            copy["frame"] = frame
            copy.pop("hold_until", None)
            copy.pop("scene_root", None)
            added.append(copy)
            taken.add(frame)
    return sorted(ordered + added, key=lambda pin: pin["frame"])


def embedding_cache_path(prompt, root=None):
    """Where the encoded form of `prompt` is kept.

    Encoding a prompt means loading a 13 GB text model - measured at 17.6 s of
    a 50 s run, and identical every time the words have not changed. Re-rolling
    a seed or nudging the steps should not pay it twice.
    """
    digest = hashlib.sha1(prompt.strip().encode("utf-8")).hexdigest()[:16]
    folder = os.path.join(root or install_root(), "embeddings")
    return os.path.join(folder, digest + ".f32").replace("\\", "/")


def keep_embedding(take_dir, prompt, root=None):
    """File the embedding a finished run wrote, so the next one can skip it."""
    produced = os.path.join(take_dir, "embedding.f32")
    if not os.path.isfile(produced):
        return ""
    cached = embedding_cache_path(prompt, root)
    folder = os.path.dirname(cached)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    if not os.path.isfile(cached):
        shutil.copyfile(produced, cached)
    return cached


def build_constrain_command(model_path, out_dir, prompt, frames, steps, seed,
                            poses, root=None, pin_weight=2.0, text_weight=2.0,
                            hard=False, use_cache=True):
    """Assemble the kmd-constrain argv for a pinned generation."""
    base = root or install_root()
    generator = constrain_path(base)
    if not generator:
        raise IOError("kmd-constrain not found under %s - rebuild kimodo.cpp"
                      % base)
    if not poses:
        raise ValueError("no poses pinned")

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    prompt_path = os.path.join(out_dir, "p01.txt").replace("\\", "/")
    with open(prompt_path, "wb") as handle:
        handle.write(prompt.strip().encode("utf-8"))

    joint_count = len(poses[0]["global"])
    poses_path = write_pose_file(
        os.path.join(out_dir, "pins.kmdp").replace("\\", "/"), poses, joint_count)

    # The generator takes either the text bundle or an already-encoded prompt
    # in the same slot, so a cache hit simply changes what is handed over.
    cached = embedding_cache_path(prompt, base)
    hit = use_cache and os.path.isfile(cached)
    text_input = cached if hit else text_bundle_path(base)

    return [generator, model_path, text_input, prompt_path,
            poses_path, str(int(frames)), str(int(steps)), str(int(seed)),
            out_dir, "%.3f" % float(pin_weight), "%.3f" % float(text_weight),
            "1" if hard else "0"]


def run():
    """Menu entry point - opens the UI."""
    from azkimodo import az_kimodo_gen_qt
    return az_kimodo_gen_qt.show()
