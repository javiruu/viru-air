from app.hotels.contracts import HotelProviderAdapter, ProviderHotelRecord, ProviderRateRecord
from app.hotels.ingestion import HotelIngestionResult, HotelIngestionService, resolve_hotel_provider
from app.hotels.mapping import HotelMappingResult, HotelMappingService
from app.hotels.normalization import HotelNormalizationService

__all__ = [
    "HotelProviderAdapter",
    "ProviderHotelRecord",
    "ProviderRateRecord",
    "HotelIngestionResult",
    "HotelIngestionService",
    "HotelMappingResult",
    "HotelMappingService",
    "HotelNormalizationService",
    "resolve_hotel_provider",
]

