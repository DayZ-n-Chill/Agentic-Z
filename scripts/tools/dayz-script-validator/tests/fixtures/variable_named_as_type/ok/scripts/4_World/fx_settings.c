// `bool Debug;` in a comment is no declaration.
/* bool Debug; */
class FX_Settings
{
    int Version = 1;
    bool debug;
    bool m_Debug;
    Debug m_Logger;
    ref array<ref Debug> m_Loggers;
    string m_Note = "bool Debug;";

    void Log(string message)
    {
        Debug.Log(message);
        m_Loggers.Insert(new Debug);
        // FX_MissionOnly is a 5_Mission type: 4_World does not see it.
        int FX_MissionOnly = 1;
        // FX_OnlyInAComment is named only inside a vanilla comment.
        int FX_OnlyInAComment = 2;
    }
}

#if 0
class FX_Dead
{
    bool Debug;
}
#endif
