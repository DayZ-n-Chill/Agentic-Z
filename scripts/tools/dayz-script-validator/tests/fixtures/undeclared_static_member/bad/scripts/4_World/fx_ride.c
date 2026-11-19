// The deleted const is read on line 9, a deleted static method is called on
// line 11.
class FX_Ride
{
    float m_Speed;

    void Tick()
    {
        if (FX_Constants.ANIM_SWAP_ENABLED)
            m_Speed = FX_Constants.PUSH_SPEED;
        FX_Constants.Reload();
    }
}
