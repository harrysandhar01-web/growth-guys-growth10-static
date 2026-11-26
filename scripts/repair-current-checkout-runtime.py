"""Repair only the compiled current-checkout runtime; no evidence or publication.

Usage: python3 scripts/repair-current-checkout-runtime.py --apply | --test
The projector cache-busts the resulting asset only when publication runs.
Tests use disposable local fixtures, never the accepted production record.
"""
from pathlib import Path
import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / 'public/assets/index-DZ4iYGW2.js'

LATEST_OPTIONS = '''function g10LatestQueryOptions(){const a=window.__RQ_STATE__?.json?.queries?.find(n=>JSON.stringify(n.queryKey?.[0])==='["verification","latest"]')?.state?.data;return a?.projectionVersion===1?{enabled:!1,staleTime:Infinity,refetchInterval:!1,refetchOnMount:!1,refetchOnWindowFocus:!1,refetchOnReconnect:!1,retry:!1}:{staleTime:6e4,refetchInterval:3e5,retry:1}}'''
CURRENT_COPY = '''function g10CurrentCheckoutCopy(){const{currentRecord:a}=Br();return a?.projectionVersion===1&&a.currentRecordAnswer?c.jsx("p",{"data-current-checkout-copy":"true",className:"mt-3 text-sm leading-relaxed",children:a.currentRecordAnswer+" Method: "+a.method+"."}):null}'''
CURRENT_SCHEMA = '''function g10CurrentSchema(a,n,i){if(!a||typeof a!=="object")return a;if(Array.isArray(a))return a.map(s=>g10CurrentSchema(s,n,i));let s={...a};if(s["@graph"])s["@graph"]=g10CurrentSchema(s["@graph"],n,i);if(["WebPage","Article","BlogPosting"].includes(s["@type"])){s.description=n.seoDescription+" "+n.currentRecordSummary;s.dateModified=n.publishedAt;if(s["@type"]==="WebPage")s.url=i;s.additionalProperty=[...(s.additionalProperty??[]).filter(l=>!/verification status|latest.*record|current.*record/i.test(l.name??"")),{"@type":"PropertyValue",name:"Verification status",value:n.status},{"@type":"PropertyValue",name:"Latest GROWTH10 verified checkout record",value:n.currentRecordSummary}]}if(s["@type"]==="FAQPage"){s.dateModified=n.publishedAt;s.mainEntity=(s.mainEntity??[]).map(l=>["What does the GROWTH10 discount code do?","How much did GROWTH10 reduce the current cart?","What is the current Growth Guys promo code?","What discount does GROWTH10 give?","Who verifies GROWTH10?","Does GROWTH10 still work in 2026?"].includes(l.name)?{...l,acceptedAnswer:{...l.acceptedAnswer,text:n.currentRecordAnswer+" Observed "+zG(new Date(n.verifiedAt))+". Method: "+n.method+"."}}:l)}return s}'''
SEO = '''function da({title:a,description:n,canonical:i,jsonLd:s,breadcrumbs:l,pageModifiedDate:u}){const{verifiedIso:p,publishedIso:f,verifiedLabel:m,methodLabel:y,runId:v,productName:b,cartTotalMinor:x,discountMinor:T,finalTotalMinor:G,currentRecord:_record}=Br(),k=new URL(i).pathname,j=gH.has(k)&&!!(p&&m),_projected=j&&_record?.projectionVersion===1,D=j?`${a} | Latest ${m}`:a,K=Ia(y),Z=Q=>Q===null?"not published":`$${(Math.abs(Q)/100).toFixed(2)} CAD`,$=_projected?_record.currentRecordSummary:j&&v&&b?`Current documented record; ${b}; observed ${m}; subtotal ${Z(x)}; discount ${Z(T)}; total ${Z(G)}; GROWTH10; Verified at checkout. ${la}`:void 0,L=_projected?_record.seoDescription:$?`${n} Latest accepted GROWTH10 cart observation: ${$}`:n,_modified=_projected?_record.publishedAt:u,_existingCanonical=document.querySelector('link[rel="canonical"]')?.href,_canonical=_existingCanonical&&new URL(_existingCanonical).pathname.replace(/\\/$/,"")===k.replace(/\\/$/,"")?_existingCanonical:i;return H.useEffect(()=>{document.title=D;let Q=document.querySelector('meta[name="description"]');Q||(Q=document.createElement("meta"),Q.name="description",document.head.appendChild(Q)),Q.content=L;let C=document.querySelector('link[rel="canonical"]');C||(C=document.createElement("link"),C.rel="canonical",document.head.appendChild(C)),C.href=_canonical;const q=(J,ae,ee="property")=>{let ne=document.querySelector(`meta[${ee}="${J}"]`);ne||(ne=document.createElement("meta"),ne.setAttribute(ee,J),document.head.appendChild(ne)),ne.content=ae};q("og:title",D),q("og:description",L),q("og:url",_canonical),q("og:type","website"),q("og:site_name",kn),q("twitter:card","summary_large_image","name"),q("twitter:title",D,"name"),q("twitter:description",L,"name"),_modified&&q("article:modified_time",_modified),_projected&&q("og:updated_time",_modified),document.querySelectorAll('script[data-seo="true"], script[data-ssr-seo="true"]').forEach(J=>J.remove());const X=[];return X.push({"@context":"https://schema.org","@type":"WebSite",name:kn,url:Ue}),X.push({"@context":"https://schema.org","@type":"WebPage",name:D,description:_projected?L+" "+$:L,...j?{..._modified||f?{dateModified:_modified??f}:{},additionalProperty:[{"@type":"PropertyValue",name:"Latest GROWTH10 cart observation",value:_projected?$: `${K} ${la} — ${m}; Code GROWTH10; 10% discount observed`},...$?[{"@type":"PropertyValue",name:"Current GROWTH10 record",value:$}]:[]]}:{},...!j&&u?{dateModified:u}:{},url:_canonical}),X.push({"@context":"https://schema.org","@type":"Offer",name:"Growth Guys Discount Code GROWTH10",description:_projected?L:"GROWTH10 information with a documented 10% pre-payment cart reduction observation at growthguys.com.",url:Lu,priceCurrency:"CAD",priceSpecification:{"@type":"UnitPriceSpecification",priceType:"https://schema.org/SalePrice"},seller:{"@type":"Organization",name:"Growth Guys",url:Ki}}),X.push({"@context":"https://schema.org","@type":"Organization",name:kn,url:Ue,description:"Independent resource documenting GROWTH10, a Growth Guys discount code also commonly sought using coupon-code and promo-code terminology, through cart-observation records.",sameAs:[pw,QG]}),l&&l.length>0&&X.push({"@context":"https://schema.org","@type":"BreadcrumbList",itemListElement:l.map((J,ae)=>({"@type":"ListItem",position:ae+1,name:J.name,item:J.url}))}),s&&X.push(_projected?g10CurrentSchema(s,_record,_canonical):s),X.forEach(J=>{const ae=document.createElement("script");ae.type="application/ld+json",ae.setAttribute("data-seo","true"),ae.textContent=JSON.stringify(J),document.head.appendChild(ae)}),()=>{document.querySelectorAll('script[data-seo="true"], script[data-ssr-seo="true"]').forEach(J=>J.remove()),_modified&&document.querySelector('meta[property="article:modified_time"]')?.remove()}},[D,L,_canonical,s,l,u,j,y,K,m,p,f,v,b,x,T,G,$,_record,_projected,_modified]),null}'''


