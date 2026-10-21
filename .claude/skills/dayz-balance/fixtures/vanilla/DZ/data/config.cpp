// Test fixture: a small stand in for the unpacked vanilla data on P:\DZ\. Values are made up.
class CfgPatches
{
    class DZ_Data
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = {};
    };
};
class CfgVehicles
{
    class HouseNoDestruct;
    class Inventory_Base: HouseNoDestruct
    {
        scope = 0;
        weight = 100;
    };
    class Clothing_Base: Inventory_Base
    {
        scope = 0;
    };
    class Clothing: Clothing_Base
    {
        scope = 0;
    };
    class Bottle_Base: Inventory_Base
    {
        scope = 0;
        varQuantityMax = 1000;
    };
};
class CfgAmmo
{
    class BulletCore;
    class Bullet_Base: BulletCore
    {
        scope = 0;
        class DamageApplied
        {
            class Health { damage = 50; };
            class Blood { damage = 100; };
            class Shock { damage = 50; };
        };
    };
};
