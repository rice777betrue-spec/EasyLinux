# Before/after hooks surround native WINCH; native trap is never replaced.
easylinux_resize_pending=
easylinux_resize_busy=
function easylinux/bash/geometry-ok {
  [[ $COLUMNS =~ ^[0-9]+$ && $LINES =~ ^[0-9]+$ ]] &&
    ((COLUMNS>=16 && LINES>=8))
}
function easylinux/bash/onwinch {
  ((++easylinux_winch_count))
  easylinux/diag winch-begin
  easylinux_resize_pending=1
  [[ ! $easylinux_resize_busy ]] || return 0
  ble/term/update-winsize
  easylinux_render_phase=discard-old-info
  easylinux/bash/clear
  easylinux_seen= easylinux_suppressed=
  _ble_complete_menu_style_hash=
  _ble_complete_menu_style_pages=()
  _ble_complete_menu_style_measure=()
  easylinux/diag winch-before-native
}
function easylinux/bash/afterwinch {
  [[ $easylinux_resize_pending && ! $easylinux_resize_busy ]] || return 0
  [[ ! $_ble_app_onwinch_Suppress && ! $_ble_app_onwinch_Deferred ]] || return 0
  easylinux_resize_busy=1
  ble/term/update-winsize
  easylinux_render_phase=after-native
  easylinux/diag winch-after-native
  if easylinux/bash/geometry-ok &&
     [[ $_ble_term_state == internal && $easylinux_core_cache_text == "$_ble_edit_str" &&
        $easylinux_core_cache_cursor == "$_ble_edit_ind" ]] &&
     ((${#easylinux_candidates[@]})); then
    easylinux_text=$_ble_edit_str easylinux_cursor=$_ble_edit_ind
    easylinux/bash/show || easylinux/bash/clear
  else
    easylinux/bash/clear
  fi
  easylinux_resize_pending= easylinux_resize_busy=
  easylinux_diag_previous_size=$LINES'x'$COLUMNS
  easylinux_render_phase=idle
  easylinux/diag winch-finished
  ble/util/idle.cancel easylinux/bash/idle
  ble/util/idle.push-background easylinux/bash/idle
}
function easylinux/bash/attach-resize {
  blehook internal_WINCH+-=easylinux/bash/onwinch
  blehook internal_WINCH-+=easylinux/bash/afterwinch
  blehook idle_after_task!=easylinux/bash/afterwinch
  easylinux/diag attached
}
