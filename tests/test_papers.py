"""Integration checks for public paper overviews and their downloadable sources."""
import copy
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

import build
from tools import check_links


class PaperMetadata(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('name', '').startswith('citation_'):
            self.meta.setdefault(attrs['name'], []).append(attrs['content'])


class PaperPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = build.load_all()
        cls.pages = build.render_all(cls.ctx)

    def test_citation_metadata_matches_paper_and_public_pdf(self):
        for page_id, paper in self.ctx['paper_pages'].items():
            filename = build.public_page_files(self.ctx)[page_id]
            pub = self.ctx['pubs_by_id'][paper['publication']]
            text = self.pages[filename]
            meta = PaperMetadata(text).meta
            self.assertEqual(meta['citation_title'], [pub['title']])
            self.assertEqual(meta['citation_author'], pub['authors'])
            self.assertEqual(meta['citation_publication_date'], [str(pub['year'])])
            self.assertEqual(meta['citation_conference_title'], [pub['venue']])
            page_url = self.ctx['site']['base_url'] + '/' + filename
            if pub.get('pdf'):
                pdf_url = meta['citation_pdf_url'][0]
                self.assertEqual(urlsplit(pdf_url).path.rsplit('/', 1)[0], urlsplit(page_url).path.rsplit('/', 1)[0])
                self.assertEqual(pdf_url, page_url.replace('.html', '.pdf'))
            else:
                self.assertNotIn('citation_pdf_url', meta)
            self.assertNotIn('noindex', text)
            for paragraph in paper['abstract']:
                self.assertIn('<p>' + build.esc(paragraph) + '</p>', text)
            self.assertIn('aria-current="page">Publications', text)
            self.assertIn(filename[:-5] + '.md', self.pages['llms.txt'])

    def test_nested_pages_work_under_a_repository_path_and_copy_original_pdfs(self):
        ctx = copy.deepcopy(self.ctx)
        ctx['site']['base_url'] += '/preview'
        pages = build.render_all(ctx)
        with tempfile.TemporaryDirectory() as temporary:
            out = build.write(pages, Path(temporary) / 'site')
            for name in ('flash', 'argus', 'hollow-llm'):
                path = 'papers/' + name
                text = pages[path + '.html']
                self.assertIn(ctx['site']['base_url'] + '/' + path + '.html', text)
                if name == 'argus':
                    self.assertFalse((out / (path + '.pdf')).exists())
                else:
                    self.assertEqual((out / (path + '.pdf')).read_bytes(),
                                     (build.ROOT / (path + '.pdf')).read_bytes())
                self.assertIn('href="../assets/css/style.css"', text)
            # Check all local targets with the same parser used by the link checker.
            for page in out.rglob('*.html'):
                for _, _, href, _ in check_links.parse(page).refs:
                    target = urlsplit(href)
                    if target.scheme or target.netloc:
                        continue
                    resolved = (page.parent / target.path).resolve() if target.path else page
                    self.assertTrue(resolved.is_file(), (page, href))
            note = out / 'papers/private-notes.txt'
            note.write_text('keep')
            with self.assertRaisesRegex(SystemExit, 'papers'):
                build.write(pages, out)
            self.assertEqual(note.read_text(), 'keep')

    def test_withdrawn_argus_pdf_is_removed_from_previous_output_and_all_exports(self):
        for filename, text in self.pages.items():
            self.assertNotIn('papers/argus.pdf', text, filename)
        self.assertNotIn('application/pdf', self.pages['papers/argus.html'])
        with tempfile.TemporaryDirectory() as temporary:
            out = build.write(self.pages, Path(temporary) / 'site')
            stale = out / 'papers/argus.pdf'
            stale.write_bytes(b'%PDF-previously-published-file')
            build.write(self.pages, out)
            self.assertFalse(stale.exists())
            self.assertTrue((out / 'papers/argus.html').is_file())

    def test_unknown_publication_and_invalid_slug_are_rejected(self):
        data = {'papers': [copy.deepcopy(next(iter(self.ctx['paper_pages'].values())))]}
        data['papers'][0]['publication'] = 'missing-paper'
        with patch.object(build, 'load_json', return_value=data), patch.object(build, 'ERRORS', build.DataErrors()):
            build.load_paper_pages(self.ctx['pubs_by_id'])
            with self.assertRaisesRegex(SystemExit, 'unknown published paper'):
                build.ERRORS.raise_if_any()
        data['papers'][0]['slug'] = '../outside'
        with patch.object(build, 'load_json', return_value=data), patch.object(build, 'ERRORS', build.DataErrors()):
            build.load_paper_pages(self.ctx['pubs_by_id'])
            with self.assertRaisesRegex(SystemExit, 'slug'):
                build.ERRORS.raise_if_any()
