# Dabs MVC traps

Which Dabs Framework MVC habits break a view in shipped mods: property notification, creating views, auto binding inside buttons, `Relay_Command` firing twice, collection leaks and a second controller. Floating windows, colours, hover and scaling are in `dabs-floating-windows.md`.

These are patterns met in shipped mods that use the third-party Dabs Framework. They are not checked against the Dabs source; what was read there is in `../integrations/dabs_framework.md`. Full UI work is in the UI pack, `_shared/ui/`.

## The parts

| Part | Role |
|---|---|
| `ViewController` | The data model with bound properties |
| `ScriptView` | View and event handler; builds the widgets from the layout |
| `ViewBinding` (a `scriptclass` in the layout) | Binds a widget to a controller property |
| `Relay_Command` (`ScriptParams` in the layout) | Sends a button click to a controller method |
| `ObservableCollection` | A bound list of `ScriptView` items |
| `Two_Way_Binding` | Binding both ways, such as an edit box and a property |
| `NotifyPropertyChanged` | Tells the UI a controller property changed |

## Property names as string literals

`ctrl.NotifyPropertyChanged("HeaderTitle");` is valid Enforce Script: string literals work as arguments, vanilla passes them everywhere (`RegisterNetSyncVariableBool("m_EM.m_IsSwichedOn")`, `P:\scripts\3_game\entities\entityai.c:218`), and the Dabs integration file calls `NotifyPropertyChanged("FieldName")` the same way. Reported once, not reproduced: the literal failed in one mod. Write the literal, and only if it fails in your build pass a local `string` instead.

## Create views when a workspace exists

`new ScriptView()` calls `CreateWidgets()`, which needs a valid `WorkspaceWidget`. Never create a view inside an RPC handler or during early init; there is no workspace yet and the creation crashes. Create it in `MissionGameplay.OnInit()` and show or hide it later:

```c
override void OnInit()
{
    m_View = new MyMod_SorterView();
}
```

## Auto binding inside a `ButtonWidget`

Auto binding finds widgets by the controller property names. For widgets nested inside a `ButtonWidget`, both auto binding and `FindAnyWidget` can return a wrong reference that is not null. After the view is built, overwrite those bindings by walking the button's children, from an `EnsureBindings()` method:

```c
ImageWidget MyMod_FindButtonImage(Widget root, string buttonName)
{
    Widget button = root.FindAnyWidget(buttonName);
    if (!button)
        return null;
    Widget child = button.GetChildren();
    while (child)
    {
        ImageWidget img = ImageWidget.Cast(child);
        if (img)
            return img;
        child = child.GetSibling();
    }
    return null;
}
```

Write the same walk with `TextWidget.Cast` for the label.

## `Relay_Command` fires twice

`ScriptView.OnClick` already runs the `Relay_Command`. Override `OnClick`, call `super.OnClick()` as well, and the handler runs twice; a toggle such as a tab or a checkbox then cancels itself and seems to do nothing. Handle your own buttons directly and return true, and pass anything else to `super`:

```c
override bool OnClick(Widget w, int x, int y, int button)
{
    if (!m_IsOpen || !w || button != 0)
        return super.OnClick(w, x, y, button);
    Widget check = w;
    ButtonWidget btn;
    while (check && !btn)
    {
        btn = ButtonWidget.Cast(check);
        check = check.GetParent();
    }
    MyMod_SorterController ctrl = MyMod_SorterController.Cast(GetController());
    if (!btn || !ctrl)
        return super.OnClick(w, x, y, button);
    if (btn.GetName() == "TabOut0") { ctrl.TabOut0(); return true; }
    return super.OnClick(w, x, y, button);
}
```

## Collection items and their owner

When an item view in an `ObservableCollection` keeps a reference back to the owning controller, clearing the collection does not break the cycle: controller, list, item view, item controller, back to the controller. Break it in the item's destructor:

```c
void ~MyMod_SorterTagView()
{
    MyMod_SorterTagController ctrl = MyMod_SorterTagController.Cast(GetController());
    if (ctrl)
        ctrl.m_OwnerController = null;
}
```

Items can also lose their parent by the time a callback fires, so `ScriptView.Cast(GetParent())` may be null. Pass the owning controller to the item when you create it (`SetData(..., MyMod_SorterController ownerCtrl)`) and use that reference instead of walking up.

## `scriptclass` on the root widget

If the layout's root widget has `scriptclass "ViewBinding"` and the view's `GetControllerType()` also returns a controller type, two controllers are created. Remove the `scriptclass` line from the root and let `GetControllerType()` create the controller.
