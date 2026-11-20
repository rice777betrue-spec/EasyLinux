"""Public JSON interface; offsets are Unicode code points, not bytes."""
from dataclasses import dataclass, asdict
@dataclass(frozen=True)
class Request:
    line: str
    cursor: int
    shell: str = "bash"
    platform: str = "linux"
    cwd: str = ""
    def __post_init__(self):
        if not isinstance(self.line,str) or len(self.line)>16384 or '\0' in self.line:raise ValueError("invalid line")
        if isinstance(self.cursor,bool) or not isinstance(self.cursor,int) or not 0<=self.cursor<=len(self.line):raise ValueError("invalid cursor")
@dataclass(frozen=True)
class Context:
    begin: int
    prefix: str
    command: str
    supported: bool = True
@dataclass(frozen=True)
class Candidate:
    id: str
    command: str
    description: str
    insertion: str
    edit_start: int
    edit_end: int
    cursor_after: int
    matched_prefix: str
    category: str
    risk: str
    warning: str
    examples: list
    command_type: str
    environments: list
    packages: list
    recommendation_kind: str = "command"
    option_name: str = ""
    def json(self): return asdict(self)
