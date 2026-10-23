"""Add a workflow for every specialist and an Add-ons section to the guide builder."""
import pathlib
here = pathlib.Path(__file__).parent
p = here / 'make_guide.py'
g = p.read_text(encoding='utf-8')

F = [
 ('Script lead', [
  ('dayz-script-specialist', ['Searches the vanilla scripts for the class it will change and reads the real file.', 'Writes a <code>modded class</code> in the right layer (3_Game, 4_World or 5_Mission) and calls <code>super</code>.', 'Adds RPCs only where client and server must talk, and checks which side runs each line.', 'Build gate compiles it; the in-game gate reads script.log for errors.']),
  ('dayz-workbench-specialist', ['Reads how vanilla Workbench plugins are registered.', 'Writes the plugin script and its tool panel.', 'Opens Workbench with <code>/dayz-launch-workbench</code> to load it.', 'Returns the plugin and how to run it.']),
  ('dayz-persistence-specialist', ['Lists every value that must survive a restart.', 'Writes OnStoreSave and OnStoreLoad, with a version number written first.', 'Adds an upgrade path so saves from the last version still load.', 'Runs the data audit: every field is written and read back in the same order.', 'Hands the audit to the server lead before release.']),
  ('dayz-ai-specialist', ['Studies how vanilla infected and animals decide what to do.', 'Writes the behavior as its own script classes, never copied from another mod.', 'Gives the server lead the spawn setup.', 'In-game test watches the behavior and server performance.']),
 ]),
 ('Config lead', [
  ('dayz-config-specialist', ['Finds the closest vanilla parent class with a RAG search.', 'Writes CfgPatches with the right requiredAddons, then the class itself.', 'Matches hiddenSelections to the names in the model.', '<code>/dayz-lint</code> and the build gate check it loads.']),
  ('dayz-vehicle-specialist', ['Picks the closest vanilla vehicle as the parent.', 'Writes the vehicle class and its simulation: engine, gearbox, axles, wheels.', 'Adds attachment slots for doors, hood, trunk, wheels, battery and plug, and the fluids.', 'Writes the CarScript or BoatScript class for seats, doors and damage.', 'Gives the server lead a types.xml entry; the in-game test spawns and drives it.']),
  ('dayz-weapon-specialist', ['Picks the closest vanilla weapon as the parent.', 'Writes the weapon, magazine and ammo classes and the attachment slots.', 'Sets recoil and fire modes.', 'Lists the model selections and memory points the art lead must provide.', 'In-game test fires, reloads and fits each attachment.']),
 ]),
 ('Art lead', [
  ('dayz-object-builder', ['Sets up the LODs: visual, geometry, fire geometry, view geometry and memory.', 'Names the selections and memory points the config and animations need.', 'Runs <code>/dayz-p3d-audit</code> on the result.', 'Hands the selection names to the config lead.']),
  ('dayz-asset-specialist', ['Checks each texture has the right suffix (_co, _nohq, _smdi and the rest).', 'Packs them with <code>/dayz-pack-texture</code>.', 'Writes the .rvmat for each material.', 'Checks the look in Object Builder or in game.']),
  ('dayz-wearables-specialist', ['Picks the inventory slot and the closest vanilla item as the parent.', 'Sets slots held, protection and insulation.', 'Sets hidden selections so one model carries every color.', 'Notes the proxy positions for the Object Builder specialist.', 'In-game test wears it and checks each color.']),
  ('dayz-animation-specialist', ['Lists the moving parts and their bones.', 'Writes the skeleton and animations in model.cfg.', 'Gives the user the bone and selection names for their own Blender export.', 'Wires the script that plays the animation; the in-game test uses it.']),
 ]),
 ('UI lead', [
  ('dayz-ui-specialist', ['Reads the vanilla layout closest to the new screen.', 'Writes the .layout and the script class that drives it.', 'Builds icons into an imageset with <code>/dayz-build-imageset</code>.', 'The layout checker compares it with the design; the in-game test opens it.']),
  ('figma-node-normalizer', ['Reads the Figma frame.', 'Cleans layer names and structure so they map to DayZ widgets.', 'Hands the clean tree to the layout converter.']),
  ('figma-to-dayz-layout', ['Turns the clean tree into a DayZ .layout.', 'Uses only widget types the game supports.', 'Hands it to the layout checker.']),
 ]),
 ('Server lead', [
  ('dayz-server-admin', ['Writes types.xml entries with <code>/dayz-edit-types</code>.', 'Adds events, spawn points and gameplay settings where needed.', 'Splits large economy files with <code>/dayz-split-types</code>.', 'Starts the test server with <code>/dayz-add-server</code> and <code>/dayz-launch-test</code>.']),
  ('dayz-map-specialist', ['Exports the layout from the DayZ Editor.', 'Imports it into Terrain Builder and sets layers, surfaces and clutter.', 'Returns the files and the steps to rebuild the map.']),
 ]),
 ('Release lead', [
  ('dayz-build-engineer', ['Packs the mod with <code>/dayz-build-pbo</code>.', 'Starts the test session with <code>/dayz-launch-test</code>.', 'Reports the build result to the orchestrator.']),
  ('dayz-docs-writer', ['Reads what changed in the wave.', 'Updates the README, changelog and classname list.', 'With <code>/dayz-release-pack</code>, writes the Workshop text and server-owner notes.']),
 ]),
 ('Any lead', [
  ('dayz-audio-fx-specialist', ['Reads the vanilla sound or particle closest to the request.', 'Writes the sound shader and sound set, or the particle with <code>/dayz-particles</code>.', 'Adds the script line that plays it.', 'In-game test listens and looks.']),
  ('dayz-physics-specialist', ['Reads the model\'s geometry LODs and mass.', 'Finds the fault: missing geometry, wrong mass or bad collision.', 'Hands the fix to the Object Builder or config specialist.', 'In-game test drops, throws and shoots it.']),
 ]),
 ('Checks and fixes', [
  ('dayz-mod-reviewer', ['Reads the finished task against the DayZ rules file.', 'Lists each problem with the specialist who owns it.', 'Never edits files.']),
  ('dayz-layout-validator', ['Compares the .layout with the design.', 'Reports PASS or FAIL with each difference.']),
  ('dayz-build-checker', ['Runs only when <code>/dayz-gate build</code> itself breaks.', 'Reads the AddonBuilder output and names the failing file.']),
  ('dayz-ingame-tester', ['Runs only when <code>/dayz-gate ingame</code> itself breaks.', 'Reads the logs from the test session and reports what failed.']),
  ('dayz-mod-debugger', ['Gets new errors that triage does not know.', 'Reads script.log, RPT and crash files back to the line that failed.', 'Hands the cause and the fix to the owning lead.']),
 ]),
]

