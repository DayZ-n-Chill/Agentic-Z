# Preview widgets

Which widgets draw a 3D item or player inside the UI, their full script API, and the 1.30 changelog items that script cannot reach. Inventory slots, inspect windows and character creation use them.

`PreviewWidget`, `ItemPreviewWidget` and `PlayerPreviewWidget` are declared in `P:\scripts\3_game\gameplay.c:276` to `:313`, not in `enwidgets.c`. The blocks below are copied from that file.

## PreviewWidget

```c
// P:\scripts\3_game\gameplay.c:276
class PreviewWidget: Widget
{
	proto native void		ApplyToCamera(int cam);

	proto native void		SetModelOrientation(vector vOrientation);
	proto native vector		GetModelOrientation();
	proto native void		SetModelPosition(vector vPos);
	proto native vector		GetModelPosition();
};
```

## ItemPreviewWidget

```c
// P:\scripts\3_game\gameplay.c:286
class ItemPreviewWidget: PreviewWidget
{
	proto native void SetItem(EntityAI object);
	proto native EntityAI GetItem();

	proto native int GetView();
	/**
	* 0 - default boundingbox_min + boundingbox_max + invView
	* 1 - boundingbox_min2 + boundingbox_max2 + invView2
	* 2 - boundingbox_min3 + boundingbox_max3 + invView3
	* ...
	*/
	proto native void SetView(int viewIndex);

	proto native void SetForceFlipEnable(bool enable);
	proto native void SetForceFlip(bool value);
};
```

`SetView` picks which bounding box and view of the item's model frames it. `SetForceFlipEnable` and `SetForceFlip` are new in 1.30 (`ui-changes-1-30.md`). A layout with `ItemPreviewWidgetClass` and a `SetItem` call renders one item with no camera setup.

## PlayerPreviewWidget

```c
// P:\scripts\3_game\gameplay.c:305
class PlayerPreviewWidget: PreviewWidget
{
	proto native void		UpdateItemInHands(EntityAI object);
	proto native void		SetPlayer(DayZPlayer player);
	//proto native void		SetPlayerType(string type);
	proto native DayZPlayer	GetDummyPlayer();

	proto native void		Refresh();
};
```

## What the 1.30 changelog promises and script does not have

- The 1.30 changelog lists "WorldToScreen and ScreenToWorld methods for ItemPreviewWidget and PlayerPreviewWidget classes (T181406)". The three classes above hold only the methods shown, and no `.c` file under `P:\scripts` names `WorldToScreen` or `ScreenToWorld` on a preview widget. Do not call them from a mod.
- The changelog also lists turning off particles attached to items in a preview. No preview class declares a particle method; whether a layout attribute exists for it is not checked on `P:\`.

## Lighting

Previews have their own brightness, `Widget.SetObjectLighting(float)` from 0 to 1, default 1 (`P:\scripts\1_core\proto\enwidgets.c:119`). It is separate from the HUD brightness that `SetLV` sets (`widget-prototypes.md`).
