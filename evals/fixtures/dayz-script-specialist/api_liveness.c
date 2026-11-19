class ActiveApi
{
    void Run();
}

// class CommentedApi
// {
//     void Run();
// }

#ifdef DEVELOPER
class GuardedApi
{
    void Run();
}
#endif
