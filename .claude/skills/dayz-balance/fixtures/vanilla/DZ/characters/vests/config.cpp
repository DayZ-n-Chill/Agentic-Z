// Test fixture: vests. Values are made up.
class CfgPatches
{
    class DZ_Characters_Vests
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgVehicles
{
    class Clothing;
    class Vest_Base: Clothing
    {
        scope = 0;
    };
    class PlateVest: Vest_Base
    {
        scope = 2;
        weight = 10000;
        itemsCargoSize[] = {0, 0};
        class DamageSystem
        {
            class GlobalHealth
            {
                class Health { hitpoints = 200; };
            };
            class GlobalArmor
            {
                class Projectile
                {
                    class Health { damage = 0.3; };
                    class Blood { damage = 0; };
                    class Shock { damage = 0.6; };
                };
                class Melee
                {
                    class Health { damage = 0.4; };
                };
            };
        };
    };
    class PlateVest_Black: PlateVest
    {
        scope = 2;
    };
    class PlateVest_Green: PlateVest
    {
        scope = 2;
        weight = 10500;
    };
    class PressVest: Vest_Base
    {
        scope = 2;
        weight = 2000;
        class DamageSystem
        {
            class GlobalHealth
            {
                class Health { hitpoints = 120; };
            };
            class GlobalArmor
            {
                class Projectile
                {
                    class Health { damage = 0.8; };
                };
            };
        };
    };
};
