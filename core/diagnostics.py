"""File diagnostics only: no command text or raw protocol output."""
import atexit,json,os,signal,time
PATH=os.environ.get("EASYLINUX_CORE_LOG")
_exit_status=0
_shutting_down=False
def emit(event,**fields):
    if not PATH:return
    try:
        with open(PATH,"a",encoding="utf-8") as stream:
            stream.write(json.dumps(dict(time=time.time(),pid=os.getpid(),ppid=os.getppid(),event=event,**fields),ensure_ascii=False)+"\n")
    except OSError:pass
def terminate(signum,frame):
    global _exit_status,_shutting_down
    if _shutting_down:return
    _shutting_down=True
    _exit_status=128+signum;emit("signal",signal=signum,status=_exit_status);raise SystemExit(_exit_status)
def finish():
    global _shutting_down
    _shutting_down=True
    emit("exit",status=_exit_status)
def setup():
    emit("start")
    atexit.register(finish)
    for number in (signal.SIGTERM,signal.SIGHUP):signal.signal(number,terminate)
def exception(exc):
    global _exit_status
    _exit_status=1;emit("exception",type=type(exc).__name__,message=str(exc)[:200])
