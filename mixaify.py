import bpy

# -------------------------------------------------------
# Bone Mapping Table
# Mixamo -> Rigify
# -------------------------------------------------------

# Define relations between Mixamo and Rigify FK bones
BONE_MAP = {
    "mixamorig:Hips": "torso",
    "mixamorig:Spine": "spine_fk",
    "mixamorig:Spine1": "spine_fk.002",
    "mixamorig:Spine2": "spine_fk.003",
    "mixamorig:Neck": "neck",
    "mixamorig:Head": "head",
    
    "mixamorig:LeftShoulder": "shoulder.L",
    "mixamorig:LeftArm": "upper_arm_fk.L",
    "mixamorig:LeftForeArm": "forearm_fk.L",
    "mixamorig:LeftHand": "hand_fk.L",
    
    "mixamorig:RightShoulder": "shoulder.R",
    "mixamorig:RightArm": "upper_arm_fk.R",
    "mixamorig:RightForeArm": "forearm_fk.R",
    "mixamorig:RightHand": "hand_fk.R",

    "mixamorig:LeftUpLeg": "thigh_fk.L",
    "mixamorig:LeftLeg": "shin_fk.L",
    "mixamorig:LeftFoot": "foot_fk.L",
    "mixamorig:LeftToeBase": "toe_fk.L",

    "mixamorig:RightUpLeg": "thigh_fk.R",
    "mixamorig:RightLeg": "shin_fk.R",
    "mixamorig:RightFoot": "foot_fk.R",
    "mixamorig:RightToeBase": "toe_fk.R",
}

# Location Rigify stores the IK/FK control state of limbs
RIGIFY_IKFK_TOGGLES = {
    "left_arm": "upper_arm_parent.L",
    "right_arm": "upper_arm_parent.R",
    "left_leg": "thigh_parent.L",
    "right_leg": "thigh_parent.R",
}

# Name of propery Rigify uses to hold control state of limb
RIGIFY_IKFK_PROP = "IK_FK"

# Rig root bone names
RIGIFY_ROOT = "root"
MIXAMO_ROOT = "mixamorig:Hips"

# Tag we used when adding constraints so we can find them again
CONSTRAINT_TAG = "MIXAMO_RETARGET"


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
    
# Constrains Rigify FK controls to Mixamo sources generally using Damped Track constraints.
# This prevents underlying bone roll differences between rigs causing twisting. Tracking to
# the source bones tail maintains animation intent while allowing for joint position mismatch.
# Positions are all tracked in WORLD space for consistency. Set FK state on Rigify rigs limbs.
def add_constraints(source_arm, target_arm, ikfk_state):
    prev_obj, prev_mode = ensure_pose_mode(target_arm)
    
    try: # Add Damped Tracks
        for mixamo_name, rigify_name in BONE_MAP.items():
            if rigify_name not in target_arm.pose.bones or mixamo_name not in source_arm.pose.bones:
                continue
            
            tgt_pb = target_arm.pose.bones[rigify_name]
            
            # Ensure no duplicates. Constraints will be replaced on each run.
            for c in tgt_pb.constraints:
                if c.name.startswith(CONSTRAINT_TAG):
                    tgt_pb.constraints.remove(c)

            # Copy Z/X Location if mixamo root instead of track. Y motion will be copied to Rigify root.
            if mixamo_name == MIXAMO_ROOT: 
                con = tgt_pb.constraints.new('COPY_LOCATION')
                con.use_y = False
            else:
                con = tgt_pb.constraints.new('DAMPED_TRACK')
                con.head_tail = 1.0
                con.track_axis = 'TRACK_Y'
                
            con.name = CONSTRAINT_TAG
            con.target = source_arm
            con.subtarget = mixamo_name

            con.target_space = 'WORLD'
            con.owner_space = 'WORLD'

        # Rigify Root copies Mixamo root Y movement, Z/X is copied above to Rigify torso. This decouples root motion.
        if RIGIFY_ROOT in target_arm.pose.bones and MIXAMO_ROOT in source_arm.pose.bones:
            
            tgt_pb = target_arm.pose.bones[RIGIFY_ROOT]
            
            # Ensure no duplicates. Constraints will be replaced on each run.
            for c in tgt_pb.constraints:
                if c.name.startswith(CONSTRAINT_TAG):
                    tgt_pb.constraints.remove(c)
            
            con = tgt_pb.constraints.new('COPY_LOCATION')
            con.name = CONSTRAINT_TAG
            con.target = source_arm
            con.subtarget = MIXAMO_ROOT

            con.target_space = 'WORLD'
            con.owner_space = 'WORLD'
            con.use_z = False
            con.use_x = False
            
        # Switch rig into FK mode, saving the current state
        bpy.context.scene.rtm_ikfk_mode = 'FK'
            
    finally: # Restore state
        restore_mode(prev_obj, prev_mode)


