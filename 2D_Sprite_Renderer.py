import bpy
import os

# ================= USER SETTINGS =================
OUTPUT_PATH = r"YOUR/OUTPUT/FOLDER/HERE"
RENDER_KEYFRAMES_ONLY = False   # False = render every frame in strip range
FRAME_STEP = 1   # 1 = every frame, 2 = every 2nd frame, 3 = every 3rd, etc.
FILE_PREFIX = "Your_File_Prefix_Here (start of the file name)"   # <- type whatever you want here
PAD_DIGITS  = 3              # 001, 002, 003...
USE_PREFIX_FOLDER = True     # folder name = FILE_PREFIX (use the file prefix as folder name)
# =================================================

def safe_name(name: str) -> str:
    s = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
    return s.strip().strip(".")

def safe_prefix(name: str) -> str:
    return safe_name(name) if name else ""

def require_armature():
    arm = bpy.context.view_layer.objects.active
    if not arm or arm.type != 'ARMATURE':
        raise RuntimeError("Select the Armature before running the script.")
    return arm

def stash_nla_state(arm):
    ad = arm.animation_data
    state = []
    if ad and ad.nla_tracks:
        for tr in ad.nla_tracks:
            state.append((tr, tr.mute))
            for st in tr.strips:
                state.append((st, st.mute))
    return state

def restore_nla_state(state):
    for thing, mute in state:
        thing.mute = mute

def mute_all_strips(arm):
    for tr in arm.animation_data.nla_tracks:
        tr.mute = True
        for st in tr.strips:
            st.mute = True

def collect_action_keyframes(strip):
    action = strip.action
    if not action:
        return []
    frames = set()
    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            frames.add(int(round(kp.co.x)))
    return sorted(frames)

def main():
    arm = require_armature()
    arm.data.pose_position = 'POSE'
    arm.animation_data_create()

    scene = bpy.context.scene
    original_frame = scene.frame_current
    nla_state = stash_nla_state(arm)

    root_dir = os.path.abspath(OUTPUT_PATH)
    os.makedirs(root_dir, exist_ok=True)

    ad = arm.animation_data
    if not ad or not ad.nla_tracks:
        raise RuntimeError("No NLA tracks found on armature.")

    try:
        for track in ad.nla_tracks:
            for strip in track.strips:
                if not strip.action:
                    continue

                clean_name = safe_name(strip.name)
                print(f"Rendering strip: {clean_name}")

                mute_all_strips(arm)
                track.mute = False
                strip.mute = False

                prefix = safe_name(FILE_PREFIX)
                folder_name = prefix if (USE_PREFIX_FOLDER and prefix) else clean_name
                strip_dir = os.path.join(root_dir, folder_name)
                os.makedirs(strip_dir, exist_ok=True)

                # guaranteed animated frames
                if not RENDER_KEYFRAMES_ONLY:
                    start = int(strip.frame_start)
                    end   = int(strip.frame_end)
                    step  = max(1, int(FRAME_STEP))
                    frames = list(range(start, end + 1, step))
                    
                    if not frames:
                        frames = [start]
                    
                    # force include final frame
                    if frames[-1] != end:
                        frames.append(end)
    
                else:
                    frames = collect_action_keyframes(strip)
                    if not frames:
                        print("  No keyframes found, skipping.")
                        continue

                for f in frames:
                    scene.frame_set(f)
                    bpy.context.view_layer.update()
                    bpy.context.evaluated_depsgraph_get().update()

                    prefix = safe_name(FILE_PREFIX) or clean_name

                    for idx, f in enumerate(frames, start=1):
                        scene.frame_set(f)
                        bpy.context.view_layer.update()
                        bpy.context.evaluated_depsgraph_get().update()

                        filename = f"{prefix}_{idx:0{PAD_DIGITS}d}.png"
                        out_path = os.path.join(strip_dir, filename)

                        scene.render.filepath = out_path
                        bpy.ops.render.render(write_still=True)

                strip.mute = True

    finally:
        restore_nla_state(nla_state)
        scene.frame_set(original_frame)
        bpy.context.view_layer.update()

    print("✔ Done rendering sprites.")

if __name__ == "__main__":
    main()
