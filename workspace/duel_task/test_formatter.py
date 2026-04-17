from formatter import extract_links
import pytest

def test_extract_links_basic():
    html = '<a href="http://google.com">Google</a>'
    assert extract_links(html) == ["http://google.com"]

def test_extract_links_no_href():
    # This test replicates the user issue
    html = '<a>No link</a><a href="http://example.com/">Example</a>'
    links = extract_links(html)
    assert links == ["http://example.com/"]

def test_extract_links_whitespace():
    # Whitespace inside the URL should be stripped according to user request
    html = '<a href=" http://example.com/ ">Example</a>'
    links = extract_links(html)
    assert links == ["http://example.com/"]
