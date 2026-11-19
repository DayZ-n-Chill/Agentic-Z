class MessageLayoutDialog
{
    static const string LOG_TAG = "[FxGroupMod]";

    Widget m_Root;

    void Init()
    {
        m_Root = GetGame().GetWorkspace().CreateWidgets("FxGroupMod/gui/layouts/my_dialog.layout");
        if (!m_Root)
            Print(LOG_TAG + " CreateWidgets failed for my_dialog.layout");
    }
}
