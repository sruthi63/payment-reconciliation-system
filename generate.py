"""Deterministic synthetic payment reconciliation data generator."""
from __future__ import annotations
import argparse, csv, hashlib, json, random
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SEED = 20261022
CURRENCIES = ["USD", "EUR", "GBP", "INR"]
STATUSES = ["created", "authorized", "captured", "failed", "refunded"]


def money(v):
    return str(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8"); return
    with path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(dict.fromkeys(k for row in rows for k in row.keys()))
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="raise")
        w.writeheader(); w.writerows(rows)

def generate(out: Path, merchants_n=2000, orders_n=50000, attempts_n=55000, batches_n=1000, bank_n=5000, seed=SEED):
    rng = random.Random(seed); out.mkdir(parents=True, exist_ok=True)
    merchants=[]; orders=[]; attempts=[]; events=[]; batches=[]; lines=[]; banks=[]; matches=[]; exceptions=[]; resolutions=[]; truth=[]
    start=date(2026,1,1)
    for i in range(1, merchants_n+1):
        merchants.append({"merchant_id":f"MER-{i:07d}","merchant_name":f"Merchant {i:05d}","country":rng.choice(["US","GB","IN","DE","SG"]),"default_currency":rng.choice(CURRENCIES),"status":"active","effective_from":str(start),"effective_to":""})
    # distribute attempts across orders; one attempt minimum per order when possible
    for i in range(1, orders_n+1):
        created=start+timedelta(days=rng.randrange(270))
        orders.append({"payment_id":f"PAY-2026-{i:08d}","merchant_id":f"MER-{rng.randint(1,merchants_n):07d}","amount":money(rng.uniform(5,1200)),"currency":rng.choice(CURRENCIES),"created_at":created.isoformat(),"status":"created"})
    attempt_by_payment=defaultdict(list)
    for i in range(1, attempts_n+1):
        p=orders[(i-1)%orders_n]; seq=len(attempt_by_payment[p['payment_id']])+1
        status=rng.choices(STATUSES,weights=[5,10,65,15,5])[0]
        ts=datetime.fromisoformat(p['created_at'])+timedelta(minutes=rng.randrange(1,180), days=rng.randrange(0,4))
        aid=f"ATT-{p['payment_id']}-{seq:02d}"
        attempts.append({"attempt_id":aid,"payment_id":p['payment_id'],"attempt_no":seq,"status":status,"amount":p['amount'],"currency":p['currency'],"created_at":ts.isoformat(timespec="seconds")})
        attempt_by_payment[p['payment_id']].append(aid)
        evtype="capture" if status=="captured" else ("refund" if status=="refunded" else status)
        event_amount = money(Decimal(p['amount']) * Decimal(str(round(rng.uniform(0.1, 0.8), 4)))) if status == 'refunded' else p['amount']
        events.append({"processor_event_id":f"EVT-{i:09d}","attempt_id":aid,"event_type":evtype,"event_status":"succeeded" if status in ("captured","refunded") else status,"amount":event_amount,"currency":p['currency'],"event_at":(ts+timedelta(minutes=rng.randrange(0,120))).isoformat(timespec="seconds"),"idempotency_key":f"IDEM-{i:09d}","ingest_status":"accepted"})
    # Build a fixed number of settlement batches from captured/refunded events, preserving fee arithmetic.
    eligible=[e for e in events if e['event_type'] in ('capture','refund') and e['event_status']=='succeeded']
    rng.shuffle(eligible)
    chunks=[eligible[i::batches_n] for i in range(batches_n)]
    for bi in range(1,batches_n+1):
        bid=f"SET-2026-{bi:06d}"; chunk=chunks[bi-1]
        cur=chunk[0]['currency'] if chunk else rng.choice(CURRENCIES)
        chunk=[e for e in chunk if e['currency']==cur]
        gross=Decimal('0.00'); fee=Decimal('0.00'); line_count=0
        for e in chunk:
            amt=Decimal(e['amount']); gross += amt if e['event_type']=='capture' else -amt
            if e['event_type']=='capture': fee += (amt*Decimal('0.029')+Decimal('0.30')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            line_count += 1
            lines.append({"settlement_line_id":f"STL-{bid}-{line_count:03d}","batch_id":bid,"processor_event_id":e['processor_event_id'],"line_type":e['event_type'],"amount":money(amt if e['event_type']=='capture' else -amt),"currency":cur,"created_at":e['event_at']})
        net=gross-fee
        dt=start+timedelta(days=bi%270 + rng.choice([1,1,2,3,7]))
        batches.append({"batch_id":bid,"processor_name":"SyntheticPay","currency":cur,"gross_amount":money(gross),"fee_amount":money(fee),"net_amount":money(net),"line_count":line_count,"settlement_date":dt.isoformat(),"status":"settled"})
    # Bank statement lines: include batch-referenced records plus unmatched lines to target count.
    for i,b in enumerate(batches[:bank_n],1):
        amount=Decimal(b['net_amount']); issue="none"; ref=b['batch_id']; curr=b['currency']
        # Deliberate, labelled cases among first six batches.
        if i==1: amount += Decimal('0.30'); issue="bank_amount_differs_by_fee"
        elif i==2: curr="ZZZ"; issue="currency_mismatch"
        elif i==3: ref="SET-2026-999999"; issue="unmatched_bank_record"
        elif i==4: issue="delayed_settlement"
        banks.append({"bank_line_id":f"BANK-2026-{i:06d}","bank_account":"OPERATING-001","reference":ref,"amount":money(amount),"currency":curr,"booking_date":b['settlement_date'],"value_date":b['settlement_date'],"description":"Synthetic settlement credit","source_file":"bank_statement_2026.csv"})
        if issue!="none": truth.append({"record_type":"BankStatementLine","record_id":f"BANK-2026-{i:06d}","issue_type":issue,"ground_truth":"exception_expected","expected_reason":issue})
    for i in range(len(banks)+1, bank_n+1):
        banks.append({"bank_line_id":f"BANK-2026-{i:06d}","bank_account":"OPERATING-001","reference":f"BANK-REF-{i:06d}","amount":money(rng.uniform(10,9000)),"currency":rng.choice(CURRENCIES),"booking_date":(start+timedelta(days=rng.randrange(270))).isoformat(),"value_date":"","description":"Unmatched incoming/outgoing movement","source_file":"bank_statement_2026.csv"})
        truth.append({"record_type":"BankStatementLine","record_id":f"BANK-2026-{i:06d}","issue_type":"unmatched_bank_record","ground_truth":"exception_expected","expected_reason":"No settlement reference"})
    # Inject additional explicit anomaly records without silently corrupting unrelated rows.
    if lines:
        dup=dict(lines[0]); dup['settlement_line_id']=f"STL-{dup['batch_id']}-DUP"; dup['issue_type']="duplicate_settlement_line"; lines.append(dup)
        truth.append({"record_type":"SettlementLine","record_id":dup['settlement_line_id'],"issue_type":"duplicate_settlement_line","ground_truth":"exception_expected","expected_reason":"Duplicate processor event in settlement lines"})
    if events:
        dup_event=dict(events[0]); dup_event['processor_event_id']="EVT-DUP-000000001"; dup_event['ingest_status']="duplicate"; events.append(dup_event)
        truth.append({"record_type":"ProcessorEvent","record_id":dup_event['processor_event_id'],"issue_type":"duplicate_webhook","ground_truth":"idempotent_duplicate","expected_reason":"Same idempotency key ingested twice"})
    # Refund-before-capture labelled event; independent row, valid attempt FK.
    refunded=next((a for a in attempts if a['status']=='refunded'), attempts[0])
    events.append({"processor_event_id":"EVT-ANOM-REFUND-0001","attempt_id":refunded['attempt_id'],"event_type":"refund","event_status":"succeeded","amount":refunded['amount'],"currency":refunded['currency'],"event_at":"2026-01-01T00:00:00","idempotency_key":"IDEM-ANOM-REFUND-0001","ingest_status":"accepted","issue_type":"refund_before_capture"})
    truth.append({"record_type":"ProcessorEvent","record_id":"EVT-ANOM-REFUND-0001","issue_type":"refund_before_capture","ground_truth":"exception_expected","expected_reason":"Refund event timestamp precedes capture"})
    # A labelled expected source event is absent from the event input: the control plane must flag the gap.
    truth.append({"record_type":"ProcessorEvent","record_id":"EVT-MISSING-0001","issue_type":"silently_dropped_record","ground_truth":"missing_record_expected","expected_reason":"Expected processor event is absent from ingested events"})
    exid=f"EXC-{len(exceptions)+1:07d}"
    exceptions.append({"exception_id":exid,"bank_line_id":"","batch_id":"","exception_type":"missing_processor_event","severity":"high","status":"open","created_at":"2026-10-27T00:00:00"})
    resolutions.append({"resolution_id":f"RES-{len(resolutions)+1:07d}","exception_id":exid,"resolution_action":"pending_review","resolution_note":"Expected processor event missing from ingestion; investigate source feed","resolved_by":"","resolved_at":"","outcome":"pending"})
    # Deterministic reconciliation by exact reference, currency, amount within $0.01; one-to-one consumption.
    batch_by_id={b['batch_id']:b for b in batches}; used=set(); recno=1
    for bank in banks:
        b=batch_by_id.get(bank['reference']); reason=None
        if not b: reason="unmatched_bank_or_settlement"
        elif bank['currency']!=b['currency']: reason="currency_mismatch"
        elif abs(Decimal(bank['amount'])-Decimal(b['net_amount']))>Decimal('0.01'): reason="amount_mismatch"
        elif b['batch_id'] in used: reason="duplicate_bank_match"
        else:
            used.add(b['batch_id']); matches.append({"reconciliation_id":f"REC-2026-{recno:06d}","bank_line_id":bank['bank_line_id'],"batch_id":b['batch_id'],"match_status":"matched","match_method":"reference_amount_currency","amount_difference":money(Decimal(bank['amount'])-Decimal(b['net_amount'])),"evaluated_at":"2026-10-27T00:00:00"}); recno+=1
        if reason:
            exid=f"EXC-{len(exceptions)+1:07d}"
            exceptions.append({"exception_id":exid,"bank_line_id":bank['bank_line_id'],"batch_id":b['batch_id'] if b else "","exception_type":reason,"severity":"high" if reason in ('currency_mismatch','amount_mismatch') else "medium","status":"open","created_at":"2026-10-27T00:00:00"})
            resolutions.append({"resolution_id":f"RES-{len(resolutions)+1:07d}","exception_id":exid,"resolution_action":"pending_review","resolution_note":"Awaiting operations analyst review","resolved_by":"","resolved_at":"","outcome":"pending"})
    tables={"Merchant":merchants,"PaymentOrder":orders,"PaymentAttempt":attempts,"ProcessorEvent":events,"SettlementBatch":batches,"SettlementLine":lines,"BankStatementLine":banks,"ReconciliationMatch":matches,"Exception":exceptions,"Resolution":resolutions}
    for name,rows in tables.items(): write_csv(out/f"{name}.csv",rows)
    write_csv(out/"ground_truth.csv",truth)
    # Manifest and deterministic checksums for reproducibility.
    manifest={"seed":seed,"generated_at":"fixed synthetic reference date; no external data","parameters":{"merchants":merchants_n,"payment_orders":orders_n,"payment_attempts":attempts_n,"settlement_batches":batches_n,"bank_statement_lines":bank_n},"row_counts":{k:len(v) for k,v in tables.items()}|{"GroundTruth":len(truth)},"files":{}}
    for p in sorted(out.glob("*.csv")): manifest['files'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (out/"source_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='data/generated'); ap.add_argument('--merchants',type=int,default=2000); ap.add_argument('--orders',type=int,default=50000); ap.add_argument('--attempts',type=int,default=55000); ap.add_argument('--batches',type=int,default=1000); ap.add_argument('--bank-lines',type=int,default=5000); ap.add_argument('--seed',type=int,default=SEED)
    a=ap.parse_args(); print(json.dumps(generate(Path(a.out),a.merchants,a.orders,a.attempts,a.batches,a.bank_lines,a.seed),indent=2))
