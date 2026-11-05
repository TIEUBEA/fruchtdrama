"""« Au fil de l'histoire » : feuilles d'état (changement d'apparence visible à partir d'une scène)."""
import copy, importlib.util, io, os, pathlib, tempfile, unittest

TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_state_sheets', pathlib.Path(__file__).parents[1] / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import board_check, refusal  # noqa: E402  (server.py puts the project on the path)


def script(changes=None):
    cast = [{'id': c, 'name': n, 'appearance': f'{c} fruit', 'voice': 'v', 'image_prompt': f'{c} reference'} for c, n in (('orange', 'Sanguine'), ('kiwi', 'Verte'))]
    who = [['orange'], ['orange', 'kiwi'], ['kiwi'], ['orange']]
    scenes = [{'characters': w, 'meaning': 'm', 'image_prompt': f'scene {i}', 'video_prompt': 'v', 'dialogue': [{'speaker': w[0], 'text': 'Hallo'}]} for i, w in enumerate(who)]
    out = {'title': 'Vendue', 'cover_title': 'QUI A FAIT ÇA ?', 'description': 'Description', 'characters': cast, 'scenes': scenes}
    if changes is not None:
        out['state_changes'] = changes
    return out


TORN = {'from_scene': 2, 'character': 'orange', 'change': 'dos lisse : l’étiquette a été décollée par Verte'}


def make_job(changes=None, quality='normal', sheet=1):
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': 'b', 'characters': [], 'scenes': [], 'candidates': [], 'flow_profile': None,
         'config': {'scene_count': 4, 'provider': 'chatgpt', 'flow_cost': 10, 'language': 'Français (fr-FR)', 'quality': quality}}
    if sheet:
        j['character_sheet'] = sheet
    s.STATE['jobs'].append(j); s.store_script(j, script(changes)); s.schedule(j); return j


def png(color):
    from PIL import Image
    buffer = io.BytesIO(); Image.new('RGB', (64, 128), color).save(buffer, 'PNG'); return buffer.getvalue()


def active():
    return [t for t in s.STATE['tasks'] if t['status'] in ('queued', 'claimed')]


def deliver(j, name, color):
    t = active()[0]; t['status'] = 'claimed'
    (s.job_dir(j) / name).write_bytes(png(color))
    s.accept_task_result(t, {'ok': True, 'file': name}); return t


