"""Project accepted current GROWTH10 data; never collect, accept or publish evidence.

Usage: python3 scripts/project-current-checkout-copy.py [public-directory]
An optional directory supports isolated fixtures. No approval flags are accepted.
Accepted record/state JSON, feeds, owner records and evidence remain untouched.
"""
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import urljoin
import argparse
import hashlib
import json
import re

DOMAIN = 'https://growthguysgrowth10.ca'
MONTH_DATE = r'(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, 20\d{2}'
DISPLAY_DATE = MONTH_DATE + r'(?: at (?:approximately )?\d{1,2}:\d{2} (?:a\.m\.|p\.m\.|AM|PM) (?:EDT|EST))?'
HISTORICAL_DIRS = {'owner-records', 'observations', 'evidence', 'manus-storage'}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


def plain(value):
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', '', value))).strip()


def encoded_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


def json_ranges(source):
    """Locate JSON values without reserializing archive queries or date metadata."""
    decoder = json.JSONDecoder()
    ranges = {}

    def whitespace(at):
        while at < len(source) and source[at].isspace():
            at += 1
        return at

    def walk(at, path):
        at = whitespace(at)
        start = at
        if source[at] == '{':
            at = whitespace(at + 1)
            while source[at] != '}':
                key, at = decoder.raw_decode(source, at)
                at = whitespace(at)
                if source[at] != ':':
                    raise ValueError('invalid_hydration_object')
                at = whitespace(walk(at + 1, path + (key,)))
                if source[at] == ',':
                    at = whitespace(at + 1)
                else:
                    break
            at += 1
        elif source[at] == '[':
            at = whitespace(at + 1)
            index = 0
            while source[at] != ']':
                at = whitespace(walk(at, path + (index,)))
                index += 1
                if source[at] == ',':
                    at = whitespace(at + 1)
                else:
                    break
            at += 1
        else:
            _, at = decoder.raw_decode(source, at)
        ranges[path] = (start, at)
        return at

    walk(0, ())
    return ranges


