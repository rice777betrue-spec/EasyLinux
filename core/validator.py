import json,re,shlex
from pathlib import Path
FIELDS=("id","command","description","category","platform","shell","tags","examples","risk","command_type","environments","packages","parameters","warning")
RISKS={"low","medium","high"}
def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,list):
        for v in value:yield from strings(v)
    elif isinstance(value,dict):
        for v in value.values():yield from strings(v)
def validate(data):
    errors=[];seen=set();commands=set()
    if not isinstance(data,list):return ["database must be a list"]
    for n,e in enumerate(data):
        where=f"entry[{n}]"
        if any(any(ord(c)<32 or ord(c)==127 for c in text) for text in strings(e)):errors.append(where+": control character in record")
        if not isinstance(e,dict):errors.append(where+": not object");continue
        for f in FIELDS:
            if f not in e:errors.append(where+": missing "+f)
        ident=e.get("id")
        if not isinstance(ident,str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]+",ident):errors.append(where+": invalid id")
        key=str(ident)
        if key in seen:errors.append(where+": duplicate id")
        seen.add(key)
        for f in ("command","description","category"):
            if not isinstance(e.get(f),str) or not e.get(f,"").strip():errors.append(where+": empty "+f)
        command=e.get("command","")
        if not isinstance(command,str):command=""
        if command in commands:errors.append(where+": duplicate command")
        commands.add(command)
        if any(ord(c)<32 or ord(c)==127 for c in command+str(e.get("description",""))):errors.append(where+": control character")
        try:shlex.split(command)
        except ValueError:errors.append(where+": unbalanced command quoting")
        if re.search(r"[;&|]",command) or chr(96) in command or "$(" in command:errors.append(where+": compound command not allowed")
        if not re.search(r"[\u3400-\u9fff]",str(e.get("description",""))):errors.append(where+": missing Chinese explanation")
        if e.get("risk") not in RISKS:errors.append(where+": invalid risk")
        if e.get("risk") in ("medium","high") and not e.get("warning"):errors.append(where+": missing risk warning")
        if e.get("command_type") not in ("external","builtin","developer"):errors.append(where+": invalid command type")
        if e.get("platform")!="linux" or e.get("shell")!=["bash"]:errors.append(where+": unsupported environment")
        for f in ("tags","environments","packages"):
            if not isinstance(e.get(f),list) or any(not isinstance(v,str) or not v for v in e.get(f,[])):errors.append(where+": invalid "+f)
        examples=e.get("examples")
        if not isinstance(examples,list) or not examples:errors.append(where+": invalid examples")
        else:
            for x in examples:
                if not isinstance(x,dict) or not all(isinstance(x.get(k),str) and x[k].strip() for k in ("command","description")):
                    errors.append(where+": invalid example");continue
                try:shlex.split(x["command"])
                except ValueError:errors.append(where+": invalid example quoting")
        params=e.get("parameters")
        if not isinstance(params,list) or any(not isinstance(x,dict) or not all(isinstance(x.get(k),str) and x[k] for k in ("name","description")) for x in params or []):errors.append(where+": invalid parameters")
        if not isinstance(e.get("root_priority",0),int) or not isinstance(e.get("context_priority",0),int):errors.append(where+": invalid priority")
    return errors
def load(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"));errors=validate(data)
    if errors:raise ValueError("\n".join(errors))
    return data
