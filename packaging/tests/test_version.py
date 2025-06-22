import re
import pytest

PEP440 = re.compile(r'(?P<major>\d)\.(?P<minor>\d)(\.(?P<fix>\d))?((?P<pre>a|b|rc)(?P<rel>\d))?')


def _pep440_to_windows_version(version: str) -> str:
    """Convert a PEP440-compatible version string to a Windows version string"""
    if m := PEP440.match(version):
        groups = m.groupdict()
        if not groups.get('fix'):
            groups['fix'] = '0'
        build_number = 5000
        if groups.get('pre'):
            if groups['pre'] == 'a':
                build_number = 1000
            elif groups['pre'] == 'b':
                build_number = 2000
            elif groups['pre'] == 'rc':
                build_number = 3000
        if groups.get('rel'):
            try:
                rel = int(groups['rel'])
                build_number += rel
            except ValueError:
                pass
        return f'{groups["major"]}.{groups["minor"]}.{groups["fix"]}.{build_number}'
    else:
        return '0.0.0.0'


@pytest.mark.parametrize('pep440_version, windows_version', [
    ('2.9.1', '2.9.1.5000'), ('3.1rc1', '3.1.0.3001'), ('3.0.2b2', '3.0.2.2002'), ('1.9a1', '1.9.0.1001')])
def test_pep440_to_windows_version(pep440_version, windows_version):
    assert _pep440_to_windows_version(pep440_version) == windows_version
