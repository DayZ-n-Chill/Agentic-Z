class MyCraftRecipe extends RecipeBase
{
    override void Init()
    {
        AddIngredient("Rag");
        SetIsCacheable(false);
    }

    void ApplyAreaDamage(EntityAI target, EntityAI source, vector pos)
    {
        target.ProcessIndirectDamage(DamageType.EXPLOSION, source, "", "Grenade_Ammo", pos, 1.0);
    }
}
