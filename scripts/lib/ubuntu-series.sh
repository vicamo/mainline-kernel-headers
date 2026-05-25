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

    # Descending order: newest first
    local -a releases=(
        "700 resolute"
        "617 questing"
        "614 plucky"
        "611 oracular"
        "608 noble"
        "605 mantic"
        "602 lunar"
        "519 kinetic"
        "515 jammy"
        "513 impish"
        "511 hirsuit"
        "508 groovy"
        "504 focal"
        "503 eoan"
        "500 disco"
        "418 cosmic"
        "415 bionic"
        "413 artful"
        "410 zesty"
        "408 yakkety"
        "404 xenial"
        "402 wily"
        "319 vivid"
        "316 utopic"
        "313 trusty"
        "311 saucy"
        "308 raring"
        "305 quantal"
        "302 precise"
        "300 oneiric"
    )

    for entry in "${releases[@]}"; do
        local rel_ver="${entry%% *}"
        local rel_name="${entry##* }"
        if [ ${ver_num} -ge ${rel_ver} ]; then
            echo "${rel_name}"
            return
        fi
    done
    # Fallback for very old kernels
    echo "oneiric"
}
