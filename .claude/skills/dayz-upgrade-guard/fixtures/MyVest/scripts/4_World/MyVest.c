// Fixture mod for test_upgrade_guard.py. Each class hits one upgrade guard case.

class MyVest_Base extends Clothing
{
	override bool CanPutInCargo(EntityAI parent)
	{
		return super.CanPutInCargo(parent);
	}
}

modded class ItemBase
{
	override void SetActions()
	{
		super.SetActions();
	}

	override int GetQuickBarBonus()
	{
		return 1;
	}

	override void OnWasAttached(EntityAI parent, int slot_id)
	{
		super.OnWasAttached(parent, slot_id);
	}
}

modded class PlayerBase
{
	override void OnConnect()
	{
		super.OnConnect();
	}
}

class MyVest_Hologram extends Hologram
{
}

class MyVest_Helper : Managed
{
	void Help() {}
}

// Built on another mod's class, not vanilla: skipped.
class MyVest_Module extends CF_ModuleWorld
{
}
