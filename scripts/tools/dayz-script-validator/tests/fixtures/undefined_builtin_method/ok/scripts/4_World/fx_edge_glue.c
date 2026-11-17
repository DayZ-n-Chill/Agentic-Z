class FX_EdgeGlue
{
	vector m_Forward;
	ref array<string> m_Names;
	ref map<string, int> m_Counts;
	ref set<int> m_Seen;

	void Frame(vector right, TStringArray labels, typename kind)
	{
		vector forward = m_Forward;
		forward.Normalize();
		// The fix: the cross product written out.
		vector up = Vector(forward[1] * right[2] - forward[2] * right[1], forward[2] * right[0] - forward[0] * right[2], forward[0] * right[1] - forward[1] * right[0]);
		float d = vector.Dot(up, forward);
		float n = up.Length();
		string s = d.ToString();
		bool flag = n > 0;
		s = flag.ToString();
		int count = m_Names.Count() + m_Counts.Count() + m_Seen.Count() + labels.Count();
		m_Names.Insert(s);
		labels.Insert(s);
		if (m_Counts.Contains(s))
			count = s.Length();
		s = count.ToString() + string.Format("%1", count);
		s = typename.EnumToString(kind, count) + kind.ToString();
		// Members of Class, the implicit root.
		s = m_Names.ClassName();
		// Not judged: a call's result, a member access, an index.
		GetForward().Cross(right);
		this.m_Forward.Cross(right);
		labels[0].Cross(right);
		// The bad call in a comment and in a string.
		// up.Cross(forward);
		string note = "up.Cross(forward)";
	}

	vector GetForward()
	{
		return m_Forward;
	}
}
