import argparse
import json
import pathlib
import re
import sys
import time


from shared.input_errors import (
    INPUT_ENCODING_ERROR_RULE_ID,
    INPUT_NOT_FOUND_RULE_ID,
    build_input_encoding_error,
    build_input_not_found_error,
    decode_error_line_number,
    discover_files,
    read_text_utf8_or_error,
    relative_path,
)
from shared.method_recognition import (
    METHOD_SIGNATURE_RE,
    PARAMS_READ_CONTEXT_PARAM_RE,
    collect_method_signature,
    count_braces,
    find_block_end_line,
    find_if_body_range,
    find_inline_pattern_line,
    find_method_for_line,
    find_method_regions,
    find_next_nonblank_line,
    find_params_read_context_param_name,
    find_signature_brace_line,
    first_param_is_params_read_context,
    method_is_onrpc,
    method_is_onstoreload,
)
from shared.control_flow import (
    ES_EMPTY_IFDEF_RE_CLOSE,
    ES_EMPTY_IFDEF_RE_OPEN,
    ES_EMPTY_IFDEF_RE_UNSUPPORTED_DIRECTIVE,
    ES_EMPTY_IFDEF_RE_UNSUPPORTED_IFDEF,
    SERVER_GUARD_IF_RE,
    TRY_BLOCK_RE,
    compute_ifdef_stack_at,
    find_matching_endif_line,
    find_server_ifdef_block_for_line,
    line_is_inside_server_guard,
    line_is_inside_server_if_guard,
    line_is_inside_server_ifdef,
    line_is_inside_try_block,
    mark_supported_ifdef_stack_has_statement,
    unsupported_directive_opens_block,
    update_ifdef_stack_for_line,
)
from stripper import (
    UNTERMINATED_BLOCK_COMMENT_RULE_ID,
    UNTERMINATED_STRING_RULE_ID,
    make_stripper_warning,
    strip_enforce_comments_and_strings,
)
from detectors.rvmat import (
    RVMAT_MESSAGE,
    RVMAT_RULE_ID,
    RVMAT_SHADER_RE,
    check_rvmat_normalmapmacro,
    strip_rvmat_line_comment,
)
# ES-NO-DELETE quarantined 2026-08-18: vanilla ships 125 `delete` statements and
# its own proto demands manual delete. See the detector module header.
from detectors.es_empty_ifdef import (
    ES_EMPTY_IFDEF_MESSAGE,
    ES_EMPTY_IFDEF_RULE_ID,
    ES_EMPTY_IFDEF_STRAY_ENDIF_MESSAGE,
    ES_EMPTY_IFDEF_UNSUPPORTED_MESSAGE,
    ES_EMPTY_IFDEF_UNSUPPORTED_RULE_ID,
    ES_EMPTY_IFDEF_UNTERMINATED_MESSAGE,
    build_es_empty_ifdef_stray_endif_warning,
    build_es_empty_ifdef_unsupported_warning,
    build_es_empty_ifdef_unterminated_warning,
    check_es_empty_ifdef,
)
from detectors.es_ctx_read import (
    ES_CTX_READ_FAIL_MESSAGE,
    ES_CTX_READ_RULE_ID,
    ES_CTX_READ_UNSUPPORTED_MESSAGE,
    ES_CTX_READ_UNSUPPORTED_RULE_ID,
    ES_CTX_READ_WARN_MESSAGE,
    bool_local_is_checked_within_window,
    build_es_ctx_read_finding,
    build_es_ctx_read_unsupported_warning,
    check_es_ctx_read_unchecked,
    compile_ctx_read_bool_local_re,
    compile_ctx_read_inline_negated_re,
    compile_ctx_read_inline_positive_re,
    compile_ctx_read_re,
    ctx_read_has_supported_check,
    extract_if_condition,
    find_bool_local_unsupported_reason,
    find_ctx_read_unsupported_reason,
    if_body_has_statement,
    line_has_combined_ctx_read_condition,
    line_has_statement_content,
)
from detectors.es_syncvar import (
    ES_SYNCVAR_ALT_GUARD_UNSUPPORTED_MESSAGE,
    ES_SYNCVAR_CLASS_CANDIDATE_RE,
    ES_SYNCVAR_CLASS_HEADER_NEXT_LINE_RE,
    ES_SYNCVAR_CLASS_HEADER_RE,
    ES_SYNCVAR_CLASS_UNKNOWN_MESSAGE,
    ES_SYNCVAR_CLASS_UNKNOWN_RULE_ID,
    ES_SYNCVAR_IFDEF_BRANCH_UNSUPPORTED_MESSAGE,
    ES_SYNCVAR_METHOD_UNPARSED_UNSUPPORTED_MESSAGE,
    ES_SYNCVAR_REGISTER_CALL_RE,
    ES_SYNCVAR_REGISTER_OUTSIDE_CTOR_MESSAGE,
    ES_SYNCVAR_REGISTER_RE,
    ES_SYNCVAR_RULE_ID,
    ES_SYNCVAR_SET_DIRTY_RE,
    ES_SYNCVAR_UNSUPPORTED_RULE_ID,
    ES_SYNCVAR_WRITE_NO_DIRTY_MESSAGE,
    ES_SYNCVAR_WRITE_NO_IFDEF_MESSAGE,
    build_es_syncvar_class_unknown_warning,
    build_es_syncvar_error,
    build_es_syncvar_unsupported_warning,
    check_es_syncvar_construction_hook_classes,
    check_es_syncvar_contract,
    compile_syncvar_assignment_re,
    find_es_syncvar_classes,
    find_es_syncvar_registers,
    find_unknown_class_brace_line,
    method_is_syncvar_registration_target,
    range_contains_register,
    syncvar_assignment_has_set_dirty,
    syncvar_register_match_is_code,
    unique_in_order,
    vanilla_declares_construction_hook,
)
from detectors.es_int_min_compare import (
    ES_INT_MIN_COMPARE_MESSAGE,
    ES_INT_MIN_COMPARE_RE,
    ES_INT_MIN_COMPARE_RULE_ID,
    check_es_int_min_compare,
)
from detectors.es_gettype_exact_match import (
    ES_GETTYPE_EXACT_MATCH_MESSAGE,
    ES_GETTYPE_EXACT_MATCH_RE,
    ES_GETTYPE_EXACT_MATCH_RULE_ID,
    check_es_gettype_exact_match,
)
from detectors.es_layout_path_pboprefix import (
    ES_LAYOUT_PATH_PBOPREFIX_RULE_ID,
    check_es_layout_path_pboprefix,
    parse_pboprefix,
)
# ES-PROCESSDIRECTDAMAGE-DT-ALIAS quarantined 2026-08-18: entityai.c:4103 calls
# ProcessDirectDamage(DT_CUSTOM, ...). See the detector module header.
from detectors.es_local_var_redeclare import (
    ES_LOCAL_VAR_REDECLARE_RULE_ID,
    check_es_local_var_redeclare,
)
from detectors.es_protected_cross_module import (
    check_es_protected_cross_module,
    _module_of as module_of_rel_path,
)
from detectors.es_external_consumer_missing import (
    check_es_external_consumer_missing,
)
from detectors.es_reserved_word_identifier import (
    check_es_reserved_word_identifier,
)
from detectors.es_modulo_float_context import check_es_modulo_float_context
from detectors.es_formula_too_complex import check_es_formula_too_complex
from detectors.es_multiline_condition_operator import (
    check_es_multiline_condition_operator,
)
from detectors.es_unbalanced_brackets import check_es_unbalanced_brackets
from detectors.es_modded_engine_class import check_es_modded_engine_class
from detectors.es_undefined_class_ref import check_es_undefined_class_ref
from detectors.es_variable_named_as_type import check_es_variable_named_as_type
from detectors.es_cast_unrelated_types import check_es_cast_unrelated_types
from detectors.es_proto_argument_downcast import (
    check_es_proto_argument_downcast,
)
from detectors.es_undeclared_static_member import (
    check_es_undeclared_static_member,
)
from detectors.es_protected_method_cross_class import (
    check_es_protected_method_cross_class,
)
from detectors.es_undefined_builtin_method import (
    check_es_undefined_builtin_method,
)
from shared.vanilla_build import compare_vanilla_build, resolve_game_root
from shared.vanilla_tree import resolve_vanilla_root
from detectors.es_member_redeclare_base import (
    ES_MEMBER_REDECLARE_BASE_RULE_ID,
    check_es_member_redeclare_base,
)
from detectors.es_override_param_name_mismatch import (
    ES_OVERRIDE_PARAM_NAME_MISMATCH_RULE_ID,
    check_es_override_param_name_mismatch,
)
from detectors.es_config_nested_override import (
    ES_CONFIG_NESTED_OVERRIDE_RULE_ID,
    check_es_config_nested_override,
)
from detectors.es_config_inputs_xml import (
    ES_INPUTS_XML_NOT_REGISTERED_RULE_ID,
    check_es_inputs_xml_registered,
    check_es_inputs_xml_root,
    detect_inputs_xml,
)
from detectors.es_config_attachments_append import (
    ES_ATTACHMENTS_APPEND_CROSSPBO_RULE_ID,
    check_es_attachments_compound_append,
)
from detectors.es_ref_autoptr_combined import (
    ES_REF_AUTOPTR_COMBINED_RULE_ID,
    check_es_ref_autoptr_combined,
)
from detectors.pdrive_path import (
    PDRIVE_PATH_CONFIG_RULE_ID,
    PDRIVE_PATH_RVMAT_RULE_ID,
    check_pdrive_path,
)
from detectors.es_layout_file_missing import (
    ES_LAYOUT_FILE_MISSING_RULE_ID,
    check_es_layout_file_missing,
)
from detectors.es_method_name_collides_vanilla_class import (
    ES_METHOD_NAME_COLLIDES_VANILLA_CLASS_RULE_ID,
    check_es_method_name_collides_vanilla_class,
)
from detectors.layout_xml_format import check_layout_xml_format
from detectors.es_onmouseleave_param_count import (
    ES_ONMOUSELEAVE_PARAM_COUNT_RULE_ID,
    check_es_onmouseleave_param_count,
)
from detectors.es_registerrecipes_typo import (
    ES_REGISTERRECIPES_TYPO_RULE_ID,
    check_es_registerrecipes_typo,
)
from detectors.es_nonexistent_method import (
    ES_NONEXISTENT_METHOD_RULE_ID,
    check_es_nonexistent_method,
)
from detectors.es_respawn_equip_onclientrespawn import (
    ES_RESPAWN_EQUIP_RULE_ID,
    check_es_respawn_equip_onclientrespawn,
)
# ES-C-STYLE-CAST and ES-STRING-PLUS-BOOL were quarantined 2026-08-18: both rested
# on claims the vanilla tree refutes. See the headers of their detector modules.
from detectors.es_override_of_platform_gated_method import (
    ES_OVERRIDE_OF_PLATFORM_GATED_METHOD_RULE_ID,
    check_es_override_of_platform_gated_method,
)


