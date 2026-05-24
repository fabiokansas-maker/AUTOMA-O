"""Apply automático em vagas Gupy via Playwright headless.

V2:
- A2.3: sem cap [:10], shuffle + threshold 65
- A2.4: cover selector expandido
- A2.5: log Counter(company) no Actions
- A2.8: respeita GUPY_DRY_RUN=1 (preenche tudo, screenshot, NÃO submeter)
- N2: lida com etapas extras (DISC, dissertativa, vídeo, Excel, salário)
  - dissertativa: Gemini gera resposta com profile
  - DISC: responde simulando perfil analítico-calculista
  - vídeo/lógica/técnico: aborta + screenshot + status partial_apply_needs_manual
  - salário: auto-preenche R$7000
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CANDIDATE = {
    "name": "Fabio Fernandes",
    "email": "fabiokansas@gmail.com",
    "phone": "(11) 95927-3390",
    "linkedin": "https://www.linkedin.com/in/fabiokansas",
    "salary": "7000",
    "salary_text": "R$ 7.000,00",
}

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

# N2: keywords pra detectar tipos de teste no DOM
SKIP_KEYWORDS = (
    "vídeo", "video", "gravação", "gravacao", "upload de vídeo", "envie um vídeo",
    "raciocínio lógico", "raciocinio logico", "matemática", "matematica",
    "cálculo", "calculo", "excel avançado", "fórmula", "formula",
    "sql", "tabela dinâmica", "tabela dinamica",
)
DISC_KEYWORDS = ("disc", "comportamental", "perfil comportamental", "personalidade")


def _try_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        return sync_playwright
    except ImportError:
        return None


def _gemini_answer(question: str, vaga_title: str, vaga_company: str, profile_bundle: str, max_words: int = 180) -> str:
    """Resposta dissertativa via Gemini com contexto perfil + vaga."""
    if not GEMINI_KEY:
        return "Tenho 6 anos de experiência em Controladoria e FP&A, com vivência em SAP/Bluesoft, fechamento mensal, DRE consolidado e análise de variação. Atualmente busco posições onde possa aplicar essa expertise contribuindo com resultados mensuráveis."
    prompt = (
        f"Responda a seguinte pergunta de processo seletivo em PT-BR, tom profissional, máximo {max_words} palavras. "
        f"Sem clichês. Sem markdown. Resposta direta usando 1-2 exemplos concretos do perfil.\n\n"
        f"=== VAGA ===\n{vaga_title} @ {vaga_company}\n\n"
        f"=== PERFIL DO CANDIDATO ===\n{profile_bundle[:4000]}\n\n"
        f"=== PERGUNTA ===\n{question}\n\n"
        f"Resposta:"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600},
    }
    try:
        import urllib.request as _u
        req = _u.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with _u.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
        return resp.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
    except Exception as e:
        print(f"[gupy-ai] err: {e}", file=sys.stderr)
        return "Tenho experiência relevante em Controladoria e FP&A que considero alinhada à vaga."


def _detect_test_type(page) -> str | None:
    """Identifica tipo do teste/etapa atual. Retorna 'skip'|'disc'|'dissertativa'|'salary'|None."""
    try:
        page_text = page.text_content("body", timeout=2000) or ""
    except Exception:
        page_text = ""
    page_text_low = page_text.lower()
    if any(k in page_text_low for k in SKIP_KEYWORDS):
        return "skip"
    if any(k in page_text_low for k in DISC_KEYWORDS):
        return "disc"
    # Dissertativa: presença de textarea com pergunta
    try:
        if page.locator("textarea").count() > 0:
            return "dissertativa"
    except Exception:
        pass
    # Salário
    try:
        if page.locator('input[name*="salary" i], input[name*="pretensa" i], input[name*="pretensão" i]').count() > 0:
            return "salary"
    except Exception:
        pass
    return None


def _handle_disc(page) -> bool:
    """Responde DISC com perfil analítico-calculista (escolhe primeira opção 'analítica' em cada questão).

    Heurística: nas opções de cada questão, prefere texto contendo 'analiso', 'dados',
    'planejo', 'reflito'; senão escolhe a primeira opção.
    """
    try:
        radios = page.locator('input[type="radio"]')
        cnt = radios.count()
        if cnt == 0:
            return False
        # Agrupa radios por name (cada name = 1 questão)
        names_seen: set[str] = set()
        for i in range(cnt):
            try:
                name = radios.nth(i).get_attribute("name") or ""
                if name in names_seen:
                    continue
                names_seen.add(name)
                # Escolhe a opção mais "analítica" — fallback first
                same_name = page.locator(f'input[type="radio"][name="{name}"]')
                picked = False
                for j in range(same_name.count()):
                    r = same_name.nth(j)
                    label_text = ""
                    try:
                        rid = r.get_attribute("id") or ""
                        if rid:
                            lbl = page.locator(f'label[for="{rid}"]').first
                            if lbl.count() > 0:
                                label_text = (lbl.text_content() or "").lower()
                    except Exception:
                        pass
                    if any(k in label_text for k in ("analis", "dado", "planej", "reflet", "calcul", "decid")):
                        r.check(force=True)
                        picked = True
                        break
                if not picked:
                    same_name.first.check(force=True)
            except Exception as e:
                print(f"[gupy-disc] err q{i}: {e}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[gupy-disc] err: {e}", file=sys.stderr)
        return False


def _handle_dissertativa(page, vaga: dict, profile_bundle: str) -> bool:
    """Responde todas as textareas presentes via Gemini."""
    try:
        textareas = page.locator("textarea")
        cnt = textareas.count()
        if cnt == 0:
            return False
        for i in range(cnt):
            ta = textareas.nth(i)
            try:
                # Pergunta = label próximo ou placeholder
                question = ta.get_attribute("placeholder") or ""
                if not question:
                    try:
                        tid = ta.get_attribute("id") or ""
                        if tid:
                            lbl = page.locator(f'label[for="{tid}"]').first
                            if lbl.count() > 0:
                                question = (lbl.text_content() or "").strip()
                    except Exception:
                        pass
                if not question:
                    # Tenta encontrar texto irmão anterior
                    try:
                        prev_text = ta.evaluate("el => el.previousElementSibling ? el.previousElementSibling.innerText : ''")
                        if prev_text:
                            question = prev_text.strip()
                    except Exception:
                        pass
                if not question:
                    question = f"Por que você se interessou pela vaga de {vaga['title']} em {vaga['company']}?"
                ans = _gemini_answer(question, vaga.get("title", ""), vaga.get("company", ""), profile_bundle, max_words=180)
                ta.fill(ans[:2000])
            except Exception as e:
                print(f"[gupy-diss] err ta{i}: {e}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[gupy-diss] err: {e}", file=sys.stderr)
        return False


def _handle_salary(page) -> bool:
    """Auto-preenche pretensão salarial."""
    try:
        for sel in (
            'input[name*="salary" i]',
            'input[name*="pretensa" i]',
            'input[name*="pretensão" i]',
            'input[placeholder*="pretensão" i]',
            'input[placeholder*="salário" i]',
        ):
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=1500):
                    loc.fill(CANDIDATE["salary"])
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _handle_extra_steps(page, vaga: dict, profile_bundle: str, evidence_dir: Path, vaga_id: str, dry_run: bool = False) -> dict:
    """Loop sobre etapas extras (até 3) detectando tipo e respondendo.

    Returns: {"status": "ok"|"partial_apply_needs_manual", "step": "...", "screenshot": "..."}
    """
    for step_idx in range(3):
        url_now = page.url
        if any(p in url_now.lower() for p in ("parabens", "sucesso", "completed", "thank")):
            return {"status": "ok", "step": f"finished_at_step_{step_idx}"}
        ttype = _detect_test_type(page)
        if not ttype:
            return {"status": "ok", "step": f"no_extra_step_{step_idx}"}
        print(f"[gupy-extra] step {step_idx} → tipo={ttype}", file=sys.stderr)
        if ttype == "skip":
            shot = evidence_dir / f"gupy-{vaga_id}-skiptype-{int(time.time())}.png"
            try:
                page.screenshot(path=str(shot), full_page=True)
            except Exception:
                pass
            return {
                "status": "partial_apply_needs_manual",
                "step": f"detected_skip_type_at_step_{step_idx}",
                "screenshot": str(shot.relative_to(evidence_dir.parent)),
            }
        if ttype == "disc":
            _handle_disc(page)
        elif ttype == "dissertativa":
            _handle_dissertativa(page, vaga, profile_bundle)
        elif ttype == "salary":
            _handle_salary(page)
        # Em dry_run não clica "próximo" — screenshot e sai
        if dry_run:
            shot = evidence_dir / f"gupy-{vaga_id}-dryrun-extra{step_idx}-{int(time.time())}.png"
            try:
                page.screenshot(path=str(shot), full_page=True)
            except Exception:
                pass
            return {"status": "dry_run", "step": f"would_submit_step_{step_idx}", "screenshot": str(shot.relative_to(evidence_dir.parent))}
        # Clica próximo/enviar/submeter
        clicked = False
        for sel in ('button:has-text("próximo")', 'button:has-text("proximo")', 'button:has-text("avançar")', 'button:has-text("avancar")', 'button:has-text("continuar")', 'button:has-text("enviar")', 'button[type="submit"]'):
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=1500):
                    btn.click()
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            return {"status": "ok", "step": f"no_next_button_at_step_{step_idx}"}
        time.sleep(3)
    return {"status": "ok", "step": "max_steps_reached"}


def _apply_one_gupy(vaga: dict, cv_pdf: Path, cover_letter: str, evidence_dir: Path, vaga_id: str, profile_bundle: str = "", dry_run: bool = False) -> dict:
    sync_playwright = _try_playwright()
    if not sync_playwright:
        return {"status": "failed", "info": "playwright não instalado (pip install playwright + python -m playwright install chromium)"}

    apply_url = vaga.get("url", "")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            locale="pt-BR",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        try:
            page.goto(apply_url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)

            # Cloudflare Turnstile?
            if page.locator("iframe[src*='challenges.cloudflare.com']").count() > 0:
                shot = evidence_dir / f"gupy-{vaga_id}-captcha-{int(time.time())}.png"
                page.screenshot(path=str(shot), full_page=True)
                return {"status": "needs_captcha", "screenshot": str(shot.relative_to(evidence_dir.parent))}

            # Botão candidatar (tentativas múltiplas)
            for sel in ('button:has-text("candidatar")', 'a:has-text("candidatar")', '[data-testid*="apply"]'):
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        break
                except Exception:
                    continue
            time.sleep(2)

            # Preenche campos básicos
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

            # A2.4: Cover letter — selectors expandidos
            if cover_letter:
                for sel in (
                    'textarea[placeholder*="apresenta" i]',
                    'textarea[name*="cover" i]',
                    'textarea[id*="motiv" i]',
                    'textarea[name*="message" i]',
                    'div[contenteditable="true"]',
                    'textarea',
                ):
                    try:
                        ta = page.locator(sel).first
                        if ta.is_visible(timeout=1500):
                            ta.fill(cover_letter[:2000])
                            break
                    except Exception:
                        continue

            # A2.8 dry-run: screenshot e NÃO submeter
            if dry_run:
                shot = evidence_dir / f"gupy-{vaga_id}-dryrun-{int(time.time())}.png"
                page.screenshot(path=str(shot), full_page=True)
                return {
                    "status": "dry_run",
                    "info": "form preenchido + CV anexado; submit pulado por GUPY_DRY_RUN=1",
                    "screenshot": str(shot.relative_to(evidence_dir.parent)),
                }

            # Submit
            submitted = False
            for sel in ('button:has-text("enviar")', 'button:has-text("submeter")', 'button[type="submit"]', 'button:has-text("candidatar")'):
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

            time.sleep(3)

            # N2: lida com etapas extras (DISC/dissertativa/vídeo/Excel/salário)
            extra = _handle_extra_steps(page, vaga, profile_bundle, evidence_dir, vaga_id, dry_run=dry_run)

            # Se chegou aqui sem skip, aguarda confirmação final
            ok = False
            try:
                page.wait_for_selector("text=/parab[ée]ns|candidatura enviada|sucesso|cadastrad[oa]/i", timeout=15000)
                ok = True
            except Exception:
                pass

            shot = evidence_dir / f"gupy-{vaga_id}-{'ok' if ok else 'submitted'}-{int(time.time())}.png"
            page.screenshot(path=str(shot), full_page=True)
            status = "sent" if ok else extra.get("status", "submitted_no_confirmation")
            return {
                "status": status,
                "extra_step": extra.get("step"),
                "screenshot": str(shot.relative_to(evidence_dir.parent)),
            }
        except Exception as e:
            return {"status": "failed", "info": f"playwright err: {e}"[:300]}
        finally:
            ctx.close()
            browser.close()


def apply_gupy_top(
    vagas: list[dict],
    profile_bundle: str,
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

    # A2.3: sem cap, threshold 65
    targets = [
        v for v in vagas
        if (v.get("source", "").startswith("gupy") or v.get("source") == "gupy")
        and v.get("_recommend")
        and v.get("_score", 0) >= 65
    ]
    if not targets:
        print("[gupy] sem alvos (score>=65 + recommend)", file=sys.stderr)
        return out

    # Shuffle se >15 (diversificar empresas, evitar 15 hits no mesmo subdomínio)
    if len(targets) > 15:
        random.shuffle(targets)

    # A2.5: log Counter
    by_co = Counter(v.get("company", "?") for v in targets)
    print(f"[gupy] {len(targets)} alvos distribuídos por: {dict(by_co)}", file=sys.stderr)

    dry_run = os.environ.get("GUPY_DRY_RUN", "0") == "1"
    if dry_run:
        print(f"[gupy] DRY-RUN ativo (GUPY_DRY_RUN=1) — não submete, salva screenshots", file=sys.stderr)

    captcha_streak = 0
    for v in targets:
        if dedupe_check("gupy", "vaga_id", v["external_id"], window_days=30):
            print(f"[gupy] skip {v['external_id']} (já aplicado <30d)", file=sys.stderr)
            continue
        cover = gen_cover_letter(profile_bundle, [v], audience="empresa", match_analysis=v.get("_match"))
        try:
            r = _apply_one_gupy(v, cv_pdf, cover, evidence_dir, v["external_id"], profile_bundle=profile_bundle, dry_run=dry_run)
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
        # Abort se 3 captchas seguidos
        if rec.get("status") == "needs_captcha":
            captcha_streak += 1
            if captcha_streak >= 3:
                print(f"[gupy] 3 captchas seguidos — abortando fila", file=sys.stderr)
                break
        else:
            captcha_streak = 0
        time.sleep(random.uniform(30, 60))
    return out


# Backward compat — old signature called _apply_one_gupy(applyUrl, cv_pdf, cover_letter, evidence_dir, vaga_id)
# now we pass vaga dict. Wrapper for tests:
def _apply_one_gupy_url(apply_url: str, cv_pdf, cover_letter, evidence_dir, vaga_id):
    return _apply_one_gupy(
        {"url": apply_url, "title": "(test)", "company": "(test)"},
        cv_pdf, cover_letter, evidence_dir, vaga_id,
    )