# Reverses everything done by add_constraints
def remove_constraints(target_arm, ikfk_state):
    prev_obj, prev_mode = ensure_pose_mode(target_arm)
    
    try: # Remove any constraints starting with tag
        for pb in target_arm.pose.bones:
            for c in pb.constraints:
                if c.name.startswith(CONSTRAINT_TAG):
                    pb.constraints.remove(c)
    
    finally: # Restore state
        bpy.context.rtm_ikfk_mode = ikfk_state.prev_mode
        restore_mode(prev_obj, prev_mode)


### State controls for IK/FK ###

def save_ikfk_state(arm_obj, state):
    # Must be in pose mode when saving
    for limb, state_bone in RIGIFY_IKFK_TOGGLES.items():
        state[limb] = arm_obj.pose.bones[state_bone][RIGIFY_IKFK_PROP]
        
        
def load_ikfk_state(arm_obj, state):
    # Must be in pose mode when loading
    for limb, state_bone in RIGIFY_IKFK_TOGGLES.items():
        arm_obj.pose.bones[state_bone][RIGIFY_IKFK_PROP] = state[limb]
        
        
def set_fk_state(arm_obj):
    # Must be in pose mode to set FK state
    for limb, state_bone in RIGIFY_IKFK_TOGGLES.items():
        arm_obj.pose.bones[state_bone][RIGIFY_IKFK_PROP] = 1.0
        

def set_ik_state(arm_obj):
    # Must be in pose mode to set IK state
    for limb, state_bone in RIGIFY_IKFK_TOGGLES.items():
        arm_obj.pose.bones[state_bone][RIGIFY_IKFK_PROP] = 0.0
                

### Pose mode swapping  ###

def ensure_pose_mode(arm_obj):
    """Ensure armature is active and in pose mode.
    Returns previous mode to restore later."""
    
    prev_obj = bpy.context.view_layer.objects.active
    prev_mode = bpy.context.mode

    bpy.context.view_layer.objects.active = arm_obj

    if arm_obj.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')

    return prev_obj, prev_mode


def restore_mode(prev_obj, prev_mode):
    """Restores mode returned by the ensure_pose_mode function."""
    try:
        bpy.ops.object.mode_set(mode=prev_mode)
    except:
        pass
    finally:
        bpy.context.view_layer.objects.active = prev_obj
        

### Bone visibility ###
    
def ensure_bones_visible(arm_obj):
    # Save current state while setting all bone groups visible
    prev_state_grp = {}
    for b_col in arm_obj.data.collections_all:
        prev_state_grp[b_col.name] = {'vis': b_col.is_visible, 'solo': b_col.is_solo}
        b_col.is_visible = True
        b_col.is_solo = False
        
    # Same for all bones and make them unselected
    prev_state_bone = {}
    for bone in arm_obj.pose.bones:
        prev_state_bone[bone.name] = {'hide': bone.hide, 'select': bone.select}
        bone.hide = False
        bone.select = False
        
    return prev_state_grp, prev_state_bone
        