def once(source, old, new, label):
    if source.count(new) == 1 and source.count(old) == new.count(old):
        print('already repaired:', label)
        return source
    if source.count(old) != 1:
        raise ValueError(f'unique_runtime_match_failed:{label}:{source.count(old)}')
    print('matched once:', label)
    return source.replace(old, new, 1)


def apply():
    original = ASSET.read_text()
    source = original
    source = once(source, 'function FG({children:a}){const n=sr.verification.latest.useQuery(void 0,{staleTime:6e4,refetchInterval:3e5,retry:1})', LATEST_OPTIONS + 'function FG({children:a}){const n=sr.verification.latest.useQuery(void 0,g10LatestQueryOptions())', 'projected latest snapshot query')
    source = once(source, 'methodLabel:n.data?.publicSummary??null,runId:', 'currentRecord:n.data??null,methodLabel:n.data?.method??n.data?.publicSummary??null,runId:', 'method and accepted current fields')
    source = once(source, 'function Ia(a){return a?.toLowerCase().includes("independent cart observation")?aH:tH}', 'function Ia(a){return a==="Automated laptop checkout verification"?a:a?.toLowerCase().includes("independent cart observation")?aH:tH}' + CURRENT_COPY + CURRENT_SCHEMA, 'current method; retain legacy labels')
    source = once(source, 'c.jsx("p",{"data-loc":"client/src/components/CurrentVerificationSummary.tsx:47"', 'c.jsx(g10CurrentCheckoutCopy,{}),c.jsx("p",{"data-loc":"client/src/components/CurrentVerificationSummary.tsx:47"', 'current global summary checkout details')
    source = once(source, 'v=n??"Verification record pending",b=a?Ia(i):"Verification Pending";', 'v=n??"Verification record pending",b=a?(Br().currentRecord?.status??Ia(i)):"Verification Pending";', 'home current status')
    source = once(source, 'c.jsxs("div",{"data-loc":"client/src/pages/Home.tsx:138"', 'c.jsx(g10CurrentCheckoutCopy,{}),c.jsxs("div",{"data-loc":"client/src/pages/Home.tsx:138"', 'home full accepted checkout copy')
    source = once(source, 'D=l?Ia(f):"Verification Pending",K=[', 'D=l?(Br().currentRecord?.status??Ia(f)):"Verification Pending",K=[', 'current record status')
    source = once(source, 'c.jsx(il,{"data-loc":"client/src/pages/Growth10.tsx:320"', 'c.jsx(g10CurrentCheckoutCopy,{}),c.jsx(il,{"data-loc":"client/src/pages/Growth10.tsx:320"', 'current record currency and USD details')
    source = once(source, 'function WH(){const a=sr.verification.latest.useQuery(),', 'function WH(){const a=sr.verification.latest.useQuery(void 0,g10LatestQueryOptions()),', 'history latest snapshot query; archive query unchanged')
    # Only the current-record function's two incorrect final-total claims.
    for old, new in [
        ('A successful result requires GROWTH10 to apply a 10% reduction to the order total before payment.', 'A successful result requires GROWTH10 to apply a 10% code discount to the item subtotal before payment.'),
        ('a pre-payment cart observation confirms that GROWTH10 reduces the order total by 10%.', 'a pre-payment cart observation confirms that GROWTH10 reduces the item subtotal by 10%.')
    ]:
        source = once(source, old, new, 'current FAQ item discount boundary')
    start = source.index('function da({title:a,description:n,canonical:i,jsonLd:s,breadcrumbs:l,pageModifiedDate:u})')
    if source.count('function da({title:a,description:n,canonical:i,jsonLd:s,breadcrumbs:l,pageModifiedDate:u})') != 1:
        raise ValueError('unique_seo_function_match_failed')
    end = source.index('const Yy=', start)
    if source[start:end] != SEO:
        if 'L=$?`${n} Latest accepted GROWTH10 cart observation: ${$}`:n;' not in source[start:end]:
            raise ValueError('unexpected_seo_function_shape')
        print('matched once: current SEO function')
        source = source[:start] + SEO + source[end:]
    else:
        print('already repaired: current SEO function')
    # No historical component or archive money/date/summary code is changed.
    source = once(source,
                  'jc.hasChildNodes()?sy.hydrateRoot(jc,ob):sy.createRoot(jc).render(ob);',
                  'g10LatestQueryOptions().enabled===!1?sy.createRoot(jc).render(ob):jc.hasChildNodes()?sy.hydrateRoot(jc,ob):sy.createRoot(jc).render(ob);',
                  'projected static snapshot bootstrap; legacy hydration retained')
    for start_token, end_token in [('function dH(', 'const gw='), ('function SH(', 'function '), ('function qO(', 'function ')]:
        if start_token in original:
            at = original.index(start_token)
            end_at = original.index(end_token, at + len(start_token))
            assert original[at:end_at] in source, 'historical_component_changed:' + start_token
    subprocess.run(['node', '--check', '--input-type=module'], input=source, text=True, check=True)
    if source != original:
        ASSET.write_text(source)
    print('runtime syntax valid; only uniquely selected fragments repaired')


