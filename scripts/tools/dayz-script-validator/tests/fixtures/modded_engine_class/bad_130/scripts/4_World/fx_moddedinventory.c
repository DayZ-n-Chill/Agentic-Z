// DayZDiag 1.30.164200, server script log:
//   Engine class 'DayZPlayerInventory' cannot be modded.
//   Engine class 'Magazine' cannot be modded.
//   Can't compile "World" script module!
// The two modded classes sit on lines 7 and 15.

modded class DayZPlayerInventory
{
    override bool ValidateInventoryCommandServer(ParamsReadContext ctx)
    {
        return super.ValidateInventoryCommandServer(ctx);
    }
}

modded class Magazine
{
    override void CombineItems(ItemBase other_item, bool use_stack_max = false)
    {
        super.CombineItems(other_item, use_stack_max);
    }
}
