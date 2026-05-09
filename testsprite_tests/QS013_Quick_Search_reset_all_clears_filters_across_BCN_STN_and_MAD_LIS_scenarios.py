import asyncio
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",         # Set the browser window size
                "--disable-dev-shm-usage",        # Avoid using /dev/shm which can cause issues in containers
                "--ipc=host",                     # Use host-level IPC for better stability
                "--single-process"                # Run the browser in a single process mode
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        context.set_default_timeout(5000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> Navigate to http://localhost:3000
        await page.goto("http://localhost:3000")
        
        # -> Navigate to /login and wait for the login page to render (observe input[name="origin_iata"], input[name="destination_iata"], and [data-ui="qs-filter-console"] availability after proceeding to /quick-search).
        await page.goto("http://localhost:3000/login")
        
        # -> Fill email and password on the login form, submit, then navigate to /quick-search and wait for input[name="origin_iata"], input[name="destination_iata"], and [data-ui="qs-filter-console"] to be present.
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/div/div/main/section/form/label/input').nth(0)
        await asyncio.sleep(3); await elem.fill('user@viru.local')
        
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/div/div/main/section/form/label[2]/input').nth(0)
        await asyncio.sleep(3); await elem.fill('ViruUser123')
        
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/main/section/form/button').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # -> Click the Sign in button to authenticate, then navigate to /quick-search and wait for the origin/destination inputs and filter console to appear.
        await page.goto("http://localhost:3000/quick-search")
        
        # -> Set route to BCN → STN by updating origin and destination inputs, then open the date picker to choose a future outbound date.
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/div/div/label/div/input').nth(0)
        await asyncio.sleep(3); await elem.fill('BCN')
        
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/div/div[3]/label/div/input').nth(0)
        await asyncio.sleep(3); await elem.fill('STN')
        
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/div[3]/label/div/button').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # -> Select a future outbound date (pick 1 May 2026) so we can enable filters next.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/div[3]/label/div/div/div[3]/button[33]').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # -> Enable the four guided-console filters (Cobertura, Tiempo y viabilidad, Resultados visibles, Escalas y exclusiones) and then change the route to MAD → LIS (without navigating away) so the UI shows unapplied/pending changes.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/section/div[2]/button').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/section/div[2]/button[2]').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/section/div[2]/button[3]').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # --> Assertions to verify final state
        frame = context.pages[-1]
        assert await frame.locator("xpath=//*[contains(., 'Active filters')]").nth(0).is_visible(), "The filter count and active chips should be visible after enabling filters.",
        assert await frame.locator("xpath=//*[contains(., 'Pending changes')]").nth(0).is_visible(), "The console should indicate pending changes after changing the route without applying filters.",
        assert await frame.locator("xpath=//*[contains(., 'No extra filters')]").nth(0).is_visible(), "The console should return to the no-extra-filters copy after clicking reset-all."]}
        
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    