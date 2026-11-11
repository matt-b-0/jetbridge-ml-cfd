"""Package an already reviewed PPTX and its rendered previews for GitHub.

This copies supplied artifacts; it does not create or modify the slides.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import posixpath
import shutil
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL = '{http://schemas.openxmlformats.org/package/2006/relationships}'


def main():
    """Copy reviewed artifacts, extract notes, and write a GitHub entry page."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deck', type=Path, required=True)
    parser.add_argument('--renders', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / 'docs/presentation'
    previews = output / 'slides'
    previews.mkdir(parents=True, exist_ok=True)
    deck = output / 'Jet_Bridge_Presentation.pptx'
    shutil.copyfile(args.deck, deck)
    slides = []
    with ZipFile(deck) as archive:
        rels = ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
        targets = {r.get('Id'): r.get('Target') for r in rels}
        order = ET.fromstring(archive.read('ppt/presentation.xml')).findall('.//p:sldId', NS)
        for number, node in enumerate(order, 1):
            target = targets[node.get('{'+NS['r']+'}id')]
            slide_path = posixpath.normpath(posixpath.join('ppt', target)) if not target.startswith('/') else target.lstrip('/')
            slide = ET.fromstring(archive.read(slide_path))
            paragraphs = [''.join(t.itertext()) for t in slide.findall('.//a:t', NS)]
            title = paragraphs[0] if paragraphs else f'Slide {number}'
            parent, filename = posixpath.split(slide_path)
            relpath = posixpath.join(parent, '_rels', filename + '.rels')
            notes = ''
            if relpath in archive.namelist():
                for rel in ET.fromstring(archive.read(relpath)):
                    if rel.get('Type', '').endswith('/notesSlide'):
                        notepath = posixpath.normpath(posixpath.join(parent, rel.get('Target'))).lstrip('/')
                        note = ET.fromstring(archive.read(notepath))
                        chunks = []
                        for shape in note.findall('.//p:sp', NS):
                            placeholder = shape.find('.//p:ph', NS)
                            if placeholder is not None and placeholder.get('type') in ('sldNum', 'sldImg', 'dt', 'ftr', 'hdr'):
                                continue
                            for paragraph in shape.findall('.//a:p', NS):
                                chunks.append(''.join(t.text or '' for t in paragraph.findall('.//a:t', NS)))
                        notes = '\n'.join(chunks)
            preview = previews / f'slide-{number:02d}.png'
            shutil.copyfile(args.renders / f'slide-{number}.png', preview)
            slides.append(dict(number=number, title=title, notes=notes, preview=f'slides/{preview.name}'))
    notes_md = '# Speaker notes\n\nMain talk: slides 1–9, target 300 seconds. All remaining slides are for questions. Current delivery notes are extracted from the packaged PowerPoint below; older nested evidence notes are omitted from this readable copy and remain in the deck.\n'
    for slide in slides:
        delivery = slide['notes'].split('Previous evidence notes:')[0].strip()
        notes_md += f'\n## Slide {slide["number"]}: {slide["title"]}\n\n{delivery}\n'
    (output / 'SPEAKER_NOTES.md').write_text(notes_md, encoding='utf-8')
    landing = '''# Presentation materials

Use this page as the entry point during the presentation. It is readable directly on GitHub.

- [Download the PowerPoint](Jet_Bridge_Presentation.pptx?raw=true) — nine main slides with timed speaker notes, followed by eleven backup slides.
- [Five-minute tutorial and questions](PRESENTATION_TUTORIAL.md).
- [Tests explained line by line](TEST_WALKTHROUGH.md).
- [Speaker notes extracted from the deck](SPEAKER_NOTES.md).
- [Actual demonstration test source](../../tests/test_presentation_examples.py).
- [Actual SVR leakage/scaling test source](../../tests/test_four_workstreams.py).
- [Repository setup and reproduction](../../README.md).

Fresh scientific-worker checks on 11 November: **128 passed, 1 skipped**; Ruff passed. The native Tk layout module was skipped in WSL. Earlier native GUI evidence remains separately dated. Scientific results are unchanged.

## HTML pages

GitHub's file viewer displays HTML source rather than running the page. To use the interactive tutorial, API documentation and readable test report, choose **Code → Download ZIP**, extract it, and open `docs/presentation/index.html`. All required pages are included and work offline. No Python or OpenFOAM installation is needed to read them. Running the numerical workflows requires the documented environment.

The local tutorial links the complete test source catalogue and current API. Two Tk-only module references are explicitly generated from source; they are not evidence of successful native execution.

## Main slides — browser fallback

Use these images if PowerPoint is unavailable. Each image is rendered from the packaged deck; editable slides and notes remain in the PPTX.
'''
    for slide in slides[:9]:
        landing += f'\n### {slide["number"]}. {slide["title"]}\n\n![Slide {slide["number"]}: {slide["title"]}]({slide["preview"]})\n'
    landing += '\n## Backup slides\n\n'
    for slide in slides[9:]:
        landing += f'- [{slide["number"]}. {slide["title"]}]({slide["preview"]})\n'
    (output / 'README.md').write_text(landing, encoding='utf-8')
    manifest = dict(deck=deck.name, deck_sha256=sha256(deck.read_bytes()).hexdigest(), main_slides=9, total_slides=len(slides), previews={s['preview']: sha256((output / s['preview']).read_bytes()).hexdigest() for s in slides})
    (output / 'package_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Packaged {len(slides)} slide previews, PPTX and extracted speaker notes in {output}')


if __name__ == '__main__':
    main()