NODE_TEST = r'''
const assert=require('node:assert/strict'),fs=require('node:fs');
const source=fs.readFileSync(process.argv[2],'utf8'),fixture=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
function between(start,end){let i=source.indexOf(start);assert(i>=0,start);return source.slice(i,source.indexOf(end,i+start.length))}
const record=fixture.record,window={__RQ_STATE__:fixture.hydration},c={jsx:(type,props)=>({type,props}),jsxs:(type,props)=>({type,props})};
const tH='Verified at checkout.',aH='Verified at checkout.',la='Documented pre-payment cart observation; no purchase was made.';
const gH=new Set(['/','/growth10','/guides/fixture']),Ue='https://growthguysgrowth10.ca',kn='GROWTH10 Verification Desk',Lu='https://growthguys.com/shop/',Ki='https://growthguys.com',pw='instagram',QG='tiktok';
let context={},effects=[];const H={useEffect:fn=>effects.push(fn)};
function Br(){return context}
eval(between('function zG(', 'function g10LatestQueryOptions('));
eval(between('function g10LatestQueryOptions(', 'function FG('));
eval(between('function Ia(', 'function rH('));
eval(between('function da(', 'const Yy='));
assert.equal(Ia('Automated laptop checkout verification'),'Automated laptop checkout verification');
for(const historic of [undefined,'Verified at checkout.','Independent cart observation','Automated independent cart observation']) assert.equal(Ia(historic),'Verified at checkout.');
assert.equal(g10LatestQueryOptions().enabled,false);assert.equal(g10LatestQueryOptions().refetchInterval,false);
window.__RQ_STATE__={json:{queries:[]}};assert.equal(g10LatestQueryOptions().staleTime,60000);window.__RQ_STATE__=fixture.hydration;
const n={data:record,isLoading:false},sr={verification:{latest:{useQuery:()=>n}}},uw={Provider:'Provider'};
eval(between('function FG(', 'function Br('));context=FG({children:null}).props.value;
assert.equal(context.methodLabel,record.method);assert.equal(context.verifiedIso,'2026-11-26T06:46:23.509Z');assert.equal(context.publishedIso,record.publishedAt);
assert.equal(context.currentRecord.currencyFeeDiscountMinor,124);assert.equal(context.currentRecord.chargeUsdMinor,4801);
const rendered=g10CurrentCheckoutCopy();for(const term of ['55.00','5.50','20.00','1.24','68.26','48.01',record.method]) assert(rendered.props.children.includes(term),term);
function doc(canonical){const nodes=[];function element(tag){return{tag,attrs:{},setAttribute(k,v){this.attrs[k]=v},remove(){const at=nodes.indexOf(this);if(at>=0)nodes.splice(at,1)}}}const can=element('link');can.rel='canonical';can.href=canonical;nodes.push(can);return{nodes,head:{appendChild:e=>nodes.push(e)},createElement:element,querySelector(sel){if(sel==='link[rel="canonical"]')return nodes.find(e=>e.rel==='canonical');let m=sel.match(/^(?:meta)\[(name|property)="([^"]+)"\]$/);return m?nodes.find(e=>e[m[1]]===m[2]||e.attrs[m[1]]===m[2]):null},querySelectorAll(){return nodes.filter(e=>e.tag==='script'&&(e.attrs['data-seo']==='true'||e.attrs['data-ssr-seo']==='true'))}}}
let document=doc(Ue+'/growth10/');const schema={'@graph':[{'@type':'WebPage',url:Ue+'/wrong',description:'subtotal minus coupon equals final total',dateModified:'1999-01-01'},{'@type':'FAQPage',mainEntity:[{name:'What discount does GROWTH10 give?',acceptedAnswer:{text:'10% reduction to order total'}}]}]};
da({title:'Current record',description:'old generic copy',canonical:Ue+'/growth10',jsonLd:schema,pageModifiedDate:'1999-01-01'});effects.pop()();
assert.equal(document.querySelector('link[rel="canonical"]').href,Ue+'/growth10/');assert.equal(document.querySelector('meta[name="description"]').content,record.seoDescription);assert.equal(document.querySelector('meta[property="article:modified_time"]').content,record.publishedAt);
const schemas=document.nodes.filter(e=>e.tag==='script').map(e=>JSON.parse(e.textContent));
for(const page of schemas.filter(e=>e['@type']==='WebPage')){assert.equal(page.url,Ue+'/growth10/');assert.equal(page.dateModified,record.publishedAt);assert(page.description.includes('68.26'))}
const graph=schemas.find(e=>e['@graph'])['@graph'];assert.equal(graph[0].url,Ue+'/growth10/');assert.equal(graph[0].dateModified,record.publishedAt);assert(graph[1].mainEntity[0].acceptedAnswer.text.includes('1.24'));
assert.equal(schema['@graph'][0].description,'subtotal minus coupon equals final total','input schemas not mutated');
// SPA navigation must not inherit the previous route canonical.
document=doc(Ue+'/growth10/');da({title:'Guide',description:'guide copy',canonical:Ue+'/guides/fixture'});effects.pop()();assert.equal(document.querySelector('link[rel="canonical"]').href,Ue+'/guides/fixture');
// A historical detail page gets its own original description/schema/date, not today's checkout.
document=doc(Ue+'/verification-archive/old/');const historic={'@type':'WebPage',description:'historical 57.60',dateModified:'2026-11-09'};da({title:'Historical',description:'Historical original record',canonical:Ue+'/verification-archive/old',jsonLd:historic,pageModifiedDate:'2026-11-09'});effects.pop()();assert.equal(document.querySelector('meta[name="description"]').content,'Historical original record');assert.equal(document.querySelector('meta[property="article:modified_time"]').content,'2026-11-09');assert.deepEqual(JSON.parse(document.nodes.filter(e=>e.tag==='script').at(-1).textContent),historic);
// Alternate accepted hydration values prove that runtime money and dates are not globally hardcoded.
context={...context,verifiedIso:'2026-12-02T10:00:00.000Z',verifiedLabel:'December 2, 2026',currentRecord:{...record,verifiedAt:'2026-12-02T10:00:00.000Z',currentRecordAnswer:'Fixture product subtotal CAD 100.00, discount CAD 10.00, shipping CAD 8.00, currency-fee discount CAD 2.00, final total CAD 96.00, USD 70.00.',currentRecordSummary:'December 2 fixture CAD 96.00',seoDescription:'Save 10% on a December 2 fixture; total CAD 96.00.'}};
assert(g10CurrentCheckoutCopy().props.children.includes('96.00'));assert(!g10CurrentCheckoutCopy().props.children.includes('68.26'));document=doc(Ue+'/growth10/');da({title:'Current',description:'old',canonical:Ue+'/growth10'});effects.pop()();assert(document.querySelector('meta[name="description"]').content.includes('96.00'));
console.log('PASS runtime: method, exact observed timestamp, published timestamp, all money fields, protected latest-query options, current SEO/schema, route canonicals, history, and alternate hydration');
'''


