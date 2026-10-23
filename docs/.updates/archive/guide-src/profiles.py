import pathlib
p = pathlib.Path(__file__).parent / 'make_guide.py'
t = p.read_text(encoding='utf-8')

P = [
 ('dayz-persistence-specialist', 'Script lead (the release audit goes to the server lead)',
  'Makes modded items and systems keep their data across server restarts. It writes the save and load code (OnStoreSave and OnStoreLoad), stamps every save with a version number, and writes the upgrade path so old saves still load after the mod changes. It covers base building parts that must survive restarts, and before release it runs a data audit that checks every saved field is written and read back in the same order.',
  'Make my safe keep its code and contents after a restart, and do not break saves from the last version.',
  'Save and load code with a version number, a migration note for old saves, and an audit report for the server lead.'),
 ('dayz-vehicle-specialist', 'Config lead',
  'Builds cars, boats and helicopters. It sets up the vehicle class and its simulation (engine, gearbox, axles, wheels), the parts that attach to it (doors, hood, trunk, wheels, battery, spark plug), its fluids (fuel, oil, coolant, brake fluid), seats and crew positions, and how it takes damage. Helicopters are not in vanilla DayZ, so it builds them on the vanilla vehicle classes with the user\'s own code, never copied from another mod.',
  'Add a four door pickup with its own doors and a bigger fuel tank.',
  'CfgVehicles entries, the CarScript or BoatScript class, attachment slots, and a types.xml entry for the server lead.'),
 ('dayz-weapon-specialist', 'Config lead',
  'Builds firearms and everything that goes with them: the weapon class, magazines, ammunition, attachment slots for optics, suppressors, stocks and handguards, recoil, fire modes and muzzle effects. It inherits from the closest vanilla weapon so reloading, jamming and damage behave like the base game.',
  'Add a scoped hunting rifle that takes a five round magazine and the vanilla long range optics.',
  'CfgWeapons, CfgMagazines and CfgAmmo entries, a recoil class, and a list of the model selections the art lead must provide.'),
 ('dayz-wearables-specialist', 'Art lead',
  'Builds clothing, gear and characters: which inventory slot an item uses, how many slots it holds, its protection and insulation, the hidden selections that let one model carry several textures, and how it shows on the character through proxies. It covers new survivor characters too.',
  'Make a plate carrier with three colors that fits the vest slot and holds six items.',
  'Config entries, hidden selection names, texture slots for each color, and proxy notes for the Object Builder specialist.'),
 ('dayz-animation-specialist', 'Art lead',
  'Makes things move: doors, lids, hatches, triggers and moving parts. It writes the skeleton and animations in model.cfg (rotations, movements and hiding parts), handles .rtm animation files, and writes the handoff for models built in Blender so bones and selections line up when they reach Object Builder.',
  'Make the doors on my bunker open and close when a player uses them.',
  'model.cfg entries, the selection and bone names the model needs, and the script hook that plays the animation.'),
 ('dayz-audio-fx-specialist', 'Any lead that needs it',
  'Handles sound and visual effects: sound shaders and sound sets, how far a sound carries and how loud it is, and particle effects such as smoke, sparks and muzzle flashes. It builds on the /dayz-particles skill for particle files.',
  'Give my generator a running sound that fades with distance and a puff of exhaust smoke.',
  'CfgSoundShaders and CfgSoundSets entries, particle files, and the script lines that play them.'),
 ('dayz-physics-specialist', 'Any lead that needs it',
  'Makes objects behave physically: their weight, collision shapes in the Geometry and Fire Geometry LODs, how they land when dropped or thrown, and how they push against players and vehicles. It catches the common faults, such as items falling through floors or bullets passing through walls.',
  'My crate falls through the floor when I drop it. Fix it.',
  'Geometry and mass fixes for the Object Builder specialist and any config changes for the config lead.'),
 ('dayz-ai-specialist', 'Script lead',
  'Builds behavior for computer controlled characters: infected, animals and human AI such as patrols and guards. It learns the patterns other modders use by studying how they work, then writes the user\'s own version. Nothing is copied from another mod.',
  'Add a patrol of guards that walk a route around my military base and react to gunfire.',
  'Script classes for the behavior, the config the server lead needs to spawn them, and notes on server performance.'),
]

cards = '\n <h3>Each specialist in detail</h3>\n'
for name, lead, what, ask, back in P:
    cards += ''' <div class="tbl"><table><thead><tr><th scope="col" colspan="2"><code>%s</code></th></tr></thead><tbody>
  <tr><th scope="row">What it does</th><td>%s</td></tr>
  <tr><th scope="row">Ask it for</th><td>"%s"</td></tr>
  <tr><th scope="row">Works under</th><td>%s</td></tr>
  <tr><th scope="row">Hands back</th><td>%s</td></tr>
 </tbody></table></div>
''' % (name, what, ask, lead, back)
cards = cards.replace('%', '%%')

anchor = ' <h3>How every specialist\'s knowledge is checked</h3>'
assert anchor in t and 'Each specialist in detail' not in t
t = t.replace(anchor, cards + anchor, 1)
p.write_text(t, encoding='utf-8')
print('ok')
