class LFTest_OnMouseLeaveOk extends ScriptedWidgetEventHandler
{
    override bool OnMouseLeave(Widget w, Widget enterW, int x, int y)
    {
        return true;
    }

    void ForwardLeave(Widget w, Widget enterW, int x, int y)
    {
        OnMouseLeave(w, enterW, x, y);
    }
}
