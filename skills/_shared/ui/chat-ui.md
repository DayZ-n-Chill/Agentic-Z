# Chat UI

How a production mod replaces the vanilla chat: measuring text before placing it, a ring of reused line widgets, pausing fades while the chat is open, scrolling, and replacing the chat input without breaking it.

The patterns come from a large production group and map mod; `My*` names are its helper classes and are not vanilla. The vanilla calls are cited.

## Measuring text before placing it

A `TextWidget` does not wrap. To wrap chat by hand, keep one hidden text widget, set the text and size, force a layout pass, and read its width. `SetTextExactSize` is at `P:\scripts\1_core\proto\enwidgets.c:193` and `Update()` at `:164`:

```c
class MyMod_TextMeasure
{
    protected TextWidget m_Probe; // created once, off screen

    float GetTextLength(string text, int size)
    {
        m_Probe.SetTextExactSize(size);
        m_Probe.SetText(text);
        m_Probe.Update();
        float width, height;
        m_Probe.GetScreenSize(width, height);
        return width / screenWidth; // a fraction of the screen
    }
}
```

Split a message into words and add words to a line until the measured width passes the maximum, then start the next line. Or use a `MultilineTextWidget` with `wrap 1`. Vanilla doesn't measure at all: `Chat.Add` cuts a message by character count, `ChatMaxUserLength` for players and `ChatMaxSystemLength` for system and BattlEye messages, and adds each piece as its own line (`P:\scripts\5_mission\gui\chat\chat.c:68` to `:125`). It also drops a message when the player turned off that channel group in the game options (`:76` to `:98`).

## A ring of reused lines

Vanilla already works this way: `Chat` creates `LINE_COUNT = 12` `ChatLine` objects in `Init` and `AddInternal` reuses them in a ring (`P:\scripts\5_mission\gui\chat\chat.c:16`, `:47` and `:127` to `:144`). Each `ChatLine` loads `day_z_chat_item.layout`, fades out after `FADE_TIMEOUT = 30` seconds over `FADE_OUT_DURATION = 3` (`P:\scripts\5_mission\gui\chat\chatline.c:4`, `:5` and `:25`). The group mod raises the pool to 100 widgets created once, showing 12. A new message takes the next slot and every line moves to its place:

```c
const int LINE_COUNT = 100;
const int VISIBLE_LINES_COUNT = 12;
int m_LastLine = 0;

void AddInternal(ChatMessageEventParams params)
{
    m_LastLine = (m_LastLine + 1) % m_Lines.Count();
    ChatLine line = m_Lines.Get(m_LastLine);
    line.Set(params);
    for (int i = 0; i < m_Lines.Count(); i++)
    {
        line = m_Lines.Get((m_LastLine + 1 + i) % LINE_COUNT);
        line.m_RootWidget.SetPos(0, i * m_LineHeight);
    }
}
```

While the chat input is open, pause every line's fade and timeout timers and show them all; resume the timers when it closes. In vanilla `ChatLine` both timers are `private` (`chatline.c:20` and `:21`), so this needs the mod's own line class:

```c
void OnChatMenuOpened()
{
    foreach (ChatLine line : m_Lines)
    {
        line.m_FadeTimer.Pause();
        line.m_TimeoutTimer.Pause();
        line.m_RootWidget.Show(true);
    }
}

void OnChatMenuClosed()
{
    foreach (ChatLine line : m_Lines)
    {
        line.m_FadeTimer.Continue();
        line.m_TimeoutTimer.Continue();
    }
}
```

## Scrolling

`ScrollWidget` scrolls by steps or to a position from 0 (top) to 1 (bottom): `GetVScrollPos01`, `VScrollStep(int steps)`, `VScrollToPos01(float pos01)` and `VScrollToWidget(Widget child)` (`P:\scripts\1_core\proto\enwidgets.c:497` to `:501`). The chat reads the position upside down and clamps it to the share of lines that hold messages:

```c
void OnMouseWheel(int count)
{
    float max = Math.Clamp(addedMessages / LINE_COUNT, 0, 1.0);
    rootPositionWidget.VScrollStep(count); // positive scrolls down
    float pos = 1.0 - rootPositionWidget.GetVScrollPos01();
    if (pos > max)
        rootPositionWidget.VScrollToPos01(1.0 - max);
}
```

## Text outline and shadow

`SetOutline(int outlineSize, int argb)`, `SetShadow(int shadowSize, int shadowARGB, float shadowOpacity, float shadowOffsetX, float shadowOffsetY)` and their getters are at `enwidgets.c:196` to `:201`. The chat sets them from the player's settings:

```c
textWidget.SetTextExactSize(14);
textWidget.SetShadow(1, ARGB(255, 0, 0, 0), 0.8);
textWidget.SetOutline(1, ARGB(200, 0, 0, 0));
int shadowSize = textWidget.GetShadowSize();
```

## Replacing the chat input

To swap the vanilla chat input layout and keep its API, call `super.Init()` first, then unlink what it built and load your own:

```c
modded class ChatInputMenu
{
    override Widget Init()
    {
        Widget old = super.Init();
        old.Unlink();
        layoutRoot = MyLayoutManager.Get().CreateLayout("ChatInput");
        m_edit_box = EditBoxWidget.Cast(layoutRoot.FindAnyWidget("InputEditBoxWidget"));
        return layoutRoot;
    }

    EditBoxWidget GetEditBox()
    {
        return m_edit_box;
    }
}
```

`m_edit_box` is `private` in vanilla (`P:\scripts\5_mission\gui\chat\chatinputmenu.c:3`) and vanilla has no `GetEditBox()`; the getter above is the mod's own. That a modded class can read the private field is not checked on `P:\`; no vanilla script shows it.

`super.Init()` has to run because it sets fields the menu needs later, such as `m_BackInputWrapper` (`P:\scripts\5_mission\gui\chat\chatinputmenu.c:5`, set at `:15`); skip it and the menu hits a null reference.

The vanilla menu gets `OnChange` from its own edit box without `SetHandler`, because a `UIScriptedMenu` receives the events of its layout; it sends on `finished` (`chatinputmenu.c:29` to `:40`). A separate handler object gets the events only after `SetHandler` on the edit box:

```c
class MyMod_ChatEventHandler : ScriptedWidgetEventHandler
{
    EditBoxWidget m_edit_box;
    ChatInputMenu chatMenu;

    void MyMod_ChatEventHandler(ChatInputMenu menu)
    {
        chatMenu = menu;
        m_edit_box = menu.GetEditBox();
        m_edit_box.SetHandler(this);
    }

    override bool OnChange(Widget w, int x, int y, bool finished)
    {
        if (!finished)
            return false; // still typing
        SendChatMessage(m_edit_box.GetText());
        return true;
    }
}
```

`finished` is true when the player presses Enter and false on every other key; vanilla returns early on `!finished` (`chatinputmenu.c:33`), and the Enter part is not checked on `P:\`.

## Moving the chat

`Widget.AddChild(Widget child, bool immedUpdate = true)` (`enwidgets.c:161`) moves a widget, children and all, to a new parent. The group mod uses it to switch the chat between the vanilla root and a root the player can position:

```c
if (!atDefault)
    customParent.AddChild(chatWidget);
else
    vanillaRoot.AddChild(chatWidget);
```
