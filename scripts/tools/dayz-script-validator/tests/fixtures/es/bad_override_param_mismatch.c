class MyAction extends ActionBase
{
    override void OnExecuteServer(ActionData actionData)
    {
        actionData.GetPlayer();
    }
}
