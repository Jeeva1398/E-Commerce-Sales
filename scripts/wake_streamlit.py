"""Open the streamlit dashboard in a headless browser so it doesn't go to sleep.

Streamlit Cloud sleeps an app after 12h without a visitor, and a plain http
request doesn't count - the page is a static shell and the app only runs once a
browser opens its websocket. So this loads it properly, and if it's already
asleep, presses the wake button.

    python scripts/wake_streamlit.py https://jeeva-ecom-sales.streamlit.app/
"""

import re
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://jeeva-ecom-sales.streamlit.app/"
WAKE_BUTTON = re.compile("get this app back up", re.I)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(5_000)

        button = page.get_by_role("button", name=WAKE_BUTTON)
        if button.count():
            print("app was asleep, waking it")
            button.first.click()
            # cold start reinstalls requirements, give it time to come back
            page.wait_for_timeout(90_000)
        else:
            print("app was awake")
            # stay long enough for the session to register as a visit
            page.wait_for_timeout(20_000)

        still_asleep = page.get_by_role("button", name=WAKE_BUTTON).count() > 0
        browser.close()

    if still_asleep:
        sys.exit("wake button still showing - app did not come back up")


if __name__ == "__main__":
    main()