def restore_bone_visible(arm_obj, prev_state_grp, prev_state_bone):
    # Restore visibility settings
    for bone, state in prev_state_bone.items():
        arm_obj.pose.bones[bone].hide = state['hide']
        arm_obj.pose.bones[bone].select = state['select']
    for grp, state in prev_state_grp.items():
        arm_obj.data.collections_all[grp].is_visible = state['vis']
        arm_obj.data.collections_all[grp].is_solo = state['solo']


# Bakes retarget to set animation. If assigned actions on rigs are different
# to those set in the UI it will swap them before baking and restore them after.
# Mode must be switched to POSE, with FK controls visible and selected. Bake will
# use visual keying and if no action is set for target rig will bake to a new action.
# All states changed are restored on completion.
def bake_fk_retarget(source_arm, target_arm, src_action, trg_action):
    # Set actions if provided
    prev_src_action = source_arm.animation_data.action
    if src_action:
        source_arm.animation_data.action = src_action
        
    prev_trg_action = target_arm.animation_data.action
    overwrite = False
    if trg_action:
        target_arm.animation_data.action = trg_action
        overwrite = True
    
    # Set pose mode and all bones visible
    prev_obj, prev_mode = ensure_pose_mode(target_arm)
    prev_grp, prev_bone = ensure_bones_visible(target_arm)    
    
    try: # Try bake
        # Select FK bones to bake
        fk_bones = BONE_MAP.values()
        
        # Root is added manually since it's not in the bone map (has special handling for root motion)
        target_arm.pose.bones[RIGIFY_ROOT].select = True
        
        # Set mapped bones selected to include them in bake
        for bone in fk_bones:
            target_arm.pose.bones[bone].select = True
            
        # Get action length
        start, end = map(int, source_arm.animation_data.action.frame_range)    
    
        bpy.ops.nla.bake(
            frame_start = start,
            frame_end = end,
            step = 1,
            only_selected = True,
            visual_keying = True,
            use_current_action = overwrite,
            bake_types = {'POSE'}
        )
        if not bpy.context.scene.rtm_rigify_action:
            bpy.context.scene.rtm_rigify_action = target_arm.animation_data.action
            
    finally: # Restore states
        restore_bone_visible(target_arm, prev_grp, prev_bone)
        restore_mode(prev_obj, prev_mode)
        source_arm.animation_data.action = prev_src_action
        #target_arm.animation_data.action = prev_trg_action


# -------------------------------------------------------
# Operators
# -------------------------------------------------------

    
class RTM_OT_retarget(bpy.types.Operator):
    '''Create retargeting constraints on Rigify FK chains'''
    bl_idname = "rtm.retarget"
    bl_label = "Retarget"

    def execute(self, context):
        if not context.scene.rtm_mixamo or not context.scene.rtm_rigify:
            self.report({'ERROR'}, "Armatures not set")
            return {'CANCELLED'}
        
        src = bpy.context.view_layer.objects[context.scene.rtm_mixamo.name]
        tgt = bpy.context.view_layer.objects[context.scene.rtm_rigify.name]
        ikfk = context.scene.rtm_ikfk_state

        add_constraints(src, tgt, ikfk)

        return {'FINISHED'}


class RTM_OT_untarget(bpy.types.Operator):
    '''Remove any retargeting constraints previously created'''
    bl_idname = "rtm.untarget"
    bl_label = "Untarget"

    def execute(self, context):
        if not context.scene.rtm_rigify:
            self.report({'ERROR'}, "Rigify armature not set")
            return {'CANCELLED'}
        
        tgt = bpy.context.view_layer.objects[context.scene.rtm_rigify.name]
        ikfk = context.scene.rtm_ikfk_state
        
        remove_constraints(tgt, ikfk)

        return {'FINISHED'}

    
