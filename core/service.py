"""One persistent process per shell; NUL-framed data, never executable code."""
import sys,json,argparse,time
from pathlib import Path
from .matcher import Engine
from .models import Request
from .parser import parse
from . import diagnostics
def read_field(stream):
    out=bytearray()
    while True:
        c=stream.read(1)
        if not c:return None
        if c==b'\0':return out.decode('utf-8')
        out+=c
        if len(out)>65536:raise ValueError("field exceeds limit")
def main():
    p=argparse.ArgumentParser();p.add_argument("--database");p.add_argument("--stdio",action="store_true")
    args=p.parse_args();diagnostics.setup();engine=Engine(args.database)
    settings=json.loads((Path(__file__).resolve().parents[1]/"config/settings.json").read_text())
    delay=settings["idle_delay_ms"];height=settings["menu_maxlines"];limit=settings["max_candidates"]
    if not isinstance(limit,int) or not 1<=limit<=4:raise ValueError("invalid candidate limit")
    if not isinstance(delay,int) or not 0<=delay<=500 or not isinstance(height,int) or not 5<=height<=40:
        raise ValueError("invalid numeric settings")
    diagnostics.emit("ready",records=len(engine.entries),scopes=len(engine.scopes))
    if args.stdio:
        sys.stdout.buffer.write(f"READY\0{delay}\0{height}\0".encode());sys.stdout.buffer.flush()
    if not args.stdio:
        for line in sys.stdin:
            try:
                request=Request(**json.loads(line));start=time.perf_counter();items=engine.recommend(request,limit)
                print(json.dumps({"candidates":[x.json() for x in items],"elapsed_ms":(time.perf_counter()-start)*1000},ensure_ascii=False),flush=True)
            except (ValueError,TypeError) as exc:print(json.dumps({"error":str(exc),"candidates":[]}),flush=True)
        return
    while True:
        fields=[read_field(sys.stdin.buffer) for _ in range(6)]
        if fields[0] is None or any(v is None for v in fields):break
        ident,line,cursor,shell,platform,cwd=fields
        request_started=time.perf_counter()
        try:
            request=Request(line,int(cursor),shell,platform,cwd);context=parse(request);items=engine.recommend(request,limit)
            output=["OK",ident,str(context.begin),context.prefix,str(len(items))]
            for item in items:
                description=item.description
                if item.risk!="low":description+=f" [风险:{item.risk}] {item.warning}"
                output +=[item.command,description,item.insertion,str(item.edit_start),str(item.edit_end),str(item.cursor_after),item.risk,item.id,item.category]
        except (ValueError,TypeError):output=["OK",ident,"0","","0"]
        diagnostics.emit("response",request=ident,count=int(output[4]),matching_ms=(time.perf_counter()-request_started)*1000,stdout="framed-response")
        sys.stdout.buffer.write(("\0".join(output)+"\0").encode());sys.stdout.buffer.flush()
if __name__=="__main__":
    try:main()
    except BaseException as exc:
        if not isinstance(exc,SystemExit):diagnostics.exception(exc)
        raise
