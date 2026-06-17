# IDEALS / DSpace Repository Scraping for Missing Metadata

## When to Use

- CrossRef and OpenAlex have incomplete metadata for older journal special issues
  (pre-2010, non-Elsevier/Springer publishers, university-press journals).
- The publisher hosts its own DSpace-based repository (e.g., IDEALS at Illinois,
  eCommons at Cornell, DSpace@MIT).
- You have verified that the repository contains the full issue TOC and individual
  article pages with structured metadata.

## Example: Library Trends 52(3) 2004

CrossRef returned **0 records** for `issn:1559-0682, year:2004`. OpenAlex title
searches for key papers (Cornelius 2004 "Information and Its Philosophy",
Spink & Cole 2004 "A Human Information Behavior Approach to a Philosophy of
Information") returned **no matches**. The articles exist in IDEALS with stable
item IDs.

## Technique

### 1. Discover item IDs

Browse the issue collection page or use the repository search:

```
https://www.ideals.illinois.edu/collections/99/items
https://www.ideals.illinois.edu/search?q=Information+and+its+philosophy+Cornelius
```

Extract `/items/NNNN` URLs from the HTML. For LT 52(3) 2004, the article IDs
were 1719–1783.

### 2. Scrape individual item pages

IDEALS uses Rails with server-rendered HTML. The metadata is in the DOM as
plain text labels (Title, Author(s), Issue Date, Abstract, etc.):

```python
import urllib.request, re, html

def ideals_item(item_id: int) -> dict | None:
    url = f'https://www.ideals.illinois.edu/items/{item_id}'
    txt = urllib.request.urlopen(
        urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}),
        timeout=20
    ).read().decode('utf-8', 'replace')

    # Strip scripts/styles, extract plain text lines
    nojs = re.sub(r'<(script|style).*?</\1>', '', txt, flags=re.S)
    plain = re.sub(r'<[^>]+>', '\n', nojs)
    lines = [html.unescape(x.strip()) for x in plain.splitlines() if x.strip()]

    # Field extraction: read lines after a label until the next label
    stops = {'Title','Author(s)','Contributor(s)','Issue Date','Keyword(s)',
             'Date of Ingest','Abstract','Publisher','ISSN','Type of Resource',
             'Genre of Resource','Language','Permalink',
             'Copyright and License Information','Owning Collections',
             'Manage Files'}

    def field(label: str) -> str:
        if label not in lines:
            return ''
        i = lines.index(label) + 1
        vals = []
        while i < len(lines) and lines[i] not in stops:
            vals.append(lines[i])
            i += 1
        return ' '.join(vals).strip()

    title = field('Title') or (lines[0] if lines else '')
    authors_raw = field('Author(s)') or field('Contributor(s)')
    authors = [a.strip() for a in re.split(r';|\n', authors_raw) if a.strip()]
    year = None
    y = field('Issue Date')
    if re.search(r'\d{4}', y):
        year = int(re.search(r'\d{4}', y).group(0))
    abstract = field('Abstract')
    permalink = field('Permalink') or url

    # PDF URL extraction
    pdfs = re.findall(
        r'https?://www\.ideals\.illinois\.edu/items/\d+/bitstreams/[^"\']+data\.pdf',
        txt
    )
    pdf_url = pdfs[0] if pdfs else ''

    return {
        'source': 'ideals',
        'title': title,
        'authors': authors,
        'year': year,
        'venue': 'Library Trends',
        'abstract': abstract,
        'is_oa': bool(pdf_url),
        'oa_url': pdf_url,
        'url': permalink,
    }
```

### 3. Batch discovery by ID range

When the issue collection page uses JavaScript/XHR and doesn't list items in
static HTML, brute-force the ID range:

```python
for item_id in range(1717, 1785):
    try:
        rec = ideals_item(item_id)
        if rec and 'Library Trends 52 (3)' in rec.get('title', ''):
            print(item_id, rec['title'])
    except Exception:
        pass
```

### 4. Validate completeness

After scraping, cross-check against the publisher's official TOC or the
editorial introduction. For LT 52(3) 2004, the TOC lists:
- Introduction (Herold)
- LIS as Applied Philosophy of Information (Floridi)
- Information and Its Philosophy (Cornelius)
- Documentation Redux (Frohmann)
- Information Studies Without Information (Furner)
- Classification and Categorization (Jacob)
- Social epistemology from Shera to Fuller (Zandonade)
- A Human Information Behavior Approach (Spink & Cole)
- Arguments for Philosophical Realism (Hjørland)
- Plus classification articles (Mills, Olson, Paling, Svenonius)

## Caveats

- **Rate limiting**: DSpace repositories may throttle rapid sequential requests.
  Add `time.sleep(0.1)` between requests.
- **Platform differences**: Not all DSpace instances use the same HTML structure.
  The label-based parser above works for IDEALS (Rails/DSpace-CRIS) but may
  need adjustment for plain DSpace 6/7 instances.
- **Abstract completeness**: Some older issues may lack abstracts in the
  repository; the PDF may contain the only abstract.
- **DOI absence**: Repository metadata often lacks DOI. Use the permalink
  (handle.net URL) as the stable identifier.
