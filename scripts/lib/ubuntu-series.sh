#!/usr/bin/env bash
#
# Library: maps kernel version to Ubuntu series codename.
# Source this file to get ubuntu_series_for_kver().
#

ubuntu_series_for_kver() {
    local kver="$1"
    local major minor ver_num
    major=$(echo "${kver}" | cut -d. -f1)
    minor=$(echo "${kver}" | cut -d. -f2)
    ver_num=$(( major * 100 + minor ))

    # Ascending order: oldest first; pick the first release whose kernel >= ver
    local -a releases=(
        "300 oneiric"
        "302 precise"
        "305 quantal"
        "308 raring"
        "311 saucy"
        "313 trusty"
        "316 utopic"
        "319 vivid"
        "402 wily"
        "404 xenial"
        "408 yakkety"
        "410 zesty"
        "413 artful"
        "415 bionic"
        "418 cosmic"
        "500 disco"
        "503 eoan"
        "504 focal"
        "508 groovy"
        "511 hirsute"
        "513 impish"
        "515 jammy"
        "519 kinetic"
        "602 lunar"
        "605 mantic"
        "608 noble"
        "611 oracular"
        "614 plucky"
        "617 questing"
        "700 resolute"
        "9999 devel"
    )

    for entry in "${releases[@]}"; do
        local rel_ver="${entry%% *}"
        local rel_name="${entry##* }"
        if [ ${ver_num} -le ${rel_ver} ]; then
            echo "${rel_name}"
            return
        fi
    done
}
