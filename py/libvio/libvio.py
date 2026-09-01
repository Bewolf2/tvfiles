import json
import urllib.parse
import re
import base64
from base.spider import Spider

class LibvioSpider(Spider):
    def __init__(self):
        super().__init__()
        self.site_url = "https://www.libvio.cam/"  # Current default domain
        self.vod_list_xpath = '//ul[contains(@class, "vodlist")]/li'
        self.playlist_xpath = '//div[contains(@class, "playlist-panel")]'

    def init(self, extend=""):
        """
        Initialize crawler with config parameter (siteUrl override)
        """
        if extend:
            try:
                if isinstance(extend, str):
                    if extend.startswith("{") or extend.startswith("["):
                        extend = json.loads(extend)
                
                if isinstance(extend, dict) and "siteUrl" in extend:
                    self.site_url = extend["siteUrl"]
                elif isinstance(extend, str) and extend.startswith("http"):
                    self.site_url = extend
            except Exception:
                pass
        
        # Format the URL
        if not self.site_url.endswith("/"):
            self.site_url += "/"

    def get_headers(self, referer=None):
        """
        Generate HTTP headers to mimic a real web browser
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ms;q=0.7",
            "Connection": "keep-alive"
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def decode_text_payload(self, content):
        """Normalize normal HTML and Libvio's occasional JSON-wrapped HTML responses."""
        if isinstance(content, bytes):
            try:
                text = content.decode("utf-8-sig", errors="replace")
            except Exception:
                return content
        elif isinstance(content, str):
            text = content.lstrip("\ufeff")
        else:
            return content

        stripped = text.strip()
        if len(stripped) >= 2 and stripped.startswith('"') and stripped.endswith('"'):
            try:
                decoded = json.loads(stripped)
                if isinstance(decoded, str) and ("<html" in decoded.lower() or "<!doctype" in decoded.lower()):
                    text = decoded
            except Exception:
                pass
        return text

    def html(self, content):
        """
        Override parent html parser to prevent UCS4 / USC4 string-encoding parser crashes on Android
        """
        content = self.decode_text_payload(content)
        if isinstance(content, str):
            try:
                # Remove encoding declarations which cause libxml2 conflicts with Python's internal UCS4 strings
                content = re.sub(r'<\?xml[^>]*encoding=[^>]*\?>', '', content, flags=re.I)
                content = content.encode('utf-8')
            except Exception:
                pass
        return super().html(content)

    def safe_xpath(self, node, path, default=""):
        """
        Safely query an XPath that returns a single text or attribute string, preventing crashes.
        """
        try:
            elements = node.xpath(path)
            if elements:
                val = elements[0]
                if hasattr(val, 'text'):
                    return val.text.strip() if val.text else default
                return str(val).strip()
        except Exception as e:
            self.log(f"XPath Error for query '{path}': {e}")
        return default

    def safe_xpath_list(self, node, path):
        """
        Safely query an XPath that returns a list of elements.
        """
        try:
            return node.xpath(path)
        except Exception:
            return []

    def homeContent(self, filter):
        """
        Returns Libvio classification categories
        """
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "剧集"},
            {"type_id": "4", "type_name": "番剧"},
            {"type_id": "15", "type_name": "日韩"},
            {"type_id": "16", "type_name": "欧美"}
        ]
        
        # Programmatically generate filter values to keep the code compact
        years = [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2009, -1)]
        
        langs = [
            {"n": "全部", "v": ""},
            {"n": "国语", "v": "国语"},
            {"n": "英语", "v": "英语"},
            {"n": "粤语", "v": "粤语"},
            {"n": "闽南语", "v": "闽南语"},
            {"n": "韩语", "v": "韩语"},
            {"n": "日语", "v": "日语"},
            {"n": "法语", "v": "法语"},
            {"n": "德语", "v": "德语"},
            {"n": "其它", "v": "其它"}
        ]
        
        sorts = [
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"}
        ]
        
        filters = {
            "1": [
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "动作", "v": "6"},
                        {"n": "喜剧", "v": "7"},
                        {"n": "爱情", "v": "8"},
                        {"n": "科幻", "v": "9"},
                        {"n": "恐怖", "v": "10"},
                        {"n": "剧情", "v": "11"},
                        {"n": "战争", "v": "12"},
                        {"n": "动画", "v": "23"}
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in ["中国大陆", "中国香港", "中国台湾", "美国", "法国", "英国", "日本", "韩国", "德国", "泰国", "印度", "意大利", "西班牙", "加拿大", "其他"]]
                },
                {"key": "year", "name": "年份", "value": years},
                {"key": "lang", "name": "语言", "value": langs},
                {"key": "by", "name": "排序", "value": sorts}
            ],
            "2": [
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "国剧", "v": "13"},
                        {"n": "港台", "v": "14"},
                        {"n": "日韩", "v": "15"},
                        {"n": "欧美", "v": "16"},
                        {"n": "纪录片", "v": "21"},
                        {"n": "泰国剧", "v": "24"}
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in ["中国大陆", "中国台湾", "中国香港", "韩国", "日本", "美国", "泰国", "英国", "新加坡", "其他"]]
                },
                {"key": "year", "name": "年份", "value": years},
                {"key": "lang", "name": "语言", "value": langs},
                {"key": "by", "name": "排序", "value": sorts}
            ],
            "4": [
                {
                    "key": "area",
                    "name": "地区",
                    "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in ["中国", "日本", "欧美", "其他"]]
                },
                {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2003, -1)]},
                {"key": "lang", "name": "语言", "value": langs},
                {"key": "by", "name": "排序", "value": sorts}
            ],
            "15": [
                {
                    "key": "area",
                    "name": "地区",
                    "value": [{"n": "全部", "v": ""}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}]
                },
                {"key": "year", "name": "年份", "value": years},
                {"key": "lang", "name": "语言", "value": langs},
                {"key": "by", "name": "排序", "value": sorts}
            ],
            "16": [
                {
                    "key": "area",
                    "name": "地区",
                    "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in ["美国", "英国", "德国", "加拿大", "其他"]]
                },
                {"key": "year", "name": "年份", "value": years},
                {"key": "lang", "name": "语言", "value": langs},
                {"key": "by", "name": "排序", "value": sorts}
            ]
        }
        
        return {
            "class": classes,
            "filters": filters
        }

    def homeVideoContent(self):
        """
        Fetch trending recommended content from homepage
        """
        try:
            r = self.fetch(self.site_url, headers=self.get_headers(), verify=False)
            tree = self.html(r.content)
            
            cards = self.safe_xpath_list(tree, self.vod_list_xpath)
            vod_list = []
            for card in cards:
                title = self.safe_xpath(card, './/h4/a/text()')
                if not title:
                    title = self.safe_xpath(card, './/h4[contains(@class, "title")]/a/text()')
                if not title:
                    title = self.safe_xpath(card, './/a/text()')
                
                href = self.safe_xpath(card, './/a/@href')
                if not href:
                    href = self.safe_xpath(card, './/h4/a/@href')
                
                if not title or not href:
                    continue
                
                vod_id = href.split('/')[-1].replace('.html', '')
                pic = self.safe_xpath(card, './/@data-original')
                if not pic:
                    pic = self.safe_xpath(card, './/img/@src')
                
                remarks = self.safe_xpath(card, './/span[contains(@class, "pic-text")]/text()')
                if not remarks:
                    remarks = self.safe_xpath(card, './/span/text()')
                
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            
            return {"list": vod_list}
        except Exception as e:
            self.log(f"Libvio home recommendation error: {e}")
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        """
        Fetch category list dynamically using site URLs
        """
        # Determine query_tid from extend subclass filter "class"
        query_tid = extend.get("class", tid)
        if not query_tid:
            query_tid = tid
            
        # Build MacCMS filter URL: show/F1-F2-F3-F4-F5-F6-F7-F8-F9-F10-F11-F12.html
        # F1: tid, F2: area, F3: by, F5: lang, F9: pg, F12: year.
        fields = [""] * 12
        fields[0] = str(query_tid)
        fields[1] = urllib.parse.quote(extend.get("area", ""))
        fields[2] = extend.get("by", "")
        fields[4] = urllib.parse.quote(extend.get("lang", ""))
        fields[8] = str(pg)
        fields[11] = extend.get("year", "")
        
        url = f"{self.site_url}show/{'-'.join(fields)}.html"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            cards = self.safe_xpath_list(tree, self.vod_list_xpath)
            vod_list = []
            for card in cards:
                title = self.safe_xpath(card, './/h4/a/text()')
                if not title:
                    title = self.safe_xpath(card, './/a/text()')
                href = self.safe_xpath(card, './/a/@href')
                if not href:
                    href = self.safe_xpath(card, './/h4/a/@href')
                if not title or not href:
                    continue
                
                vod_id = href.split('/')[-1].replace('.html', '')
                pic = self.safe_xpath(card, './/@data-original')
                if not pic:
                    pic = self.safe_xpath(card, './/img/@src')
                
                remarks = self.safe_xpath(card, './/span[contains(@class, "pic-text")]/text()')
                if not remarks:
                    remarks = self.safe_xpath(card, './/span/text()')
                
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
                
            return {
                "list": vod_list,
                "page": pg,
                "pagecount": 999
            }
        except Exception as e:
            self.log(f"Libvio category list error: {e}")
            return {"list": []}

    def detailContent(self, ids):
        """
        Fetch movie/series details and compile source playlist listings
        """
        vod_id = ids[0]
        url = f"{self.site_url}detail/{vod_id}.html"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            name = self.safe_xpath(tree, '//h1[@class="title"]/text()')
            if not name:
                name = self.safe_xpath(tree, '//h3[contains(@class, "title")]/text()')
            
            # Robust poster parsing for the new Libvio layout
            pic = self.safe_xpath(tree, '//div[contains(@class, "vod-poster")]//img/@data-original')
            if not pic:
                pic = self.safe_xpath(tree, '//div[contains(@class, "stui-content__thumb")]//img/@data-original')
            if not pic:
                pic = self.safe_xpath(tree, '//img[@id="js-poster-img"]/@data-original')
            if not pic:
                pic = self.safe_xpath(tree, '//div[contains(@class, "thumb")]/a/img/@data-original')
            if not pic:
                pic = self.safe_xpath(tree, '//div[contains(@class, "thumb")]/a/img/@src')
            if not pic:
                pic = self.safe_xpath(tree, '//img/@data-original')
                
            desc = self.safe_xpath(tree, '//span[contains(@class, "detail-sketch")]/text()')
            if not desc:
                desc = self.safe_xpath(tree, '//span[contains(@class, "detail-content")]/text()')
            
            # Extract director and actors
            actor = self.safe_xpath(tree, '//span[contains(text(), "主演：")]/text()').replace("主演：", "").strip()
            if not actor:
                actor = self.safe_xpath(tree, '//div[@class="vod-info"]//span[contains(text(), "主演")]/text()').replace("主演：", "").strip()
                
            director = self.safe_xpath(tree, '//span[contains(text(), "导演：")]/text()').replace("导演：", "").strip()
            if not director:
                director = self.safe_xpath(tree, '//div[@class="vod-info"]//span[contains(text(), "导演")]/text()').replace("导演：", "").strip()
            
            # Extract year and area
            meta_items = self.safe_xpath_list(tree, '//div[@class="vod-info"]//span[@class="meta-item"]/text()')
            year = ""
            area = ""
            for item in meta_items:
                item_str = item.strip()
                if re.match(r'^\d{4}$', item_str):
                    year = item_str
                elif item_str in ["日本", "韩国", "中国", "大陆", "香港", "台湾", "美国", "英国", "法国", "加拿大", "西班牙", "泰国", "欧洲", "海外"]:
                    area = item_str

            # Current stui layout stores metadata directly in p.data text.
            detail_data = self.safe_xpath_list(tree, '//div[contains(@class, "stui-content__detail")]//p[contains(@class, "data")]/text()')
            for item in detail_data:
                item_str = str(item).strip()
                if not item_str:
                    continue
                if not year:
                    m = re.search(r'年份：\s*(\d{4})', item_str)
                    if m:
                        year = m.group(1)
                if not area:
                    m = re.search(r'地区：\s*([^/]+)', item_str)
                    if m:
                        area = m.group(1).strip()
                if not actor and "主演：" in item_str:
                    actor_part = item_str.split("主演：", 1)[1]
                    actor = actor_part.split(" / 导演：", 1)[0].strip()
                if not director and "导演：" in item_str:
                    director = item_str.split("导演：", 1)[1].strip()

            play_from_list = []
            play_url_lists = []

            # Current stui layout renders each source heading and playlist as siblings.
            current_playlists = self.safe_xpath_list(tree, '//ul[contains(@class, "stui-content__playlist")]')
            for playlist in current_playlists:
                tab_name = self.safe_xpath(playlist, './preceding-sibling::div[contains(@class, "stui-vodlist__head")][1]//h3/text()')
                eps = self.safe_xpath_list(playlist, './/li/a')
                ep_strs = []
                for ep in eps:
                    ep_name = self.safe_xpath(ep, './text()')
                    ep_href = self.safe_xpath(ep, './@href')
                    if ep_name and ep_href:
                        ep_strs.append(f"{ep_name.strip()}${ep_href.strip()}")
                if ep_strs:
                    play_from_list.append(tab_name.strip() if tab_name else f"线路{len(play_from_list) + 1}")
                    play_url_lists.append("#".join(ep_strs))

            # Older layouts wrapped each source in a playlist panel.
            panels = self.safe_xpath_list(tree, self.playlist_xpath)
            if not panels:
                panels = self.safe_xpath_list(tree, '//div[contains(@class, "playlist")]')

            if not play_url_lists:
                for panel in panels:
                    tab_name = self.safe_xpath(panel, './/h3/text()')
                    if not tab_name:
                        tab_name = self.safe_xpath(panel, './/h3//text()')
                    if not tab_name:
                        continue
                    eps = self.safe_xpath_list(panel, './/ul[contains(@class, "playlist")]//a')
                    if not eps:
                        eps = self.safe_xpath_list(panel, './/div[contains(@class, "netdisk-list")]/a')
                    if not eps:
                        eps = self.safe_xpath_list(panel, './/a[contains(@class, "netdisk-item")]')
                    if not eps:
                        eps = self.safe_xpath_list(panel, './/li/a')
                    if not eps:
                        eps = self.safe_xpath_list(panel, './/a')
                    ep_strs = []
                    for ep in eps:
                        ep_name = self.safe_xpath(ep, './/span[contains(@class, "name")]/text()')
                        if not ep_name:
                            ep_name = self.safe_xpath(ep, './text()')
                        ep_href = self.safe_xpath(ep, './@href')
                        if ep_name and ep_href:
                            ep_strs.append(f"{ep_name.strip()}${ep_href.strip()}")
                    if ep_strs:
                        play_from_list.append(tab_name.strip())
                        play_url_lists.append("#".join(ep_strs))
            
            play_from = "$$$".join(play_from_list)
            play_url = "$$$".join(play_url_lists)
            
            # Fallback: single play button
            if not play_url:
                play_btn_href = self.safe_xpath(tree, '//div[contains(@class, "play-btn")]/a/@href')
                if play_btn_href:
                    play_from = "立即播放"
                    play_url = f"立即播放${play_btn_href}"
                    
            if not play_from:
                play_from = "默认源"
            
            vod = {
                "vod_id": vod_id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_year": year,
                "vod_area": area,
                "vod_actor": actor,
                "vod_director": director,
                "vod_content": desc,
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }
            return {"list": [vod]}
        except Exception as e:
            self.log(f"Libvio details error: {e}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        """
        Execute search query via the AJAX suggest API for robust and fast results
        """
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}index.php/ajax/suggest?mid=1&wd={encoded_key}&limit=50"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            data = r.json()
            
            vod_list = []
            for item in data.get("list", []):
                vod_id = str(item.get("id", ""))
                vod_name = item.get("name", "")
                
                pic = item.get("pic", "")
                if pic and not pic.startswith("http"):
                    pic = self.site_url + pic.lstrip("/")
                    
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": pic,
                    "vod_remarks": ""
                })
            return {"list": vod_list}
        except Exception as e:
            self.log(f"Libvio search error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        """
        Resolve the player configuration from Libvio's play page.
        """
        url = f"{self.site_url}{id.lstrip('/')}"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            page_text = self.decode_text_payload(r.text)

            # Current pages omit the historical semicolon before </script>.
            player_json = self.regStr(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*;?\s*</script>', page_text)
            if not player_json:
                player_json = self.regStr(r'var\s+player_aaaa\s*=\s*(\{.*?\});', page_text)
            if not player_json:
                player_json = self.regStr(r'var\s+player_data\s*=\s*(\{.*?\})\s*;?\s*</script>', page_text)
            if not player_json:
                player_json = self.regStr(r'var\s+player_data\s*=\s*(\{.*?\});', page_text)

            if player_json:
                data = json.loads(player_json)
                player_url = str(data.get("url", "") or "")
                try:
                    encrypt = int(data.get("encrypt", 0) or 0)
                except Exception:
                    encrypt = 0

                # Libvio's current encrypt=3 values are opaque source tokens.
                # They are decoded by the site's source-specific ArtPlayer code,
                # so returning the token itself as a URL breaks playback.
                if encrypt == 3:
                    if re.search(r'\.(?:m3u8|mp4|flv)(?:[?#]|$)', player_url, re.I):
                        return {
                            "parse": 0,
                            "url": player_url,
                            "header": {
                                "User-Agent": self.get_headers()["User-Agent"],
                                "Referer": url
                            }
                        }
                else:
                    clean_url = player_url
                    if encrypt == 2:
                        try:
                            missing_padding = len(clean_url) % 4
                            if missing_padding:
                                clean_url += '=' * (4 - missing_padding)
                            clean_url = base64.b64decode(clean_url).decode('utf-8')
                        except Exception:
                            clean_url = ""
                    clean_url = urllib.parse.unquote(clean_url)

                    if clean_url:
                        parse_mode = 0 if re.search(r'\.(?:m3u8|mp4|flv)(?:[?#]|$)', clean_url, re.I) else 1
                        return {
                            "parse": parse_mode,
                            "url": clean_url,
                            "header": {
                                "User-Agent": self.get_headers()["User-Agent"],
                                "Referer": url
                            }
                        }
        except Exception as e:
            self.log(f"Libvio player parse error: {e}")

        # encrypt=3 and any unrecognized source are resolved in Libvio's own
        # player page; let the app's WebView sniff the final media request.
        return {
            "parse": 1,
            "url": url,
            "header": self.get_headers(referer=self.site_url)
        }

def Spider():
    return LibvioSpider()
