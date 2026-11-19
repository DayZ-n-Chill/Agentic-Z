class MyVehicleDamage
{
    void ApplyHit(EntityAI hit, int zone, string ammo, vector pos)
    {
        hit.ProcessDirectDamage(DamageType.FIRE_ARM, this, zone, ammo, pos);
    }
}
