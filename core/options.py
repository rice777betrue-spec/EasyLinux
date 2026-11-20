"""Scoped flags/values from options.json; no command-specific branches."""
import json,shlex,re
from .validator import strings
from pathlib import Path
from .parser import edit_for
def load_scopes(path):
    doc=json.loads(Path(path).read_text())
    if doc.get("schema_version")!=1 or not isinstance(doc.get("scopes"),list):raise ValueError("invalid option schema")
    if any(any(ord(c)<32 or ord(c)==127 for c in text) for text in strings(doc)):raise ValueError("option schema control character")
    seen=set()
    for scope in doc["scopes"]:
        tokens=scope.get("tokens")
        if not isinstance(tokens,list) or not tokens or not all(isinstance(x,str) and x and not any(ord(c)<32 for c in x) for x in tokens):raise ValueError("invalid scope tokens")
        if tuple(tokens) in seen:raise ValueError("duplicate option scope")
        seen.add(tuple(tokens));names=set()
        for arg in scope.get("arguments",[]):
            if not isinstance(arg,dict) or not all(isinstance(arg.get(k),str) and arg[k] for k in ("name","example","description")):raise ValueError("invalid argument example")
        for spec in scope.get("options",[]):
            for key in ("name","description"):
                if not isinstance(spec.get(key),str) or not spec[key]:raise ValueError("invalid option field")
            for name in [spec["name"]]+spec.get("aliases",[]):
                if not isinstance(name,str) or not name.startswith("-") or name in names:raise ValueError("duplicate/invalid option name")
                names.add(name)
            for text in [spec["name"],spec["description"],spec.get("value_example","")]:
                if any(ord(c)<32 or ord(c)==127 for c in text):raise ValueError("option control character")
    return doc["scopes"]
def generate(request,context,scopes,entries):
    prefix=context.prefix
    try:words=shlex.split(prefix)
    except ValueError:return []
    if not words:return []
    trailing=prefix.endswith((" ","\t"))
    before=words if trailing else words[:-1]
    partial="" if trailing else words[-1]
    matches=[s for s in scopes if before[:len(s["tokens"])]==s["tokens"]]
    if not matches:return []
    scope=max(matches,key=lambda s:len(s["tokens"]))
    base=" ".join(scope["tokens"])
    parents=[e for e in entries if e["command"]==base or e["command"].startswith(base+" ")]
    if not parents:return []
    parent=min(parents,key=lambda e:len(e["command"]))
    rest=before[len(scope["tokens"]):];used=set();positionals=[];waiting=None
    lookup={n:o for o in scope["options"] for n in [o["name"]]+o.get("aliases",[])}
    for word in rest:
        if waiting is not None:waiting=None;continue
        key=word.split("=",1)[0]
        if key in lookup:
            opt=lookup[key];used.add(opt["name"])
            if opt.get("value_example") and "=" not in word:waiting=opt
        elif not word.startswith("-"):positionals.append(word)
    results=[]
    head=prefix if trailing else prefix[:-len(partial)]
    def add(tail,description,kind,option_name):
        full=head+tail;edit=edit_for(request,context,full)
        if edit is None:return
        entry=dict(parent)
        entry.update(command=full,description=description,
            id="option."+".".join(scope["tokens"])+"."+option_name.lstrip("-").replace("=","."),
            examples=[dict(command=full,description=description)],context_priority=110,root_priority=110,
            recommendation_kind=kind,option_name=option_name)
        results.append((entry,edit))
    if waiting:
        value=waiting["value_example"]
        if value.startswith(partial):add(shlex.quote(value),waiting["description"]+"：示例参数值","value",waiting["name"])
        return results
    for opt in scope["options"]:
        if opt["name"] in used:continue
        for name in [opt["name"]]+opt.get("aliases",[]):
            if name.startswith(partial):
                tail=name+(" "+shlex.quote(opt["value_example"]) if opt.get("value_example") else "")
                add(tail,opt["description"],"option",opt["name"]);break
    if not positionals and not partial.startswith("-"):
        for arg in scope.get("arguments",[]):
            if arg["example"].startswith(partial):add(shlex.quote(arg["example"]),arg["description"],"argument-example",arg["name"])
    return results
