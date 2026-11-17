class LFTest_OnMouseLeavePage
{
    bool OnMouseLeave(Widget w, int x, int y)
    {
        return false;
    }
}

class LFTest_OnMouseLeaveHost extends ScriptedWidgetEventHandler
{
    ref LFTest_OnMouseLeavePage m_Page;

    override bool OnMouseLeave(Widget w, Widget enterW, int x, int y)
    {
        return m_Page.OnMouseLeave(w, x, y);
    }
}