class ValidationTests(unittest.TestCase):
    ids = ['orange', 'kiwi']

    def test_invalid_entries_are_ignored_never_fatal(self):
        raw = [TORN, {'from_scene': 0, 'character': 'orange', 'change': 'x'}, {'from_scene': 9, 'character': 'orange', 'change': 'x'},
               {'from_scene': 3, 'character': 'banane', 'change': 'x'}, {'from_scene': 3, 'character': 'kiwi', 'change': '  '},
               {'from_scene': True, 'character': 'kiwi', 'change': 'x'}, 'texte', None, dict(TORN),
               {'from_scene': '3', 'character': 'kiwi', 'change': '  manteau   déchiré '}]
        self.assertEqual(s.clean_state_changes(raw, self.ids, 4), [TORN, {'from_scene': 3, 'character': 'kiwi', 'change': 'manteau déchiré'}])
        self.assertEqual(s.clean_state_changes('n’importe quoi', self.ids, 4), [])

    def test_at_most_three_ordered_by_scene(self):
        raw = [{'from_scene': n, 'character': c, 'change': f'c{n}{c}'} for n in (4, 3, 2) for c in self.ids]
        out = s.clean_state_changes(raw, self.ids, 4)
        # The first three received are kept, then ordered by scene.
        self.assertEqual(len(out), 3); self.assertEqual([(x['from_scene'], x['character']) for x in out], [(3, 'orange'), (4, 'orange'), (4, 'kiwi')])

    def test_script_validation_keeps_valid_changes_and_drops_empty_field(self):
        kept = s.validate_script(script([TORN, {'from_scene': 'x'}]), 4)
        self.assertEqual(kept['state_changes'], [TORN])
        self.assertNotIn('state_changes', s.validate_script(script([{'bad': 1}]), 4))
        self.assertNotIn('state_changes', s.validate_script(script(), 4))

    def test_script_prompt_asks_for_optional_changes(self):
        j = {'id': s.uid(), 'selected': {}, 'brief': 'b', 'config': {'scene_count': 4, 'language': 'Français (fr-FR)'}}
        prompt = s.script_prompt(j)
        self.assertIn('state_changes', prompt); self.assertIn('FACULTATIF', prompt); self.assertIn('0 à 3', prompt)


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_normal_quality_draws_the_state_sheet_from_the_cast_sheet(self):
        j = make_job([TORN])
        deliver(j, 'sheet.png', (200, 120, 20))
        t = active()[0]
        self.assertEqual(t['slot'], 'state:0'); self.assertEqual(t['kind'], 'chat_image')
        self.assertEqual(t['payload']['attachments'], [s.asset_url(j, 'sheet.png')])
        self.assertIn('Sanguine (orange)', t['payload']['prompt']); self.assertIn('étiquette a été décollée', t['payload']['prompt'])
        self.assertEqual(j['stage'], 'characters')
        deliver(j, 'state.png', (180, 40, 40))
        self.assertEqual(j['state_sheets'], [{**TORN, 'file': 'state.png'}])
        self.assertEqual(j['stage'], 'images'); self.assertEqual(active()[0]['slot'], 'image:0')

    def test_economy_makes_no_state_sheet(self):
        j = make_job([TORN], quality='economy')
        deliver(j, 'sheet.png', (200, 120, 20))
        self.assertEqual(j['stage'], 'images'); self.assertEqual([t['slot'] for t in active()], ['image:0'])
        self.assertFalse(any(t['slot'].startswith('state:') for t in s.STATE['tasks']))

    def test_boards_from_the_scene_on_attach_the_state_sheet(self):
        j = make_job([TORN])
        deliver(j, 'sheet.png', (200, 120, 20)); deliver(j, 'state.png', (180, 40, 40))
        seen = []
        for i, color in enumerate([(10, 10, 200), (10, 200, 10), (200, 10, 200), (90, 90, 90)]):
            t = active()[0]; self.assertEqual(t['slot'], f'image:{i}')
            seen.append((t['payload']['attachments'], t['payload']['prompt']))
            deliver(j, f'board{i}.png', color)
        sheet, state = s.asset_url(j, 'sheet.png'), s.asset_url(j, 'state.png')
        self.assertEqual(seen[0][0], [sheet], 'scène 1 : avant le changement')
        self.assertNotIn('Changed look', seen[0][1])
        self.assertEqual(seen[1][0], [state], 'scène 2 : la feuille d’état remplace la feuille commune')
        self.assertIn('Sanguine: dos lisse', seen[1][1])
        self.assertEqual(seen[2][0], [sheet], 'scène 3 : personnage absent, feuille commune')
        self.assertEqual(seen[3][0], [state], 'scène 4 : toujours après le changement')

    def test_individual_references_replace_only_the_changed_character(self):
        j = make_job([TORN], sheet=None)
        deliver(j, 'orange.png', (200, 120, 20)); deliver(j, 'kiwi.png', (20, 200, 20))
        t = active()[0]; self.assertEqual(t['slot'], 'state:0'); self.assertEqual(t['payload']['attachments'], [s.asset_url(j, 'orange.png')])
        deliver(j, 'state.png', (180, 40, 40))
        attachments, states = s.scene_references(j, 1)
        self.assertEqual(attachments, [s.asset_url(j, 'state.png'), s.asset_url(j, 'kiwi.png')]); self.assertEqual(len(states), 1)

    def test_without_state_changes_nothing_changes(self):
        j = make_job()
        self.assertNotIn('state_changes', j['script'])
        deliver(j, 'sheet.png', (200, 120, 20))
        t = active()[0]; self.assertEqual(t['slot'], 'image:0'); self.assertEqual(t['payload']['attachments'], [s.asset_url(j, 'sheet.png')])
        self.assertEqual(s.scene_references(j, 3), (s.image_assets(j), []))
        self.assertNotIn('changed_look', board_check.prompt(j))

    def test_no_state_sheet_when_its_boards_are_already_drawn(self):
        j = make_job([TORN]); j['scenes'][1]['image'] = 'b1.png'; j['scenes'][3]['image'] = 'b3.png'
        deliver(j, 'sheet.png', (200, 120, 20))
        self.assertEqual(j['stage'], 'images'); self.assertEqual(active()[0]['slot'], 'image:0')

    def test_copy_of_the_reference_is_rejected(self):
        j = make_job([TORN]); deliver(j, 'sheet.png', (200, 120, 20))
        t = active()[0]; t['status'] = 'claimed'; (s.job_dir(j) / 'copy.png').write_bytes(png((200, 120, 20)))
        with self.assertRaisesRegex(ValueError, 'copie exacte'):
            s.accept_task_result(t, {'ok': True, 'file': 'copy.png'})
        self.assertFalse(j.get('state_sheets'))

    def test_refused_for_good_the_production_goes_on(self):
        self.assertTrue(refusal.applies({'kind': 'chat_image', 'slot': 'state:0'}))
        j = make_job([TORN]); deliver(j, 'sheet.png', (200, 120, 20))
        for _ in range(refusal.MAX_LEVEL + 1):
            t = active()[0]; self.assertEqual(t['slot'], 'state:0'); t['status'] = 'claimed'
            s.accept_task_result(t, {'ok': False, 'error': 'This request violates our content policy', 'error_kind': 'refusal'})
        self.assertEqual(j['state_sheets'][0]['character'], 'orange'); self.assertIn('skipped', j['state_sheets'][0])
        self.assertEqual(j['stage'], 'images'); self.assertEqual(active()[0]['slot'], 'image:0')
        self.assertEqual(s.scene_references(j, 1)[0], [s.asset_url(j, 'sheet.png')])

    def test_redo_state_sheet(self):
        j = make_job([TORN]); deliver(j, 'sheet.png', (200, 120, 20)); deliver(j, 'state.png', (180, 40, 40))
        for t in active():
            t['status'] = 'cancelled'
        s.redo(j, 'state:0', 'étiquette plus visible')
        self.assertEqual(j['stage'], 'characters'); t = active()[0]
        self.assertEqual(t['slot'], 'state:0'); self.assertIn('étiquette plus visible', t['payload']['prompt'])
        self.assertTrue(any(h['slot'] == 'state:0' and h['file'] == 'state.png' for h in j['redo_history']))

    def test_redo_refused_once_a_later_board_uses_it(self):
        j = make_job([TORN]); deliver(j, 'sheet.png', (200, 120, 20)); deliver(j, 'state.png', (180, 40, 40))
        for t in active():
            t['status'] = 'cancelled'
        j['scenes'][3]['image'] = 'b3.png'
        with self.assertRaisesRegex(ValueError, 'Les planches 4'):
            s.redo(j, 'state:0')

    def test_board_check_expects_the_planned_change(self):
        j = make_job([TORN])
        prompt = board_check.prompt(j)
        self.assertIn('changed_look', prompt); self.assertIn('étiquette', prompt)

    def test_language_version_reuses_state_sheets(self):
        j = make_job([TORN]); deliver(j, 'sheet.png', (200, 120, 20)); deliver(j, 'state.png', (180, 40, 40))
        for i in range(4):
            j['scenes'][i]['image'] = f'board{i}.png'
            (s.job_dir(j) / f'board{i}.png').write_bytes(png((i * 40, 10, 10)))
        for t in active():
            t['status'] = 'cancelled'
        nxt = s.make_variant(j, 'language', 'English (en-US)')
        self.assertEqual(nxt['state_sheets'], [{**TORN, 'file': 'state.png'}]); self.assertTrue((s.job_dir(nxt) / 'state.png').is_file())


if __name__ == '__main__':
    unittest.main()
