// Test fixture: masks. They sit right under Clothing with backpacks, so only the
// Mask slot tells them apart. Values are made up.
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
    class BandanaMask: Clothing
    {
        scope = 2;
        inventorySlot = "Mask";
        class Protection { biological = 0.25; };
    };
};
