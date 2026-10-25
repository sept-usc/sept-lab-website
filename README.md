# SEPT Lab website

Source for the website of SEPT Lab (Security, Privacy, and Trust) at the University of Southern California. Content is stored in JSON files and rendered into static HTML by a small Python build script.

The configured public URL is [septlab.com](https://septlab.com/).

## Build and preview

The site build requires Python 3.9 or later and uses only the standard library. Run these commands from the repository root:

```sh
python3 build.py
python3 tools/check_links.py
python3 -m http.server 8000 --directory dist
```

Open [localhost:8000](http://localhost:8000/) to preview the site. Rebuild after editing content or assets. The generated `dist/` directory is ignored by Git; edit the source files rather than generated HTML.

To validate the data and render every page without writing output:

```sh
python3 build.py --check
python3 -m unittest discover -s tests -v
```

To build elsewhere, choose a new or empty directory, or one containing only an earlier build:

```sh
python3 build.py --out /tmp/sept-preview
python3 tools/check_links.py /tmp/sept-preview
```

Each build replaces its output directory. The builder rejects directories containing unrelated files. The link checker validates local files, anchors, and HTML ID references; external URLs are counted but not fetched.

## Edit content

Edit the corresponding file under [data/](data/), then rebuild and check links.

| File | Content |
| --- | --- |
| [site.json](data/site.json) | Lab identity, homepage text, navigation, sidebar, social preview, and public URL |
| [people.json](data/people.json) | Principal investigator, current members, alumni, and contact email |
| [research.json](data/research.json) | Research directions, topics, representative papers, and projects |
| [publications.json](data/publications.json) | Publication records, paper and artifact links, and scholarly profiles |
| [news.json](data/news.json) | Dated announcements |
| [teaching.json](data/teaching.json) | Courses, terms, descriptions, and course links |
| [join.json](data/join.json) | Recruitment information and email subjects |
| [contact.json](data/contact.json) | Address, maps, and profile links |

Keep publication and research IDs stable: they form page anchors and connect records across files. Publication `themes` must match research theme IDs, and representative `papers` must refer to published entries. The optional publication `since` year controls which entries appear on the site. Lab members are bolded in author lists when their names match `people.json` exactly.

News dates accept `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`; each item's date and `slug` form its anchor. Use only the date precision the announcement supports.

Paragraph fields such as homepage `about`, research `description`, and news `body` support `[label](url)`, `**bold**`, and `*italic*`. Names, titles, summaries, and topic labels are plain text. Use relative site links such as `publications.html#wave-asplos26`; links beginning with `/` are rejected because the site can be hosted under a repository path. External links may use HTTP, HTTPS, or `mailto:`.

The builder reports unknown fields, invalid dates and URLs, duplicate IDs, and unresolved references. Keep `site.json` homepage text consistent with the research directions when changing the lab's mission.

## Search and agent-readable files

With `base_url` set, every public page has its own title, description and canonical URL. JSON-LD describes the lab, its website, the PI, people, research subjects and the publications that are visible on the site. PI profiles belong to the PI; alumni are not marked as current members. Paper records retain their supplied year without an invented publication day.

The build also writes:

| File | Purpose |
| --- | --- |
| `robots.txt` | Allows crawling and points to the sitemap |
| `sitemap.xml` | Lists the eight canonical public HTML pages, excluding the 404 page |
| `index.md`, `people.md`, and other page-matched Markdown files | Main-column content with links, generated from the rendered HTML |
| `llms.txt` | A short guide to the official pages and their text copies |
| `llms-full.txt` | The combined text of those pages |

The text exports leave out navigation, sidebars and the optional game. Edit the JSON content and rebuild to keep HTML and text aligned. A content page links its Markdown copy in the document head. The 404 page remains `noindex` and has no canonical URL or text copy.

For Google and Bing, submit `https://septlab.com/sitemap.xml` through the site's verified webmaster account. Google's [organization](https://developers.google.com/search/docs/appearance/structured-data/organization) and [site-name](https://developers.google.com/search/docs/appearance/site-names) guidance explain the identity metadata. The text exports help direct agent readers; Google Search, including its [AI features](https://developers.google.com/search/docs/appearance/ai-features), uses the standard search requirements and does not require these extra files.

## Deploy with GitHub Pages

The [Pages workflow](.github/workflows/pages.yml) builds and checks pushes to `main` and pull requests with Python 3.9 and 3.12. Publishing is enabled separately:

1. In repository **Settings → Pages**, set **Build and deployment → Source** to **GitHub Actions**.
2. In **Settings → Secrets and variables → Actions → Variables**, add the repository variable `PAGES_ENABLED` with the value `true`.
3. Set `base_url` in [data/site.json](data/site.json) to the final public URL. Without a custom domain, the expected URL is `https://sept-usc.github.io/sept-lab-website/`.
4. Push to `main`, or run **Build and deploy to GitHub Pages** manually from the Actions tab. Check the deployment result and open the URL reported by GitHub Pages.

The workflow publishes `dist/`; pull requests are checked without deployment. Changing the repository variable alone does not start a workflow run. Setting `base_url` enables canonical URLs and the social-preview image, and makes links on nested 404 pages resolve correctly.

Other static hosts can serve the contents of `dist/` after a local build.

### Use a custom domain

1. Follow GitHub's [domain verification instructions](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages) for the `sept-usc` organization.
2. Enter the hostname in repository **Settings → Pages → Custom domain** before pointing its DNS to GitHub.
3. At the DNS provider, configure the records in GitHub's [custom-domain guide](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site). A subdomain such as `www.example.com` uses a CNAME pointing to `sept-usc.github.io`, without a scheme or repository path. An apex domain such as `example.com` uses the apex records specified in that guide.
4. Once DNS and the certificate are ready, enable **Enforce HTTPS** in Pages settings.
5. Update `base_url` to the final HTTPS URL and redeploy. For a domain serving this site at its root, omit `/sept-lab-website`.

This Actions deployment does not require a `CNAME` file. Configure the domain in Pages settings, and keep generated files out of the source editing workflow.

## Layout and illustrations

The masthead, sidebar layout, and publication list are modeled on the [Computer Security Group at ETH Zurich](https://comsec.ethz.ch/). SEPT Lab branding, the isometric illustrations, and the interactive journey are maintained in this repository.

The site uses responsive CSS and progressive enhancement: the research text, navigation, and publication list remain available without JavaScript. The homepage vision image has a pause control and respects reduced-motion preferences. Its “Start the journey” link opens an optional game illustrating the research directions; the game loads when a visitor shows interest in it.

Edit the layout and typography in [assets/css/style.css](assets/css/style.css). Page templates are in [build.py](build.py); [assets/js/site.js](assets/js/site.js) handles navigation, motion controls, and the journey loader. The journey has its own [stylesheet](assets/css/journey.css) and [script](assets/js/journey.js).

The vision image and research icons have editable Python generators in [design/vision/](design/vision/). Regenerate the masters and copy them into the published assets:

```sh
python3 design/vision/make_vision.py design/vision/vision.svg --check
python3 design/vision/make_icons.py design/vision/icons
cp design/vision/vision.svg assets/img/vision.svg
cp design/vision/icons/*.svg assets/img/icons/
python3 build.py --check
```

Keep the vision generator's `LABELS` aligned with research theme `layer` values, and update the image's text alternative when its meaning changes. After changing geometry, regenerate the motion timing:

```sh
python3 design/vision/make_vision.py design/vision/vision.svg --check --motion > /tmp/sept-vision-motion.css
```

Replace the marked `make_vision.py --motion` block in `assets/css/style.css` with that output, then copy the updated SVG into `assets/img/`. Check the rebuilt site on desktop and mobile, including reduced motion, the pause control, and the journey dialog.

The social-preview image is `assets/img/og-image.jpg`. Its helper, [tools/og_image.py](tools/og_image.py), generates a rendering page; `--render` additionally requires Chrome and macOS `sips`. The page loads Karla from Google Fonts, so rendering needs a network connection. Update `site.json` `og_image.alt` when replacing the card.

## Repository layout

```text
build.py                  Data validation and HTML rendering
site_discovery.py         Search metadata, sitemap and text exports
data/                     Editable website content
assets/                   Published styles, scripts, and images
design/                   Image masters and illustration generators
tools/check_links.py      Local link, anchor, and ID validation
tools/og_image.py          Social-preview image helper
tests/                    Generator and discovery integration tests
.github/workflows/        Build checks and GitHub Pages deployment
dist/                     Generated site, ignored by Git
```
