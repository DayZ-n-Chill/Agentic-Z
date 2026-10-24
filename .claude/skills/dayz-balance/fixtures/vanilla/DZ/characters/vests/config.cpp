// Test fixture: vests. Class names and parents are vanilla; values are made up.
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
    class PlateCarrierVest: Clothing
    {
        scope = 2;
        inventorySlot[] = {"Vest"};
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
    class PlateCarrierVest_Black: PlateCarrierVest
    {
        scope = 2;
    };
    class PlateCarrierVest_Green: PlateCarrierVest
    {
        scope = 2;
        weight = 10500;
    };
    class PressVest_ColorBase: Clothing
    {
        scope = 0;
        inventorySlot[] = {"Vest"};
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
    class PressVest_Blue: PressVest_ColorBase
    {
        scope = 2;
    };
};
