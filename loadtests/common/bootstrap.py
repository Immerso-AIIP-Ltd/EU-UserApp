# This file contains the bootstrap logic for the load tests.

import threading
from locust import events
from locust.contrib.fasthttp import FastHttpSession

from loadtests.common.test_constants import DEFAULT_HEADERS

BOOTSTRAP_LOCK = threading.Lock()
BOOTSTRAPPED = False


@events.test_start.add_listener
def bootstrap_all(environment, **_):
    """
    Master bootstrap function to run before tests begin.
    Currently performs minimal setup as user_app doesn't require
    external data fetching for countries/languages.
    """
    global BOOTSTRAPPED
    with BOOTSTRAP_LOCK:
        if BOOTSTRAPPED:
            return

        session = FastHttpSession(
            environment=environment,
            base_url=environment.host,
            request_event=environment.events.request,
            user=None,
        )

        # Add any future bootstrap logic here
        # For example: fetching test data, warming up caches, etc.

        print("Bootstrap complete (using static constants).")
        BOOTSTRAPPED = True
