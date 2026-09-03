import pytest

from matchlens.security import sign_result, validate_remote_url, verify_result


@pytest.mark.parametrize("url",["file:///etc/passwd","http://127.0.0.1/x","http://localhost/x"])
def test_rejects_unsafe_urls(url):
    with pytest.raises(ValueError): validate_remote_url(url)

def test_signed_result_url():
    expires,signature=sign_result("job","report.html","secret",5)
    assert verify_result("job","report.html",expires,signature,"secret")
    assert not verify_result("other","report.html",expires,signature,"secret")