def build_result(addon_root, errors, warnings, files_scanned, elapsed_ms,
                 skipped_checks=None):
    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    info = {
        "files_scanned": files_scanned,
        "elapsed_ms": elapsed_ms,
    }
    if skipped_checks:
        # What a rule could not judge. It does not change the status: a missing
        # tree is not a failure of the addon, but it is no PASS of that rule either.
        info["skipped_checks"] = skipped_checks
    return {
        "addon_root": str(addon_root),
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "info": info,
    }


def exit_code_for_status(status):
    if status == "FAIL":
        return 1
    if status == "WARN":
        return 2
    return 0


def collect_external_scripts(external_roots):
    """Read the .c files of roots OUTSIDE the addon (missions, other mods).

    The paths arrive as arguments, never hardcoded: the repo forbids committing
    absolute paths of one particular machine.
    """
    collected = []
    for root in external_roots or []:
        root_path = pathlib.Path(root)
        if not root_path.exists():
            continue
        for path in sorted(root_path.rglob("*.c")):
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            rel = relative_path(path, root_path)
            stripped, _ = strip_enforce_comments_and_strings(source, rel)
            collected.append((rel, stripped))
    return collected


def collect_external_configs(external_roots):
    """config.cpp of the external roots: their CfgPatches says which dependency they cover."""
    collected = []
    for root in external_roots or []:
        root_path = pathlib.Path(root)
        if not root_path.exists():
            continue
        for path in sorted(root_path.rglob("config.cpp")):
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            collected.append((relative_path(path, root_path), source))
    return collected


