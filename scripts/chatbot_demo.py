"""Opt-in, real-key browser smoke and authentic Fiverr screenshot capture.
Runs only on explicit --live; never supplies mocked success responses.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Allow real Gemini calls (may consume quota)')
    parser.add_argument('--frontend', default='http://localhost:5173')
    parser.add_argument('--backend', default='http://127.0.0.1:8010')
    parser.add_argument('--output', default='/tmp/fify-gallery')
    args = parser.parse_args()
    if not args.live:
        parser.error('--live is required; this smoke test calls real Gemini')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    transcripts = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1280, 'height':769}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.frontend, wait_until='networkidle')
        page.wait_for_selector('#fify-assistant-widget')
        frame = page.frame_locator('#fify-assistant-widget')
        frame.get_by_role('button', name='Open FiFy AI Assistant').click()
        def ask(text):
            previous = frame.locator('.message.assistant').count()
            frame.get_by_role('textbox', name='Your message').fill(text)
            frame.get_by_role('button', name='Send message', exact=True).click()
            frame.locator('#send:not([disabled])').wait_for(timeout=45000)
            assert frame.locator('.message.assistant').count() > previous, frame.locator('#feedback').inner_text()
            answer = frame.locator('.message.assistant').nth(previous).inner_text()
            transcripts.append({'question':text, 'answer':answer})
            page.wait_for_timeout(400)
            return answer
        answer = ask('How do I search with a photo?')
        assert 'upload' in answer.lower() and 'photo' in answer.lower(), answer
        page.screenshot(path=str(out / '01-fify-assistant-hero.png'))
        ask('Can I save my finds without creating an account?')
        page.screenshot(path=str(out / '02-live-conversation.png'))
        # This plain HTML page loads one script, independently of React/Vite.
        page.goto(args.backend + '/embed-test.html', wait_until='networkidle')
        frame = page.frame_locator('#fify-assistant-widget')
        frame.get_by_role('button', name='Open FiFy AI Assistant').click()
        answer = ask('Is this the same FiFy help assistant? What can you help me with?')
        assert 'fify' in answer.lower(), answer
        page.screenshot(path=str(out / '03-one-script-integration.png'))
        # Functional narrow-screen check, without spending another model request.
        page.set_viewport_size({'width':375,'height':812})
        page.wait_for_timeout(150)
        box = page.locator('#fify-assistant-widget').bounding_box()
        assert box and box['x'] >= 0 and box['x'] + box['width'] <= 375
        assert frame.get_by_role('textbox', name='Your message').is_visible()
        frame.get_by_role('button', name='Close assistant').click()
        assert frame.get_by_role('button', name='Open FiFy AI Assistant').get_attribute('aria-expanded') == 'false'
        frame.get_by_role('button', name='Open FiFy AI Assistant').click()
        frame.get_by_role('button', name='Clear conversation').click()
        assert frame.locator('.message').count() == 0
        assert not errors, errors
        browser.close()
    # Only explicitly submitted public demo prompts are captured; the app stores no conversations.
    (out / 'demo-transcript.json').write_text(json.dumps(transcripts, indent=2))
    (out / 'browser-checks.json').write_text(json.dumps({'viewport':'1280x769','mobile':'375x812',
        'real_answers':len(transcripts),'browser_errors':errors,'independent_embed':True,'mobile_open_close_reset':True}, indent=2))
    print('Real Gemini + independent embed + mobile checks passed. Gallery:', out)


if __name__ == '__main__':
    main()
