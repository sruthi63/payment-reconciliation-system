import csv, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    with path.open(newline='', encoding='utf-8') as f: return list(csv.DictReader(f))

def test_small_generation_and_foreign_keys(tmp_path):
    out=tmp_path/'data'
    subprocess.run([sys.executable, str(ROOT/'src'/'generate.py'), '--out', str(out), '--merchants','10','--orders','30','--attempts','35','--batches','5','--bank-lines','8'],check=True,capture_output=True,text=True)
    merchants=read(out/'Merchant.csv'); orders=read(out/'PaymentOrder.csv'); attempts=read(out/'PaymentAttempt.csv'); events=read(out/'ProcessorEvent.csv')
    assert len(merchants)==10 and len(orders)==30 and len(attempts)==35
    assert {x['merchant_id'] for x in orders} <= {x['merchant_id'] for x in merchants}
    assert {x['payment_id'] for x in attempts} <= {x['payment_id'] for x in orders}
    assert {x['attempt_id'] for x in events} <= {x['attempt_id'] for x in attempts}
    assert (out/'ground_truth.csv').exists() and (out/'source_manifest.json').exists()

def test_fixed_seed_reproducible(tmp_path):
    outs=[tmp_path/'a',tmp_path/'b']
    for out in outs:
        subprocess.run([sys.executable,str(ROOT/'src'/'generate.py'),'--out',str(out),'--merchants','5','--orders','12','--attempts','13','--batches','3','--bank-lines','4'],check=True,capture_output=True,text=True)
    a=json.loads((outs[0]/'source_manifest.json').read_text()); b=json.loads((outs[1]/'source_manifest.json').read_text())
    assert a['files']==b['files']

def test_required_edge_cases_present(tmp_path):
    out=tmp_path/'data'
    subprocess.run([sys.executable,str(ROOT/'src'/'generate.py'),'--out',str(out),'--merchants','10','--orders','30','--attempts','35','--batches','5','--bank-lines','8'],check=True,capture_output=True,text=True)
    truth=read(out/'ground_truth.csv')
    issues={r['issue_type'] for r in truth}
    assert {'bank_amount_differs_by_fee','currency_mismatch','unmatched_bank_record','duplicate_settlement_line','duplicate_webhook','refund_before_capture'} <= issues
