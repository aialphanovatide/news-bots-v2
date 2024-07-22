from playwright.sync_api import sync_playwright

from playwright.sync_api import sync_playwright
import time

def resolve_redirects_playwright(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        page.goto(url)
        time.sleep(4)

        page.evaluate("""
            navigator.clipboard.writeText(window.location.href).then(function() {
                console.log('URL ok');
            }, function(err) {
                console.error('Error: ', err);
            });
        """)

        time.sleep(1)

        # Obtener la URL actual
        final_url = page.url

        browser.close()
        return final_url

# # Ejemplo de uso
# input_url = 'https://news.google.com/articles/CBMidmh0dHBzOi8vd3d3LmNvaW5kZXNrLmNvbS9idXNpbmVzcy8yMDI0LzA3LzIyL3N3YW4tYml0Y29pbi1kcm9wcy1pcG8tcGxhbi1jdXRzLXN0YWZmLWFuZC13aWxsLXNodXQtbWFuYWdlZC1taW5pbmctdW5pdC_SAXpodHRwczovL3d3dy5jb2luZGVzay5jb20vYnVzaW5lc3MvMjAyNC8wNy8yMi9zd2FuLWJpdGNvaW4tZHJvcHMtaXBvLXBsYW4tY3V0cy1zdGFmZi1hbmQtd2lsbC1zaHV0LW1hbmFnZWQtbWluaW5nLXVuaXQvYW1wLw?hl=en-US&gl=US&ceid=US%3Aen'
# resolved_url = resolve_redirects_playwright(input_url)
# print(f"Resolved URL: {resolved_url}")

