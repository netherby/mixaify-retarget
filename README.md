### Mixaify ###

Mixamo to Rigify animation retargeter (Blender 5).

Usage:

1) Preferably use your target model on Mixamo to export the animations. Having Mixamo target your models proportions will improve bone placement and size accuracy in most cases.

2) Import Mixamo fbx into Blender. Set both rigs to Rest pose. Adjust the scale of the Mixamo rig to closely match your model (if you uploaded your model to Mixamo and then also included it when exporting. You can easily see when they are the same size, as opposed to just having the bones).

3) Locate the "Retarget Mixamo -> Rigify" panel in the "Item" tab (it should be above the Rigify UI). Set Mixamo rig to the one you imported (the action should be auto filled, but if not also pick the animation you want to retarget). Set Rigify rig and either leave the animation blank to create a new animation or select one to be overwritten.

4) Press the Retarget button. Your Rigify rig should now be in FK mode and follow the Mixamo animation (remember to put your rigs into Pose position if you still have them in Rest).

5) Scrub through the animation to make sure it looks good. If you're happy hit the Bake FK button and wait for it to finish.

6) Toggle off Retarget, set your Rigify rig to FK mode and check the animation. I've included a Rigify Mode drop down at the bottom of the panel to allow quickly swapping between IK, FK and what ever settings you previously had.

Retargeting to IK: Use the FK->IK functions in Rigify to convert. I recommend just calculating the IK positions at key frames rather than having it convert every FK key to IK. Firstly it takes ages and secondly the results are rather less than perfect in my experience. It often messes up rotations doing something silly like rotating 368 degrees instead of -3 degrees and there can be jitter in positions when they are keyed on every frame.

Errors:

It only works in Blender 5.

If your FK bone names are not the defaults in Rigify it will not find them. Same is true for Mixamo. It's fast and easy to use because we assume the bone names are the default and you don't have to configure any mapping. Of course you can just edit the bone mapping table at the top of the script if you really want to use different names.

The animations will never be perfectly the same. The joint positions between the rigs are different even for the exact same model. We track the bone end positions and match them, but bend at the Rigify points. So the exact pose cannot be perfectly matched. This is a simple FK solver using bone constraints, we don't do anything super fancy with intermeidate transfer rigs or whatever. So long as your rigs are the same size and have roughly similar bone positions you should get decent results.

Feel free to submit imporvements.
