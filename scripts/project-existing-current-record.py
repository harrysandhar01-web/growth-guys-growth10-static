"""Project the existing accepted current JSON; never collect or publish evidence."""
from pathlib import Path
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape

public = Path(__file__).resolve().parents[1] / 'public'
record = json.loads((public / 'api/current-record.json').read_text())
state = json.loads((public / 'owner-publication-state.json').read_text())
assert state['latest'] == record['record_reference'] and record['code'] == 'GROWTH10'
observed = datetime.fromisoformat(record['observed_at'].replace('Z', '+00:00')).astimezone(ZoneInfo('America/Toronto'))
date = f"{observed:%B} {observed.day}, {observed.year}"
time = f"{date} at {observed.hour % 12 or 12}:{observed.minute:02d} {'a.m.' if observed.hour < 12 else 'p.m.'} {observed:%Z}"
product = record['product_name']
summary = f"Current documented record; {product}; observed {time}; subtotal CAD {record['subtotal_cad']}; discount CAD {record['discount_cad']}; total CAD {record['total_cad']}; GROWTH10; {record['status']}. {record['scope']}"
pages = ['index.html', 'growth10/index.html', 'discount-codes/index.html', 'how-we-verify/index.html', 'verification-history/index.html', 'growth10-offer-status-and-checkout-help/index.html', 'verification-archive/index.html']


def current_text(text):
    # Only invoked on explicitly current sections, never archive/history rows.
    text = re.sub(r'(?:October|November) \d{1,2}, 2026(?: at (?:approximately )?\d{1,2}:\d{2} (?:a\.m\.|p\.m\.|AM|PM) (?:EDT|EST))?', lambda m: time if ' at ' in m[0] else date, text)
    text = re.sub(r'(dateTime|datetime|data-observed-at)="[^"]+"', lambda m: f'{m[1]}="{record["observed_at"]}"', text)
    text = re.sub(r'(?:hCG 7,000 IU — Single vial|Retatrutide 10mg - Single vial|TB-500 5mg - Single vial|Semaglutide 5mg single vial|Tirzepatide 10mg - Single vial)', product, text)
    text = text.replace('$32.40 CAD', '$' + record['total_cad'] + ' CAD').replace('$64.80 CAD', '$' + record['total_cad'] + ' CAD')
    text = text.replace('CAD 64.80', 'CAD ' + record['total_cad']).replace('CAD 45.00', 'CAD ' + record['total_cad'])
    text = text.replace('$36.00 CAD', '$' + record['total_cad'] + ' CAD')
    text = text.replace('$40.00 CAD', '$' + record['subtotal_cad'] + ' CAD').replace('$4.00 CAD', '$' + record['discount_cad'] + ' CAD')
    text = text.replace('CAD 5.00 on a CAD 50.00', f"CAD {record['discount_cad']} on a CAD {record['subtotal_cad']}")
    text = re.sub(r'href="/(?:owner-records/growth10-owner-[^/]+|verification-archive/growth10-observed-[^/]+|observations/2026-[^/]+)/"', f'href="{record["record_url"]}"', text)
    text = re.sub(r'href="/evidence/2026-11-(?:06|09)/[^\"]+"', f'href="{record["evidence_url"]}"', text)
    return text

