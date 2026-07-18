// billing-snapshot-worker.mjs — oneshot snapshot entry point
// Called by systemd timer; runs snapshot once then exits.

import { snapshot } from "./billing-snapshotter.mjs";

await snapshot();
