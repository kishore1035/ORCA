// ORCA push notification service worker. Handles real Web Push events so a
// hazard alert can reach the user even with no tab open -- the point of
// this file existing at all. Everything else (the chat UI itself) is not
// cached or served offline here; this worker's only job is push delivery.

self.addEventListener("push", (event) => {
  let payload = { title: "ORCA hazard alert", body: "Conditions may have changed." };
  try {
    if (event.data) payload = event.data.json();
  } catch {
    // Non-JSON push payload -- fall back to the generic message above.
  }
  event.waitUntil(self.registration.showNotification(payload.title, { body: payload.body }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.openWindow("/"));
});
