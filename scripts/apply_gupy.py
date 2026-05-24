"""Apply automático em vagas Gupy via Playwright headless.

Substitui o Browserless TS connector. Sem Docker — apenas chromium local.
Abort imediato se detectar Cloudflare Turnstile.
"""
from __future__ import annotations

import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CANDIDATE = {
    "name": "Fabio Fernandes",
    "email": "fabiokansas@gmail.com",
    "phone": "(11) 95927-3390",
    "linkedin": "https://www.linkedin.com/in/fabiokansas",
}


def _try_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        return sync_playwright
    except ImportError:
        return None


def _apply_one_gupy(applyUrl: str, cv_pdf: Path, cover_letter: str, evidence_dir: Path, vaga_id: str) -> dict:
    sync_playwright = _try_playwright()
    if not sync_playwright:
        return {"status": "failed", "info": "playwright não instalado (pip install playwright + python -m playwright install chromium)"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            locale="pt-BR",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        try:
            page.goto(applyUrl, wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)

            # Cloudflare Turnstile?
            if page.locator("iframe[src*='challenges.cloudflare.com']").count() > 0:
                shot = evidence_dir / f"gupy-{vaga_id}-captcha-{int(time.time())}.png"
                page.screenshot(path=str(shot), full_page=True)
                return {"status": "needs_captcha", "screenshot": str(shot.relative_to(evidence_dir.parent))}

            # Botão candidatar (tentativas múltiplas)
            for sel in ['button:has-text("candidatar")', 'a:has-text("candidatar")', '[data-testid*="apply"]']:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        break
                except Exception:
                    continue
            time.sleep(2)

            # Preenche campos básicos (vários nomes possíveis)
            field_map = {
                "name": ['input[name*="name" i]:not([type="email"])', 'input[id*="name" i]:not([type="email"])'],
                "email": ['input[type="email"]', 'input[name*="email" i]'],
                "phone": ['input[type="tel"]', 'input[name*="phone" i]', 'input[name*="telefone" i]'],
                "linkedin": ['input[name*="linkedin" i]', 'input[placeholder*="linkedin" i]'],
            }
            for key, selectors in field_map.items():
                for s in selectors:
                    try:
                        loc = page.locator(s).first
                        if loc.is_visible(timeout=1500):
                            loc.fill(CANDIDATE[key])
                            break
                    except Exception:
                        continue

            # Upload CV
            try:
                file_inputs = page.locator('input[type="file"]')
                if file_inputs.count() > 0:
                    file_inputs.first.set_input_files(str(cv_pdf))
                    time.sleep(2)
            except Exception as e:
                print(f"[gupy] upload err: {e}", file=sys.stderr)

            # Cover letter
            if cover_letter:
                for sel in ['textarea[placeholder*="apresenta" i]', 'textarea[name*="cover" i]', 'textarea']:
                    try:
                        ta = page.locator(sel).first
                        if ta.is_visible(timeout=1500):
                            ta.fill(cover_letter[:2000])
                            break
                    except Exception:
                        continue

            # Submit
            submitted = False
            for sel in ['button:has-text("enviar")', 'button:has-text("submeter")', 'button[type="submit"]', 'button:has-text("candidatar")']:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=1500):
                        btn.click()
                        submitted = True
                        break
                except Exception:
                    continue

            if not submitted:
                shot = evidence_dir / f"gupy-{vaga_id}-nosubmit-{int(time.time())}.png"
                page.screenshot(path=str(shot), full_page=True)
                return {"status": "failed", "info": "submit button not found", "screenshot": str(shot.relative_to(evidence_dir.parent))}

            # Aguarda confirmação
            try:
                page.wait_for_selector("text=/parab[ée]ns|candidatura enviada|sucesso|cadastrad[oa]/i", timeout=20000)
                ok = True
            except Exception:
                ok = False

            shot = evidence_dir / f"gupy-{vaga_id}-{'ok' if ok else 'submitted'}-{int(time.time())}.png"
            page.screenshot(path=str(shot), full_page=True)
            return {
                "status": "sent" if ok else "submitted_no_confirmation",
                "screenshot": str(shot.relative_to(evidence_dir.parent)),
            }
        except Exception as e:
            return {"status": "failed", "info": f"playwright err: {e}"[:300]}
        finally:
            ctx.close()
            browser.close()


def apply_gupy_top(
    vagas: list[dict],
    profile: str,
    evidence_dir: Path,
    append_application,
    dedupe_check,
    gen_cover_letter,
    cv_pdf: Path,
) -> list[dict]:
    out: list[dict] = []
    if not cv_pdf.exists():
        print("[gupy] CV PDF não encontrado, skip", file=sys.stderr)
        return out

    targets = [
        v for v in vagas
        if (v.get("source", "").startswith("gupy") or v.get("source") == "gupy")
        and v.get("_recommend")
        and v.get("_score", 0) >= 75
    ]
    # Rate limit 10/dia
    targets = targets[:10]
    if not targets:
        print("[gupy] sem alvos (score>=75 + recommend)", file=sys.stderr)
        return out

    for v in targets:
        if dedupe_check("gupy", "vaga_id", v["external_id"], window_days=30):
            print(f"[gupy] skip {v['external_id']} (já aplicado <30d)", file=sys.stderr)
            continue
        cover = gen_cover_letter(profile, [v], audience="empresa")
        try:
            r = _apply_one_gupy(v["url"], cv_pdf, cover, evidence_dir, v["external_id"])
        except Exception as e:
            r = {"status": "failed", "info": f"exception: {e}"[:300]}
        rec = {
            "platform": "gupy",
            "vaga_id": v["external_id"],
            "vaga_title": v["title"],
            "company": v["company"],
            "url": v["url"],
            "sent_at": datetime.now(timezone.utc).isoformat(),
            **r,
        }
        append_application(rec)
        out.append(rec)
        print(f"[gupy] {v['external_id'][:40]} → {rec.get('status')}", file=sys.stderr)
        time.sleep(random.uniform(30, 60))
    return out
