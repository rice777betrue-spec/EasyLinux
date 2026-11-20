from pathlib import Path
from .models import Request,Candidate
from .parser import parse,edit_for
from .ranker import score
from .validator import load
from .options import load_scopes,generate
class Engine:
    def __init__(self,path=None,entries=None):
        self.entries=load(path or Path(__file__).resolve().parents[1]/"data/commands.json") if entries is None else entries
        self.scopes=load_scopes(Path(__file__).resolve().parents[1]/"data/options.json") if entries is None else []
        self.index={}
        for entry in self.entries:self.index.setdefault(entry["command"][0],[]).append(entry)
    def recommend(self,request:Request,limit=4):
        if request.shell!="bash" or request.platform!="linux":return []
        context=parse(request)
        if not context.supported:return []
        matches=[]
        for entry in self.index.get(context.prefix[0],[]):
            if request.shell not in entry["shell"] or entry["platform"]!=request.platform:continue
            edit=edit_for(request,context,entry["command"])
            if edit is not None:matches.append((entry,edit))
        dynamic=generate(request,context,self.scopes,self.entries)
        unique={e["command"]:(e,edit) for e,edit in matches}
        for e,edit in dynamic:unique[e["command"]]=(e,edit)
        matches=list(unique.values())
        matches.sort(key=lambda x:score(x[0],context))
        return [Candidate(id=e["id"],command=e["command"],description=e["description"],
            matched_prefix=context.prefix,category=e["category"],risk=e["risk"],warning=e["warning"],
            examples=e["examples"],command_type=e["command_type"],environments=e["environments"],
            packages=e["packages"],recommendation_kind=e.get("recommendation_kind","command"),option_name=e.get("option_name",""),**edit) for e,edit in matches[:max(0,min(4,limit))]]
