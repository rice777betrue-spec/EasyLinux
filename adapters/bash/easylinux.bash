# Bash adapter: keyboard lifecycle; candidate data and edit plans from Core.
easylinux_candidates=()
easylinux_descriptions=()
easylinux_active=
easylinux_selected=-1
easylinux_text=
easylinux_cursor=0
easylinux_suppressed=
easylinux_seen=
easylinux_last_action=setup
easylinux_inserted=
easylinux_edit_start=0
easylinux_edit_end=0

function easylinux/bash/key {
  ret=${#_ble_edit_str}:$_ble_edit_ind:$COLUMNS:$LINES:$_ble_edit_str
}
function easylinux/bash/clear {
  if [[ $easylinux_active ]]; then ble/complete/menu/clear; fi
  easylinux_active= easylinux_selected=-1
}
# Candidate and edit data come exclusively from Core.
# The public candidate API keeps display candidate, insertion and data separate.
function ble/complete/action:easylinux-core/initialize { INSERT=$CAND; }
function ble/complete/action:easylinux-core/complete { return 0; }
function ble/complete/action:easylinux-core/get-desc { desc=$DATA; }
function ble/complete/source:easylinux-core {
  local i
  for ((i=0;i<${#easylinux_candidates[@]};i++)); do
    ble/complete/cand/yield easylinux-core "${easylinux_candidates[i]}" "${easylinux_descriptions[i]}"
  done
}
function easylinux/bash/idle {
  ble/util/idle.wait-user-input
  [[ $_ble_decode_keymap == emacs && $_ble_attached ]] || return 0
  local ret key status
  if ! easylinux/bash/geometry-ok; then easylinux/bash/clear; return 0; fi
  easylinux/bash/key; key=$ret
  if [[ $easylinux_suppressed && $key != "$easylinux_suppressed" ]]; then easylinux_suppressed=; fi
  [[ $key == "$easylinux_suppressed" || $key == "$easylinux_seen" ]] && return 0
  ble/util/idle.sleep-until "$((_ble_idle_clock_start+easylinux_idle_delay))" checked && return 0
  [[ ! $easylinux_resize_busy ]] || return 0
  easylinux/bash/clear
  easylinux/bash/generate; status=$?
  if ((status==75)); then ble/util/idle.sleep 5; return 0; fi
  easylinux_seen=$key
  if ((status==0)); then
    easylinux_text=$_ble_edit_str easylinux_cursor=$_ble_edit_ind
    easylinux/bash/show || easylinux/bash/clear
  fi
}
function easylinux/bash/current {
  [[ $easylinux_active && $_ble_edit_str == "$easylinux_text" && $_ble_edit_ind == "$easylinux_cursor" ]]
}
function ble/widget/easylinux/tab {
  if ! easylinux/bash/current; then
    easylinux/bash/clear
    ble/widget/complete
    return
  fi
  local index=$easylinux_selected
  local insert=${easylinux_insertions[index]} start=${easylinux_starts[index]} end=${easylinux_ends[index]}
  easylinux_edit_start=$start easylinux_edit_end=$end easylinux_inserted=$insert
  ble-edit/content/replace "$start" "$end" "$insert"
  _ble_edit_ind=${easylinux_cursors[index]}
  _ble_edit_mark=$_ble_edit_ind _ble_edit_mark_active=
  easylinux/bash/clear
  easylinux/bash/key; easylinux_suppressed=$ret
  easylinux_last_action=tab-insert
}
function ble/widget/easylinux/down {
  if easylinux/bash/current; then
    easylinux_selected=$(((easylinux_selected+1)%${#easylinux_candidates[@]}))
    ble/complete/menu#select "$easylinux_selected"
    easylinux_last_action=select-down
  else easylinux/bash/clear; ble/widget/forward-line history; fi
}
function ble/widget/easylinux/up {
  if easylinux/bash/current; then
    easylinux_selected=$(((easylinux_selected+${#easylinux_candidates[@]}-1)%${#easylinux_candidates[@]}))
    ble/complete/menu#select "$easylinux_selected"
    easylinux_last_action=select-up
  else easylinux/bash/clear; ble/widget/backward-line history; fi
}
function ble/widget/easylinux/escape {
  easylinux/bash/clear
  easylinux/bash/key; easylinux_suppressed=$ret
  easylinux_last_action=escape
}
# The owned coprocess is a running Bash job. Permit native EOF only when it
# is the sole job; all other jobs and IGNOREEOF keep ble.sh's native behavior.
function ble/widget/easylinux/eof {
  local owned_jobs
  owned_jobs=$(jobs -p)
  if [[ ! $_ble_edit_str && $owned_jobs == "$easylinux_core_pid" ]]; then
    local bleopt_allow_exit_with_jobs=1
    ble/widget/delete-region-or delete-forward-char-or-exit
  else
    ble/widget/delete-region-or delete-forward-char-or-exit
  fi
}
function easylinux/bash/snapshot {
  local file=$EASYLINUX_LAB/logs/snapshot.bin i attached=false
  [[ $_ble_attached ]] && attached=true
  {
    printf '%s\0%s\0' buffer "$_ble_edit_str" cursor "$_ble_edit_ind" selected "$easylinux_selected" active "${easylinux_active:-0}" count "${#easylinux_candidates[@]}"
    for ((i=0;i<4;i++)); do printf '%s\0%s\0' "candidate_$i" "${easylinux_candidates[i]-}" "description_$i" "${easylinux_descriptions[i]-}"; done
    printf '%s\0%s\0' attached "$attached" version "${BLE_VERSION[*]}" execution_count "${easylinux_lab_exec_count:-0}" columns "$COLUMNS" lines "$LINES"
    printf '%s\0%s\0' history_file "$HISTFILE" inputrc "$INPUTRC" xdg_config "$XDG_CONFIG_HOME" xdg_cache "$XDG_CACHE_HOME" xdg_state "$XDG_STATE_HOME" runtime "${XDG_RUNTIME_DIR-}" path "$PATH" base_cache "${_ble_base_cache-}" base_state "${_ble_base_state-}" base_run "${_ble_base_run-}"
    printf '%s\0%s\0' edit_start "$easylinux_edit_start" edit_end "$easylinux_edit_end" inserted "$easylinux_inserted" last_action "$easylinux_last_action"
    printf '%s\0%s\0' core_pid "$easylinux_core_pid" core_requests "$easylinux_core_id" core_failed "$easylinux_core_failed"
  } > "$file"
}
function ble/widget/easylinux/snapshot { easylinux/bash/snapshot; }
function easylinux/bash/setup {
  easylinux/bash/core-start
  blehook EXIT+=easylinux/diag/exit
  blehook EXIT+=easylinux/bash/core-stop
  blehook ATTACH+=easylinux/bash/attach-resize
  bleopt complete_menu_style=easylinux-cards
  ble/util/idle.cancel easylinux/bash/idle 2>/dev/null
  ble/util/idle.push-background easylinux/bash/idle
  ble-bind -m emacs -f C-d easylinux/eof
  ble-bind -m emacs -f TAB easylinux/tab
  ble-bind -m emacs -f C-i easylinux/tab
  ble-bind -m emacs -f up easylinux/up
  ble-bind -m emacs -f down easylinux/down
  ble-bind -m emacs -f ESC easylinux/escape
  ble-bind -m emacs -f 'C-[' easylinux/escape
  ble-bind -m emacs -f 'C-x C-t' easylinux/snapshot
  # Enter is intentionally untouched: it keeps Bash/ble.sh execution semantics.
}
