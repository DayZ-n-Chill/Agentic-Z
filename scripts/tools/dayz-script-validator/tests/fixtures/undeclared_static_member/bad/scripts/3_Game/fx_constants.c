// A change deleted
// ANIM_SWAP_ENABLED and its siblings from this class while the World module
// still read them, and DayZ refused the World module on the first boot.
class FX_Constants
{
    static const float PUSH_SPEED = 2.5;
    static const int SWAP_DELAY_MS = 150;
}
