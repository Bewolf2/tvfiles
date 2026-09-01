import os
import sys
import re
import urllib.request
import urllib.parse
import ssl
import subprocess
from lxml import etree

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Paths Setup
pipeline_dir = os.path.dirname(os.path.abspath(__file__))
tvfiles_dir = os.path.abspath(os.path.join(pipeline_dir, "..", ".."))
dm84_path = os.path.join(tvfiles_dir, "py", "dm84", "dm84.py")
validate_script = os.path.join(pipeline_dir, "validate_crawler.py")

site_url = "https://www.dm845.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

def fetch_html(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            return content
    except Exception as e:
        print(f"Error fetching URL '{url}': {e}")
        return None

def self_heal_recommendations(html_content):
    """
    Search for lists of videos on the homepage to find new grid layouts
    """
    tree = etree.HTML(html_content)
    
    # Try different xpaths to find video grids
    candidates = [
        '//div[contains(@class, "item")]',
        '//ul[contains(@class, "vodlist")]/li',
        '//div[contains(@class, "vod-list")]//li',
        '//ul/li[contains(@class, "item")]',
        '//div[contains(@class, "list-item")]'
    ]
    
    for xpath in candidates:
        nodes = tree.xpath(xpath)
        if len(nodes) >= 6:
            # Found a matching container! Let's check if we can parse title and link
            test_node = nodes[0]
            title = test_node.xpath('.//a[contains(@class, "title")]/text()') or test_node.xpath('.//a/text()')
            href = test_node.xpath('.//a[contains(@class, "title")]/@href') or test_node.xpath('.//a/@href')
            if title and href:
                print(f" -> Heuristic Success: Found matching grid container XPath: '{xpath}'")
                return xpath
    return None

def run_healing_cycle():
    print("=" * 60)
    print("STARTING CRAWLER SELF-HEALING DIAGNOSTIC FOR DM84")
    print("=" * 60)
    
    # Step 1: Run validator to see if anything is broken
    print("Running diagnostic verification...")
    res = subprocess_run_validator()
    if res == 0:
        print("Crawler is working perfectly. No self-healing required!")
        return True
        
    print("\nCrawler failure detected. Analyzing structure...")
    
    # Fetch homepage
    home_html = fetch_html(site_url)
    if not home_html:
        print("CRITICAL: Failed to connect to website. Check network connection or domain name.")
        return False
        
    # Heuristic 1: Verify recommendations list
    new_recs_xpath = self_heal_recommendations(home_html)
    if new_recs_xpath:
        # Update XPath in dm84.py
        update_xpath_in_dm84("vod_list_xpath", new_recs_xpath)
        
    # Re-run validator
    print("\nRe-running diagnostic verification after repairs...")
    res = subprocess_run_validator()
    if res == 0:
        print("SUCCESS: Self-healing has repaired the crawler!")
        return True
    else:
        print("ALERT: Automated healing heuristics could not fully resolve the issues.")
        return False

def subprocess_run_validator():
    try:
        res = subprocess.call([sys.executable, validate_script])
        return res
    except Exception as e:
        print(f"Failed to run validator: {e}")
        return 1

def update_xpath_in_dm84(old_indicator, new_xpath):
    if not os.path.exists(dm84_path):
        print(f"dm84.py not found at: {dm84_path}")
        return
        
    with open(dm84_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if old_indicator == "vod_list_xpath":
        new_content = re.sub(
            r"(self\.vod_list_xpath\s*=\s*)(['\"])(.*?)\2",
            lambda m: f"{m.group(1)}{m.group(2)}{new_xpath}{m.group(2)}",
            content
        )
        if new_content != content:
            print(f" -> Modifying self.vod_list_xpath in dm84.py to: '{new_xpath}'")
            with open(dm84_path, "w", encoding="utf-8") as f:
                f.write(new_content)

if __name__ == "__main__":
    run_healing_cycle()
