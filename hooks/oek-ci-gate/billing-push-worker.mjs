// billing-push-worker.mjs — oneshot push entry point
// Called by systemd timer; reads daily state and pushes report once then exits.

import { pushReport } from "./billing-snapshotter.mjs";

await pushReport();
