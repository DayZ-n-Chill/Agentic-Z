// Pipeline inbox fb-20261103-150432-9f93, DayZDiag 1.30.164200 server, on
// the source this one stands for:
//   Undefined function 'vector.Cross'
// and the World module did not compile. The calls sit on lines 13 and 15.
class FX_EdgeGlue
{
	vector m_Forward;

	void Frame(vector right)
	{
		vector forward = m_Forward;
		forward.Normalize();
		vector up = forward.Cross(right);
		up.Normalize();
		right = up.Cross(forward);
	}
}
