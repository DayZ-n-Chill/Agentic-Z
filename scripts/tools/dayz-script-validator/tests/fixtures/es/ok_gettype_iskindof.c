class GettypeIsKindOfFixture
{
    bool CanUseTool(ItemBase itemInHands)
    {
        string kindHatchet = "Hatchet";
        if (!itemInHands.IsKindOf(kindHatchet))
            return false;
        return true;
    }
}