class RTM_OT_bake_fk(bpy.types.Operator):
    '''Bake selected Mixamo animation to Rigify FK controls'''
    bl_idname = "rtm.bake_fk"
    bl_label = "Bake FK"
    
    _action_name: str = ""
    
    # If animation name is set, tell the user it will be overwritten before execute. Otherwise just do it.
    def invoke(self, context, event):
        if context.scene.rtm_rigify_action:
            action = context.scene.rtm_rigify_action
            self._action_name = action.name if hasattr(action, "name") else str(action)
            return context.window_manager.invoke_confirm(self, event, message=f"Overwrite Animation: <{self._action_name}> ?")
        else:
            return self.execute(context)

    def execute(self, context):
        if not context.scene.rtm_mixamo or not context.scene.rtm_rigify:
            self.report({'ERROR'}, "Armatures not set")
            return {'CANCELLED'}
        
        src = bpy.context.view_layer.objects[context.scene.rtm_mixamo.name]
        src_act = context.scene.rtm_mixamo_action
        tgt = bpy.context.view_layer.objects[context.scene.rtm_rigify.name]
        tgt_act = context.scene.rtm_rigify_action

        bake_fk_retarget(src, tgt, src_act, tgt_act)

        return {'FINISHED'}
    

# -------------------------------------------------------
# UI Panel
# -------------------------------------------------------

class RTM_PT_panel(bpy.types.Panel):
    bl_label = "Retarget Mixamo -> Rigify"
    bl_idname = "VIEW3D_PT_rig_ui_aa"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Item'
    bl_order = 100

    def draw(self, context):
        layout = self.layout
        
        # Miximo box
        col = layout.column(align=True)
        col.label(text="Mixamo:")
        box = col.box()
        bcol = box.column(align=True)
        bcol.prop(context.scene, "rtm_mixamo", placeholder="Armature", text="Rig")
        bcol.prop(context.scene, "rtm_mixamo_action", text="Anim")
        
        # Rigify box
        col = layout.column(align=True)
        col.label(text="Rigify:")
        box = col.box()
        bcol = box.column(align=True)
        bcol.prop(context.scene, "rtm_rigify", placeholder="Armature", text="Rig")
        bcol.prop(context.scene, "rtm_rigify_action", text="Anim")
        
        layout.separator()

        # Buttons
        row = layout.row(align=True)
        col1 = row.column(align=True)
        col2 = row.column(align=True)
        col1.prop(context.scene, "rtm_enabled", toggle=True, icon='CONSTRAINT')
        col2.operator("rtm.bake_fk", icon='CAMERA_DATA')
        
        # Rigify IK/FK mode switcher
        row = layout.row(align=True)
        row.label(text="Rigify Mode:")
        row.prop(context.scene, "rtm_ikfk_mode", text="")
        
        # Mode switch only enabled in pose mode when retargeting inactive
        if context.mode != 'POSE' or context.scene.rtm_enabled:
            row.enabled = False
        # Bake only enabled when retargeting is also active
        if not context.scene.rtm_enabled:
            col2.enabled = False


# -------------------------------------------------------
# Properties
# -------------------------------------------------------

def armature_poll(self, obj):
    return obj.type == 'ARMATURE'


def mixamo_armature_update(self, context):
    if not context.scene.rtm_mixamo_action and self.rtm_mixamo:
        context.scene.rtm_mixamo_action = self.rtm_mixamo.animation_data.action
        

def action_poll(self, obj):
    return True


def rtm_toggle_update(self, context):
    if context.scene.rtm_enabled:
        bpy.ops.rtm.retarget('INVOKE_DEFAULT')
    else:
        bpy.ops.rtm.untarget('INVOKE_DEFAULT')
        

def rtm_ikfk_modes():
    return [
        ('FK', "FK", "Forward Kinematics"),
        ('IK', "IK", "Inverse Kinematics"),
        ('RIG', "Rigify", "Use Rigify Settings"),
    ]
    

