#!/usr/bin/env python
"""Checagem visual do app (spec 017, D4). Roda local; fora do CI e da imagem Docker.

Abre cada URL em 375, 900 e 1280px, nos temas claro e escuro, falha
se `document.documentElement.scrollWidth > window.innerWidth` e salva capturas em
`.visual-check/` (ignorado pelo git).

Uso (servidor local com `python manage.py seed_demo_data` aplicado):

    VISUAL_CHECK_USERNAME=... VISUAL_CHECK_PASSWORD=... \\
        python scripts/visual_check.py [--base-url http://127.0.0.1:8000]

Usuario e senha vem so de variaveis de ambiente (nunca de arquivo nem de argumento).
Depois do login so ha requisicoes GET. Usa o Chrome do sistema (`--channel chrome`);
nao precisa de `playwright install`.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

URLS = [
    "/",
    "/transactions/",
    "/transactions/create/",
    "/transactions/transfers/",
    "/transactions/transfers/create/",
    "/cards/",
    "/cards/create/",
    "/cards/statements/",
    "/imports/upload/page/",
    "/imports/review/page/",
    "/reports/month/",
    "/recurrences/month/page/",
    "/goals/",
    "/goals/monthly/",
    "/insights/page/",
    "/accounts/",
    "/accounts/create/",
    "/categories/",
    "/categories/create/",
    "/institutions/",
    "/institutions/create/",
    "/installments/",
    "/installments/create/",
]
LOGIN_URL = "/login/"
WIDTHS = (375, 900, 1280)
THEMES = ("light", "dark")
HEIGHT = 900


def slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.strip("/").lower()).strip("-") or "inicio"


def measure(page) -> dict:
    return page.evaluate(
        """() => ({
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth,
            dataTheme: document.documentElement.getAttribute("data-theme"),
            font: getComputedStyle(document.body).fontFamily,
            interLoaded: document.fonts.check('16px Inter'),
            background: getComputedStyle(document.body).backgroundColor,
        })"""
    )


def redirected(url: str, landed_path: str) -> bool:
    """True se a pagina terminou em outro caminho. A query string da URL pedida e ignorada."""

    return url != LOGIN_URL and urlparse(url).path != landed_path


def check_page(page, base_url: str, url: str, out_file: Path) -> dict:
    response = page.goto(base_url + url, wait_until="networkidle")
    status = response.status if response else 0
    landed = urlparse(page.url).path
    info = measure(page)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out_file), full_page=True)
    problems = []
    if status != 200:
        problems.append(f"HTTP {status}")
    if redirected(url, landed):
        problems.append(f"redirecionou para {landed}")
    if info["scrollWidth"] > info["innerWidth"]:
        problems.append(f"overflow {info['scrollWidth']}>{info['innerWidth']}")
    return {"url": url, "info": info, "problems": problems}


def run(args) -> int:
    username = os.environ.get("VISUAL_CHECK_USERNAME")
    password = os.environ.get("VISUAL_CHECK_PASSWORD")
    if not username or not password:
        print("Defina VISUAL_CHECK_USERNAME e VISUAL_CHECK_PASSWORD.", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    rows = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel)
        try:
            for theme in args.themes:
                context = browser.new_context(
                    color_scheme=theme,
                    viewport={"width": args.widths[0], "height": HEIGHT},
                )
                # Escolha manual de tema, pelo mesmo localStorage que o app usa.
                context.add_init_script(
                    f"try {{ localStorage.setItem('theme', '{theme}'); }} catch (e) {{}}"
                )
                page = context.new_page()

                for width in args.widths:
                    page.set_viewport_size({"width": width, "height": HEIGHT})
                    folder = out_dir / f"{theme}-{width}"
                    result = check_page(page, args.base_url, LOGIN_URL, folder / "login.png")
                    rows.append((theme, width, result))

                page.goto(args.base_url + LOGIN_URL)
                page.fill('input[name="username"]', username)
                page.fill('input[name="password"]', password)
                with page.expect_navigation():
                    page.click('button[type="submit"], input[type="submit"]')
                if urlparse(page.url).path == LOGIN_URL:
                    print("Login recusado; confira as credenciais.", file=sys.stderr)
                    return 2

                for width in args.widths:
                    page.set_viewport_size({"width": width, "height": HEIGHT})
                    for url in args.urls:
                        out_file = out_dir / f"{theme}-{width}" / f"{slug(url)}.png"
                        rows.append((theme, width, check_page(page, args.base_url, url, out_file)))
                context.close()
        finally:
            browser.close()

    return report(rows, out_dir)


def report(rows, out_dir: Path) -> int:
    lines = [
        "| URL | Largura | Tema | Resultado |",
        "| --- | ------- | ---- | --------- |",
    ]
    failures = 0
    for theme, width, result in rows:
        problems = result["problems"]
        failures += bool(problems)
        info = result["info"]
        status = "OK" if not problems else "FALHA: " + "; ".join(problems)
        lines.append(f"| `{result['url']}` | {width} | {theme} | {status} |")
        if not info["interLoaded"]:
            lines.append(f"| `{result['url']}` | {width} | {theme} | AVISO: Inter nao carregada |")
    lines.append("")
    lines.append(f"{len(rows)} combinacoes, {failures} com falha. Capturas em `{out_dir}/`.")
    text = "\n".join(lines)
    print(text)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.md").write_text(text + "\n", encoding="utf-8")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--out", default=".visual-check")
    parser.add_argument("--channel", default="chrome", help="canal do Chrome instalado")
    parser.add_argument("--widths", type=int, nargs="+", default=list(WIDTHS))
    parser.add_argument("--themes", nargs="+", choices=THEMES, default=list(THEMES))
    parser.add_argument("--urls", nargs="+", default=URLS)
    args = parser.parse_args()
    args.base_url = args.base_url.rstrip("/")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
