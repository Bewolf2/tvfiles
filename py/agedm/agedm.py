import json
import urllib.parse
import re
from base.spider import Spider

class AgedmSpider(Spider):
    def __init__(self):
        super().__init__()
        self.site_url = "https://www.agedm.io/"
        self.vod_list_xpath = '//div[contains(@class, "cata_video_item")]'

    def init(self, extend=""):
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
        
        if not self.site_url.endswith("/"):
            self.site_url += "/"

    def get_headers(self, referer=None):
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
        try:
            return node.xpath(path)
        except Exception:
            return []

    def homeContent(self, filter):
        classes = [
            {"type_id": "all", "type_name": "全部"},
            {"type_id": "TV", "type_name": "TV动画"},
            {"type_id": "剧场版", "type_name": "剧场版"},
            {"type_id": "OVA", "type_name": "OVA"}
        ]
        
        filter_list = [
            {
                "key": "region",
                "name": "地区",
                "value": [{"n": "全部", "v": "all"}, {"n": "日本", "v": "日本"}, {"n": "中国", "v": "中国"}, {"n": "欧美", "v": "欧美"}]
            },
            {
                "key": "genre",
                "name": "题材",
                "value": [{"n": "全部", "v": "all"}] + [{"n": g, "v": g} for g in ["搞笑", "运动", "励志", "热血", "战斗", "竞技", "校园", "青春", "爱情", "恋爱", "冒险", "后宫", "百合", "治愈", "萝莉", "魔法", "悬疑", "推理", "奇幻", "科幻", "游戏", "神魔", "恐怖", "血腥", "机战", "战争", "犯罪", "历史", "社会", "职场", "剧情"]]
            },
            {
                "key": "year",
                "name": "年份",
                "value": [{"n": "全部", "v": "all"}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2000, -1)] + [{"n": "2000以前", "v": "2000以前"}]
            },
            {
                "key": "season",
                "name": "季度",
                "value": [{"n": "全部", "v": "all"}, {"n": "1月", "v": "1"}, {"n": "4月", "v": "4"}, {"n": "7月", "v": "7"}, {"n": "10月", "v": "10"}]
            },
            {
                "key": "status",
                "name": "状态",
                "value": [{"n": "全部", "v": "all"}, {"n": "连载", "v": "连载"}, {"n": "完结", "v": "完结"}, {"n": "未播放", "v": "未播放"}]
            },
            {
                "key": "by",
                "name": "排序",
                "value": [{"n": "时间", "v": "time"}, {"n": "点击量", "v": "点击量"}]
            }
        ]
        
        filters = {
            "all": filter_list,
            "TV": filter_list,
            "剧场版": filter_list,
            "OVA": filter_list
        }
        
        return {
            "class": classes,
            "filters": filters
        }

    def homeVideoContent(self):
        try:
            r = self.fetch(self.site_url, headers=self.get_headers(), verify=False)
            tree = self.html(r.content)
            
            cards = self.safe_xpath_list(tree, '//div[contains(@class, "video_item")]')
            vod_list = []
            for card in cards:
                title = self.safe_xpath(card, './/div[contains(@class, "video_item-title")]/a/text()')
                href = self.safe_xpath(card, './/div[contains(@class, "video_item-title")]/a/@href')
                if not title or not href:
                    continue
                
                vod_id = href.split('/')[-1]
                pic = self.safe_xpath(card, './/div[contains(@class, "video_item--image")]//img/@data-original')
                if not pic:
                    pic = self.safe_xpath(card, './/div[contains(@class, "video_item--image")]//img/@src')
                
                remarks = self.safe_xpath(card, './/span[contains(@class, "video_play_status")]/text()')
                
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            return {"list": vod_list}
        except Exception as e:
            self.log(f"Agedm home recommendation error: {e}")
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        type_str = tid
        region_str = extend.get("region", "all")
        genre_str = extend.get("genre", "all")
        year_str = extend.get("year", "all")
        season_str = extend.get("season", "all")
        status_str = extend.get("status", "all")
        order_str = extend.get("by", "time")
        
        letter_str = "all"
        resource_str = "all"
        page_str = str(pg)
        
        parts = [urllib.parse.quote(part) for part in [
            type_str, year_str, letter_str, genre_str, resource_str,
            order_str, page_str, region_str, season_str, status_str
        ]]
        url = f"{self.site_url}catalog/{'-'.join(parts)}"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            cards = self.safe_xpath_list(tree, self.vod_list_xpath)
            vod_list = []
            for card in cards:
                title = self.safe_xpath(card, './/h5[contains(@class, "card-title")]/a/text()')
                href = self.safe_xpath(card, './/h5[contains(@class, "card-title")]/a/@href')
                if not title or not href:
                    continue
                
                vod_id = href.split('/')[-1]
                pic = self.safe_xpath(card, './/img[contains(@class, "video_thumbs")]/@data-original')
                if not pic:
                    pic = self.safe_xpath(card, './/img[contains(@class, "video_thumbs")]/@src')
                
                remarks = self.safe_xpath(card, './/span[contains(@class, "video_play_status")]/text()')
                
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
            self.log(f"Agedm category list error: {e}")
            return {"list": []}

    def detailContent(self, ids):
        vod_id = ids[0]
        url = f"{self.site_url}detail/{vod_id}"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            name = self.safe_xpath(tree, '//*[contains(@class, "video_detail_title")]/text()')
            pic = self.safe_xpath(tree, '//div[contains(@class, "video_detail_cover")]//img/@data-original')
            if not pic:
                pic = self.safe_xpath(tree, '//div[contains(@class, "video_detail_cover")]//img/@src')
            
            desc = self.safe_xpath(tree, '//div[contains(@class, "video_detail_desc")]/text()')
            
            # Loop meta items
            meta_items = self.safe_xpath_list(tree, '//ul[contains(@class, "detail_imform_list")]/li')
            year = ""
            area = ""
            actor = ""
            director = ""
            
            for item in meta_items:
                tag = self.safe_xpath(item, './span[contains(@class, "detail_imform_tag")]/text()')
                val = self.safe_xpath(item, './span[contains(@class, "detail_imform_value")]/text()')
                if not tag or not val:
                    continue
                tag = tag.strip()
                val = val.strip()
                if "地区" in tag:
                    area = val
                elif "首播时间" in tag:
                    match = re.search(r'\d{4}', val)
                    year = match.group(0) if match else val
                elif "制作公司" in tag or "开发商" in tag:
                    director = val
                elif "原作" in tag or "原案" in tag:
                    actor = val
            
            # Extract playlist tabs & panes
            tab_buttons = self.safe_xpath_list(tree, '//ul[contains(@class, "nav-pills")]/li[contains(@class, "nav-item")]/button[contains(@class, "nav-link")]')
            tab_panes = self.safe_xpath_list(tree, '//div[contains(@class, "tab-content")]/div[contains(@class, "tab-pane")]')
            
            play_from_list = []
            play_url_lists = []
            
            # Match tab button to pane
            for btn, pane in zip(tab_buttons, tab_panes):
                btn_text = "".join(btn.xpath('.//text()')).strip()
                has_vip_badge = self.safe_xpath(btn, './/span[contains(@class, "bg-danger")]/text()')
                if "vip" in btn_text.lower() or (has_vip_badge and "vip" in has_vip_badge.lower()):
                    continue
                
                ep_links = self.safe_xpath_list(pane, './/ul[contains(@class, "video_detail_episode")]/li/a')
                ep_strs = []
                for a in ep_links:
                    ep_name = "".join(a.xpath('.//text()')).strip()
                    ep_href = a.get('href', '').strip()
                    if ep_name and ep_href:
                        ep_strs.append(f"{ep_name}${ep_href}")
                        
                if ep_strs:
                    play_from_list.append(btn_text)
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
            self.log(f"Agedm details error: {e}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}search?query={encoded_key}&page={pg}"
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            cards = self.safe_xpath_list(tree, '//div[@id="cata_video_list"]//div[contains(@class, "cata_video_item")]')
            vod_list = []
            for card in cards:
                title = self.safe_xpath(card, './/h5[contains(@class, "card-title")]/a/text()')
                href = self.safe_xpath(card, './/h5[contains(@class, "card-title")]/a/@href')
                if not title or not href:
                    continue
                
                vod_id = href.split('/')[-1]
                pic = self.safe_xpath(card, './/img[contains(@class, "video_thumbs")]/@data-original')
                if not pic:
                    pic = self.safe_xpath(card, './/img[contains(@class, "video_thumbs")]/@src')
                
                remarks = self.safe_xpath(card, './/span[contains(@class, "video_play_status")]/text()')
                
                vod_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                })
            return {"list": vod_list}
        except Exception as e:
            self.log(f"Agedm search error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        url = self.site_url + id.lstrip('/')
        try:
            r = self.fetch(url, headers=self.get_headers(referer=self.site_url), verify=False)
            tree = self.html(r.content)
            
            iframe_src = self.safe_xpath(tree, '//iframe[@id="iframeForVideo"]/@src')
            if iframe_src:
                clean_url = urllib.parse.unquote(iframe_src)
                parse_mode = 0 if (".m3u8" in clean_url or ".mp4" in clean_url or ".flv" in clean_url) else 1
                return {
                    "parse": parse_mode,
                    "url": iframe_src,
                    "header": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                }
        except Exception as e:
            self.log(f"Agedm player error: {e}")
            
        return {
            "parse": 1,
            "url": url,
            "header": self.get_headers()
        }

def Spider():
    return AgedmSpider()
