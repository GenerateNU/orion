// Turns a hook's error into something a person can act on.
// apiClient throws "API request failed: <status>" for bad responses, and fetch itself
// throws a TypeError when the backend can't be reached at all.
export function describeError(error) {
  if (error instanceof TypeError) {
    return "Couldn't reach the server. Check that the backend is running.";
  }

  const status = Number(error?.message?.match(/\d{3}/)?.[0]);
  if (status === 404) return "We couldn't find that data.";
  if (status >= 500) return "The server ran into a problem. Try again in a moment.";

  return "Something went wrong while loading data.";
}
