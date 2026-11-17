class FX_OnMouseLeavePage
{
    bool OnMouseLeave(Widget w, int x, int y)
    {
        return false;
    }
}

class FX_OnMouseLeaveHost extends ScriptedWidgetEventHandler
{
    ref FX_OnMouseLeavePage m_Page;

    override bool OnMouseLeave(Widget w, Widget enterW, int x, int y)
    {
        return m_Page.OnMouseLeave(w, x, y);
    }
}
