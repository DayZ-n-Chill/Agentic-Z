class GettypeEqualityFixture
{
    bool CanUseTool(ItemBase itemInHands)
    {
        if (itemInHands.GetType() != "Hatchet")
            return false;
        return true;
    }
}
