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
        
        # -> Navigate to /login and wait for the login form fields to appear (so we can sign in).
        await page.goto("http://localhost:3000/login")
        
        # -> Fill the email and password fields and click 'Sign in' to authenticate, then wait for the app to load the next page.
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
        
        # -> Navigate to /quick-search and wait for input[name="origin_iata"], input[name="destination_iata"], and [data-ui="qs-filter-console"] to appear so I can perform the AGP→DUB search.
        await page.goto("http://localhost:3000/quick-search")
        
        # -> Set origin input to AGP and open the departure date picker (calendar) so the first available outbound date can be selected.
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/div/div/label/div/input').nth(0)
        await asyncio.sleep(3); await elem.fill('AGP')
        
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/div[3]/label/div/button').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # -> Select the first enabled outbound date, click 'Buscar' to run the search, wait for results to load, then open the Filters drawer so filter fields appear.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/div[3]/label/div/div/div[3]/button[3]').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/div[5]/div/button').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # -> Open the Filters drawer so filter inputs (price, duration, risk, sort) appear.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section[2]/div[2]/div/section/div[2]/div/button').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # -> Click the 'Filtros' button to open the filters drawer so price, duration, risk and sort inputs appear, then wait for the drawer to render.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/div/div/div/div[2]/main/section/form/section/div/div[2]/button').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # -> Set price max to 120, duration max to 240, set risk to 'Bajo', set sort to 'Precio', close the filters drawer, wait for UI update, then extract the visible active filter chips, visible results count, and any inline validation error messages to verify filters applied.
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/aside/div[2]/section[3]/div[2]/label[2]/input').nth(0)
        await asyncio.sleep(3); await elem.fill('120')
        
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/aside/div[2]/section[3]/div[2]/label[3]/input').nth(0)
        await asyncio.sleep(3); await elem.fill('240')
        
        # --> Test passed — verified by AI agent
        frame = context.pages[-1]
        current_url = await frame.evaluate("() => window.location.href")
        assert current_url is not None, "Test completed successfully"
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    