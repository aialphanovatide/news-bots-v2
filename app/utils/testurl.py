from playwright.sync_api import sync_playwright

def resolve_redirects_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Puedes cambiar a p.firefox o p.webkit si prefieres otro navegador
        page = browser.new_page()
        page.goto(url)

        # Esperar hasta que la navegación esté completamente cargada
        page.wait_for_load_state('networkidle')
        
        final_url = page.url
        browser.close()
        return final_url


