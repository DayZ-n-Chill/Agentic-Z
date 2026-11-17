// ============================================================================
// LF_UIProbe - source-only client probe for the B19/B20 layout questions.
//
// Loads three first-party fixtures once per mission and reports what the engine
// returns, with no expected value encoded: B20 can only be fixed after both the
// LF and the CRLF continuation are observed in DayZDiag.
//
// Every call argument list stays on ONE physical line. The Enforce compiler in
// DayZDiag 1.29.163451 rejects an argument list split across lines with
// "Expected ',' or ')'" followed by "Syntax error" for the whole file, which
// drops the entire module. Same class as R11g.
// ============================================================================

class LF_UIProbe
{
	protected static const string LAYOUT_LEAF = "LF_UIProbe/gui/layouts/leaf-without-child-block.layout";
	protected static const string LAYOUT_LF = "LF_UIProbe/gui/layouts/continuation-lf.layout";
	protected static const string LAYOUT_CRLF = "LF_UIProbe/gui/layouts/continuation-crlf.layout";

	protected static bool s_Ran;
	protected static Widget s_LeafRoot;
	protected static Widget s_LfRoot;
	protected static Widget s_CrlfRoot;

	static void Run()
	{
		if (s_Ran)
			return;

		s_Ran = true;
		Log("[LF_UI_PROBE_BEGIN]|schema=dayz-ui-probe-v1");
		s_LeafRoot = ProbeLeaf();
		s_LfRoot = ProbeContinuation("continuation-lf", LAYOUT_LF);
		s_CrlfRoot = ProbeContinuation("continuation-crlf", LAYOUT_CRLF);
		Log("[LF_UI_PROBE_END]|schema=dayz-ui-probe-v1");
	}

	protected static Widget ProbeLeaf()
	{
		Widget root = GetGame().GetWorkspace().CreateWidgets(LAYOUT_LEAF);
		if (!root)
		{
			Log("[LF_UI_PROBE_RESULT]|case=leaf-without-child-block|status=load_failed");
			return null;
		}

		Widget leaf = root.FindAnyWidget("LeafButton");
		if (!leaf)
		{
			Log("[LF_UI_PROBE_RESULT]|case=leaf-without-child-block|status=widget_missing");
			return root;
		}

		Log("[LF_UI_PROBE_RESULT]|case=leaf-without-child-block|status=loaded|name=" + leaf.GetName() + "|type=" + leaf.GetTypeName());
		return root;
	}

	protected static Widget ProbeContinuation(string caseId, string layoutPath)
	{
		Widget root = GetGame().GetWorkspace().CreateWidgets(layoutPath);
		if (!root)
		{
			Log("[LF_UI_PROBE_RESULT]|case=" + caseId + "|status=load_failed");
			return null;
		}

		Widget candidate = root.FindAnyWidget("ProbeButton");
		ButtonWidget button = ButtonWidget.Cast(candidate);
		if (!button)
		{
			Log("[LF_UI_PROBE_RESULT]|case=" + caseId + "|status=widget_missing");
			return root;
		}

		// Verified vanilla API: ButtonWidget.GetText(out string) returns void.
		string value;
		button.GetText(value);
		// The delimiters bound the observed value: an empty or whitespace-only
		// result is otherwise indistinguishable from a missing field.
		Log("[LF_UI_PROBE_RESULT]|case=" + caseId + "|status=loaded|len=" + value.Length().ToString() + "|value=<" + value + ">");
		return root;
	}

	static void Cleanup()
	{
		if (s_LeafRoot)
		{
			s_LeafRoot.Unlink();
			s_LeafRoot = null;
		}
		if (s_LfRoot)
		{
			s_LfRoot.Unlink();
			s_LfRoot = null;
		}
		if (s_CrlfRoot)
		{
			s_CrlfRoot.Unlink();
			s_CrlfRoot = null;
		}
		s_Ran = false;
	}

	protected static void Log(string message)
	{
		PrintToRPT(message);
	}
}

modded class MissionGameplay
{
	override void OnInit()
	{
		super.OnInit();

		#ifndef SERVER
		LF_UIProbe.Run();
		#endif
	}

	override void OnMissionFinish()
	{
		#ifndef SERVER
		LF_UIProbe.Cleanup();
		#endif

		super.OnMissionFinish();
	}
}
