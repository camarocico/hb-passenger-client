# hb-passenger-client

`hb-passenger-client` is a workstation-local launcher for the [Habrok Open OnDemand (OOD) ORCA app](https://portal.hb.hpc.rug.nl/pun/dev/hb-passenger). It lets a user select one `.inp` file and press `Run on Habrok`. The browser opens the authenticated OOD preparation page and transfers the file there. OOD then lets the user choose a resource profile, review the exact input, and explicitly confirm Slurm submission. This client does not submit jobs or store the input file.


## Requirements

-   Python 3.13 or newer and `uv` on the workstation.
-   A browser with access to the Habrok OOD portal and an active OOD sign-in session.
-   The OOD app deployed at the configured preparation URL. For the `portal1` sandbox, this is `https://portal.hb.hpc.rug.nl/pun/dev/hb-passenger/prepare`.


## Run locally

From this repository on the workstation, set the fixed OOD preparation URL and start the server:

```sh
env HB_PASSENGER_OOD_PREPARE_URL='https://portal.hb.hpc.rug.nl/pun/dev/hb-passenger/prepare' \
  uv run python -m src.local_handoff
```

Open `http://127.0.0.1:8765` in the same browser used for OOD. Keep the terminal running while using the page; stop the server with `Ctrl-C`. The first `uv run` may create `.venv` and install the dependencies from `uv.lock`.

Select one ORCA `.inp` file (maximum 10 MiB) and press `Run on Habrok`. Allow the OOD window if the browser blocks pop-ups. Complete the resource selection, input review, and confirmation in that OOD window. The local page will also show a link to the OOD review page once preparation succeeds. A successful transfer or review is not a submitted Slurm job; only OOD's confirmation step submits it.


## Configuration and boundaries

| Environment variable                | Purpose                                                                              |
|----------------------------------- |------------------------------------------------------------------------------------ |
| `HB_PASSENGER_OOD_PREPARE_URL`      | Required, fixed HTTPS URL ending in `/prepare`; use the URL of the deployed OOD app. |
| `HB_PASSENGER_LOCAL_HANDOFF_ORIGIN` | Optional local origin; defaults to `http://127.0.0.1:8765`.                          |

The client binds only to `127.0.0.1` and accepts requests for the configured loopback host and port. Use the numeric `127.0.0.1` URL, not `localhost` or a LAN address. The local origin must match the origin configured in the OOD app; change both if using a different port. The client validates the OOD URL at startup and does not accept a portal URL from a browser request. Do not put credentials or tokens in the URL.

The browser reads the selected file and transfers its bytes to the OOD page. The client server does not receive or persist the file. The OOD app receives it through its authenticated preparation form and stores its review copy according to the portal's workflow. The two applications exchange a one-time browser state value and check message origins; the local server is not itself an SSO endpoint.


## Troubleshooting

-   If the local page returns `Bad Request`, open the numeric `http://127.0.0.1:8765` address and check that the configured local origin uses the same port.
-   If no OOD window opens, allow the pop-up for the local page and press the button again.
-   If the OOD page asks for sign-in or fails to load, check the browser's OOD session and the configured `HB_PASSENGER_OOD_PREPARE_URL`. OOD app initialization and Passenger failures must be resolved on the portal.
-   If the file does not arrive, check that the client and OOD local origins match and that the OOD preparation page loaded its handoff script. The file must end in `.inp` and be no larger than 10 MiB.


## Development

The Flask launcher is in `src/local_handoff.py`; its page and browser script are in `templates/local_handoff.html` and `static/local_handoff.js`. Contract tests are in `tests/test_local_handoff.py`.

```sh
uv run -m pytest
```

These tests cover the local server's URL and host restrictions and the rendered page. They do not prove an end-to-end transfer to a live OOD deployment or a successful Slurm job.
