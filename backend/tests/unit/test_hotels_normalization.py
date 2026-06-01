from app.hotels.normalization import HotelNormalizationService


def test_normalize_text_handles_case_accents_punctuation_and_spaces() -> None:
    value = "  HOTEL Sol,  Madrid!!!  "
    assert HotelNormalizationService.normalize_text(value) == "hotel sol madrid"


def test_normalize_city_and_country_are_stable() -> None:
    assert HotelNormalizationService.normalize_city("Malaga") == "malaga"
    assert HotelNormalizationService.normalize_country_code(" es ") == "ES"
