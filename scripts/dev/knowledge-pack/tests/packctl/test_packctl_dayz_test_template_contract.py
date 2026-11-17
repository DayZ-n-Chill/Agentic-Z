from pathlib import Path


from packctl_testlib import REPO_ROOT


def _template_text() -> str:
    template = REPO_ROOT / "skills/dayz-test-ingame/templates/dayz-test.ps1"
    return template.read_text(encoding="utf-8")


def test_vpp_password_has_no_public_default_and_is_never_echoed() -> None:
    text = _template_text()

    assert "[string]$AdminPass = ''" in text
    assert "VPP login password set -> '$AdminPass'" not in text
    assert "Set-Content -Path $cred -Value $AdminPass" in text
    assert "if (-not [string]::IsNullOrWhiteSpace($AdminPass))" in text


def test_lifecycle_credentials_are_scoped_to_the_child_call() -> None:
    text = _template_text()

    assert "function Initialize-LifecycleCredentials" in text
    assert "GetEnvironmentVariable('DAYZ_MCP_CLIENT_ID_JSON', 'Process')" in text
    assert "GetEnvironmentVariable('DAYZ_MCP_LEASE_TOKEN', 'Process')" in text
    assert "SetEnvironmentVariable('DAYZ_MCP_CLIENT_ID_JSON', $null, 'Process')" in text
    assert "SetEnvironmentVariable('DAYZ_MCP_LEASE_TOKEN', $null, 'Process')" in text
    assert "SetEnvironmentVariable('DAYZ_MCP_CLIENT_ID_JSON', $previousIdentity, 'Process')" in text
    assert "SetEnvironmentVariable('DAYZ_MCP_LEASE_TOKEN', $previousLease, 'Process')" in text
    assert "Initialize-LifecycleCredentials\nif ($Kill)" in text
