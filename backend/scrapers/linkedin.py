"""
LinkedIn scraper con Playwright — Fase 3
Usar siempre cuenta secundaria. NUNCA cuenta principal.
"""

import os
import asyncio
import random
from dotenv import load_dotenv

load_dotenv()

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")


async def scrape_linkedin(search_string: str, max_results: int = 100) -> list[dict]:
    """
    Placeholder — implementar en Fase 3.
    """
    # TODO: Fase 3
    # from playwright.async_api import async_playwright
    # async with async_playwright() as p:
    #     browser = await p.chromium.launch(headless=False)
    #     ...
    print("LinkedIn Playwright scraper — pendiente Fase 3")
    return []


async def _delay():
    """Delay aleatorio 2-5s para simular comportamiento humano."""
    await asyncio.sleep(random.uniform(2, 5))
