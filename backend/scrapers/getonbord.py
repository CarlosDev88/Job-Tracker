"""
GetOnBord scraper — Fase 3
API REST pública, sin auth.
"""

import httpx

BASE_URL = "https://www.getonbrd.com/api/v0"


async def scrape_getonbord(tags: list[str]) -> list[dict]:
    """
    Scrapa vacantes de GetOnBord por tags.
    tags: ["react-js", "typescript"]
    """
    vacantes = []

    async with httpx.AsyncClient() as client:
        for tag in tags:
            try:
                response = await client.get(
                    f"{BASE_URL}/tags/{tag}/jobs",
                    params={"per_page": 100},
                    timeout=15,
                )
                if response.status_code != 200:
                    continue

                data = response.json()
                jobs = data.get("data", [])

                for job in jobs:
                    attrs = job.get("attributes", {})
                    vacantes.append(
                        {
                            "titulo": attrs.get("title", ""),
                            "empresa": attrs.get("company", {})
                            .get("data", {})
                            .get("attributes", {})
                            .get("name", ""),
                            "ubicacion": attrs.get("country", "Remote"),
                            "descripcion": attrs.get("description", "")
                            + " "
                            + attrs.get("functions", ""),
                            "link": attrs.get("url", ""),
                        }
                    )

            except Exception as e:
                print(f"Error GetOnBord tag '{tag}': {e}")

    # Deduplicar por link
    seen = set()
    unique = []
    for v in vacantes:
        if v["link"] and v["link"] not in seen:
            seen.add(v["link"])
            unique.append(v)

    return unique
