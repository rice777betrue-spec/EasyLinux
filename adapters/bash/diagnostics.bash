# File diagnostics omit command text and protocol payload.
easylinux_winch_count=0
easylinux_diag_previous_size="${LINES-0}x${COLUMNS-0}"
function easylinux/diag {
  [[ ${EASYLINUX_SESSION_LOG-} ]] || return 0
  printf 'time=%s\tpid=%s\tppid=%s\tevent=%q\trows=%s\tcols=%s\tprevious=%q\tterm=%q\thost=%q\twinch=%s\tmenu=%s\tcore_pid=%s\tcore_failed=%s\tphase=%q\tdetail=%q\n' \
    "$EPOCHREALTIME" "$BASHPID" "$PPID" "$1" "${LINES-0}" "${COLUMNS-0}" \
    "$easylinux_diag_previous_size" "${TERM-}" "${EASYLINUX_HOST_KIND-unknown}" \
    "$easylinux_winch_count" "${easylinux_active-0}" "${easylinux_core_pid-0}" \
    "${easylinux_core_failed-0}" "${easylinux_render_phase-boot}" "${2-}" >> "$EASYLINUX_SESSION_LOG"
}
function easylinux/diag/exit {
  local status=$?
  easylinux/diag bash-exit "status=$status"
  return "$status"
}
