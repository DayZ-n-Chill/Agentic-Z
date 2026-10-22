// Test fixture: masks. As in vanilla they sit right under Clothing with the
// backpacks and vests, so only the Mask slot tells them apart. Class names and
// parents are vanilla; values follow P:\DZ\characters\masks\config.cpp.
class CfgPatches
{
    class DZ_Characters_Masks
    {
        units[] = {};
        weapons[] = {};
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgVehicles
{
    class Clothing;
    class GasMask: Clothing
    {
        scope = 2;
        inventorySlot[] = {"Mask"};
        class Protection { biological = 1; };
    };
    class SurgicalMask: Clothing
    {
        scope = 2;
        inventorySlot[] = {"Mask"};
        class Protection { biological = 0.5; };
    };
    class NioshFaceMask: Clothing
    {
        scope = 2;
        inventorySlot[] = {"Mask"};
        class Protection { biological = 0.75; };
    };
    class BalaclavaMask_ColorBase: Clothing
    {
        scope = 0;
        inventorySlot = "Mask";
        class Protection { biological = 0.25; };
    };
    class BalaclavaMask_Black: BalaclavaMask_ColorBase
    {
        scope = 2;
    };
};
