from app.hotels.normalization import HotelNormalizationService


def test_normalize_text_handles_case_accents_punctuation_and_spaces() -> None:
    value = "  HOTEL Sol,  Madrid!!!  "
    assert HotelNormalizationService.normalize_text(value) == "hotel sol madrid"


def test_normalize_text_collapses_tabs_dashes_and_symbols_into_stable_tokens() -> None:
    value = "\tHôtel-Sol & Spa\nMadrid  "
    assert HotelNormalizationService.normalize_text(value) == "hotel sol spa madrid"


def test_normalize_city_and_country_are_stable() -> None:
    assert HotelNormalizationService.normalize_city("Malaga") == "malaga"
    assert HotelNormalizationService.normalize_country_code(" es ") == "ES"


def test_normalize_text_handles_empty_values_without_noise() -> None:
    assert HotelNormalizationService.normalize_text(None) == ""
    assert HotelNormalizationService.normalize_text("   ") == ""
