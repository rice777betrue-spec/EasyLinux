declare -gA easylinux_wrap_lines=() easylinux_wrap_widths=()
declare -gA easylinux_char_width=()
# Wrap plain demo strings using ble.sh's character-width table. No subprocesses.
function easylinux/bash/wrap {
  local text=$1 width=$2 i ch cw line= used=0 ret
  ((width>=2)) || return 1
  local cachekey="$bleopt_char_width_mode:${_ble_unicode_c2w_ambiguous-}:$width:$text"
  if [[ ${easylinux_wrap_lines[$cachekey]+exists} ]]; then
    IFS=$'\x1f' read -r -a easylinux_wrapped <<< "${easylinux_wrap_lines[$cachekey]}"
    IFS=' ' read -r -a easylinux_widths <<< "${easylinux_wrap_widths[$cachekey]}"
    return 0
  fi
  easylinux_wrapped=() easylinux_widths=()
  for ((i=0;i<${#text};i++)); do
    ch=${text:i:1}
    if [[ $ch == [\ -~] ]]; then
      cw=1
    else
      local widthkey="$bleopt_char_width_mode:${_ble_unicode_c2w_ambiguous-}:$ch"
      cw=${easylinux_char_width[$widthkey]-}
      if [[ ! $cw ]]; then
        ble/util/s2w "$ch"; cw=$ret
        easylinux_char_width[$widthkey]=$cw
      fi
    fi
    if ((used+cw>width&&used)); then
      easylinux_wrapped+=("$line") easylinux_widths+=("$used")
      line= used=0
    fi
    line=$line$ch
    ((used+=cw))
  done
  easylinux_wrapped+=("$line") easylinux_widths+=("$used")
  local serialized
  printf -v serialized '%s\x1f' "${easylinux_wrapped[@]}"
  easylinux_wrap_lines[$cachekey]=$serialized
  easylinux_wrap_widths[$cachekey]="${easylinux_widths[*]}"
}
function easylinux/bash/pad {
  local n=$1
  ((n>=0 && n<=COLUMNS)) || { ret=; return 1; }
  printf -v ret '%*s' "$n" ''
}
# Custom menu class renders a complete card. Its bbox is also used by native
# selection repaint, so border/description layout remains stable on navigation.
function easylinux/bash/menu/render-item {
  local opts=$2 ACTION CAND INSERT DATA PREFIX_LEN
  ble/complete/cand/unpack "$1"
  local width=$cols inner=$((cols-4)) out= line w i base=0 prefixlen=${#easylinux_prefix}
  local normal=$'\e[0m' matched=$'\e[1;36m' selected=
  [[ :$opts: == *:selected:* ]] && selected=$'\e[7m'
  easylinux/bash/wrap "$CAND" "$inner"
  local -a command_lines=("${easylinux_wrapped[@]}") command_widths=("${easylinux_widths[@]}")
  for ((i=0;i<${#command_lines[@]};i++)); do
    line=${command_lines[i]} w=${command_widths[i]}
    local n=$((prefixlen-base))
    ((n<0)) && n=0
    ((n>${#line})) && n=${#line}
    easylinux/bash/pad "$((inner-w))"
    out=$out'│ '$selected$matched${line::n}$normal$selected${line:n}$normal$ret' │'
    ((base+=${#line}))
    out=$out$'\n'
  done
  easylinux/bash/wrap "$DATA" "$inner"
  for ((i=0;i<${#easylinux_wrapped[@]};i++)); do
    line=${easylinux_wrapped[i]} w=${easylinux_widths[i]}
    easylinux/bash/pad "$((inner-w))"
    out=$out'│ '$line$ret' │'
    ((i+1<${#easylinux_wrapped[@]})) && out=$out$'\n'
  done
  y=$((${#command_lines[@]}+${#easylinux_wrapped[@]}-1)) x=$width
  ret=$out
}
function easylinux/bash/menu/onselect { return 0; }
function easylinux/bash/menu/get-desc {
  local ACTION CAND INSERT DATA PREFIX_LEN
  ble/complete/cand/unpack "$1"; desc=$DATA
}
function ble/complete/menu-style:easylinux-cards/construct-page {
  local width=$((cols-1)) inner i pack body h used=1 index=$begin
  ((width>76)) && width=76
  ((width>=12&&lines>=5)) || return 1
  local rule
  printf -v rule '%*s' "$((width-2))" ''
  rule=${rule// /─}
  esc='┌'$rule'┐'
  for ((i=begin;i<${#menu_items[@]};i++)); do
    pack=${menu_items[i]}
    local ret
    x=0 y=0
    cols=$width easylinux/bash/menu/render-item "$pack"
    body=$ret h=$((y+1))
    ((used+h+1<=lines)) || break
    esc=$esc$'\n'$body
    _ble_complete_menu_style_icons[i]=0,$used,$width,$((used+h-1)),${#pack},${#body},"0 0 $width $h":$pack$body
    ((used+=h,index++))
    # Separator is outside the icon, so only the card repaints on selection.
    if ((i+1<${#menu_items[@]}&&used+4<=lines)); then
      esc=$esc$'\n''├'$rule'┤'
      ((used++))
    fi
  done
  ((index>begin)) || return 1
  esc=$esc$'\n''└'$rule'┘'
  end=$index x=$width y=$used
  return 0
}
function ble/complete/menu-style:easylinux-cards/locate {
  case $1 in down) ret=$(($2+1)) ;; up) ret=$(($2-1)) ;; *) return 1 ;; esac
}
function easylinux/bash/show {
  easylinux/bash/geometry-ok || return 1
  local render_started=$EPOCHREALTIME
  easylinux_render_phase=menu-construct
  easylinux/diag render-start
  local COMP1=$easylinux_begin COMP2=$_ble_edit_ind
  local COMPS=$easylinux_prefix COMPV=$easylinux_prefix comps_flags=v comps_fixed=
  local comp_type=sync:menu-color:menu-color-match comp_filter_type=none comp_filter_pattern=*
  local COMP_PREFIX= flag_force_fignore= flag_source_filter=1 cand_count=0
  local -a cand_cand=() cand_word=() cand_pack=()
  ble/complete/source:easylinux-core
  ((cand_count)) || return 1
  local menu_common_part=$COMPS
  ble/complete/menu/show init:show_menu:sync || return 1
  # menu/show supplies the stock completion class. This prototype installs its
  # documented custom menu-class renderer for multi-line selected-item repaint.
  _ble_complete_menu_class=easylinux/bash/menu
  easylinux_active=1 easylinux_selected=0
  ble/complete/menu#select 0
  easylinux_render_phase=idle
  easylinux/diag render-end "start=$render_started end=$EPOCHREALTIME"
}
