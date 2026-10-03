import unittest

from fishing_core.dungeon_catalog import CATALOG, dungeon, routes_for


class DungeonCatalogTests(unittest.TestCase):
    def test_catalog_contains_all_consulted_zones_and_specials(self):
        self.assertEqual(len(CATALOG),77)
        self.assertEqual({item['zone'] for item in CATALOG},set(range(1,21)))
        self.assertEqual(len({item['id'] for item in CATALOG}),77)
        self.assertEqual(dungeon('Z5D2')['name'],"Zorul's Gauntlet")
        self.assertTrue(dungeon('Z1D4')['special'])
        self.assertFalse(dungeon('Z7D2')['special'])

    def test_familiar_selects_exact_routes_not_similar_names(self):
        self.assertEqual(routes_for('  bob ')[0]['id'],'Z1D2')
        self.assertEqual(routes_for('Shrump')[0]['id'],'Z1D2')
        self.assertEqual(routes_for('Mer’lan')[0]['id'],'Z1D3')
        self.assertEqual(routes_for('Grampz')[0]['id'],'Z2D2')
        self.assertEqual(routes_for('Bob unknown'),[])
        self.assertEqual(routes_for("Bor'lan"),[])  # Fusión, no captura directa.

    def test_every_route_references_a_real_catalog_dungeon(self):
        from fishing_core.dungeon_catalog import FAMILIARS
        self.assertEqual(len(FAMILIARS),220)
        for name in FAMILIARS:
            self.assertTrue(routes_for(name),name)
            for route in routes_for(name):
                self.assertIn(route,CATALOG)
                self.assertTrue(route['source'].startswith('https://bit-heroes.fandom.com/wiki/Zones'))

    def test_unknown_dungeon_never_defaults_to_a_different_route(self):
        with self.assertRaises(ValueError):dungeon('Z99D1')

    def test_plan_has_finite_limits_and_target_must_belong_to_route(self):
        from fishing_core.dungeon_catalog import farm_plan
        plan=farm_plan('Z1D2','Normal',1,30,'Bob')
        self.assertEqual(plan['runs'],1)
        self.assertEqual(plan['target'],'Bob')
        for args in [('Z1D1','Normal',1,30,'Bob'),('Z1D2','Normal',0,30,''),
                     ('Z1D2','Normal',True,30,''),('Z1D2','Heroic',1,0,''),
                     ('Z1D4','Heroic',1,30,''),('Z1D2','Ancient',1,30,'')]:
            with self.assertRaises(ValueError):farm_plan(*args)


if __name__=='__main__':unittest.main()
