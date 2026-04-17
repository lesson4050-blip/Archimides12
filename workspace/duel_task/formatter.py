import re

def extract_links(html_content: str) -> list[str]:
    """
    Extracts all URLs from href attributes of <a> tags within html_content.
    """
    # Regex to find all <a> tags
    pattern = r'<a\s+[^>]*>'
    tags = re.findall(pattern, html_content, re.IGNORECASE)
    
    links = []
    for tag in tags:
        # Regex to extract href value
        href_match = re.search(r'href=[\'"]([^\'"]+)[\'"]', tag, re.IGNORECASE)
        if href_match:
            links.append(href_match.group(1))
        else:
            # Bug: Crashes if an anchor tag doesn't contain an href attribute
            raise KeyError("Anchor tag is missing an 'href' attribute")
            
    return links
