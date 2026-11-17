class CfgVehicles
{
    class my_base
    {
        attachments[] = {"CarBattery"};
    };
    class my_armed: my_base
    {
        attachments[] += {"my_slot"};
    };
};
