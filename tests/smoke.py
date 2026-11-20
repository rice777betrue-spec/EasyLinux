import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pty_support as h
from core.matcher import Engine
from core.models import Request
h.LOGS=ROOT/'logs/smoke';h.LOGS.mkdir(parents=True,exist_ok=True)
def main():
 e=Engine();assert len(e.entries)==159
 s=h.Session('bundle');rows=[]
 try:
  initial=s.snap('initial');count=initial['execution_count']
  for prefix in ('g','git st','docker','make -j','make -f ','gcc -','cmake --build','bash -n','bash -x','shellcheck'):
   expected=e.recommend(Request(prefix,len(prefix)));assert expected
   s.line(prefix);snap=s.snap('before-'+str(len(rows)))
   assert snap['candidate_0']==expected[0].command and snap['buffer']==prefix
   if len(expected)>1:
    s.send(b'\x1b[B',.15);down=s.snap('down')
    assert down['selected']!=snap['selected']
    s.send(b'\x1b[A',.15);up=s.snap('up');assert up['selected']==snap['selected']
   s.send(b'\t',.2);filled=s.snap('filled')
   assert filled['buffer']==expected[0].command and filled['execution_count']==count
   s.line(prefix);s.send(b'\x1b',1.0);closed=s.snap('closed')
   assert h.inactive(closed) and closed['buffer']==prefix
   assert closed['execution_count']==count
   rows.append(dict(prefix=prefix,passed=True,completed=filled['buffer']))
   print('PASS',prefix,flush=True)
 finally:s.close()
 (h.LOGS/'results.json').write_text(json.dumps(dict(cases=rows,execution_count_unchanged=True,native_host='requires manual acceptance'),ensure_ascii=False,indent=2))
 print('10/10 passed; no candidate executed',flush=True)
if __name__=='__main__':main()
