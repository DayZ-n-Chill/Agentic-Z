class GettypeEnumCompareFixture
{
    bool IsGround(InventoryLocation location)
    {
        return location.GetType() == InventoryLocationType.GROUND;
    }
}
