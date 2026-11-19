# UI view lifecycle

How shipped mods decide what to bind, release bound collections and singleton views, avoid allocating in update loops, and route many buttons. State, animation and input locking are in `production-patterns.md`.

These are third-party mod patterns built on the Dabs Framework (`../integrations/dabs_framework.md`), not vanilla code.

## What to bind

- Bind lists that change often to an `ObservableCollection`: clear and refill it, and the binding updates the UI.
- Bind a single value only when it changes often, or when the whole view is data driven.
- For a title set once or a rare change, use `FindAnyWidget` with `SetText` or `SetColor` directly; a binding there is overhead with no gain.
- To change one item in a bound list, update that item's widgets instead of rebuilding the list.
- A bound property shows nothing new until its class calls `NotifyPropertyChanged`.

## Releasing collections

When item views in a collection point back at the controller, break the cycle in the item destructor (`dabs-mvc-advanced.md`, section "Collection items and their owner"), and clear the collection when the panel closes, before hiding it. Never wait for the last reference to drop on its own.

```c
void DoClose()
{
    m_IsOpen = false;
    MyMod_SorterController ctrl = MyMod_SorterController.Cast(GetController());
    if (ctrl)
        ctrl.ClearCollections();   // m_TagsList.Clear() runs every item destructor
    GetLayoutRoot().Show(false);
}
```

Call `ClearCollections()` from the controller's destructor as well. To check for a leak, open, close, open and close the panel again, with a `Print` in each destructor.

## Singleton views

A `static ref` instance keeps the view alive for good, so release it by setting it to `null`, never with `delete`, and do the real cleanup in the destructor so it runs however the view ends:

```c
class MyMod_SorterView extends ScriptView
{
    protected static ref MyMod_SorterView s_Instance;

    static void Create()
    {
        if (!s_Instance)
            s_Instance = new MyMod_SorterView();
    }

    static void Release()
    {
        s_Instance = null;   // the destructor runs when the last reference goes
    }

    void ~MyMod_SorterView()
    {
        if (GetGame())
            GetGame().GetInput().ResetGameFocus();
    }
}
```

`ResetGameFocus()` sets the focus counter to 0 (`P:\scripts\3_game\tools\input.c:27`). Check it: release, create again, and confirm the old destructor printed.

## No allocation in update loops

Allocate working arrays and maps once and `Clear()` them before each use:

```c
protected ref array<Object> m_TempObjects = new array<Object>;
protected ref map<string, bool> m_TempValidTypes = new map<string, bool>;

void PruneInvalidEntities(vector pos)
{
    m_TempObjects.Clear();
    m_TempValidTypes.Clear();
    GetGame().GetObjectsAtPosition(pos, 100, m_TempObjects, null);
    foreach (Object obj : m_TempObjects)
    {
        EntityAI ent = EntityAI.Cast(obj);
        if (ent && MyMod_IsValid(ent))
            m_TempValidTypes.Insert(ent.GetType(), true);
    }
}
```

The query is vanilla's `GetObjectsAtPosition` (`P:\scripts\3_game\global\game.c:923`); there is no `GetGame().GetWorld().QueryEntitiesInRange(...)` anywhere under `P:\scripts\`. A `new array` on every call churns the heap; measure with `EnProfiler` when you suspect it (`script-profiling.md`).

## Many buttons

Up to about five buttons, compare the clicked widget against member references in an `if` chain. Past that, register each button once in a `map<Widget, string>` and dispatch on the stored name, so adding a button is one registration and one small handler:

```c
protected ref map<Widget, string> m_ButtonActions = new map<Widget, string>;

protected void RegisterButton(string widgetName, string action)
{
    Widget btn = GetLayoutRoot().FindAnyWidget(widgetName);
    if (btn)
        m_ButtonActions.Insert(btn, action);
}

void OnButtonPress(Widget button)
{
    string action;
    if (!m_ButtonActions.Find(button, action))
        return;
    if (action == "Sort")
        OnSortClicked();
    else if (action == "Save")
        OnSaveClicked();
}
```

Keep each handler small, and null check every widget before it goes into the map.
