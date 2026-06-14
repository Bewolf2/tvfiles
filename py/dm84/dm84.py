import json
import urllib.parse
import re
from base.spider import Spider

class Dm84Spider(Spider):
    def __init__(self):
        super().__init__()
        self.site_url = "https://dm84.vip/"
        self.vod_list_xpath = '//div[contains(@class, "item")]'
        self.classes = []
        self.search_path = "s--------------.html"
        self._parsed_config = False

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

    def parse_dynamic_config(self):
        """
        Dynamically parse categories and search paths from the active domain
        """
        if self._parsed_config:
            return
            
        try:
            r = self.fetch(self.site_url, headers=self.get_headers(), verify=False)
            # Update site_url if redirected
            if r.url and r.url != self.site_url:
                self.site_url = r.url
                if not self.site_url.endswith("/"):
                    self.site_url += "/"
                    
            tree = self.html(r.content)
            
            # 1. Parse categories
            nav_links = tree.xpath('//a[contains(@href, "/list-") or contains(@href, "list-") or contains(@href, "/show-") or contains(@href, "show-")]')
            parsed_classes = []
            for link in nav_links:
                href = link.get('href', '')
                name = "".join(link.xpath('.//text()')).strip()
                if not name or not href:
                    continue
                # Match /list-28.html or list-1.html or /show-28-----------.html
                match = re.search(r'(?:list|show)-(\d+)', href)
                if match:
                    tid = match.group(1)
                    # Exclude pagination numbers or non-main category IDs if name is a number
                    if name.isdigit():
                        continue
                    # Avoid duplicates and filter out empty names
                    if name and not any(c['type_id'] == tid for c in parsed_classes):
                        parsed_classes.append({"type_id": tid, "type_name": name})
            
            if parsed_classes:
                self.classes = parsed_classes
                
            # 2. Parse search form action
            form_action = self.safe_xpath(tree, '//form[contains(@action, "s-")]/@action')
            if form_action:
                self.search_path = form_action.lstrip('/')
            else:
                # Guess from links if any, e.g. /s--------------.html
                search_link = self.safe_xpath(tree, '//a[contains(@href, "s-")]/@href')
                if search_link:
                    clean_path = search_link.split('?')[0].lstrip('/')
                    clean_path = re.sub(r's-.*?(?=\.html)', lambda m: re.sub(r'[^-]', '', m.group(0)), clean_path)
                    if clean_path.startswith('s-') and clean_path.endswith('.html'):
                        self.search_path = clean_path
                    else:
                        self.search_path = "s--------------.html"
                else:
                    self.search_path = "s--------------.html"
                    
            self._parsed_config = True
        except Exception as e:
            self.log(f"Dm84 dynamic config parsing error: {e}")
            
        # Fallback if parsing failed or returned empty
        if not self.classes:
            self.classes = [
                {"type_id": "28", "type_name": "国漫"},
                {"type_id": "30", "type_name": "日漫"},
                {"type_id": "31", "type_name": "欧美动漫"},
                {"type_id": "33", "type_name": "动漫电影"}
            ]

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
        Returns Dm84 classification categories and filters
        """
        self.parse_dynamic_config()
        
        years = [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2014, -1)]
        sorts = [
            {"n": "按时间", "v": "time"},
            {"n": "按人气", "v": "hits"},
            {"n": "按评分", "v": "score"}
        ]
        genres = [{"n": "全部", "v": ""}] + [{"n": g, "v": g} for g in ["奇幻", "战斗", "玄幻", "穿越", "科幻", "武侠", "热血", "耽美", "搞笑", "冒险", "后宫", "百合", "治愈", "萝莉", "魔法", "悬疑", "推理", "游戏", "神魔", "恐怖", "机战", "战争", "犯罪", "历史", "社会", "职场", "剧情", "运动", "青春", "励志"]]
        
        filter_list = [
            {"key": "class", "name": "类型", "value": genres},
            {"key": "year", "name": "年份", "value": years},
            {"key": "by", "name": "排序", "value": sorts}
        ]
        
        filters = {}
        for c in self.classes:
            filters[c["type_id"]] = filter_list
            
        return {
            "class": self.classes,
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
                title = self.safe_xpath(card, './/a[contains(@class, "title")]/text()')
                href = self.safe_xpath(card, './/a[contains(@class, "title")]/@href')
                
                if not title or not href:
                    continue
                
                vod_id = href.split('/')[-1].replace('.html', '')
                pic = self.safe_xpath(card, './/a[contains(@class, "cover")]/@data-bg')
                if not pic:
                    pic = self.safe_xpath(card, './/a[contains(@class, "cover")]/@data-original')
                if not pic:
                    pic = self.safe_xpath(card, './/img/@src')
                
                # Format relative picture URLs
                if pic and pic.startswith("//"):
                    pic = "https:" + pic
                elif pic and pic.startswith("/"):
                    pic = self.site_url + pic.lstrip("/")
                
                remarks = self.safe_xpath(card, './/span[contains(@class, "desc")]/text()')
                
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            
            return {"list": vod_list}
        except Exception as e:
            self.log(f"Dm84 home recommendation error: {e}")
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        """
        Fetch category list dynamically using MacCMS v10 show URLs
        """
        self.parse_dynamic_config()
        
        # Build MacCMS filter URL: show-{tid}-{area}-{by}-{class}-{lang}-{letter}-{year}-{letter}-{page}-{by}.html
        # F0: tid, F2: by, F3: class, F8: pg, F11: year
        fields = [""] * 12
        fields[0] = str(tid)
        fields[2] = extend.get("by", "time")
        fields[3] = urllib.parse.quote(extend.get("class", ""))
        fields[8] = str(pg)
        fields[11] = extend.get("year", "")
        
        url = f"{self.site_url}show-{'-'.join(fields)}.html"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            cards = self.safe_xpath_list(tree, self.vod_list_xpath)
            vod_list = []
            for card in cards:
                title = self.safe_xpath(card, './/a[contains(@class, "title")]/text()')
                href = self.safe_xpath(card, './/a[contains(@class, "title")]/@href')
                if not title or not href:
                    continue
                
                vod_id = href.split('/')[-1].replace('.html', '')
                pic = self.safe_xpath(card, './/a[contains(@class, "cover")]/@data-bg')
                if not pic:
                    pic = self.safe_xpath(card, './/a[contains(@class, "cover")]/@data-original')
                if not pic:
                    pic = self.safe_xpath(card, './/img/@src')
                
                if pic and pic.startswith("//"):
                    pic = "https:" + pic
                elif pic and pic.startswith("/"):
                    pic = self.site_url + pic.lstrip("/")
                
                remarks = self.safe_xpath(card, './/span[contains(@class, "desc")]/text()')
                
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
                
            return {
                "list": vod_list,
                "page": int(pg),
                "pagecount": 999
            }
        except Exception as e:
            self.log(f"Dm84 category list error: {e}")
            return {"list": []}

    def detailContent(self, ids):
        """
        Fetch anime details and compile play source listings
        """
        vod_id = ids[0]
        url = f"{self.site_url}v/{vod_id}.html"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            name = self.safe_xpath(tree, '//h1[@class="v_title"]/a/text()')
            if not name:
                name = self.safe_xpath(tree, '//h1[contains(@class, "title")]/text()')
            if not name:
                name = self.safe_xpath(tree, '//title/text()').replace("-动漫巴士", "").strip()
            
            pic = self.safe_xpath(tree, '//div[@class="v_content"]/div[@class="cover"]/img/@src')
            if not pic:
                pic = self.safe_xpath(tree, '//meta[@property="og:image"]/@content')
            if not pic:
                pic = self.safe_xpath(tree, '//div[contains(@class, "cover")]//img/@src')
                
            if pic and pic.startswith("//"):
                pic = "https:" + pic
            elif pic and pic.startswith("/"):
                pic = self.site_url + pic.lstrip("/")

            desc = self.safe_xpath(tree, '//div[@id="intro"]//p[contains(text(), "剧情：")]/text()')
            if desc:
                desc = desc.replace("剧情：", "").strip()
            else:
                desc = self.safe_xpath(tree, '//div[@id="intro"]/p/text()')
            if not desc:
                desc = self.safe_xpath(tree, '//meta[@property="og:description"]/@content')
            
            # Extract metadata using og meta tags
            actor = self.safe_xpath(tree, '//meta[@name="og:video:actor" or @property="og:video:actor"]/@content')
            director = self.safe_xpath(tree, '//meta[@name="og:video:director" or @property="og:video:director"]/@content')
            year = self.safe_xpath(tree, '//meta[@name="og:video:release_date" or @property="og:video:release_date"]/@content')
            area = self.safe_xpath(tree, '//meta[@name="og:video:area" or @property="og:video:area"]/@content')
            
            # Extract player tabs/sources and episodes
            tab_nodes = self.safe_xpath_list(tree, '//ul[contains(@class, "play_from")]/li | //ul[contains(@class, "tab_control")]/li')
            play_lists = self.safe_xpath_list(tree, '//div[@id="play_list"]/ul[contains(@class, "play_list")] | //ul[contains(@class, "play_list")]')
            
            play_from_list = []
            play_url_lists = []
            
            for i in range(len(tab_nodes)):
                tab_name = "".join(tab_nodes[i].xpath('.//text()')).strip()
                tab_name = re.sub(r'\(.*?\)', '', tab_name).strip()  # Clean e.g. "暴风(89)" -> "暴风"
                
                if i < len(play_lists):
                    eps = play_lists[i].xpath('.//a')
                    ep_strs = []
                    for ep in eps:
                        ep_name = "".join(ep.xpath('.//text()')).strip()
                        ep_href = ep.get('href', '').strip()
                        if ep_name and ep_href:
                            ep_strs.append(f"{ep_name}${ep_href}")
                            
                    if ep_strs:
                        play_from_list.append(tab_name)
                        play_url_lists.append("#".join(ep_strs))
            
            play_from = "$$$".join(play_from_list)
            play_url = "$$$".join(play_url_lists)
            
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
            self.log(f"Dm84 details error: {e}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        """
        Search content via the HTML search page
        """
        self.parse_dynamic_config()
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}{self.search_path}?wd={encoded_key}&page={pg}"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            cards = self.safe_xpath_list(tree, self.vod_list_xpath)
            vod_list = []
            for card in cards:
                title = self.safe_xpath(card, './/a[contains(@class, "title")]/text()')
                href = self.safe_xpath(card, './/a[contains(@class, "title")]/@href')
                if not title or not href:
                    continue
                
                vod_id = href.split('/')[-1].replace('.html', '')
                pic = self.safe_xpath(card, './/a[contains(@class, "cover")]/@data-bg')
                if not pic:
                    pic = self.safe_xpath(card, './/a[contains(@class, "cover")]/@data-original')
                if not pic:
                    pic = self.safe_xpath(card, './/img/@src')
                
                if pic and pic.startswith("//"):
                    pic = "https:" + pic
                elif pic and pic.startswith("/"):
                    pic = self.site_url + pic.lstrip("/")
                
                remarks = self.safe_xpath(card, './/span[contains(@class, "desc")]/text()')
                
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            return {"list": vod_list}
        except Exception as e:
            self.log(f"Dm84 search error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        """
        Parse player page to extract the direct stream URL from iframe src
        """
        url = f"{self.site_url}{id.lstrip('/')}"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            # Extract DPlayer iframe URL
            iframe_src = self.safe_xpath(tree, '//div[contains(@class, "p_box")]/iframe/@src | //iframe[contains(@src, "/addons/dplayer/")]/@src')
            if iframe_src:
                parsed_url = urllib.parse.urlparse(iframe_src)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                video_url = query_params.get("url", [""])[0]
                
                if video_url:
                    # Sniff in WebView if it's not a direct streaming format (m3u8/mp4/flv)
                    clean_url = urllib.parse.unquote(video_url)
                    parse_mode = 0 if (".m3u8" in clean_url or ".mp4" in clean_url or ".flv" in clean_url) else 1
                    
                    return {
                        "parse": parse_mode,
                        "url": clean_url,
                        "header": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }
                    }
        except Exception as e:
            self.log(f"Dm84 player parse error: {e}")
            
        # Fallback to WebView sniffing if parsing fails
        return {
            "parse": 1,
            "url": url,
            "header": self.get_headers()
        }

def Spider():
    return Dm84Spider()
