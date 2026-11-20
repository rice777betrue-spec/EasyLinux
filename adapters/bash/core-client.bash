# Persistent Core transport. Responses are NUL framed data, never shell code.
easylinux_core_pending=
easylinux_core_id=0
easylinux_core_cache_text=
easylinux_core_cache_cursor=-1
easylinux_core_failed=
function easylinux/bash/core-start {
  coproc EASYLINUX_CORE { cd -- "$EASYLINUX_PROJECT"; exec python3 -B -m core.service --stdio; } 2>>"$EASYLINUX_LAB/logs/diagnostics/$EASYLINUX_SESSION_ID-core.stderr"
  easylinux_core_pid=$EASYLINUX_CORE_PID
  easylinux/diag core-start
  exec {easylinux_core_read}<&"${EASYLINUX_CORE[0]}"
  exec {easylinux_core_write}>&"${EASYLINUX_CORE[1]}"
  local ready
  IFS= read -r -d '' -t 2 -u "$easylinux_core_read" ready
  IFS= read -r -d '' -t 2 -u "$easylinux_core_read" easylinux_idle_delay
  IFS= read -r -d '' -t 2 -u "$easylinux_core_read" easylinux_menu_height
  if [[ $ready != READY || ! $easylinux_idle_delay =~ ^[0-9]+$ || ! $easylinux_menu_height =~ ^[0-9]+$ ]]; then
    easylinux_core_failed=1
    return 1
  fi
  bleopt complete_menu_maxlines="$easylinux_menu_height"
}
function easylinux/bash/core-stop {
  local status=0
  if [[ ${easylinux_core_pid-} ]]; then
    exec {easylinux_core_write}>&-
    exec {easylinux_core_read}<&-
    builtin kill -TERM "$easylinux_core_pid" 2>/dev/null
    wait "$easylinux_core_pid" 2>/dev/null; status=$?
    easylinux/diag core-stop "status=$status"
    easylinux_core_pid=
  fi
  return 0
}
function easylinux/bash/core-field {
  IFS= read -r -d '' -t 0.05 -u "$easylinux_core_read" "$1"
}
function easylinux/bash/generate {
  [[ ! $easylinux_core_failed ]] || return 1
  if ! builtin kill -0 "$easylinux_core_pid" 2>/dev/null; then
    easylinux/diag core-unexpected-exit
    easylinux_core_failed=1 easylinux_core_pending=
    easylinux_candidates=() easylinux_descriptions=()
    return 1
  fi
  if [[ $easylinux_core_cache_text == "$_ble_edit_str" && $easylinux_core_cache_cursor == "$_ble_edit_ind" ]]; then
    ((${#easylinux_candidates[@]})) && return 0 || return 1
  fi
  if [[ $easylinux_core_pending ]]; then
    local header ident begin prefix count i full description insert start end cursor risk id category name
    IFS= read -r -d '' -t 0.001 -u "$easylinux_core_read" header
    local read_status=$?
    if ((read_status!=0)); then
      if ((read_status==1)); then
        easylinux_core_failed=1; easylinux/diag core-stdout-eof; return 1
      fi
      return 75
    fi
    for name in ident begin prefix count; do easylinux/bash/core-field "$name" || { easylinux_core_failed=1; return 1; }; done
    [[ $header == OK && $ident == "$easylinux_core_id" && $count =~ ^[0-4]$ && $begin =~ ^[0-9]+$ ]] || { easylinux_core_failed=1; return 1; }
    easylinux_candidates=() easylinux_descriptions=() easylinux_insertions=()
    easylinux_starts=() easylinux_ends=() easylinux_cursors=() easylinux_risks=() easylinux_ids=()
    for ((i=0;i<count;i++)); do
      for name in full description insert start end cursor risk id category; do
        easylinux/bash/core-field "$name" || { easylinux_core_failed=1; return 1; }
      done
      [[ $start =~ ^[0-9]+$ && $end =~ ^[0-9]+$ && $cursor =~ ^[0-9]+$ ]] || { easylinux_core_failed=1; return 1; }
      easylinux_candidates+=("$full") easylinux_descriptions+=("$description") easylinux_insertions+=("$insert")
      easylinux_starts+=("$start") easylinux_ends+=("$end") easylinux_cursors+=("$cursor")
      easylinux_risks+=("$risk") easylinux_ids+=("$id")
    done
    easylinux/diag ipc-response "start=${easylinux_request_started-} end=$EPOCHREALTIME"
    easylinux_core_cache_text=$easylinux_core_pending_text easylinux_core_cache_cursor=$easylinux_core_pending_cursor
    easylinux_prefix=$prefix easylinux_begin=$begin easylinux_core_pending=
    if [[ $easylinux_core_cache_text == "$_ble_edit_str" && $easylinux_core_cache_cursor == "$_ble_edit_ind" ]]; then
      ((count)) && return 0 || return 1
    fi
  fi
  ((++easylinux_core_id))
  easylinux_request_started=$EPOCHREALTIME
  easylinux/diag ipc-request "request=$easylinux_core_id"
  easylinux_core_pending_text=$_ble_edit_str easylinux_core_pending_cursor=$_ble_edit_ind
  printf '%s\0' "$easylinux_core_id" "$_ble_edit_str" "$_ble_edit_ind" bash linux "$PWD" >&"$easylinux_core_write" || { easylinux_core_failed=1; return 1; }
  easylinux_core_pending=1
  return 75
}
