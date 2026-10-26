// Test fixture: melee hits, which vanilla puts under Bullet_Base. Values are made up.
class CfgPatches
{
    class DZ_Weapons_Melee
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgAmmo
{
    class Bullet_Base;
    class MeleeDamage: Bullet_Base
    {
        class DamageApplied
        {
            class Health { damage = 5; };
        };
    };
    class MeleeKnife: MeleeDamage
    {
        class DamageApplied
        {
            class Health { damage = 15; };
        };
    };
    class FinisherHit: MeleeDamage
    {
        class DamageApplied
        {
            class Health { damage = 1000; };
        };
    };
};
