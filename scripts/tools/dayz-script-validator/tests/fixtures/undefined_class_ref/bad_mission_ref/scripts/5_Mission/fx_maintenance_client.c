class FX_MaintenanceClient
{
    static bool RequestSort(PlayerBase player, EntityAI source)
    {
        if (!player || !source)
        {
            return false;
        }

        int localResult = FX_SortPlanner.Sort(player, source);
        int sortResult = FX_ExternalStagingSortPlanner.Sort(player, source);
        return sortResult >= 0 && localResult >= 0;
    }
}
