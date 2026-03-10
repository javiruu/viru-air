import unittest

from app.services.quick_search_expansion import expand_search_sides


class QuickSearchExpansionTests(unittest.TestCase):
    def _expand(self, **kwargs):
        base = dict(
            origin_seed_iata="LEI",
            destination_seed_iata="DUB",
            include_nearby_origins=False,
            include_nearby_destinations=False,
            origin_radius_km=250,
            destination_radius_km=250,
            origin_max_candidates=6,
            destination_max_candidates=6,
            exclude_origins=[],
            exclude_destinations=[],
        )
        base.update(kwargs)
        return expand_search_sides(**base)

    def test_no_nearby_both_sides(self):
        origin, destination = self._expand()
        self.assertEqual([c.expanded_iata for c in origin.candidates], ["LEI"])
        self.assertEqual([c.expanded_iata for c in destination.candidates], ["DUB"])

    def test_nearby_origin_only(self):
        origin, destination = self._expand(include_nearby_origins=True)
        self.assertGreaterEqual(len(origin.candidates), 1)
        self.assertEqual(origin.candidates[0].expanded_iata, "LEI")
        self.assertEqual([c.expanded_iata for c in destination.candidates], ["DUB"])

    def test_nearby_destination_only(self):
        origin, destination = self._expand(include_nearby_destinations=True)
        self.assertEqual([c.expanded_iata for c in origin.candidates], ["LEI"])
        self.assertGreaterEqual(len(destination.candidates), 1)
        self.assertEqual(destination.candidates[0].expanded_iata, "DUB")

    def test_nearby_both_sides(self):
        origin, destination = self._expand(include_nearby_origins=True, include_nearby_destinations=True)
        self.assertEqual(origin.candidates[0].expanded_iata, "LEI")
        self.assertEqual(destination.candidates[0].expanded_iata, "DUB")

    def test_exclusions_side_specific(self):
        origin, destination = self._expand(
            include_nearby_origins=True,
            include_nearby_destinations=True,
            exclude_origins=["AGP"],
            exclude_destinations=["ORK"],
        )
        origin_codes = {c.expanded_iata for c in origin.candidates}
        destination_codes = {c.expanded_iata for c in destination.candidates}
        self.assertNotIn("AGP", origin_codes)
        self.assertNotIn("ORK", destination_codes)

    def test_max_candidates_counts_seed(self):
        origin, _ = self._expand(include_nearby_origins=True, origin_max_candidates=1)
        self.assertEqual(len(origin.candidates), 1)
        self.assertEqual(origin.candidates[0].expanded_iata, "LEI")

    def test_seed_excluded_explicitly_errors(self):
        with self.assertRaises(ValueError):
            self._expand(exclude_origins=["LEI"])


if __name__ == "__main__":
    unittest.main()