for relative in pages:
    path = public / relative
    original = path.read_text()
    html = original
    # Metadata belongs to the current projection, not to an accepted archive record.
    head, body = html.split('</head>', 1)
    head = re.sub(r'<title>(.*?)</title>', lambda m: '<title>' + re.sub(r'Latest .*$', 'Latest ' + time, m[1]) + '</title>', head)
    def meta(m):
        tag = m[0]
        key = re.search(r'(?:name|property)="([^"]+)"', tag)
        if not key:
            return tag
        key = key[1]
        value = None
        if key == 'verification:date': value = time
        elif key == 'verification:record-reference': value = record['record_reference']
        elif key == 'verification:current-record': value = summary
        elif key in ['description', 'og:description', 'twitter:description']:
            old = re.search(r'content="([^"]*)"', tag)[1]
            base = old.split('Current documented record:')[0].strip()
            if relative in ['index.html', 'growth10/index.html']:
                base = 'GROWTH10 Growth Guys promo code and discount code with a dated pre-payment cart record. No purchase was made.'
            value = base + ' ' + summary
        elif key in ['og:title', 'twitter:title']:
            old = re.search(r'content="([^"]*)"', tag)[1]
            value = re.sub(r'Latest .*$', 'Latest ' + time, old)
        if value is not None:
            tag = re.sub(r'content="[^"]*"', 'content="' + escape(value, quote=True) + '"', tag)
        return tag
    head = re.sub(r'<meta\b[^>]*>', meta, head)
    def ldjson(m):
        data = json.loads(m[2])
        for item in data.get('@graph', []):
            if item.get('@type') != 'WebPage': continue
            if 'Latest ' in item.get('name', ''): item['name'] = re.sub(r'Latest .*$', 'Latest ' + time, item['name'])
            item['description'] = item.get('description', '').split('Current documented record:')[0].strip() + ' ' + summary
            for prop in item.get('additionalProperty', []):
                if prop.get('name') == 'Current GROWTH10 record': prop['value'] = summary
                elif 'Documented checkout record' in prop.get('value', ''): prop['value'] = f'Documented checkout record — {time}; Code GROWTH10; 10% discount observed'
        return m[1] + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + m[3]
    head = re.sub(r'(<script[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)', ldjson, head, flags=re.S)
    def section(m):
        block = m[0]
        opening = block.split('>', 1)[0]
        if 'growth10-search-hub' in opening:
            # Preserve all historical date-finder cards byte-for-byte.
            prefix, history = block.split('<div class="g10-history"', 1)
            prefix = current_text(prefix)
            prefix = re.sub(r'The latest record shows .*?No purchase was made\.', f"The latest record shows CAD {record['discount_cad']} in code savings from a CAD {record['subtotal_cad']} basket to a CAD {record['total_cad']} displayed total before payment. No purchase was made.", prefix)
            return prefix + '<div class="g10-history"' + history
        explicit = any(x in opening for x in ['current-record-refresh', 'verification-record-summary', 'current-verification-summary-title', 'id="current-record"'])
        secondary = relative in ['index.html', 'growth10/index.html'] and re.search(r'November (?:6|11), 2026', block) and 'archive-preview-card' not in block
        if relative == 'growth10-offer-status-and-checkout-help/index.html' and 'aria-labelledby="record-heading"' in opening:
            explicit = True
        if explicit or secondary: return current_text(block)
        return block
    body = re.sub(r'<section\b[^>]*>[\s\S]*?</section>', section, body)
    if relative in ['index.html', 'growth10/index.html']:
        body = re.sub(r'(<time dateTime=")(2026-11-(?:06|11)[^"]+)(">)(November (?:6|11), 2026 at [^<]+)(</time>)', lambda m: m[1] + record['observed_at'] + m[3] + time + m[5], body)
    def hydration(m):
        data = json.loads(m[2].rstrip(';\n '))
        for query in data['json']['queries']:
            if query.get('queryKey', [None])[0] != ['verification', 'latest']: continue
            current = query['state']['data']
            current.update(runId=int(record['record_reference'].rsplit('-', 1)[1]), code=record['code'], verifiedAt=record['observed_at'], publishedAt=record['published_at'], productName=product, cartTotalMinor=round(float(record['subtotal_cad']) * 100), discountMinor=round(float(record['discount_cad']) * 100), finalTotalMinor=round(float(record['total_cad']) * 100), publicSummary=record['status'] + '.', screenshotUrl='https://growthguysgrowth10.ca' + record['evidence_url'], shippingMinor=None, recordReference=record['record_reference'], recordUrl=record['record_url'])
        return m[1] + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + m[3]
    body = re.sub(r'(<script>window\.__RQ_STATE__ = )(.*?)(</script>)', hydration, body, flags=re.S)
    html = head + '</head>' + body
    if html != original:
        path.write_text(html)
        print(relative)
