class WidgetUnlinkFixture
{
    void Cleanup(Widget widget)
    {
        widget.Unlink();
        widget = null;
    }
}