def validate_addon(addon_root, external_roots=None, vanilla_root=None,
                   vanilla_skip_reason=None, game_root=None):
    start = time.perf_counter()
    received_addon_root = pathlib.Path(addon_root)
    addon_root = pathlib.Path(addon_root).resolve()
    relative_root = addon_root if addon_root.is_dir() else addon_root.parent
    errors = []
    warnings = []

    if not addon_root.exists():
        errors.append(build_input_not_found_error(received_addon_root))
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return build_result(addon_root, errors, warnings, 0, elapsed_ms)

    files = discover_files(addon_root)
    construction_hook = vanilla_declares_construction_hook(vanilla_root)
    hook_registrations = []
    module_files = []
    addon_sources = []
    addon_configs = []
    pboprefix = parse_pboprefix(addon_root)
    inputs_xml_present = detect_inputs_xml(relative_root)
    errors.extend(check_es_inputs_xml_root(relative_root))

    for path in files:
        suffix = path.suffix.lower()
        rel_path = relative_path(path, relative_root)
        source, encoding_error = read_text_utf8_or_error(path, rel_path)
        if encoding_error:
            errors.append(encoding_error)
            continue

        if suffix == ".c":
            stripped, stripper_warnings = strip_enforce_comments_and_strings(
                source, rel_path
            )
            warnings.extend(stripper_warnings)
            module_files.append((rel_path, module_of_rel_path(rel_path), stripped))
            addon_sources.append((rel_path, stripped))
            empty_ifdef_errors, empty_ifdef_warnings = check_es_empty_ifdef(
                stripped, rel_path
            )
            errors.extend(empty_ifdef_errors)
            warnings.extend(empty_ifdef_warnings)
            ctx_read_errors, ctx_read_warnings = check_es_ctx_read_unchecked(
                stripped, rel_path
            )
            errors.extend(ctx_read_errors)
            warnings.extend(ctx_read_warnings)
            syncvar_errors, syncvar_warnings = check_es_syncvar_contract(
                source, stripped, rel_path, construction_hook, hook_registrations
            )
            errors.extend(syncvar_errors)
            warnings.extend(syncvar_warnings)
            warnings.extend(check_es_int_min_compare(stripped, rel_path))
            warnings.extend(check_es_gettype_exact_match(stripped, rel_path))
            warnings.extend(check_es_ref_autoptr_combined(stripped, rel_path))
            warnings.extend(
                check_es_onmouseleave_param_count(stripped, rel_path)
            )
            errors.extend(check_es_local_var_redeclare(stripped, rel_path))
            errors.extend(check_es_member_redeclare_base(stripped, rel_path))
            errors.extend(check_es_override_param_name_mismatch(stripped, rel_path))
            errors.extend(
                check_es_layout_path_pboprefix(source, rel_path, pboprefix)
            )
            errors.extend(
                check_es_layout_file_missing(
                    source, rel_path, pboprefix, relative_root
                )
            )
            errors.extend(
                check_es_method_name_collides_vanilla_class(stripped, rel_path)
            )
            registerrecipes_errors, registerrecipes_warnings = (
                check_es_registerrecipes_typo(stripped, rel_path)
            )
            errors.extend(registerrecipes_errors)
            warnings.extend(registerrecipes_warnings)
            errors.extend(check_es_nonexistent_method(stripped, rel_path))
            warnings.extend(
                check_es_respawn_equip_onclientrespawn(stripped, rel_path)
            )
            errors.extend(
                check_es_override_of_platform_gated_method(stripped, rel_path)
            )
            errors.extend(check_es_reserved_word_identifier(stripped, rel_path))
            errors.extend(
                check_es_modulo_float_context(source, stripped, rel_path)
            )
            warnings.extend(
                check_es_formula_too_complex(source, stripped, rel_path)
            )
            if not stripper_warnings:
                # An unterminated string or comment blanks the rest of the
                # file: its brackets cannot be counted, and the stripper
                # already reported why.
                errors.extend(check_es_unbalanced_brackets(stripped, rel_path))
            errors.extend(check_es_modded_engine_class(stripped, rel_path))
            errors.extend(
                check_es_multiline_condition_operator(stripped, rel_path)
            )
        elif suffix == ".rvmat":
            errors.extend(check_rvmat_normalmapmacro(source, rel_path))
            warnings.extend(
                check_pdrive_path(source, rel_path, PDRIVE_PATH_RVMAT_RULE_ID)
            )
        elif suffix == ".layout":
            errors.extend(check_layout_xml_format(source, rel_path))
        elif suffix == ".cpp" and path.name.lower() == "config.cpp":
            addon_configs.append((rel_path, source))
            config_stripped, config_strip_warnings = (
                strip_enforce_comments_and_strings(source, rel_path)
            )
            warnings.extend(config_strip_warnings)
            errors.extend(
                check_es_config_nested_override(config_stripped, rel_path)
            )
            errors.extend(
                check_es_inputs_xml_registered(
                    config_stripped, rel_path, inputs_xml_present
                )
            )
            warnings.extend(
                check_es_attachments_compound_append(config_stripped, rel_path)
            )
            warnings.extend(
                check_pdrive_path(source, rel_path, PDRIVE_PATH_CONFIG_RULE_ID)
            )

    # TREE checks, not file checks: they need to see one module against
    # another, the addon against an external consumer, or the addon against
    # everything that declares types (vanilla and dependencies).
    external_sources = collect_external_scripts(external_roots)
    errors.extend(
        check_es_syncvar_construction_hook_classes(
            hook_registrations, addon_sources, external_sources, vanilla_root
        )
    )
    errors.extend(check_es_protected_cross_module(module_files))
    errors.extend(
        check_es_external_consumer_missing(addon_sources, external_sources)
    )
    undefined_errors, skipped_checks = check_es_undefined_class_ref(
        addon_sources,
        addon_configs,
        external_sources,
        collect_external_configs(external_roots),
        vanilla_root,
        vanilla_skip_reason or "vanilla tree not passed (vanilla_root=None)",
        addon_is_vanilla=(
            vanilla_root is not None
            and pathlib.Path(vanilla_root).resolve() == addon_root
        ),
    )
    errors.extend(undefined_errors)
    named_as_type_errors, named_as_type_skipped = check_es_variable_named_as_type(
        addon_sources,
        external_sources,
        vanilla_root,
        vanilla_skip_reason or "vanilla tree not passed (vanilla_root=None)",
    )
    errors.extend(named_as_type_errors)
    skipped_checks = list(skipped_checks) + named_as_type_skipped
    errors.extend(
        check_es_cast_unrelated_types(addon_sources, external_sources, vanilla_root)
    )
    downcast_errors, downcast_warnings = check_es_proto_argument_downcast(
        addon_sources, external_sources, vanilla_root
    )
    errors.extend(downcast_errors)
    warnings.extend(downcast_warnings)
    errors.extend(
        check_es_undeclared_static_member(
            addon_sources, external_sources, vanilla_root
        )
    )
    warnings.extend(
        check_es_protected_method_cross_class(
            addon_sources, external_sources, vanilla_root
        )
    )
    builtin_errors, builtin_skipped = check_es_undefined_builtin_method(
        addon_sources,
        external_sources,
        vanilla_root,
        vanilla_skip_reason or "vanilla tree not passed (vanilla_root=None)",
    )
    errors.extend(builtin_errors)
    skipped_checks = list(skipped_checks) + builtin_skipped
    build_info = None
    if game_root:
        # Not a rule on the addon: whether the vanilla tree the rules above
        # read is the game's own scripts.
        build_warnings, build_skipped, build_info = compare_vanilla_build(
            vanilla_root, game_root
        )
        warnings.extend(build_warnings)
        skipped_checks = list(skipped_checks) + build_skipped

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    result = build_result(
        addon_root, errors, warnings, len(files), elapsed_ms, skipped_checks
    )
    if build_info is not None:
        result["info"]["vanilla_build"] = build_info
    return result


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("addon_root")
    parser.add_argument(
        "--terse",
        action="store_true",
        help=(
            "Print the verdict on the first line, then one line per finding, "
            "instead of the JSON report."
        ),
    )
    parser.add_argument(
        "--external-scripts",
        action="append",
        metavar="DIR",
        help=(
            "Root of script that lives OUTSIDE the addon and calls into it -- a "
            "mission folder, another mod. Repeatable. Enables "
            "ES-EXTERNAL-CONSUMER-MISSING, which catches a method removed from "
            "an addon class while an external consumer still calls it. Its "
            "classes also count as declared for ES-UNDEFINED-CLASS-REF: pass "
            "every dependency mod (CF, ...) the addon's config.cpp requires."
        ),
    )
    parser.add_argument(
        "--vanilla-root",
        metavar="DIR",
        help=(
            "Vanilla scripts tree (default: DAYZ_VANILLA_ROOT, then P:\\scripts "
            "if present). Needed by ES-UNDEFINED-CLASS-REF and "
            "ES-UNDEFINED-BUILTIN-METHOD; without it they are reported as "
            "skipped in info, never as a finding, ES-VARIABLE-NAMED-AS-TYPE "
            "judges only the addon's and external roots' type names, and "
            "ES-SYNCVAR-CONTRACT does not accept the DayZ 1.30 "
            "RegisterConstructionSyncVariables hook. Pass the scripts of the "
            "build the addon runs on: see --game-root."
        ),
    )
    parser.add_argument(
        "--game-root",
        metavar="DIR",
        help=(
            "DayZ install folder of the game the addon runs on (default: "
            "DAYZ_GAME_ROOT); its dta\\scripts.pbo itself also works. The "
            "vanilla tree is compared with that PBO file by file, and "
            "VANILLA-ROOT-BUILD-MISMATCH warns when they differ: the rules "
            "that read the vanilla tree judge against the tree, not the game. "
            "Without it nothing is compared."
        ),
    )
    return parser


