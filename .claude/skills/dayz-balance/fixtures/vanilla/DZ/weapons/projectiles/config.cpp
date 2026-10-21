// Test fixture: pistol ammo. Values are made up.
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
};
