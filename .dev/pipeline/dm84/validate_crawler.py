import os
import sys
import subprocess
import json
from unittest.mock import MagicMock

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# 1. Bootstrap dependencies (requests, lxml) if missing
def bootstrap():
    for pkg in ["requests", "lxml"]:
        try:
            __import__(pkg)
        except ImportError:
            print(f"Installing missing dependency: {pkg}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            except Exception as e:
                print(f"Failed to install {pkg} via pip: {e}")

bootstrap()

# 2. Mock Android/Chaquopy packages
sys.modules['com.github.catvod'] = MagicMock()
sys.modules['com.chaquo.python'] = MagicMock()

# 3. Setup system paths relative to this script's location
pipeline_dir = os.path.dirname(os.path.abspath(__file__))
tvfiles_dir = os.path.abspath(os.path.join(pipeline_dir, "..", "..", ".."))
dm84_dir = os.path.join(tvfiles_dir, "py", "dm84")
chaquo_py_dir = os.path.abspath(os.path.join(tvfiles_dir, "..", "chaquo", "src", "main", "python"))

if dm84_dir not in sys.path:
    sys.path.insert(0, dm84_dir)
if chaquo_py_dir not in sys.path:
    sys.path.insert(0, chaquo_py_dir)

# 4. Import the crawler module
try:
    from dm84 import Dm84Spider
except ImportError as e:
    print(f"CRITICAL: Failed to import Dm84Spider: {e}")
    print("Paths searched:")
    for path in sys.path:
        print(f" - {path}")
    sys.exit(1)

def run_tests():
    print("=" * 60)
    print("RUNNING CRAWLER INTEGRATION TESTS FOR DM84")
    print("=" * 60)
    
    spider = Dm84Spider()
    spider.init()
    
    errors = []
    
    # Test 1: homeContent (Categories and Filters)
    print("Test 1: Validating homeContent...")
    try:
        home = spider.homeContent(True)
        classes = home.get("class", [])
        filters = home.get("filters", {})
        
        if len(classes) != 4:
            errors.append(f"homeContent: Expected 4 categories, got {len(classes)} ({[c['type_name'] for c in classes]})")
        else:
            print(f" -> Found 4 categories: {[c['type_name'] for c in classes]}")
            
        if not filters or "28" not in filters or "30" not in filters:
            errors.append("homeContent: Filters dictionary is empty or missing keys '28' or '30'")
        else:
            print(" -> Filters successfully generated.")
    except Exception as e:
        errors.append(f"homeContent failed: {e}")
        
    # Test 2: homeVideoContent (Recommendations)
    print("\nTest 2: Validating homeVideoContent (Recommendations)...")
    try:
        recs = spider.homeVideoContent()
        vod_list = recs.get("list", [])
        if not vod_list:
            errors.append("homeVideoContent: Returned an empty video recommendation list")
        else:
            print(f" -> Successfully parsed {len(vod_list)} homepage recommended videos.")
            for v in vod_list[:3]:
                print(f"    - [{v.get('vod_id')}] {v.get('vod_name')} ({v.get('vod_remarks')})")
    except Exception as e:
        errors.append(f"homeVideoContent failed: {e}")
        
    # Test 3: categoryContent (Category listing)
    print("\nTest 3: Validating categoryContent...")
    try:
        # Fetch 国漫 (tid="28") page 1
        cat_data = spider.categoryContent("28", "1", True, {})
        vod_list = cat_data.get("list", [])
        if not vod_list:
            errors.append("categoryContent (国漫): Returned an empty list")
        else:
            print(f" -> Successfully fetched {len(vod_list)} items for 国漫.")
            for v in vod_list[:3]:
                print(f"    - [{v.get('vod_id')}] {v.get('vod_name')} ({v.get('vod_remarks')})")
            
        # Fetch 国漫 (tid="28") with filter (Year: 2025)
        cat_filtered = spider.categoryContent("28", "1", True, {"year": "2025"})
        filtered_list = cat_filtered.get("list", [])
        if not filtered_list:
            errors.append("categoryContent (国漫 with filter year=2025): Returned empty list")
        else:
            print(f" -> Successfully fetched {len(filtered_list)} filtered 国漫 items.")
            for v in filtered_list[:3]:
                print(f"    - [{v.get('vod_id')}] {v.get('vod_name')} ({v.get('vod_remarks')})")
    except Exception as e:
        errors.append(f"categoryContent failed: {e}")
        
    # Test 4: searchContent (Search)
    print("\nTest 4: Validating searchContent...")
    test_query = "凡人"
    search_id = None
    try:
        search_res = spider.searchContent(test_query, False)
        vod_list = search_res.get("list", [])
        if not vod_list:
            errors.append(f"searchContent: Search for '{test_query}' returned no results")
        else:
            print(f" -> Search for '{test_query}' found {len(vod_list)} results.")
            for v in vod_list[:3]:
                print(f"    - [{v.get('vod_id')}] {v.get('vod_name')} ({v.get('vod_remarks')})")
            search_id = vod_list[0]['vod_id']
    except Exception as e:
        errors.append(f"searchContent failed: {e}")
        
    # Test 5: detailContent (Details page parsing)
    print("\nTest 5: Validating detailContent...")
    test_id = search_id if search_id else "104731"
    play_url_to_test = None
    try:
        details = spider.detailContent([test_id])
        vod_list = details.get("list", [])
        if not vod_list:
            errors.append(f"detailContent: Details query for ID '{test_id}' returned no content")
        else:
            vod = vod_list[0]
            print(f" -> Successfully parsed details for ID '{test_id}':")
            print(f"    - Name: {vod.get('vod_name')}")
            print(f"    - Year: {vod.get('vod_year')}")
            print(f"    - Area: {vod.get('vod_area')}")
            print(f"    - Director: {vod.get('vod_director')}")
            print(f"    - Actor: {vod.get('vod_actor')}")
            print(f"    - Sources: {vod.get('vod_play_from')}")
            
            # Check play lists and URLs
            play_from = vod.get('vod_play_from', '')
            play_url = vod.get('vod_play_url', '')
            if not play_from or not play_url:
                errors.append("detailContent: Play sources or Play URLs are empty")
            else:
                num_sources = len(play_from.split('$$$'))
                num_urls = len(play_url.split('$$$'))
                print(f"    - Found {num_sources} play sources and {num_urls} playlists.")
                if num_sources != num_urls:
                    errors.append(f"detailContent: Sources count ({num_sources}) doesn't match Playlists count ({num_urls})")
                
                # Grab a playlist item for Test 6
                first_playlist = play_url.split('$$$')[0]
                first_episode = first_playlist.split('#')[0]
                if '$' in first_episode:
                    play_url_to_test = first_episode.split('$')[1]
                else:
                    play_url_to_test = first_episode
    except Exception as e:
        errors.append(f"detailContent failed: {e}")
        
    # Test 6: playerContent (Player details parsing)
    print("\nTest 6: Validating playerContent...")
    if play_url_to_test:
        print(f" -> Testing episode URL: {play_url_to_test}")
        try:
            player_res = spider.playerContent("", play_url_to_test, [])
            play_stream_url = player_res.get("url", "")
            parse_mode = player_res.get("parse", 1)
            if not play_stream_url:
                errors.append(f"playerContent: Returned empty stream URL for play URL '{play_url_to_test}'")
            else:
                print(f" -> Successfully resolved player URL: {play_stream_url}")
                print(f"    - Parse mode: {parse_mode}")
        except Exception as e:
            errors.append(f"playerContent failed: {e}")
    else:
        print(" -> Skipped: No test play URL resolved from details page.")
        
    print("\n" + "=" * 60)
    print("TEST REPORT SUMMARY")
    print("=" * 60)
    if errors:
        print(f"FAILED: Found {len(errors)} issues with the crawler!")
        for i, err in enumerate(errors, 1):
            print(f" {i}. {err}")
        return False
    else:
        print("ALL TESTS PASSED SUCCESSFULLY! The crawler is healthy.")
        return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