def run(argv=None):
    args = build_parser().parse_args(argv)

    vanilla_root, vanilla_skip_reason = resolve_vanilla_root(args.vanilla_root)
    result = validate_addon(
        args.addon_root,
        args.external_scripts,
        vanilla_root=vanilla_root,
        vanilla_skip_reason=vanilla_skip_reason,
        game_root=resolve_game_root(args.game_root),
    )
    return exit_code_for_status(result["status"]), result


def format_terse(result):
    """Verdict first, details after.

    A reader that stops at line one still has the answer, which is the point:
    the JSON report buries `status` three lines in, and a hook dumping the whole
    document to stderr is noise rather than a signal. The exit code stays the
    machine channel; this is the one humans and agents actually read.
    """
    errors = list(result.get("errors", []))
    warnings = list(result.get("warnings", []))
    counts = []
    if errors:
        counts.append("%d error%s" % (len(errors), "" if len(errors) == 1 else "s"))
    if warnings:
        counts.append("%d warning%s" % (len(warnings), "" if len(warnings) == 1 else "s"))
    head = result.get("status", "UNKNOWN")
    if counts:
        head = "%s - %s" % (head, ", ".join(counts))
    lines = [head]
    for finding in errors + warnings:
        lines.append("  %s  %s" % (finding.get("rule_id", "?"), finding.get("message", "")))
    for skipped in (result.get("info") or {}).get("skipped_checks") or []:
        lines.append(
            "  SKIP %s  %s" % (skipped.get("rule_id", "?"), skipped.get("reason", ""))
        )
    return "\n".join(lines)


def main(argv=None):
    args = build_parser().parse_args(argv)
    exit_code, result = run(argv)
    if args.terse:
        print(format_terse(result))
    else:
        print(json.dumps(result, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
