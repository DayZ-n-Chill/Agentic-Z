// Test fixture: a mod with planted outliers next to items that match vanilla.
class CfgPatches
{
    class BalanceMod
    {
        units[] = {"BalanceMod_HeavyPlate", "BalanceMod_FairPress", "BalanceMod_HugePack", "BalanceMod_Flask"};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data", "DZ_Characters_Vests", "DZ_Characters_Backpacks", "DZ_Gear_Drinks", "DZ_Weapons_Projectiles"};
    };
};
class CfgVehicles
{
    class PlateVest;
    class PressVest;
    class Backpack_Base;
    class Bottle_Base;
    class Inventory_Base;
    // A mod base class between the items and vanilla: peers still come from PlateVest.
    class BalanceMod_PlateBase: PlateVest
    {
        scope = 0;
        weight = 9800;
    };
    class BalanceMod_HeavyPlate: BalanceMod_PlateBase
    {
        scope = 2;
        class DamageSystem
        {
            class GlobalHealth
            {
                class Health { hitpoints = 5000; };
            };
            class GlobalArmor
            {
                class Projectile
                {
                    class Health { damage = 0.01; };
                };
            };
        };
    };
    class BalanceMod_FairPress: PressVest
    {
        scope = 2;
        weight = 2100;
    };
    class BalanceMod_HugePack: Backpack_Base
    {
        scope = 2;
        weight = 1500;
        itemsCargoSize[] = {10, 10};
    };
    class BalanceMod_Flask: Bottle_Base
    {
        scope = 2;
        weight = 200;
        varQuantityMax = 9000;
    };
    // Inherits everything: nothing the mod sets, so nothing to compare.
    class BalanceMod_PlainPlate: PlateVest
    {
        scope = 2;
    };
    // No vanilla parent in the fixture data.
    class BalanceMod_Gadget: BalanceMod_Unknown
    {
        scope = 2;
        weight = 50;
    };
};
class CfgAmmo
{
    class Bullet_Base;
    class BalanceMod_Bullet_Hot: Bullet_Base
    {
        class DamageApplied
        {
            class Health { damage = 400; };
            class Shock { damage = 45; };
        };
    };
};
