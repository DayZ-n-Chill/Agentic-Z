// Inbox fb-20261005-233046-89d1, DayZDiag 1.29.163709, on the file this
// one stands for:
//   Can't compile "Game" script module!
//   lfpg_moddedtransport.c(9): Engine class 'Transport' cannot be modded.
// The modded class sits on line 9 here too.
//
// The fix is a modded class of a script class that derives from Transport
// (CarScript, BoatScript in 4_World).
modded class Transport
{
    override void EEInit()
    {
        super.EEInit();
    }
}
