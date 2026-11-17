// Inbox e074, DayZDiag 1.30.164289, on the probe this one stands for (its call
// on line 9 too): "Types 'Object' and 'EntityAI' are unrelated" and "Cannot
// convert 'Object' to 'EntityAI' for argument '0' to method 'SetItem'", and
// the World module did not compile.
class FX_Preview
{
    static void Show(FX_ItemPreview preview, Object obj)
    {
        preview.FX_SetItem(obj);
    }
}