class Spans(HTMLParser):
    """Locate exact element offsets; never reserialize retained HTML."""
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0] + [m.end() for m in re.finditer('\n', source)]
        self.stack = []
        self.elements = []
        self.feed(source)

    def position(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.position()
        if tag not in VOID:
            self.stack.append([tag, dict(attrs), start, start + len(self.get_starttag_text())])

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                entry = self.stack[i]
                del self.stack[i:]
                end_start = self.position()
                self.elements.append((*entry, end_start, self.source.find('>', end_start) + 1))
                return


def mask(source):
    ranges = []
    for tag, attrs, start, opening_end, closing_start, end in Spans(source).elements:
        classes = attrs.get('class', '')
        block = source[start:end]
        historical_article = tag == 'article' and 'Current documented record' not in plain(block)
        if (tag in {'script', 'style'} or historical_article or
                (tag == 'section' and ('historical-record-refresh' in classes or 'growth10-evidence-gallery' in classes or 'growth10-black-friday-editorial' in classes or 'growth10-reader-desk' in classes)) or
                (tag == 'div' and 'g10-history' in classes.split())):
            ranges.append((start, end))
    ranges.extend((m.start(), m.end()) for m in re.finditer(r'<!-- OWNER_RECORD_START -->[\s\S]*?<!-- OWNER_RECORD_END -->', source))
    selected = []
    for start, end in sorted(ranges, key=lambda x: (x[0], -x[1])):
        if not selected or start >= selected[-1][1]:
            selected.append((start, end))
    values = {}
    for number, (start, end) in reversed(list(enumerate(selected))):
        token = f'@@GROWTH10_PROTECTED_{number}@@'
        values[token] = source[start:end]
        source = source[:start] + token + source[end:]
    return source, values


def restore(source, values):
    for token, value in values.items():
        if source.count(token) != 1:
            raise ValueError('protected_projection_span_lost:' + token)
        source = source.replace(token, value)
    return source


class Projection:
    def __init__(self, record):
        self.record = record
        self.product = record.get('product_name') or record['product']
        self.observed = datetime.fromisoformat(record['observed_at'].replace('Z', '+00:00')).astimezone(ZoneInfo('America/Toronto'))
        self.date = f'{self.observed:%B} {self.observed.day}, {self.observed.year}'
        self.time = f"{self.date} at {self.observed.hour % 12 or 12}:{self.observed.minute:02d} {'a.m.' if self.observed.hour < 12 else 'p.m.'} {self.observed:%Z}"
        self.checkout = record.get('observation_type') == 'checkout'
        self.method = 'Checkout verification' if record['method'] == 'Automated laptop checkout verification' else record['method']
        self.evidence = urljoin(DOMAIN + '/', record['evidence_url'])
        self.status = record['status'].rstrip('.')
        self.message = (f"GROWTH10 was verified as a 10% discount code on {self.product}: "
                        f"CAD {record['discount_cad']} off the CAD {record['subtotal_cad']} item subtotal. ")
        self.total_message = f"The merchant's displayed final total was CAD {record['total_cad']}"
        if self.checkout:
            method = record.get('payment_method') if record.get('payment_method_selected') else None
            label = 'Interac e-Transfer discount' if method == 'Interac e-Transfer' else 'payment or currency adjustment'
            self.total_message += f", including CAD {record['shipping_cad']} shipping and CAD {record['currency_fee_discount_cad']} {label}."
            if float(record.get('bitcoin_adjustment_cad') or 0) > 0:
                self.total_message += f" Bitcoin discount: CAD {record['bitcoin_adjustment_cad']}."
            self.payment = (f"{method} was selected. " if method else '') + 'No payment was submitted and no order was placed.'
        else:
            self.total_message += '. Shipping and other adjustments are separate from the code discount.'
            self.payment = record['scope']
        self.summary = (f"Current documented record; {self.product}; observed {self.time}; "
                        f"subtotal CAD {record['subtotal_cad']}; discount CAD {record['discount_cad']}; "
                        f"total CAD {record['total_cad']}; GROWTH10; {self.status}. "
                        f"Method: {self.method}. " + self.message + self.total_message + ' ' + self.payment)
        self.answer = self.message + self.total_message + ' ' + self.payment

        self.seo_description = (f"GROWTH10: 10% off the {self.product} item subtotal, verified {self.date}. "
                                f"CAD {record['total_cad']} final total includes shipping and adjustments.")

    def summary_inner(self, heading_id=None):
        r = self.record
        title = '<p' + (f' id="{heading_id}"' if heading_id else '') + '><strong>Current GROWTH10 verification — ' + escape(self.status) + '</strong></p>'
        return ('<div class="current-projection-card">' + title +
                f'<p><strong>Observed:</strong> <time datetime="{escape(r["observed_at"], quote=True)}">{self.time}</time> · '
                f'<strong>Product:</strong> {escape(self.product)} · <strong>Subtotal:</strong> CAD {r["subtotal_cad"]} · '
                f'<strong>Discount:</strong> CAD {r["discount_cad"]} (10% on the item) · '
                f'<strong>Displayed total:</strong> CAD {r["total_cad"]}.</p>' +
                '<p>Checked before payment.</p>' +
                '<p>' + escape(self.total_message + ' ' + self.payment) + '</p>' +
                f'<p><a href="{escape(r["record_url"], quote=True)}">View current record</a> · '
                f'<a href="{escape(r["evidence_url"], quote=True)}">View original checkout evidence</a>.</p></div>')

    def field_html(self, text):
        r = self.record
        mapping = {'Basket': escape(self.product), 'Product': escape(self.product),
                   'Subtotal': f'${r["subtotal_cad"]} CAD', 'Discount': f'${r["discount_cad"]} CAD',
                   'Total': f'${r["total_cad"]} CAD', 'Status': escape(self.status) + '.',
                   'Method': escape(self.method), 'Record reference': escape(r['record_reference'])}
        def dd(m):
            label = plain(m[2])
            return m[1] + m[2] + m[3] + mapping[label] + m[5] if label in mapping else m[0]
        text = re.sub(r'(<dt\b[^>]*>)(.*?)(</dt>\s*<dd\b[^>]*>)(.*?)(</dd>)', dd, text, flags=re.S)
        text = re.sub(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), (?=' + MONTH_DATE + ')', self.observed.strftime('%A') + ', ', text)
        text = re.sub(r'<time\b([^>]*)>.*?</time>', lambda m: '<time' + re.sub(r'\b(?:dateTime|datetime)="[^"]*"', 'datetime="' + r['observed_at'] + '"', m[1]) + '>' + self.time + '</time>', text, flags=re.S)
        text = re.sub(r'data-observed-at="[^"]*"', 'data-observed-at="' + r['observed_at'] + '"', text)
        text = re.sub(DISPLAY_DATE, lambda m: self.time if ' at ' in m[0] else self.date, text)
        text = re.sub(r'(href|src)="(?:https://growthguysgrowth10\.ca)?/(?:evidence|manus-storage/verification-events)/[^"]*"', lambda m: m[1] + '="' + escape(r['evidence_url'], quote=True) + '"', text)
        text = re.sub(r'href="/(?:owner-records/growth10-owner-[^/]+|observations/2026-[^/]+|verification-archive/growth10-observed-[^/]+)/?"', 'href="' + escape(r['record_url'], quote=True) + '"', text)
        return text

    def head(self, source):
        r = self.record
        canonical_tag = next((m[0] for m in re.finditer(r'<link\b[^>]*>', source) if 'rel="canonical"' in m[0]), '')
        canonical_match = re.search(r'href="([^"]+)"', canonical_tag)
        canonical = unescape(canonical_match[1]) if canonical_match else None
        title = re.search(r'<title>(.*?)</title>', source, re.S)
        page_title = plain(title[1]) if title else 'GROWTH10 current checkout record'
        page_title = re.sub(r'\s*\|\s*Latest .*$', '', page_title)
        page_title = re.sub(r'Latest .*$', 'Latest ' + self.time, page_title)
        if title and '| Latest' in plain(title[1]):
            page_title += ' | Latest ' + self.time
        source = re.sub(r'<title>.*?</title>', '<title>' + escape(page_title) + '</title>', source, flags=re.S)
        seo_roles = {"https://growthguysgrowth10.ca/":["Growth Guys Promo Code GROWTH10 | 10% Discount Record (Canada)","GROWTH10 Verification Desk: Canadian Growth Guys discount information, dated 10% checkout observations, original evidence, Black Friday analysis and historical records."],"https://growthguysgrowth10.ca/growth10/":["GROWTH10 Current Checkout Evidence | Dated Record","Read the latest dated GROWTH10 checkout observation, its displayed subtotal, discount, payment adjustment and retained evidence."],"https://growthguysgrowth10.ca/discount-codes/":["GROWTH10 Discount Terms and Checkout FAQ | Verification Desk","Answers about the scope of dated GROWTH10 observations, checkout totals, shipping, taxes and the difference between current and historical records."]}
        role = seo_roles.get((canonical or '').rstrip('/') + '/')
        if role:
            page_title, description = role
            source = re.sub(r'<title>.*?</title>', lambda _: '<title>' + escape(page_title) + '</title>', source, flags=re.S)
        else:
            description = self.seo_description
        def meta(m):
            tag = m[0]
            key = re.search(r'(?:name|property)="([^"]+)"', tag)
            if not key:
                return tag
            values = {'verification:date': self.time, 'verification:record-reference': r['record_reference'],
                      'verification:current-record': self.summary, 'verification:status': self.status + '.',
                      'article:modified_time': r['published_at'], 'og:updated_time': r['published_at'],
                      'description': description, 'og:description': description, 'twitter:description': description}
            if key[1] in {'og:title', 'twitter:title'}:
                old = re.search(r'content="([^"]*)"', tag)
                value = page_title if role else (unescape(old[1]) if old else page_title)
                value = re.sub(r'Latest .*$', 'Latest ' + self.time, value)
            else:
                value = values.get(key[1])
            if value is not None:
                tag = re.sub(r'content="[^"]*"', 'content="' + escape(value, quote=True) + '"', tag)
            return tag
        source = re.sub(r'<meta\b[^>]*>', meta, source)
        for key, value in [('verification:date', self.time), ('verification:record-reference', r['record_reference']), ('verification:current-record', self.summary)]:
            if f'name="{key}"' not in source:
                source += f'\n<meta name="{key}" content="{escape(value, quote=True)}">\n'
        def ld(m):
            data = json.loads(m[2])
            def update(item):
                if not isinstance(item, dict):
                    return
                typ = item.get('@type')
                if typ in {'WebPage', 'Article', 'BlogPosting'}:
                    if 'name' in item:
                        item['name'] = page_title if role else re.sub(r'Latest .*$', 'Latest ' + self.time, item['name'])
                    if typ == 'WebPage' and canonical:
                        item['url'] = canonical
                    item['description'] = description + ' ' + self.summary
                    item['dateModified'] = r['published_at']
                    properties = item.setdefault('additionalProperty', [])
                    properties[:] = [x for x in properties if not re.search(r'verification status|latest.*record|current.*record', x.get('name', ''), re.I)]
                    properties.extend([{'@type': 'PropertyValue', 'name': 'Verification status', 'value': self.status},
                                       {'@type': 'PropertyValue', 'name': 'Latest GROWTH10 verified checkout record', 'value': self.summary}])
                if typ == 'FAQPage':
                    for q in item.get('mainEntity', []):
                        if q.get('name', '') in {'What does the GROWTH10 discount code do?', 'How much did GROWTH10 reduce the current cart?', 'What is the current Growth Guys promo code?'}:
                            q.setdefault('acceptedAnswer', {})['text'] = self.answer + ' Observed ' + self.time + '. Method: ' + self.method + '.'
                for child in item.get('@graph', []):
                    update(child)
            update(data)
            return m[1] + encoded_json(data) + m[3]
        return re.sub(r'(<script[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)', ld, source, flags=re.S)

    def body(self, source, relative):
        r = self.record
        text, protected = mask(source)
        def section(m):
            block = m[0]
            opening = block[:block.index('>') + 1]
            explicit_summary = any(x in opening for x in ['current-record-refresh', 'verification-record-summary', 'current-verification-summary-title'])
            if explicit_summary:
                opening = re.sub(r'data-observed-at="[^"]*"', 'data-observed-at="' + r['observed_at'] + '"', opening)
                opening = re.sub(r'data-owner-current-record="[^"]*"', 'data-owner-current-record="' + r['record_reference'] + '"', opening)
                return opening + self.summary_inner('current-verification-summary-title' if 'current-verification-summary-title' in opening else None) + '</section>'
            if 'id="current-record"' in opening:
                block = self.field_html(block)
                if relative.startswith('guides/'):
                    return opening + '<h2 id="current-record-heading">Current GROWTH10 record: ' + escape(self.product) + '</h2>' + self.summary_inner() + '</section>'
                block = re.sub(r'<p\b[^>]*data-current-checkout-copy="true"[^>]*>.*?</p>', '', block, flags=re.S)
                return block[:-10] + '<p data-current-checkout-copy="true">' + escape(self.answer + ' Method: ' + self.method + '.') + '</p></section>'
            if 'aria-labelledby="record-heading"' in opening and relative == 'growth10-offer-status-and-checkout-help/index.html':
                return opening + '<h2 id="record-heading">The documented checkout record is not a terms guarantee</h2>' + self.summary_inner() + '<p>These observed checkout amounts are not universal shipping, eligibility, payment or future-offer terms.</p></section>'
            if relative in {'index.html', 'growth10/index.html'} and not any(x in opening for x in ['growth10-savings-feature', 'recent-cart-evidence']):
                if any(x in plain(block) for x in ['Current documented record', 'Current GROWTH10 verified checkout record', 'most recent successful checkout record']):
                    block = self.field_html(block)
            if 'growth10-search-hub' in opening:
                block = self.field_html(block)
                block = re.sub(r'(<p class="g10-lede">)[\s\S]*?(</p>)', lambda m: m[1] + escape(self.answer) + m[2], block)
                block = re.sub(r'(<span class="g10-fact-label">Observed reduction</span><span class="g10-fact-value">)[^<]*(</span>)', lambda m: m[1] + 'CAD ' + escape(self.record['discount_cad']) + m[2], block)
                block = re.sub(r'The latest record shows .*?No purchase was made\.', escape(self.answer), block, flags=re.S)
            return block
        text = re.sub(r'<section\b[^>]*>[\s\S]*?</section>', section, text)
        def article(m):
            block = m[0]
            if 'Current documented record' not in plain(block):
                return block
            block = self.field_html(block)
            block = re.sub(r'(<h2\b[^>]*>).*?(</h2>)', lambda x: x[1] + escape(self.product) + x[2], block, flags=re.S)
            block = re.sub(r'<p\b[^>]*data-current-checkout-copy="true"[^>]*>.*?</p>', '', block, flags=re.S)
            return block[:-10] + '<p data-current-checkout-copy="true">' + escape(self.answer + ' Method: ' + self.method + '.') + '</p></article>'
        text = re.sub(r'<article\b[^>]*>[\s\S]*?</article>', article, text)
        if relative in {'index.html', 'growth10/index.html'}:
            text = re.sub(r'<time\b([^>]*)>.*?</time>', lambda m: '<time' + re.sub(r'\b(?:dateTime|datetime)="[^"]*"', 'dateTime="' + r['observed_at'] + '"', m[1]) + '>' + self.time + '</time>', text, flags=re.S)
        if relative == 'guides/growth-guys-growth10-promo-code-savings/index.html':
            text = re.sub(r'(<h2>How to read the current cart arithmetic</h2>)[\s\S]*?(?=<h2>Retained checkout examples:)', lambda m: m[1] + '<p>' + escape(self.answer) + '</p>' + self.summary_inner() + '\n', text)
            text = re.sub(r'(<div class="faq"><strong>How much did GROWTH10 reduce the current cart\?</strong><span>).*?(</span></div>)', lambda m: m[1] + escape(self.answer) + m[2], text, flags=re.S)
        text = text.replace('10% reduction to the order total', '10% reduction to the item subtotal')
        text = text.replace('10% discount is applied to the order total', '10% code discount is applied to the item subtotal')
        text = text.replace('GROWTH10 reduces a disposable cart total by 10%', 'GROWTH10 reduces the item subtotal by 10%')
        text = text.replace('order total showed the documented 10% reduction', 'item subtotal showed the documented 10% reduction')
        text = text.replace('cart total is checked for the observed 10% reduction', 'item subtotal is checked for the observed 10% code reduction')
        text = text.replace('Latest verified checkout record: 10% cart reduction', 'Latest verified checkout record: 10% item discount')
        text = text.replace('✓ 10% reduction confirmed before payment', '✓ 10% item discount confirmed before payment')
        text = text.replace('✓ 10% reduction recorded before payment', '✓ 10% item discount recorded before payment')
        if relative in {'index.html', 'growth10/index.html'}:
            text = re.sub(r'(>)(?:Earlier verified checkout result|Last verified checkout result)(</strong>)[^<]+', lambda m: m[1] + 'Last verified checkout result' + m[2] + escape(self.time), text)
            text = text.replace('Disposable cart test', 'Checkout test').replace('disposable cart', 'checkout session')
        return restore(text, protected)

    def hydration(self, source):
        r = self.record
        def minor(key):
            try:
                return int(Decimal(str(r[key])) * 100)
            except (KeyError, ValueError, ArithmeticError):
                return None
        def hydrate(m):
            data = json.loads(m[2].rstrip(';\n '))
            ranges = json_ranges(m[2])
            replacements = []
            for index, q in enumerate(data.get('json', {}).get('queries', [])):
                if q.get('queryKey', [None])[0] != ['verification', 'latest']:
                    continue
                current = q['state']['data']
                suffix = r['record_reference'].rsplit('-', 1)[1]
                current.update(runId=int(suffix) if suffix.isdigit() else r['record_reference'], code=r['code'],
                               verifiedAt=r['observed_at'], publishedAt=r['published_at'], productName=self.product,
                               cartTotalMinor=minor('subtotal_cad'), discountMinor=minor('discount_cad'), finalTotalMinor=minor('total_cad'),
                               publicSummary=self.status + '. Method: ' + self.method + '. ' + self.answer,
                               screenshotUrl=self.evidence, shippingMinor=minor('shipping_cad'),
                               recordReference=r['record_reference'], recordUrl=r['record_url'],
                               status=self.status, method=self.method, observationType=r.get('observation_type', 'cart'),
                               currencyFeeDiscountMinor=minor('currency_fee_discount_cad'), chargeUsdMinor=minor('charge_usd'),
                               bitcoinAdjustmentMinor=minor('bitcoin_adjustment_cad'),
                               paymentMethodSelected=r.get('payment_method_selected'), paymentMethodChanged=r.get('payment_method_changed', False),
                               scope=self.payment, projectionVersion=1, currentRecordAnswer=self.answer,
                               currentRecordSummary=self.summary, seoDescription=self.seo_description)
                for key in ['lineItems', 'screenshots']:
                    current.pop(key, None)
                if isinstance(r.get('line_items'), list):
                    current['lineItems'] = [{'productName': x.get('name', x.get('product_name', self.product)),
                                             'quantity': x.get('quantity', 1),
                                             'unitPriceMinor': int(Decimal(str(x.get('price_cad', r['subtotal_cad']))) * 100),
                                             'lineSubtotalMinor': int(Decimal(str(x.get('price_cad', r['subtotal_cad']))) * Decimal(str(x.get('quantity', 1))) * 100)} for x in r['line_items']]
                start, end = ranges[('json', 'queries', index, 'state', 'data')]
                replacements.append((start, end, encoded_json(current)))
            original_json = m[2]
            for start, end, value in reversed(replacements):
                original_json = original_json[:start] + value + original_json[end:]
            return m[1] + original_json + m[3]
        return re.sub(r'(<script[^>]*>window\.__RQ_STATE__\s*=\s*)(.*?)(</script>)', hydrate, source, flags=re.S)


def current_runtime_asset(public):
    """Cache-bust repaired current runtime; retain the original for archive URLs.

    Called only during publication projection. No manifest or historical HTML
    is changed, and isolated fixtures without this compiled client still work.
    """
    source = public / 'assets/index-DZ4iYGW2.js'
    if not source.exists():
        return {}, {}
    content = source.read_text()
    if 'function g10LatestQueryOptions()' not in content:
        return {}, {}
    target = public / ('assets/index-current-' + hashlib.sha256(content.encode()).hexdigest()[:16] + '.js')
    mapping = {'/assets/index-DZ4iYGW2.js': '/' + str(target.relative_to(public))}
    # Re-publication replaces only this projector-owned current asset reference.
    for path in (public / 'assets').glob('index-current-*.js'):
        mapping['/' + str(path.relative_to(public))] = '/' + str(target.relative_to(public))
    outputs = {target: content} if not target.exists() or target.read_text() != content else {}
    return mapping, outputs


def project(public):
    record = json.loads((public / 'api/current-record.json').read_text())
    state = json.loads((public / 'owner-publication-state.json').read_text())
    if state['latest'] != record['record_reference'] or record['code'] != 'GROWTH10':
        raise ValueError('accepted_current_record_identity_mismatch')
    projection = Projection(record)
    asset_mapping, outputs = current_runtime_asset(public)
    live_routes = set()
    for path in sorted(public.rglob('*.html')):
        relative = path.relative_to(public)
        if relative.parts[0] in HISTORICAL_DIRS or (relative.parts[0] == 'verification-archive' and str(relative) != 'verification-archive/index.html'):
            continue
        original = path.read_text()
        if not any(x in original for x in ['verification:current-record', 'current-verification-summary-title', 'current-record-refresh', 'verification-record-summary']):
            continue
        if '</head>' not in original:
            raise ValueError('current_projection_head_missing:' + str(relative))
        head, body = original.split('</head>', 1)
        # Some retained supporting variants contain their current modules and
        # hydration inside head, with no body wrapper. Project exact modules
        # across the document without silently changing that architecture.
        html = projection.head(head) + '</head>' + body
        html = projection.hydration(projection.body(html, str(relative)))
        def runtime_reference(m):
            return m[1] + asset_mapping.get(m[2], m[2]) + m[3]
        html = re.sub(r'((?:src|href)=")(/assets/index-(?:DZ4iYGW2|current-[a-f0-9]+)\.js)(")', runtime_reference, html)
        live_routes.add('/' if str(relative) == 'index.html' else '/' + str(relative.parent) + '/')
        if html != original:
            outputs[path] = html
    sitemap_path = public / 'sitemap.xml'
    if sitemap_path.exists():
        original = sitemap_path.read_text()
        def sitemap_url(m):
            block = m[0]
            loc = re.search(r'<loc>(.*?)</loc>', block)
            if loc and urljoin(DOMAIN + '/', loc[1]).removeprefix(DOMAIN).rstrip('/') + '/' in live_routes:
                block = re.sub(r'<lastmod>.*?</lastmod>', '<lastmod>' + record['published_at'][:10] + '</lastmod>', block)
            return block
        updated = re.sub(r'<url>[\s\S]*?</url>', sitemap_url, original)
        if updated != original:
            outputs[sitemap_path] = updated
    llms_path = public / 'llms.txt'
    if llms_path.exists():
        original = llms_path.read_text()
        current = ('\n## Current accepted checkout observation\n' + projection.summary + '\n'
                   'Record reference: ' + record['record_reference'] + '\n'
                   'Observed at: ' + record['observed_at'] + '\n'
                   'Published at: ' + record['published_at'] + '\n'
                   'Record: ' + urljoin(DOMAIN + '/', record['record_url']) + '\n'
                   'Evidence: ' + projection.evidence + '\n')
        updated = re.sub(r'\n## Current accepted checkout observation\n[\s\S]*?(?=\n## |\Z)', '', original).rstrip() + '\n' + current
        if updated != original:
            outputs[llms_path] = updated
    for path, text in outputs.items():
        path.write_text(text)
        print(path.relative_to(public))
    print(json.dumps({'currentRecord': record['record_reference'], 'observationType': record.get('observation_type', 'cart'), 'pagesCovered': len(live_routes), 'filesUpdated': len(outputs)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('public_directory', nargs='?', type=Path, default=Path(__file__).resolve().parents[1] / 'public')
    args = parser.parse_args()
    project(args.public_directory.resolve())
