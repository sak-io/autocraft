#!/usr/bin/env bash
# Language registry shared by install.sh and onboard-repo.sh (sourced, not executed).
# shellcheck disable=SC2034  # CQ/ECO are read by the scripts that source this file
# lang_info <lang>  ->  sets CQ (CodeQL language, empty = unsupported) and ECO (Dependabot ecosystem)
LANGS="node python go java dotnet rust flutter terraform"
lang_info() {
  case "$1" in
    node)      CQ=javascript-typescript; ECO=npm ;;
    python)    CQ=python;                ECO=pip ;;
    go)        CQ=go;                    ECO=gomod ;;
    java)      CQ=java-kotlin;           ECO=maven ;;
    dotnet)    CQ=csharp;                ECO=nuget ;;
    rust)      CQ="";                    ECO=cargo ;;      # no CodeQL: clippy + cargo-audit in CI
    flutter)   CQ="";                    ECO=pub ;;        # no CodeQL: flutter analyze + Dependabot
    terraform) CQ="";                    ECO=terraform ;;  # checkov/tflint in CI
    *) return 1 ;;
  esac
}
valid_lang() { [[ " $LANGS " == *" $1 "* ]]; }
