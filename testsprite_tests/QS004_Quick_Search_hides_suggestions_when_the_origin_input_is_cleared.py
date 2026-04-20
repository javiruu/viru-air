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
        
        # -> Click the 'Sign in' link to open the login page.
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/main/section/div/div/a').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # -> Open the login page (/login) so I can sign in with user@viru.local / ViruUser123.
        await page.goto("http://localhost:3000/login")
        
        # -> Fill email and password fields with provided credentials and click 'Sign in' to authenticate.
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/main/section/form/label/input').nth(0)
        await asyncio.sleep(3); await elem.fill('user@viru.local')
        
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/main/section/form/label[2]/input').nth(0)
        await asyncio.sleep(3); await elem.fill('ViruUser123')
        
        frame = context.pages[-1]
        # Click element
        elem = frame.locator('xpath=/html/body/main/section/form/button').nth(0)
        await asyncio.sleep(3); await elem.click()
        
        # -> Navigate to /quick-search and load the quick-search page so I can exercise the origin autocomplete.
        await page.goto("http://localhost:3000/quick-search")
        
        # -> Type 'par' into the Origin (IATA) combobox to trigger suggestions, confirm suggestions appear, then clear the field and confirm suggestions are hidden.
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/div/div[2]/main/section/form/div/div/label/div/input').nth(0)
        await asyncio.sleep(3); await elem.fill('par')
        
        # -> Clear the Origin (IATA) combobox (make its value empty) and verify the suggestions dropdown is not visible.
        frame = context.pages[-1]
        # Input text
        elem = frame.locator('xpath=/html/body/div/div[2]/main/section/form/div/div/label/div/input').nth(0)
        await asyncio.sleep(3); await elem.fill('')
        
        # --> Assertions to verify final state
        frame = context.pages[-1]
        assert await frame.locator("xpath=//*[contains(., 'PAR')]").nth(0).is_visible(), "The origin suggestions dropdown should be visible after typing 'par' into the origin IATA input.",
        assert not await frame.locator("xpath=//*[contains(., 'PAR')]").nth(0).is_visible(), "The origin suggestions dropdown should be hidden after clearing the origin IATA input.",
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    