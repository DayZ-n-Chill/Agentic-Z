#define DT_FIRE_ARM DamageType.FIRE_ARM

class MyVehicleDamage
{
    void ApplyHit(EntityAI hit, int zone, string ammo, vector pos)
    {
        hit.ProcessDirectDamage(DT_FIRE_ARM, this, zone, ammo, pos);
    }
}