def test():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('projection', ROOT / 'scripts/project-current-checkout-copy.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    record = {
        'code': 'GROWTH10', 'status': 'Verified at checkout', 'method': 'Automated laptop checkout verification',
        'observation_type': 'checkout', 'product': 'Accepted checkout test fixture',
        'observed_at': '2026-11-26T06:46:23.509Z', 'published_at': '2026-11-26T06:55:00.000Z',
        'subtotal_cad': '55.00', 'discount_cad': '5.50', 'shipping_cad': '20.00',
        'currency_fee_discount_cad': '1.24', 'total_cad': '68.26', 'charge_usd': '48.01', 'bitcoin_adjustment_cad': '0.00',
        'payment_method_selected': 'Credit/Visa Debit', 'scope': 'fixture pre-payment only',
        'record_reference': 'growth10-fixture-123', 'record_url': '/owner-records/growth10-fixture-123/',
        'evidence_url': '/evidence/fixture/original.webp'
    }
    query = lambda key, data: {'queryKey': [key, {'type': 'query'}], 'state': {'data': data, 'dataUpdatedAt': 12345}}
    hydration = {'json': {'queries': [query(['verification', 'latest'], {'runId': 1, 'publicSummary': 'old'}), query(['verification', 'archive'], [{'id': 7, 'publicSummary': 'Historical original 57.60', 'executedAt': '2026-11-25T09:50:07.141Z'}])]}, 'meta': {'values': {'json.queries.1.state.data.0.executedAt': ['Date']}}}
    source = '<script>window.__RQ_STATE__=' + module.encoded_json(hydration) + ';</script>'
    projected = module.Projection(record).hydration(source)
    after = json.loads(projected.split('=', 1)[1].removesuffix(';</script>'))
    latest = after['json']['queries'][0]['state']['data']
    assert latest['verifiedAt'] == record['observed_at'] and latest['publishedAt'] == record['published_at']
    assert [latest[k] for k in ['cartTotalMinor', 'discountMinor', 'shippingMinor', 'currencyFeeDiscountMinor', 'finalTotalMinor', 'chargeUsdMinor']] == [5500, 550, 2000, 124, 6826, 4801]
    assert after['json']['queries'][1] == hydration['json']['queries'][1]
    assert after['meta'] == hydration['meta']
    assert module.encoded_json(hydration['json']['queries'][1]) in projected
    assert 'CAD 68.26' in latest['seoDescription'] and 'item subtotal' in latest['seoDescription']
    assert latest['method'] == record['method'] and latest['projectionVersion'] == 1
    assert module.Projection(record).hydration(projected) == projected
    with tempfile.TemporaryDirectory(prefix='.runtime-fixture-', dir=ROOT) as temp:
        public = Path(temp) / 'public'
        (public / 'api').mkdir(parents=True)
        (public / 'assets').mkdir()
        (public / 'api/current-record.json').write_text(json.dumps(record))
        (public / 'owner-publication-state.json').write_text(json.dumps({'latest': record['record_reference']}))
        (public / 'assets/index-DZ4iYGW2.js').write_bytes(ASSET.read_bytes())
        protected = '<!-- OWNER_RECORD_START --><p>Retained OWNER_RECORD original 57.60</p><!-- OWNER_RECORD_END -->'
        html = '<html><head><title>Fixture | Latest old</title><link rel="canonical" href="https://growthguysgrowth10.ca/growth10/"/><meta name="verification:current-record" content="old"/><script type="module" src="/assets/index-DZ4iYGW2.js"></script></head><body><section class="current-record-refresh">old</section>' + source + protected + '</body></html>'
        (public / 'growth10').mkdir()
        (public / 'growth10/index.html').write_text(html)
        historical = public / 'verification-archive/old/index.html'
        historical.parent.mkdir(parents=True)
        historical.write_text(html)
        module.project(public)
        current = (public / 'growth10/index.html').read_text()
        assert historical.read_text() == html and protected in current
        assert '/assets/index-current-' in current
        assert 'href="https://growthguysgrowth10.ca/growth10/"' in current
        assert len(list(public.rglob('*.html'))) == 2
        before = {p.relative_to(public): p.read_bytes() for p in public.rglob('*') if p.is_file()}
        module.project(public)
        assert before == {p.relative_to(public): p.read_bytes() for p in public.rglob('*') if p.is_file()}
        # Old fingerprints move forward only on current pages; archives remain byte-identical.
        with (public / 'assets/index-DZ4iYGW2.js').open('a') as out:
            out.write('\n// isolated fingerprint fixture\n')
        module.project(public)
        assert (public / 'growth10/index.html').read_text() != current and historical.read_text() == html
        fixture = Path(temp) / 'fixture.json'
        fixture.write_text(json.dumps({'record': latest, 'hydration': after}))
        subprocess.run(['node', '--input-type=commonjs', '-', str(ASSET), str(fixture)], input=NODE_TEST, text=True, check=True)
        # Exercise the real current-page selection in a disposable HTML-only
        # mirror; never run projection against the accepted production tree.
        mirror = Path(temp) / 'all-pages'
        (mirror / 'api').mkdir(parents=True)
        (mirror / 'assets').mkdir()
        (mirror / 'api/current-record.json').write_text(json.dumps(record))
        (mirror / 'owner-publication-state.json').write_text(json.dumps({'latest': record['record_reference']}))
        (mirror / 'assets/index-DZ4iYGW2.js').write_bytes(ASSET.read_bytes())
        originals = {}
        for path in (ROOT / 'public').rglob('*.html'):
            relative = path.relative_to(ROOT / 'public')
            text = path.read_text()
            originals[relative] = text
            target = mirror / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        with contextlib.redirect_stdout(io.StringIO()) as logs:
            module.project(mirror)
        report = json.loads(logs.getvalue().strip().splitlines()[-1])
        assert report['pagesCovered'] == 155, report
        assert len(list(mirror.rglob('*.html'))) == len(originals)
        for relative, original in originals.items():
            after_html = (mirror / relative).read_text()
            if relative.parts[0] in module.HISTORICAL_DIRS or (relative.parts[0] == 'verification-archive' and str(relative) != 'verification-archive/index.html'):
                assert after_html == original, 'historical_html_changed:' + str(relative)
            else:
                # Protected owner and archive modules are restored verbatim.
                _, spans = module.mask(original)
                for span in spans.values():
                    if not span.startswith('<script'):
                        assert span in after_html, 'protected_module_changed:' + str(relative)
        before = {p.relative_to(mirror): p.read_bytes() for p in mirror.rglob('*') if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()):
            module.project(mirror)
        assert before == {p.relative_to(mirror): p.read_bytes() for p in mirror.rglob('*') if p.is_file()}
        print('PASS all-page fixture: 155 current routes, unchanged HTML count, protected historical/OWNER_RECORD modules and repeat-publication idempotence')
    subprocess.run(['node', '--check', str(ASSET)], check=True)
    print('PASS projector: latest-only JSON update, archive/meta/OWNER_RECORD preservation, exact money/times, idempotence, publication-only fingerprinting and unchanged HTML counts')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--apply', action='store_true')
    group.add_argument('--test', action='store_true')
    args = parser.parse_args()
    apply() if args.apply else test()
