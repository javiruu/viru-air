import type { DoorToDoorPreferences } from "@/modules/door-to-door/types";

export const DEFAULT_PREFERENCES: DoorToDoorPreferences = {
  min_airport_buffer_minutes: 120,
  max_price: 80,
  passengers: 1,
  luggage: "cabin",
  allow_bus: true,
  allow_train: true,
  allow_rideshare: true,
  allow_shuttle: true,
  allow_taxi: false,
  allow_car: true,
  public_transport_only: false,
  sort_by: "best_balance",
};