rows = ''
for lead, specs in F:
    rows += '   <tr class="grp"><th colspan="2" scope="colgroup">%s</th></tr>\n' % lead
    for name, steps in specs:
        rows += '   <tr><th scope="row"><code>%s</code></th><td><ol class="flow">%s</ol></td></tr>\n' % (name, ''.join('<li>%s</li>' % s for s in steps))

flows = '''<section aria-labelledby="g-spec-flows">
 <h2 id="g-spec-flows">Specialist workflows</h2>
 <p>Every task goes through the same team loop: the user approves the plan, the orchestrator hands tasks to the leads, the leads hand them to specialists, and the gates check the work. Inside that loop each specialist works through its own steps. Every one starts with a RAG search of the vanilla game files and reads the real file before writing anything.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Specialist</th><th scope="col">Its steps inside the loop</th></tr></thead>
  <tbody>
%s  </tbody>
 </table></div>
</section>
''' % rows

addons = '''<section aria-labelledby="g-addons">
 <h2 id="g-addons">Add-ons</h2>
 <p>Agentic-Z needs no third-party tools. Everything in this guide runs on DayZ Tools, the vanilla game files and Claude Code.</p>
 <p>Modders who want other tools, such as Blender, an AI 3D generator or another MCP server, can add them as optional add-ons in a separate plugin. An add-on is a workflow that connects the outside tool at one point in the loop, usually handing a finished model to the Object Builder specialist, and then the normal gates check it like any other work.</p>
 <ul>
  <li><b>Optional:</b> the core never loads an add-on unless the user installs it.</li>
  <li><b>Same gates:</b> anything an add-on produces goes through the mod review, the build check and the in-game test.</li>
  <li><b>No reverse engineering:</b> no add-on unpacks protected mods or turns binarized models back into editable ones.</li>
 </ul>
</section>
'''
flows = flows.replace('%', '%%')
addons = addons.replace('%', '%%')
assert 'g-spec-flows' not in g
# insert both as literal sections right after the specialists section is defined
anchor = 'def grab(html, sid):'
g = g.replace(anchor, 'spec_flows = """%s"""\naddons = """%s"""\n\n' % (flows, addons) + anchor, 1)
p.write_text(g, encoding='utf-8')
print('ok')
