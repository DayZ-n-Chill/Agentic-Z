// DayZDiag 1.29: a
// settings class in scripts/4_World with this member made the client refuse
// the module:
//   Variable name 'Debug' already used as type name
// Debug is a vanilla class. The member sits on line 9.
class FX_Settings
{
    int Version = 1;
    bool Debug;
}
