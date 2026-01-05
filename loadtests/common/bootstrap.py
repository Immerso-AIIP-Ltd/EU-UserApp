# This file contains the bootstrap logic for the load tests.

import threading
from locust import events
from locust.contrib.fasthttp import FastHttpSession

from loadtests.common.test_constants import (
    BOOTSTRAP_COUNTRIES_PARAMS,
    BOOTSTRAP_LANGUAGES_PARAMS,
    BOOTSTRAP_TRANSLATIONS_PARAMS,
    COUNTRY_IDS,
    DEFAULT_HEADERS,
    LANGUAGE_CODES,
    LANGUAGE_KEYS,
    TEXT_KEYS,
)

BOOTSTRAP_LOCK = threading.Lock()
BOOTSTRAPPED = False


@events.test_start.add_listener
def bootstrap_all(environment, **_):
    """
    Master bootstrap function to fetch all required data sequentially
    before tests begin.
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

        # NOTE: The User App currently does not have external endpoints for countries/languages.
        # This structure is kept as per requirements, but the actual network calls are skipped 
        # or commented out until such endpoints exist.
        
        # 1. Bootstrap for countries
        # resp_countries = session.get(
        #     "/v1/external/countries/",
        #     params=BOOTSTRAP_COUNTRIES_PARAMS,
        #     headers=DEFAULT_HEADERS,
        #     name="bootstrap/countries",
        # )
        # if resp_countries.ok:
        #     payload = resp_countries.json().get("data", [])
        #     for item in payload:
        #         cid = item.get("id")
        #         if cid:
        #             COUNTRY_IDS.append(cid)

        # 2. Bootstrap for languages
        # ...

        print("Bootstrap complete (using static constants).")
        BOOTSTRAPPED = True
