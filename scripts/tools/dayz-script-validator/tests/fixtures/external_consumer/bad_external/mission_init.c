class FX_MissionProbe
{
    bool HasEdge(FX_Graph graph, string nodeId)
    {
        array<int> outgoing = graph.FX_GetOutgoing(nodeId);
        return outgoing.Count() > 0;
    }
}
