// Test fixture: pistol ammo, a non-lethal round, an explosive, a flare, two inert 40mm
// grenades and a syringe dart. Values are made up. All share Bullet_Base with the pistol
// rounds, as in vanilla, but only the pistol rounds are firearm rounds.
class CfgPatches
{
    class DZ_Weapons_Projectiles
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgAmmo
{
    class Bullet_Base;
    class Bullet_9x19: Bullet_Base
    {
        scope = 1;
        class DamageApplied
        {
            class Health { damage = 60; };
            class Shock { damage = 40; };
        };
    };
    class Bullet_45ACP: Bullet_Base
    {
        scope = 1;
        class DamageApplied
        {
            class Health { damage = 80; };
            class Shock { damage = 55; };
        };
    };
    class Bullet_380: Bullet_Base
    {
        scope = 1;
        class DamageApplied
        {
            class Health { damage = 50; };
            class Shock { damage = 35; };
        };
    };
    class Bullet_Beanbag: Bullet_Base
    {
        scope = 1;
        class DamageApplied
        {
            class Health { damage = 0; };
            class Shock { damage = 100; };
        };
    };
    class Grenade_Test: Bullet_Base
    {
        scope = 1;
        explosive = 1;
        class DamageApplied
        {
            class Health { damage = 999; };
        };
    };
    class Bullet_Flare_Test: Bullet_Base
    {
        scope = 1;
        simulation = "shotIlluminating";
        explosive = 0;
        class DamageApplied
        {
            class Health { damage = 900; };
        };
    };
    class Bullet_40mm_Base: Bullet_Base
    {
        scope = 1;
        class DamageApplied
        {
            class Health { damage = 110; };
        };
    };
    class Bullet_40mm_ChemGas: Bullet_40mm_Base
    {
        caliber = 1;
    };
    class Dart_Syringe: Bullet_Base
    {
        scope = 1;
        class DamageApplied
        {
            class Health { damage = 35; };
        };
    };
};