# This state is per scene, not per rig or animation. Design is to be working
# with only one Rigify rig per scene at a time.
class RTM_PG_ikfk_state(bpy.types.PropertyGroup):
    left_arm: bpy.props.FloatProperty(min=0.0, max=1.0)
    right_arm: bpy.props.FloatProperty(min=0.0, max=1.0)
    left_leg: bpy.props.FloatProperty(min=0.0, max=1.0)
    right_leg: bpy.props.FloatProperty(min=0.0, max=1.0)
    prev_mode: bpy.props.EnumProperty(items=rtm_ikfk_modes(), default='RIG')
    
    
# Perform mode change when the mode var is updated. If the
# previous state was 'RIG' then we save the state before changing anything
# so that when swapped back to 'RIG' the state can be restored. The user
# could have any mix of IK/FK in the 'RIG' state.
def rtm_ikfk_mode_update(self, context):
    if not self.rtm_rigify or context.mode != 'POSE':
        return
    
    rig = self.rtm_rigify
    state = self.rtm_ikfk_state
    
    if self.rtm_ikfk_mode == 'IK':
        if self.rtm_ikfk_state.prev_mode == 'RIG':
            save_ikfk_state(rig, state)
        
        set_ik_state(rig)
        self.rtm_ikfk_state.prev_mode = 'IK'
        
    elif self.rtm_ikfk_mode == 'FK':
        if self.rtm_ikfk_state.prev_mode == 'RIG':
            save_ikfk_state(rig, state)
            
        set_fk_state(rig)
        self.rtm_ikfk_state.prev_mode = 'FK'
        
    else:
        load_ikfk_state(rig, state)
        self.rtm_ikfk_state.prev_mode = 'RIG'
        

# -------------------------------------------------------
# Registration
# -------------------------------------------------------

classes = (
    RTM_OT_retarget,
    RTM_OT_untarget,
    RTM_OT_bake_fk,
    RTM_PT_panel,
    RTM_PG_ikfk_state,
)


# Properties are stored at the Scene level, meaning we only support
# using one Rigify rig per scene at a time. Swapping between Rigify
# rigs with stuff active on one in the same scene isn't properly supported.
def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.rtm_mixamo = bpy.props.PointerProperty(
        name="Mixamo Rig",
        type=bpy.types.Object,
        poll=armature_poll,
        update=mixamo_armature_update
    )
    
    bpy.types.Scene.rtm_mixamo_action = bpy.props.PointerProperty(
        name="Mixamo Animation",
        type=bpy.types.Action,
        poll=action_poll
    )

    bpy.types.Scene.rtm_rigify = bpy.props.PointerProperty(
        name="Rigify Rig",
        type=bpy.types.Object,
        poll=armature_poll
    )
    
    bpy.types.Scene.rtm_rigify_action = bpy.props.PointerProperty(
        name="Rigify Animation",
        type=bpy.types.Action,
        poll=action_poll
    )
    
    bpy.types.Scene.rtm_enabled = bpy.props.BoolProperty(
        name="Retarget",
        description="Enable/Disable retargeting constraints",
        default=False,
        update=rtm_toggle_update
    )
    
    bpy.types.Scene.rtm_ikfk_state = bpy.props.PointerProperty(
        type=RTM_PG_ikfk_state
    )
    
    bpy.types.Scene.rtm_ikfk_mode = bpy.props.EnumProperty(
        name="Rigify IK / FK Mode",
        description="Rigify limb solving mode (convinence function to swap all limb modes)",
        items=rtm_ikfk_modes(),
        default='RIG',
        update=rtm_ikfk_mode_update,
    )
    

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    # Remove props
    del bpy.types.Scene.rtm_mixamo
    del bpy.types.Scene.rtm_mixamo_action
    del bpy.types.Scene.rtm_rigify
    del bpy.types.Scene.rtm_rigify_action
    del bpy.types.Scene.rtm_ikfk_state
    del bpy.types.Scene.rtm_ikfk_mode


if __name__ == "__main__":
    register()
