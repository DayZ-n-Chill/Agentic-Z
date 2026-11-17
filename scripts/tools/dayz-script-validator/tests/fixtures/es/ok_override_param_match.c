class MyAction extends ActionBase
{
    override void OnExecuteServer(ActionData action_data)
    {
        action_data.GetPlayer();
    }
}
