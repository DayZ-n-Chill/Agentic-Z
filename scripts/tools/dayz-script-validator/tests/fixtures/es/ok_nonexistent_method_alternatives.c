class MyCraftRecipe extends RecipeBase
{
    override void Init()
    {
        InsertIngredient(0, "Rag");
        InsertIngredient(1, "WoodenStick");
    }

    void ApplyAreaDamage(EntityAI source, vector pos)
    {
        DamageSystem.ExplosionDamage(source, null, "Grenade_Ammo", pos, DamageType.EXPLOSION);
    }
}
