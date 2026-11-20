#!/usr/bin/env python3
"""Real PTY checks. No third-party packages. Never Enter a recommendation."""
from __future__ import annotations
import codecs, fcntl, hashlib, json, os, pty, select, signal, struct, termios, time, unicodedata
from pathlib import Path
LAB = Path(__file__).resolve().parents[1]
LOGS = LAB / "logs"
SAFE_HISTORY = "printf '__EASYLINUX_HISTORY__\\n'"
PASS, FAIL = "已实测通过", "已实测失败"

class VTScreen:
    """VT cell observer with replies; physical glyph rendering is out of scope."""
    def __init__(self, rows=32, cols=100):
        self.rows, self.cols = rows, cols
        self.cells = [[" "] * cols for _ in range(rows)]
        self.row = self.col = 0
        self.saved = (0, 0)
        self.top, self.bottom = 0, rows - 1
        self.state, self.buf = "text", ""
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.replies, self.autowrap, self.wrap_pending = [], True, False
    def resize(self, rows, cols):
        self.cells = [(r[:cols] + [" "] * cols)[:cols] for r in self.cells[:rows]]
        self.cells += [[" "] * cols for _ in range(rows - len(self.cells))]
        self.rows, self.cols = rows, cols
        self.row, self.col = min(self.row, rows-1), min(self.col, cols-1)
        self.top, self.bottom, self.wrap_pending = 0, rows-1, False
    def scroll(self):
        self.cells.pop(self.top); self.cells.insert(self.bottom, [" "] * self.cols)
    def lf(self):
        self.wrap_pending = False
        if self.row == self.bottom: self.scroll()
        else: self.row = min(self.rows-1, self.row+1)
    def char(self, ch):
        if ch == "\r": self.col, self.wrap_pending = 0, False
        elif ch == "\n": self.lf()
        elif ch == "\b": self.col, self.wrap_pending = max(0, self.col-1), False
        elif ch == "\t": self.col = min(self.cols-1, (self.col//8+1)*8)
        elif ord(ch) < 32 or ch == "\x7f": pass
        elif unicodedata.combining(ch):
            if self.col: self.cells[self.row][self.col-1] += ch
        else:
            width = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
            if self.wrap_pending or self.col+width > self.cols:
                if self.autowrap: self.col = 0; self.lf()
                self.wrap_pending = False
            self.cells[self.row][self.col] = ch
            if width == 2 and self.col+1 < self.cols: self.cells[self.row][self.col+1] = ""
            self.col += width
            if self.col >= self.cols: self.col, self.wrap_pending = self.cols-1, self.autowrap
    def csi(self, body, final):
        nums = [int(x) if x.isdigit() else 0 for x in body.lstrip("?<>!=").split(";")]
        n = nums[0] or 1
        if final in "ABCDEFGHfad" or final == chr(96): self.wrap_pending = False
        if final == "A": self.row = max(self.top, self.row-n)
        elif final in ("B","e"): self.row = min(self.bottom, self.row+n)
        elif final in ("C","a"): self.col = min(self.cols-1, self.col+n)
        elif final == "D": self.col = max(0, self.col-n)
        elif final == "E": self.row, self.col = min(self.bottom, self.row+n), 0
        elif final == "F": self.row, self.col = max(self.top, self.row-n), 0
        elif final in ("G",chr(96)): self.col = min(self.cols-1, max(0,n-1))
        elif final == "d": self.row = min(self.rows-1, max(0,n-1))
        elif final in ("H","f"):
            self.row = min(self.rows-1, max(0,n-1))
            self.col = min(self.cols-1,max(0,(nums[1] if len(nums)>1 else 1)-1))
        elif final == "J":
            if nums[0] in (2,3): self.cells = [[" "]*self.cols for _ in range(self.rows)]
            elif nums[0] == 0:
                self.cells[self.row][self.col:] = [" "]*(self.cols-self.col)
                for r in range(self.row+1,self.rows): self.cells[r] = [" "]*self.cols
            elif nums[0] == 1:
                for r in range(self.row): self.cells[r] = [" "]*self.cols
                self.cells[self.row][:self.col+1] = [" "]*(self.col+1)
        elif final == "K":
            a,b = (0,self.cols) if nums[0]==2 else ((0,self.col+1) if nums[0]==1 else (self.col,self.cols))
            self.cells[self.row][a:b] = [" "]*(b-a)
        elif final == "P":
            r=self.cells[self.row]; self.cells[self.row]=(r[:self.col]+r[self.col+n:]+[" "]*n)[:self.cols]
        elif final == "@":
            r=self.cells[self.row]; self.cells[self.row]=(r[:self.col]+[" "]*n+r[self.col:])[:self.cols]
        elif final == "X":
            end=min(self.cols,self.col+n); self.cells[self.row][self.col:end]=[" "]*(end-self.col)
        elif final == "L":
            for _ in range(min(n,self.bottom-self.row+1)):
                self.cells.pop(self.bottom); self.cells.insert(self.row,[" "]*self.cols)
        elif final == "M":
            for _ in range(min(n,self.bottom-self.row+1)):
                self.cells.pop(self.row); self.cells.insert(self.bottom,[" "]*self.cols)
        elif final == "S":
            for _ in range(n): self.scroll()
        elif final == "T":
            for _ in range(n): self.cells.pop(self.bottom); self.cells.insert(self.top,[" "]*self.cols)
        elif final == "r":
            self.top=max(0,n-1); self.bottom=min(self.rows-1,(nums[1] if len(nums)>1 and nums[1] else self.rows)-1)
            self.row,self.col=0,0
        elif final == "s": self.saved=self.row,self.col
        elif final == "u": self.row,self.col=self.saved
        elif final == "n" and nums[0]==6: self.replies.append(f"\x1b[{self.row+1};{self.col+1}R".encode())
        elif final == "n" and nums[0]==5: self.replies.append(b"\x1b[0n")
        elif final == "c": self.replies.append(b"\x1b[>0;370;0c" if body.startswith(">") else b"\x1b[?1;2c")
        elif final == "t" and nums[0]==18: self.replies.append(f"\x1b[8;{self.rows};{self.cols}t".encode())
        elif final in ("h","l") and body=="?7": self.autowrap=final=="h"
    def feed(self, raw):
        for ch in self.decoder.decode(raw):
            if self.state=="text":
                if ch=="\x1b": self.state="esc"
                else: self.char(ch)
            elif self.state=="esc":
                if ch=="[": self.state,self.buf="csi",""
                elif ch=="]": self.state,self.buf="osc",""
                elif ch in ("P","_","^"): self.state,self.buf="dcs",""
                elif ch in ("(",")"): self.state="charset"
                elif ch=="7": self.saved,self.state=(self.row,self.col),"text"
                elif ch=="8": (self.row,self.col),self.state=self.saved,"text"
                elif ch=="D": self.lf(); self.state="text"
                elif ch=="E": self.col=0; self.lf(); self.state="text"
                elif ch=="M":
                    if self.row==self.top: self.cells.pop(self.bottom); self.cells.insert(self.top,[" "]*self.cols)
                    else: self.row=max(0,self.row-1)
                    self.state="text"
                else: self.state="text"
            elif self.state=="charset": self.state="text"
            elif self.state=="csi":
                if "@"<=ch<="~": self.csi(self.buf,ch); self.state="text"
                else: self.buf+=ch
            elif self.state in ("osc","dcs"):
                if ch=="\x07": self.finish_string(); self.state="text"
                elif ch=="\x1b": self.state+="_esc"
                else: self.buf+=ch
            elif self.state in ("osc_esc","dcs_esc"):
                if ch=="\\": self.finish_string(); self.state="text"
                else: self.state=self.state[:-4]; self.buf+=ch
    def finish_string(self):
        if self.buf in ("10;?","11;?","12;?"):
            code=self.buf.split(";")[0]; self.replies.append(f"\x1b]{code};rgb:0000/0000/0000\x1b\\".encode())
    def text(self): return "\n".join("".join(r).rstrip() for r in self.cells).rstrip()+"\n"

class Session:
    def __init__(self,name):
        self.name,self.screen,self.raw,self.events=name,VTScreen(),bytearray(),[]
        self.transcript=(LOGS/f"pty-{name}.ansi").open("wb")
        self.pid,self.fd=pty.fork()
        if self.pid==0:
            os.environ.update(TERM="xterm-256color",LANG="C.UTF-8",EASYLINUX_TEST_GUARD="1")
            os.execv(str(LAB/"scripts/start-test"),[str(LAB/"scripts/start-test")])
        self.resize(32,100); self.read(2)
    def resize(self,rows,cols):
        fcntl.ioctl(self.fd,termios.TIOCSWINSZ,struct.pack("HHHH",rows,cols,0,0))
        self.screen.resize(rows,cols); os.kill(self.pid,signal.SIGWINCH)
    def read(self,seconds=.45):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if not select.select([self.fd],[],[],min(.08,max(0,end-time.monotonic())))[0]: continue
            try: raw=os.read(self.fd,65536)
            except OSError: return
            if not raw: return
            self.raw+=raw; self.transcript.write(raw); self.transcript.flush(); self.screen.feed(raw)
            for reply in self.screen.replies: os.write(self.fd,reply)
            self.screen.replies.clear()
    def send(self,data,wait=.4):
        if isinstance(data,str): data=data.encode()
        self.events.append({"bytes_hex":data.hex(),"monotonic":time.monotonic()})
        os.write(self.fd,data); self.read(wait)
    def line(self,text):
        assert "\r" not in text and "\n" not in text
        self.send(b"\x01\x0b",.12); self.send(text,.65)
    def snap(self,label):
        path=LAB/"logs/snapshot.bin"; path.unlink(missing_ok=True); self.send(b"\x18\x14",.25)
        deadline=time.monotonic()+3
        while not path.exists() and time.monotonic()<deadline: self.read(.1)
        if not path.exists(): raise AssertionError("Ctrl-x Ctrl-t did not create snapshot.bin")
        fields=path.read_bytes().split(b"\0")
        if fields and fields[-1]==b"": fields.pop()
        assert len(fields)%2==0,"Invalid NUL key/value snapshot"
        s={fields[i].decode():fields[i+1].decode("utf-8") for i in range(0,len(fields),2)}
        (LOGS/f"screen-{label}.txt").write_text(self.screen.text(),encoding="utf-8")
        (LOGS/f"snapshot-{label}.json").write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")
        return s
    def choose(self,index):
        s=self.snap("selection")
        for _ in range(8):
            cur=int(s.get("selected","-1"))
            if cur==index: return
            self.send(b"\x1b[B" if cur<index else b"\x1b[A",.1); s=self.snap("selection")
        raise AssertionError(f"Cannot select {index}: {s}")
    def close(self):
        try: self.line(""); self.send(b"\x04",.6)
        finally:
            try:
                got,_=os.waitpid(self.pid,os.WNOHANG)
                if not got:
                    try: os.killpg(os.tcgetpgrp(self.fd),signal.SIGHUP)
                    except (OSError,ProcessLookupError): pass
                    os.kill(self.pid,signal.SIGHUP)
                    deadline=time.monotonic()+2
                    while time.monotonic()<deadline:
                        got,_=os.waitpid(self.pid,os.WNOHANG)
                        if got:break
                        time.sleep(.05)
                    if not got:os.kill(self.pid,signal.SIGTERM);os.waitpid(self.pid,0)
            except (ProcessLookupError,ChildProcessError): pass
            os.close(self.fd); self.transcript.close()
            (LOGS/f"events-{self.name}.json").write_text(json.dumps(self.events,indent=2))

def candidates(s): return [s[f"candidate_{i}"] for i in range(int(s.get("count",0)))]
def require(ok,message):
    if not ok: raise AssertionError(message)
def inactive(s): return s.get("active") in ("","0","false")
def bordered_widths(screen):
    lines=[line for line in screen.splitlines() if line.startswith(("┌","│","├","└"))]
    return [sum(2 if unicodedata.east_asian_width(ch) in ("W","F") else 1 for ch in line if not unicodedata.combining(ch)) for line in lines]

