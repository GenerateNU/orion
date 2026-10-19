import { z } from "zod";

// The backend sends ISO 8601 strings. OrionDB `runs` / Penelope times carry an
// offset; cleaned_data / estimated_car_state times are naive, so allow both.
export const DateTimeSchema = z.iso.datetime({ offset: true, local: true });
