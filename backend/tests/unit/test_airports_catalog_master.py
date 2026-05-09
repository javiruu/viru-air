import unittest
import unicodedata

from app.infrastructure.airports_catalog import expand_side, resolve_seed_airport


class AirportsCatalogMasterTests(unittest.TestCase):
    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
        return without_marks.casefold()

    def test_resolve_seed_ok(self):
        airport = resolve_seed_airport("LEI")
        self.assertEqual(airport.iata, "LEI")
        self.assertEqual(self._normalize_text(airport.city), "almeria")

    def test_resolve_seed_missing(self):
        with self.assertRaises(ValueError):
            resolve_seed_airport("ZZZ")

    def test_expand_side_includes_seed_without_nearby(self):
        candidates = expand_side("LEI", include_nearby=False, radius_km=200, max_candidates=6)
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0].expanded_iata, "LEI")
        self.assertTrue(candidates[0].is_seed)

    def test_expand_side_with_nearby_and_limit(self):
        candidates = expand_side("LEI", include_nearby=True, radius_km=250, max_candidates=3)
        self.assertLessEqual(len(candidates), 3)
        self.assertEqual(candidates[0].expanded_iata, "LEI")
        self.assertTrue(any(c.expanded_iata != "LEI" for c in candidates))

    def test_expand_side_exclusions(self):
        candidates = expand_side(
            "LEI",
            include_nearby=True,
            radius_km=250,
            max_candidates=6,
            exclusions=["AGP", "ALC"],
        )
        codes = {c.expanded_iata for c in candidates}
        self.assertNotIn("AGP", codes)
        self.assertNotIn("ALC", codes)


if __name__ == "__main__":
    unittest.main()
