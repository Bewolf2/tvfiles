import json
import urllib.parse
import re
from base.spider import Spider

class IkanbotSpider(Spider):
    def __init__(self):
        super().__init__()
        self.site_url = "https://www1.ikanbot.com/"
        self.vod_list_xpath = '//div[contains(@class, "v-list")]//a[contains(@class, "item")]'

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

    def clean_pic(self, pic):
        if not pic:
            return ""
        pic = pic.strip()
        if "doubanio.com" in pic:
            pic = f"{pic}@Referer=https://www.douban.com/"
        return pic

    def homeContent(self, filter):
        """
        Returns classification categories and filters for iKanBot
        """
        classes = [
            {"type_id": "movie", "type_name": "电影"},
            {"type_id": "tv", "type_name": "剧集"}
        ]
        
        filters = {
            "movie": [
                {
                    "key": "class",
                    "name": "分类",
                    "value": [
                        {"n": "热门", "v": "热门"},
                        {"n": "最新", "v": "最新"},
                        {"n": "经典", "v": "经典"},
                        {"n": "豆瓣高分", "v": "豆瓣高分"},
                        {"n": "冷门佳片", "v": "冷门佳片"},
                        {"n": "华语", "v": "华语"},
                        {"n": "欧美", "v": "欧美"},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "日本", "v": "日本"},
                        {"n": "动作", "v": "动作"},
                        {"n": "喜剧", "v": "喜剧"},
                        {"n": "爱情", "v": "爱情"},
                        {"n": "科幻", "v": "科幻"},
                        {"n": "悬疑", "v": "悬疑"},
                        {"n": "恐怖", "v": "恐怖"},
                        {"n": "文艺", "v": "文艺"},
                        {"n": "豆瓣top250", "v": "豆瓣top250"}
                    ]
                }
            ],
            "tv": [
                {
                    "key": "class",
                    "name": "分类",
                    "value": [
                        {"n": "热门", "v": "热门"},
                        {"n": "美剧", "v": "美剧"},
                        {"n": "英剧", "v": "英剧"},
                        {"n": "韩剧", "v": "韩剧"},
                        {"n": "日剧", "v": "日剧"},
                        {"n": "国产剧", "v": "国产剧"},
                        {"n": "港剧", "v": "港剧"},
                        {"n": "日本动画", "v": "日本动画"},
                        {"n": "综艺", "v": "综艺"},
                        {"n": "纪录片", "v": "纪录片"}
                    ]
                }
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
            vod_list = self.parse_card_list(tree)
            return {"list": vod_list}
        except Exception as e:
            self.log(f"Ikanbot home recommendation error: {e}")
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        """
        Fetch category list dynamically
        """
        type_str = tid
        class_str = extend.get("class", "热门")
        
        if str(pg) == "1":
            url = f"{self.site_url}hot/index-{type_str}-{class_str}.html"
        else:
            url = f"{self.site_url}hot/index-{type_str}-{class_str}-p-{pg}.html"
            
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            vod_list = self.parse_card_list(tree)
            return {
                "list": vod_list,
                "page": int(pg),
                "pagecount": 999
            }
        except Exception as e:
            self.log(f"Ikanbot category list error: {e}")
            return {"list": []}

    def parse_card_list(self, tree):
        cards = self.safe_xpath_list(tree, self.vod_list_xpath)
        vod_list = []
        for card in cards:
            title = self.safe_xpath(card, './/p/text()')
            if not title:
                title = self.safe_xpath(card, './/img/@alt')
            
            href = self.safe_xpath(card, './@href')
            if not title or not href:
                continue
            
            vod_id = href.split('/')[-1]
            pic = self.safe_xpath(card, './/img/@data-src')
            if not pic:
                pic = self.safe_xpath(card, './/img/@src')
                
            vod_list.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": self.clean_pic(pic),
                "vod_remarks": ""
            })
        return vod_list

    def detailContent(self, ids):
        """
        Fetch movie/series details and compile source playlist listings using the AJAX token API
        """
        vod_id = ids[0]
        url = f"{self.site_url}play/{vod_id}"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            # Name
            name = self.safe_xpath(tree, '//div[contains(@class, "detail")]/h2[contains(@class, "title")]/text()')
            if not name:
                name = self.safe_xpath(tree, '//h1[@id="video_title"]/text()')
            
            # Pic
            pic = self.safe_xpath(tree, '//div[contains(@class, "item-root")]/img/@data-src')
            if not pic:
                pic = self.safe_xpath(tree, '//div[contains(@class, "item-root")]/img/@src')
            pic = self.clean_pic(pic)
            
            # Desc
            desc = self.safe_xpath(tree, '//meta[@name="description"]/@content')
            
            # Metadata parsing from class="meta" h3 elements
            h3_elements = self.safe_xpath_list(tree, '//div[contains(@class, "detail")]//h3[@class="meta"]/text()')
            
            year = ""
            area = ""
            actor = ""
            director = ""
            
            for val in h3_elements:
                val = val.strip()
                if not val:
                    continue
                if re.match(r'^\d{4}$', val):
                    year = val
                elif val in ["日本", "韩国", "中国", "大陆", "香港", "台湾", "美国", "英国", "法国", "加拿大", "西班牙", "泰国", "欧洲", "海外"] or "," in val:
                    if "," in val and all(part.strip() in ["日本", "韩国", "中国", "大陆", "香港", "台湾", "美国", "英国", "法国", "加拿大", "西班牙", "泰国", "欧洲", "海外"] for part in val.split(",")):
                        area = val
                    elif "," not in val:
                        area = val
                elif "/" in val:
                    parts = val.split("/")
                    director = parts[0].strip()
                    actor = parts[1].strip()
                else:
                    if not actor:
                        actor = val
            
            # Extract configuration hidden fields
            e_token = self.safe_xpath(tree, '//input[@id="e_token"]/@value')
            mtype = self.safe_xpath(tree, '//input[@id="mtype"]/@value')
            
            play_from_list = []
            play_url_lists = []
            
            if e_token and mtype:
                # Generate decryption token for the API call
                last_four = vod_id[-4:]
                res = []
                temp_token = e_token
                for char in last_four:
                    if char.isdigit():
                        digit = int(char)
                        offset = digit % 3 + 1
                        res.append(temp_token[offset:offset+8])
                        temp_token = temp_token[offset+8:]
                token = "".join(res)
                
                # Fetch lines list
                api_url = f"{self.site_url}api/getResN?videoId={vod_id}&mtype={mtype}&token={token}"
                api_headers = self.get_headers(referer=url)
                r_api = self.fetch(api_url, headers=api_headers, verify=False)
                api_data = r_api.json()
                
                data_list = api_data.get("data", {}).get("list", [])
                for index, item in enumerate(data_list):
                    line_name = f"线路{index + 1}"
                    res_data_str = item.get("resData", "")
                    if not res_data_str:
                        continue
                    
                    try:
                        res_arr = json.loads(res_data_str)
                    except Exception:
                        continue
                    
                    for res_obj in res_arr:
                        flag = res_obj.get("flag", "")
                        url_str = res_obj.get("url", "")
                        if not url_str:
                            continue
                        
                        # Parse episode listings
                        eps = url_str.split('#')
                        ep_strs = []
                        for ep in eps:
                            ep = ep.strip()
                            if not ep:
                                continue
                            parts = ep.split('$')
                            if len(parts) >= 2:
                                ep_name = parts[0].strip()
                                ep_url = parts[1].strip()
                                if '$' in ep_url:
                                    ep_url = ep_url.split('$')[0].strip()
                                ep_strs.append(f"{ep_name}${ep_url}")
                        
                        if ep_strs:
                            display_name = f"{line_name} ({flag})" if flag else line_name
                            play_from_list.append(display_name)
                            play_url_lists.append("#".join(ep_strs))
            
            play_from = "$$$".join(play_from_list)
            play_url = "$$$".join(play_url_lists)
            
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
            self.log(f"Ikanbot details error: {e}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        """
        Execute search query
        """
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}search?q={encoded_key}"
        try:
            r = self.fetch(url, headers=self.get_headers(), verify=False)
            tree = self.html(r.content)
            
            medias = tree.xpath('//div[contains(@class, "media")]')
            vod_list = []
            for media in medias:
                title = self.safe_xpath(media, './/a[contains(@class, "title-text")]/text()')
                href = self.safe_xpath(media, './/a[contains(@class, "title-text")]/@href')
                if not title or not href:
                    continue
                
                # Clean up title and extract year
                year = ""
                match = re.search(r'\s+(\d{4})$', title)
                if match:
                    year = match.group(1)
                    title = title.replace(match.group(0), "").strip()
                
                vod_id = href.split('/')[-1]
                
                pic = self.safe_xpath(media, './/img/@data-src')
                if not pic:
                    pic = self.safe_xpath(media, './/img/@src')
                pic = self.clean_pic(pic)
                
                remarks = self.safe_xpath(media, './/span[contains(@class, "label")]/text()')
                
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            return {"list": vod_list}
        except Exception as e:
            self.log(f"Ikanbot search error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        """
        Bypasses play restrictions (direct m3u8 play)
        """
        return {
            "parse": 0,
            "url": id,
            "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        }

def Spider():
    return IkanbotSpider()
