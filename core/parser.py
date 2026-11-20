"""Conservative literal Bash scanner; never evaluates shell syntax."""
from .models import Request,Context
BOUNDARY=" \t\n;|&<>"
def parse(request: Request) -> Context:
    left=request.line[:request.cursor]
    quote=None;escape=False;start=0;unsupported=False;comment=False
    if "$(" in left or chr(96) in left:return Context(0,"","",False)
    for i,ch in enumerate(left):
        if comment:
            if ch=="\n":comment=False;start=i+1;unsupported=False
            continue
        if escape:escape=False;continue
        if quote=="'":
            if ch=="'":quote=None
            continue
        if ch=="\\" and quote!="'":escape=True;continue
        if quote=='"':
            if ch=='"':quote=None
            if ch=="$":unsupported=True
            continue
        if ch in "'\"":quote=ch;continue
        if ch=="#" and (i==0 or left[i-1] in BOUNDARY):comment=True;continue
        if ch in ";|&\n":start=i+1;unsupported=False
        elif ch in "<>($)}{":unsupported=True
    while start<len(left) and left[start] in " \t":start+=1
    prefix=left[start:]
    return Context(start,prefix,prefix.split(" ",1)[0] if prefix else "",not(comment or escape or unsupported or not prefix))
def edit_for(request,context,command):
    if not command.startswith(context.prefix):return None
    missing=command[len(context.prefix):];right=request.line[request.cursor:];overlap=0
    while overlap<min(len(missing),len(right)) and missing[overlap]==right[overlap]:overlap+=1
    if overlap<len(right) and right[overlap] not in BOUNDARY:return None
    start=request.cursor+overlap
    return dict(insertion=missing[overlap:],edit_start=start,edit_end=start,cursor_after=context.begin+len(command))
