// Inbox fb-20261006-030019-e074, DayZ 1.30.164014 server, on the source this
// one stands for: "Invalid statement ')'" and "Syntax error" at the
// continuation. The trailing operators sit on lines 10 and 18.
class FX_Window
{
    static const float A = 1.0;

    static float Score(float t)
    {
        if ((t >= A && t < 2.0) ||
            (t >= 3.0 && t < 4.0))
            return -1.0;
        return t;
    }

    static void Drain(int n, bool open)
    {
        while (n > 0 &&
               open)
            n--;
    }
}
